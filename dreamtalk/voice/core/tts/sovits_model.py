# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/module/models.py

import warnings
warnings.filterwarnings("ignore")
import math
import torch
from torch import nn
from torch.nn import functional as F
from . import commons
from . import modules as modules_mod
from . import attentions
from torch.nn import Conv1d, ConvTranspose1d, Conv2d
from torch.nn.utils import weight_norm, remove_weight_norm, spectral_norm
from .commons import init_weights, get_padding
from .mrte_model import MRTE
from .quantize import ResidualVectorQuantizer
from . import symbols as symbols_v1
from . import symbols2 as symbols_v2
from torch.cuda.amp import autocast
import contextlib
import random


class StochasticDurationPredictor(nn.Module):
    def __init__(self, in_channels, filter_channels, kernel_size, p_dropout, n_flows=4, gin_channels=0):
        super().__init__()
        filter_channels = in_channels
        self.in_channels = in_channels
        self.filter_channels = filter_channels
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.n_flows = n_flows
        self.gin_channels = gin_channels
        self.log_flow = modules_mod.Log()
        self.flows = nn.ModuleList()
        self.flows.append(modules_mod.ElementwiseAffine(2))
        for i in range(n_flows):
            self.flows.append(modules_mod.ConvFlow(2, filter_channels, kernel_size, n_layers=3))
            self.flows.append(modules_mod.Flip())
        self.post_pre = nn.Conv1d(1, filter_channels, 1)
        self.post_proj = nn.Conv1d(filter_channels, filter_channels, 1)
        self.post_convs = modules_mod.DDSConv(filter_channels, kernel_size, n_layers=3, p_dropout=p_dropout)
        self.post_flows = nn.ModuleList()
        self.post_flows.append(modules_mod.ElementwiseAffine(2))
        for i in range(4):
            self.post_flows.append(modules_mod.ConvFlow(2, filter_channels, kernel_size, n_layers=3))
            self.post_flows.append(modules_mod.Flip())
        self.pre = nn.Conv1d(in_channels, filter_channels, 1)
        self.proj = nn.Conv1d(filter_channels, filter_channels, 1)
        self.convs = modules_mod.DDSConv(filter_channels, kernel_size, n_layers=3, p_dropout=p_dropout)
        if gin_channels != 0:
            self.cond = nn.Conv1d(gin_channels, filter_channels, 1)

    def forward(self, x, x_mask, w=None, g=None, reverse=False, noise_scale=1.0):
        x = torch.detach(x)
        x = self.pre(x)
        if g is not None:
            g = torch.detach(g)
            x = x + self.cond(g)
        x = self.convs(x, x_mask)
        x = self.proj(x) * x_mask
        if not reverse:
            flows = self.flows
            assert w is not None
            logdet_tot_q = 0
            h_w = self.post_pre(w)
            h_w = self.post_convs(h_w, x_mask)
            h_w = self.post_proj(h_w) * x_mask
            e_q = torch.randn(w.size(0), 2, w.size(2)).to(device=x.device, dtype=x.dtype) * x_mask
            z_q = e_q
            for flow in self.post_flows:
                z_q, logdet_q = flow(z_q, x_mask, g=(x + h_w))
                logdet_tot_q += logdet_q
            z_u, z1 = torch.split(z_q, [1, 1], 1)
            u = torch.sigmoid(z_u) * x_mask
            z0 = (w - u) * x_mask
            logdet_tot_q += torch.sum((F.logsigmoid(z_u) + F.logsigmoid(-z_u)) * x_mask, [1, 2])
            logq = torch.sum(-0.5 * (math.log(2 * math.pi) + (e_q ** 2)) * x_mask, [1, 2]) - logdet_tot_q
            logdet_tot = 0
            z0, logdet = self.log_flow(z0, x_mask)
            logdet_tot += logdet
            z = torch.cat([z0, z1], 1)
            for flow in flows:
                z, logdet = flow(z, x_mask, g=(x + h_w), reverse=reverse)
                logdet_tot = logdet_tot + logdet
            nll = torch.sum(0.5 * (math.log(2 * math.pi) + (z ** 2)) * x_mask, [1, 2]) - logdet_tot
            return nll + logq
        else:
            flows = list(reversed(self.flows))
            flows = flows[:-2] + [flows[-1]]
            z = torch.randn(x.size(0), 2, x.size(2)).to(device=x.device, dtype=x.dtype) * noise_scale
            for flow in flows:
                z = flow(z, x_mask, g=(x + self.proj(x)), reverse=reverse)
            z0, z1 = torch.split(z, [1, 1], 1)
            logw = z0
            return logw


class DurationPredictor(nn.Module):
    def __init__(self, in_channels, filter_channels, kernel_size, p_dropout, gin_channels=0):
        super().__init__()
        self.in_channels = in_channels
        self.filter_channels = filter_channels
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.gin_channels = gin_channels
        self.drop = nn.Dropout(p_dropout)
        self.conv_1 = nn.Sequential(
            nn.Conv1d(in_channels, filter_channels, kernel_size, padding=kernel_size // 2),
            nn.LayerNorm(filter_channels),
            nn.ReLU(),
            nn.Dropout(p_dropout),
        )
        self.conv_2 = nn.Sequential(
            nn.Conv1d(filter_channels, filter_channels, kernel_size, padding=kernel_size // 2),
            nn.LayerNorm(filter_channels),
            nn.ReLU(),
            nn.Dropout(p_dropout),
        )
        self.proj = nn.Conv1d(filter_channels, 1, 1)
        if gin_channels != 0:
            self.cond = nn.Conv1d(gin_channels, in_channels, 1)

    def forward(self, x, x_mask, g=None):
        x = x.detach()
        if g is not None:
            g = g.detach()
            x = x + self.cond(g)
        x = self.conv_1(x * x_mask)
        x = self.conv_2(x * x_mask)
        x = self.proj(x * x_mask)
        return x * x_mask


class TextEncoder(nn.Module):
    def __init__(self, out_channels, hidden_channels, filter_channels, n_heads, n_layers, kernel_size, p_dropout, gin_channels=0):
        super().__init__()
        self.out_channels = out_channels
        self.hidden_channels = hidden_channels
        self.filter_channels = filter_channels
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.gin_channels = gin_channels
        self.encoder = attentions.Encoder(hidden_channels, filter_channels, n_heads, n_layers, kernel_size, p_dropout)
        self.proj = nn.Conv1d(hidden_channels, out_channels * 2, 1)
        if gin_channels != 0:
            self.cond = nn.Conv1d(gin_channels, hidden_channels, 1)

    def forward(self, x, x_mask, g=None):
        x = x * x_mask
        if g is not None:
            g = g.detach()
            x = x + self.cond(g)
        x = self.encoder(x * x_mask, x_mask)
        stats = self.proj(x) * x_mask
        m, logs = torch.split(stats, self.out_channels, 1)
        return x, m, logs


class ResidualCouplingBlock(nn.Module):
    def __init__(self, channels, hidden_channels, kernel_size, dilation_rate, n_layers, n_flows=4, gin_channels=0):
        super().__init__()
        self.channels = channels
        self.hidden_channels = hidden_channels
        self.kernel_size = kernel_size
        self.dilation_rate = dilation_rate
        self.n_layers = n_layers
        self.n_flows = n_flows
        self.gin_channels = gin_channels
        self.flows = nn.ModuleList()
        for i in range(n_flows):
            self.flows.append(modules_mod.ResidualCouplingLayer(channels, hidden_channels, kernel_size, dilation_rate, n_layers, gin_channels=gin_channels, mean_only=True))
            self.flows.append(modules_mod.Flip())

    def forward(self, x, x_mask, g=None, reverse=False):
        if not reverse:
            for flow in self.flows:
                x, _ = flow(x, x_mask, g=g, reverse=reverse)
        else:
            for flow in reversed(self.flows):
                x = flow(x, x_mask, g=g, reverse=reverse)
        return x


class SynthesizerTrn(nn.Module):
    def __init__(self, n_vocab, spec_channels, segment_size, inter_channels, hidden_channels, filter_channels, n_heads, n_layers, kernel_size, p_dropout, resblock, resblock_kernel_sizes, resblock_dilation_sizes, upsample_rates, upsample_initial_channel, upsample_kernel_sizes, n_speakers=0, gin_channels=0, use_sdp=True, semantic_frame_rate=None, **kwargs):
        super().__init__()
        self.n_vocab = n_vocab
        self.spec_channels = spec_channels
        self.inter_channels = inter_channels
        self.hidden_channels = hidden_channels
        self.filter_channels = filter_channels
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.resblock = resblock
        self.resblock_kernel_sizes = resblock_kernel_sizes
        self.resblock_dilation_sizes = resblock_dilation_sizes
        self.upsample_rates = upsample_rates
        self.upsample_initial_channel = upsample_initial_channel
        self.upsample_kernel_sizes = upsample_kernel_sizes
        self.n_speakers = n_speakers
        self.gin_channels = gin_channels
        self.use_sdp = use_sdp
        self.semantic_frame_rate = semantic_frame_rate
        self.enc_p = TextEncoder(inter_channels, hidden_channels, filter_channels, n_heads, n_layers, kernel_size, p_dropout)
        self.dec = modules_mod.Generator(inter_channels, resblock, resblock_kernel_sizes, resblock_dilation_sizes, upsample_rates, upsample_initial_channel, upsample_kernel_sizes, gin_channels=gin_channels)
        self.enc_q = nn.Conv1d(spec_channels, inter_channels, 5, 1, padding=2)
        self.flow = ResidualCouplingBlock(inter_channels, hidden_channels, 5, 1, 4, gin_channels=gin_channels)
        if n_speakers > 0:
            self.emb_g = nn.Embedding(n_speakers, gin_channels)

    def forward(self, x, x_lengths, y, y_lengths, g=None, bert=None, text_bert=None):
        x_mask = torch.unsqueeze(commons.sequence_mask(x_lengths, x.size(2)), 1).to(x.dtype)
        y_mask = torch.unsqueeze(commons.sequence_mask(y_lengths, y.size(2)), 1).to(y.dtype)
        x = self.enc_p(x, x_mask)
        z, m_q, logs_q, y_mask = self.enc_q(y, y_mask, g=g)
        z_p = self.flow(z, y_mask, g=g)
        return z_p, m_q, logs_q, y_mask, x_mask

    def decode(self, z, phonemes, refer_audio_spec, speed=1.0, sv_emb=None):
        z = z.to(next(self.parameters()).device)
        phonemes = phonemes.to(next(self.parameters()).device)
        audio = self.dec(z)
        return audio

    def extract_latent(self, hubert_feature):
        z = self.enc_q(hubert_feature)
        return z

    def decode_encp(self, z, phonemes, refer_audio_spec, g=None, speed=1.0):
        z = self.dec(z)
        return z, None

    def vq2emb(self, vq_code):
        return vq_code


class SynthesizerTrnV3(nn.Module):
    def __init__(self, n_vocab, spec_channels, segment_size, inter_channels, hidden_channels, filter_channels, n_heads, n_layers, kernel_size, p_dropout, resblock, resblock_kernel_sizes, resblock_dilation_sizes, upsample_rates, upsample_initial_channel, upsample_kernel_sizes, n_speakers=0, gin_channels=0, use_sdp=True, semantic_frame_rate=None, version="v3", **kwargs):
        super().__init__()
        self.n_vocab = n_vocab
        self.spec_channels = spec_channels
        self.inter_channels = inter_channels
        self.hidden_channels = hidden_channels
        self.filter_channels = filter_channels
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.resblock = resblock
        self.resblock_kernel_sizes = resblock_kernel_sizes
        self.resblock_dilation_sizes = resblock_dilation_sizes
        self.upsample_rates = upsample_rates
        self.upsample_initial_channel = upsample_initial_channel
        self.upsample_kernel_sizes = upsample_kernel_sizes
        self.n_speakers = n_speakers
        self.gin_channels = gin_channels
        self.use_sdp = use_sdp
        self.semantic_frame_rate = semantic_frame_rate
        self.version = version
        self.enc_p = TextEncoder(inter_channels, hidden_channels, filter_channels, n_heads, n_layers, kernel_size, p_dropout)
        self.enc_q = nn.Conv1d(spec_channels, inter_channels, 5, 1, padding=2)
        if version == "v4":
            self.dec = modules_mod.Generator(inter_channels, resblock, resblock_kernel_sizes, resblock_dilation_sizes, upsample_rates, upsample_initial_channel, upsample_kernel_sizes)
        else:
            self.dec = None
        self.mrte = MRTE()
        self.flow = ResidualCouplingBlock(inter_channels, hidden_channels, 5, 1, 4)
        self.cfm = None

    def forward(self, x, x_lengths, y, y_lengths, g=None, bert=None, text_bert=None):
        return None, None, None, None, None

    def extract_latent(self, hubert_feature):
        z = self.enc_q(hubert_feature)
        return z

    def decode(self, z, phonemes, refer_audio_spec, speed=1.0, sv_emb=None):
        z = z.to(next(self.parameters()).device)
        phonemes = phonemes.to(next(self.parameters()).device)
        if self.dec is not None:
            audio = self.dec(z)
        else:
            audio = z
        return audio

    def decode_encp(self, semantic_tokens, phones, refer_audio_spec, g=None, speed=1.0):
        z, _ = self.decode(semantic_tokens, phones, refer_audio_spec, speed)
        return z, g

    def decode_streaming(self, semantic_tokens, phones, refer_audio_spec, speed=1.0, sv_emb=None, result_length=None, overlap_frames=None, padding_length=0):
        result = self.decode(semantic_tokens, phones, refer_audio_spec, speed)
        latent = semantic_tokens
        latent_mask = None
        return result, latent, latent_mask

    def vq2emb(self, vq_code):
        return vq_code


class Generator(modules_mod.Generator):
    pass
