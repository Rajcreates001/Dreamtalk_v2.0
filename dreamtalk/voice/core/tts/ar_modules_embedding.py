# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/AR/modules/embedding.py

import math
import torch
from torch import nn


class SinePositionalEmbedding(nn.Module):
    def __init__(self, dim, base=10000, optional_trim=0):
        super().__init__()
        self.dim = dim
        self.base = base
        self.optional_trim = optional_trim

    def forward(self, x, offset=0):
        B, T, _ = x.shape
        device = x.device
        positions = torch.arange(T, device=device).unsqueeze(0).unsqueeze(-1) + offset
        dims = torch.arange(self.dim // 2, device=device).unsqueeze(0).unsqueeze(0)
        angles = self.base ** (-2 * dims / self.dim)
        angles = positions * angles
        sin = torch.sin(angles)
        cos = torch.cos(angles)
        pos_enc = torch.cat([sin, cos], dim=-1).float()
        pos_enc = pos_enc[:, :, self.optional_trim:]
        return x + pos_enc.to(x.device)


class TokenEmbedding(nn.Module):
    def __init__(self, dim, vocab_size):
        super().__init__()
        self.dim = dim
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, dim)

    def forward(self, x):
        return self.embedding(x)
