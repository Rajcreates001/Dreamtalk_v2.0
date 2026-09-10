# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Source: GPT_SoVITS/module/core_vq.py

import torch
from torch import nn
from torch import Tensor
import torch.nn.functional as F
from einops import rearrange, repeat
from typing import Optional


class ResidualVectorQuantization(nn.Module):
    def __init__(self, dimension, n_q, bins, decay, kmeans_init, kmeans_iters, threshold_ema_dead_code):
        super().__init__()
        self.quantizers = nn.ModuleList([
            VectorQuantization(dimension, bins, decay, kmeans_init, kmeans_iters, threshold_ema_dead_code)
            for _ in range(n_q)
        ])

    def forward(self, x, n_q=None, layers=None):
        if layers is not None:
            n_q = len(layers)
        elif n_q is None:
            n_q = len(self.quantizers)
        quantized_out = 0
        residual = x
        all_losses = []
        all_indices = []
        for i, quantizer in enumerate(self.quantizers[:n_q]):
            quantized, indices, loss = quantizer(residual)
            residual = residual - quantized
            quantized_out = quantized_out + quantized
            all_indices.append(indices)
            all_losses.append(loss)
        out_losses = torch.stack(all_losses)
        out_indices = torch.stack(all_indices)
        return quantized_out, out_indices, out_losses

    def encode(self, x, n_q=None, layers=None):
        if layers is not None:
            n_q = len(layers)
        elif n_q is None:
            n_q = len(self.quantizers)
        residual = x
        all_indices = []
        for i, quantizer in enumerate(self.quantizers[:n_q]):
            quantized, indices, loss = quantizer(residual)
            residual = residual - quantized
            all_indices.append(indices)
        out_indices = torch.stack(all_indices)
        return out_indices

    def decode(self, q_indices):
        quantized_out = 0
        for i, quantizer in enumerate(self.quantizers):
            quantized = quantizer.decode(q_indices[i])
            quantized_out = quantized_out + quantized
        return quantized_out


class VectorQuantization(nn.Module):
    def __init__(self, dimension, bins, decay, kmeans_init, kmeans_iters, threshold_ema_dead_code):
        super().__init__()
        self.dimension = dimension
        self.bins = bins
        self.decay = decay
        self.eps = 1e-5
        self.threshold_ema_dead_code = threshold_ema_dead_code
        if kmeans_init:
            self.init = None
        else:
            self.init = True
        self.kmeans_iters = kmeans_iters
        self.kmeans_init = kmeans_init

        self.register_buffer("inited", torch.Tensor([0]))
        self.register_buffer("cluster_size", torch.zeros(bins))
        self.register_buffer("embed_avg", torch.zeros(bins, dimension))
        self.register_buffer("embedding", torch.randn(bins, dimension))

    def forward(self, x):
        inited = self.inited.item()
        if not inited and self.kmeans_init:
            self._kmeans_init(x)

        flat_x = rearrange(x, "b ... d -> (...) d")
        embedding = self.embedding.t()
        distance = -(flat_x.pow(2).sum(1, keepdim=True) - 2 * flat_x @ embedding + embedding.pow(2).sum(0, keepdim=True))
        indices = distance.max(1).indices

        quantized = F.embedding(indices, self.embedding)
        quantized = rearrange(quantized, "... d -> b ... d", b=x.shape[0])

        if self.training:
            if not inited:
                self._tile_with_noise(x)
            else:
                self._ema_update(x, indices, embedding)

        loss = F.mse_loss(quantized.detach(), x)
        quantized = x + (quantized - x).detach()
        return quantized, indices, loss

    def _kmeans_init(self, x):
        bins = self.bins
        dtype = x.dtype
        device = x.device
        flat_x = rearrange(x, "b ... d -> (...) d")
        x_init = flat_x[np.random.choice(flat_x.shape[0], bins, replace=False)]
        embedding = x_init
        for _ in range(self.kmeans_iters):
            distance = torch.cdist(flat_x, embedding)
            labels = distance.min(1).indices
            for i in range(bins):
                idx = labels == i
                if idx.sum() > 0:
                    embedding[i] = flat_x[idx].mean(0)
        self.embedding.data.copy_(embedding)

    def _tile_with_noise(self, x):
        flat_x = rearrange(x, "b ... d -> (...) d")
        embedding = self.embedding
        embedding = repeat(embedding, "... -> tile ...", tile=3)
        embedding = embedding + torch.randn_like(embedding) * 0.01
        self.embedding.data.copy_(embedding[: self.bins])

    def _ema_update(self, x, indices, embedding):
        bins = self.bins
        flat_x = rearrange(x, "b ... d -> (...) d")
        n_local_cluster = torch.zeros(bins, device=x.device)
        one_hot = F.one_hot(indices, bins).to(dtype=flat_x.dtype)
        n_local_cluster.scatter_add_(0, indices, torch.ones_like(indices, dtype=flat_x.dtype))

        embed_sum = torch.zeros(bins, flat_x.shape[-1], device=x.device)
        embed_sum.index_add_(0, indices, flat_x)

        self.cluster_size.data.mul_(self.decay).add_(n_local_cluster, alpha=1 - self.decay)
        self.embed_avg.data.mul_(self.decay).add_(embed_sum, alpha=1 - self.decay)

        n = self.cluster_size.sum()
        cluster_size = (self.cluster_size + self.eps) / (n + bins * self.eps) * n
        embed_normalized = self.embed_avg / cluster_size.unsqueeze(1)
        self.embedding.data.copy_(embed_normalized)

        dead = self.cluster_size < self.threshold_ema_dead_code
        if dead.sum() > 0:
            mask = dead.float().unsqueeze(1).expand_as(self.embedding)
            noise = torch.randn_like(self.embedding) * 0.01
            self.embedding.data.mul_(1 - mask).add_(mask * noise)

    def decode(self, q_indices):
        indices = q_indices
        quantized = F.embedding(indices, self.embedding)
        quantized = rearrange(quantized, "... d -> b ... d", b=1)
        return quantized
