# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Copyright (c) 2024 NVIDIA CORPORATION.
# Source: GPT_SoVITS/BigVGAN/activations.py

import torch
import torch.nn as nn
from torch.nn import functional as F


class Snake(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.alpha = nn.Parameter(torch.ones(1, channels, 1))

    def forward(self, x):
        return x + (self.alpha + 1e-9).reciprocal() * (self.alpha * x).sin().pow(2)


class SnakeBeta(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.alpha = nn.Parameter(torch.ones(1, channels, 1))
        self.beta = nn.Parameter(torch.ones(1, channels, 1))

    def forward(self, x):
        return x + (self.beta + 1e-9).reciprocal() * (self.alpha * x).sin().pow(2)
