# Dreamtalk - Voice Engine
# Extracted from Fish Speech (DAC VQ-GAN codec)

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from torch.nn.utils.parametrizations import weight_norm
from torch.nn.utils.parametrize import remove_parametrizations


@dataclass
class VQResult:
    z: torch.Tensor
    codes: torch.Tensor
    latents: torch.Tensor
    codebook_loss: torch.Tensor
    commitment_loss: torch.Tensor


def find_multiple(n: int, k: int) -> int:
    if n % k == 0:
        return n
    return n + k - (n % k)


@dataclass
class ModelArgs:
    block_size: int = 2048
    n_layer: int = 8
    n_head: int = 8
    dim: int = 512
    intermediate_size: int = 1536
    n_local_heads: int = -1
    head_dim: int = 64
    rope_base: float = 10000
    norm_eps: float = 1e-5
    dropout_rate: float = 0.1
    channels_first: bool = True
    pos_embed_type: str = "rope"
    max_relative_position: int = 128
    window_size: int = 512

    def __post_init__(self):
        if self.n_local_heads == -1:
            self.n_local_heads = self.n_head
        if self.intermediate_size is None:
            hidden_dim = 4 * self.dim
            n_hidden = int(2 * hidden_dim / 3)
            self.intermediate_size = find_multiple(n_hidden, 256)


class Snake1d(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.alpha = nn.Parameter(torch.ones(1, channels, 1))

    def forward(self, x):
        return x + (self.alpha + 1e-9).reciprocal() * (torch.sin(self.alpha * x)).pow(2)


class WNConv1d(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.conv = weight_norm(nn.Conv1d(*args, **kwargs))

    def forward(self, x):
        return self.conv(x)


class WNConvTranspose1d(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.conv = weight_norm(nn.ConvTranspose1d(*args, **kwargs))

    def forward(self, x):
        return self.conv(x)


class ResidualUnit(nn.Module):
    def __init__(self, in_channels, out_channels, dilation):
        super().__init__()
        self.dilation = dilation
        self.layers = nn.Sequential(
            Snake1d(in_channels),
            WNConv1d(in_channels, out_channels, 3, padding=dilation, dilation=dilation),
            Snake1d(out_channels),
            WNConv1d(out_channels, out_channels, 1),
        )

    def forward(self, x):
        return x + self.layers(x)


class EncoderBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride, dilations=1):
        super().__init__()
        if dilations == 1:
            dilations = [1, 3, 9]
        self.residuals = nn.Sequential(*[
            ResidualUnit(in_channels, in_channels, d) for d in dilations
        ])
        self.proj = WNConv1d(in_channels, out_channels, 2 * stride, stride=stride, padding=stride // 2)

    def forward(self, x):
        return self.proj(self.residuals(x))


class DecoderBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride, dilations=1):
        super().__init__()
        if dilations == 1:
            dilations = [1, 3, 9]
        self.residuals = nn.Sequential(*[
            ResidualUnit(in_channels, in_channels, d) for d in dilations
        ])
        self.proj = WNConvTranspose1d(in_channels, out_channels, 2 * stride, stride=stride, padding=stride // 2)

    def forward(self, x):
        return self.proj(self.residuals(x))


class Encoder(nn.Module):
    def __init__(self, input_channels=1, channels=[32, 64, 128, 256], strides=[2, 4, 8, 8]):
        super().__init__()
        self.first = WNConv1d(input_channels, channels[0], 7, padding=3)
        self.blocks = nn.ModuleList([
            EncoderBlock(channels[i], channels[i + 1], strides[i])
            for i in range(len(strides))
        ])

    def forward(self, x):
        x = self.first(x)
        for block in self.blocks:
            x = block(x)
        return x


class Decoder(nn.Module):
    def __init__(self, input_channels=256, channels=[128, 64, 32, 1], strides=[8, 8, 4, 2]):
        super().__init__()
        channels = [input_channels] + channels
        self.blocks = nn.ModuleList([
            DecoderBlock(channels[i], channels[i + 1], strides[i])
            for i in range(len(strides))
        ])
        self.last = WNConv1d(channels[-1], 1, 7, padding=3)

    def forward(self, x):
        for block in self.blocks:
            x = block(x)
        return self.last(x)


class VectorQuantizer(nn.Module):
    def __init__(self, dim, codebook_size, codebook_dim=None, commitment=0.005):
        super().__init__()
        self.dim = dim
        self.codebook_size = codebook_size
        self.codebook_dim = codebook_dim or dim
        self.commitment = commitment
        self.codebook = nn.Embedding(codebook_size, self.codebook_dim)
        self.in_proj = nn.Linear(dim, self.codebook_dim) if dim != self.codebook_dim else nn.Identity()
        self.out_proj = nn.Linear(self.codebook_dim, dim) if dim != self.codebook_dim else nn.Identity()

    def forward(self, z):
        z_e = self.in_proj(z)
        z_e_flat = z_e.view(-1, self.codebook_dim)
        codebook = self.codebook.weight
        d = torch.cdist(z_e_flat, codebook)
        min_encoding_indices = torch.argmin(d, dim=-1)
        z_q = self.codebook(min_encoding_indices).view(z_e.shape)
        z_q = self.out_proj(z_q)
        codebook_loss = F.mse_loss(z_q.detach(), z_e)
        commitment_loss = F.mse_loss(z_q, z_e.detach())
        z_q = z_e + (z_q - z_e).detach()
        return VQResult(
            z=z_q,
            codes=min_encoding_indices.view(*z.shape[:-1]),
            latents=z_e,
            codebook_loss=codebook_loss,
            commitment_loss=commitment_loss,
        )


class ResidualVectorQuantizer(nn.Module):
    def __init__(self, dim, codebook_size, num_quantizers, codebook_dim=None, commitment=0.005):
        super().__init__()
        self.quantizers = nn.ModuleList([
            VectorQuantizer(dim, codebook_size, codebook_dim, commitment)
            for _ in range(num_quantizers)
        ])

    def forward(self, z):
        codes = []
        residual = z
        codebook_loss = 0
        commitment_loss = 0
        for q in self.quantizers:
            result = q(residual)
            residual = residual - result.z
            codes.append(result.codes)
            codebook_loss += result.codebook_loss
            commitment_loss += result.commitment_loss
        z_q = z - residual
        return VQResult(
            z=z_q,
            codes=torch.stack(codes, dim=-1),
            latents=z,
            codebook_loss=codebook_loss,
            commitment_loss=commitment_loss,
        )

    def from_codes(self, codes):
        z_q = 0
        for i, q in enumerate(self.quantizers):
            z_q = z_q + q.codebook(codes[..., i])
        return z_q


class DAC(nn.Module):
    def __init__(
        self,
        encoder_channels=[32, 64, 128, 256],
        encoder_strides=[2, 4, 8, 8],
        decoder_channels=[128, 64, 32, 1],
        decoder_strides=[8, 8, 4, 2],
        latent_dim=256,
        codebook_size=1024,
        num_quantizers=4,
        sample_rate=44100,
    ):
        super().__init__()
        self.sample_rate = sample_rate
        self.encoder = Encoder(1, encoder_channels, encoder_strides)
        self.decoder = Decoder(latent_dim, decoder_channels, decoder_strides)
        self.quantizer = ResidualVectorQuantizer(latent_dim, codebook_size, num_quantizers)

    def encode(self, audio, audio_lengths=None):
        z = self.encoder(audio)
        result = self.quantizer(z)
        return result.codes, result.z

    def decode(self, codes):
        z_q = self.quantizer.from_codes(codes)
        return self.decoder(z_q)

    def from_indices(self, codes):
        z_q = self.quantizer.from_codes(codes)
        return self.decoder(z_q)
