# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Source: GPT_SoVITS/module/quantize.py

from dataclasses import dataclass, field
import typing as tp
import torch
from torch import nn
from .core_vq import ResidualVectorQuantization


@dataclass
class QuantizedResult:
    quantized: torch.Tensor
    codes: torch.Tensor
    bandwidth: torch.Tensor
    penalty: tp.Optional[torch.Tensor] = None
    metrics: dict = field(default_factory=dict)


class ResidualVectorQuantizer(nn.Module):
    def __init__(
        self,
        dimension: int = 256,
        n_q: int = 8,
        bins: int = 1024,
        decay: float = 0.99,
        kmeans_init: bool = True,
        kmeans_iters: int = 50,
        threshold_ema_dead_code: int = 2,
    ):
        super().__init__()
        self.n_q = n_q
        self.dimension = dimension
        self.bins = bins
        self.decay = decay
        self.kmeans_init = kmeans_init
        self.kmeans_iters = kmeans_iters
        self.threshold_ema_dead_code = threshold_ema_dead_code
        self.vq = ResidualVectorQuantization(
            dim=self.dimension,
            n_q=self.n_q,
            bins=self.bins,
            decay=self.decay,
            kmeans_init=self.kmeans_init,
            kmeans_iters=self.kmeans_iters,
            threshold_ema_dead_code=self.threshold_ema_dead_code,
        )

    def forward(self, x, n_q=None, layers=None):
        quantized, codes, commit_loss = self.vq(x, n_q=n_q, layers=layers)
        return quantized, codes, commit_loss

    def encode(self, x, n_q=None, layers=None):
        return self.vq.encode(x, n_q=n_q, layers=layers)

    def decode(self, q_indices):
        return self.vq.decode(q_indices)
