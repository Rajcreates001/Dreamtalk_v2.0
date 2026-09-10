# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/AR/modules/scaling.py

import torch
from torch import nn


class BalancedDoubleSwish(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.channels = channels
        self.a = nn.Parameter(torch.zeros(1, channels))
        self.b = nn.Parameter(torch.ones(1, channels))

    def forward(self, x):
        return self.b * x * torch.sigmoid(self.a * x)
