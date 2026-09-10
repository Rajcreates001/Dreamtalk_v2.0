# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Copyright (c) 2024 NVIDIA CORPORATION.
# Source: GPT_SoVITS/BigVGAN/alias_free_activation/torch/act.py

import torch
import torch.nn as nn


class Activation1d(nn.Module):
    def __init__(self, channels, up_ratio=2, down_ratio=2, kernel_size=3):
        super().__init__()
        self.up_ratio = up_ratio
        self.down_ratio = down_ratio
        self.act = Snake(channels)
        self.conv1 = nn.Conv1d(channels, channels, kernel_size, stride=1, padding=kernel_size // 2)
        self.conv2 = nn.Conv1d(channels, channels, kernel_size, stride=1, padding=kernel_size // 2)

    def forward(self, x):
        x = self.act(x)
        return x


class Snake(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.alpha = nn.Parameter(torch.ones(1, channels, 1))

    def forward(self, x):
        return x + (self.alpha + 1e-9).reciprocal() * (self.alpha * x).sin().pow(2)
