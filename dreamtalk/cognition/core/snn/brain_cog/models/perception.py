# Dreamtalk - Cognition Module
# Extracted from Brain-Cog (https://github.com/BrainCog-X/Brain-Cog)
# License: MIT

import torch
from torch import nn

from dreamtalk.cognition.core.snn.brain_cog.models.neuron import IFNode, LIFNode


class VotingLayer(nn.Module):
    def __init__(self, voter_num: int):
        super().__init__()
        self.voting = nn.AvgPool1d(voter_num, voter_num)

    def forward(self, x: torch.Tensor):
        return self.voting(x.unsqueeze(1)).squeeze(1)


class WTALayer(nn.Module):
    def __init__(self, k: int = 1):
        super().__init__()
        self.k = k

    def forward(self, x: torch.Tensor):
        pos = x * torch.rand(x.shape, device=x.device)
        if self.k > 1:
            x = x * (pos >= pos.topk(self.k, dim=1)[0][:, -1:]).float()
        else:
            x = x * (pos >= pos.max(1, True)[0]).float()
        return x


class SNNConvLayer(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        stride: int = 1,
        padding: int = 1,
        neuron_type: str = "lif",
        threshold: float = 0.5,
        tau: float = 2.0,
        step: int = 8,
    ):
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel_size, stride, padding
        )
        if neuron_type == "lif":
            self.neuron = LIFNode(threshold=threshold, tau=tau, step=step)
        else:
            self.neuron = IFNode(threshold=threshold, step=step)
        self.step = step

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.shape[0]
        outputs = []
        for _ in range(self.step):
            out = self.conv(x)
            spike = self.neuron(out)
            outputs.append(spike)
        return torch.stack(outputs).mean(dim=0)


class SNNLinearLayer(nn.Module):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        neuron_type: str = "lif",
        threshold: float = 0.5,
        tau: float = 2.0,
        step: int = 8,
    ):
        super().__init__()
        self.fc = nn.Linear(in_features, out_features)
        if neuron_type == "lif":
            self.neuron = LIFNode(threshold=threshold, tau=tau, step=step)
        else:
            self.neuron = IFNode(threshold=threshold, step=step)
        self.step = step

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.shape[0]
        outputs = []
        for _ in range(self.step):
            out = self.fc(x)
            spike = self.neuron(out)
            outputs.append(spike)
        return torch.stack(outputs).mean(dim=0)


class SNNEncoder(nn.Module):
    def __init__(
        self,
        encoding: str = "poisson",
        step: int = 8,
    ):
        super().__init__()
        self.encoding = encoding
        self.step = step

    def poisson_encode(self, x: torch.Tensor) -> torch.Tensor:
        return (torch.rand_like(x) < x).float()

    def temporal_encode(self, x: torch.Tensor) -> torch.Tensor:
        spikes = torch.zeros(self.step, *x.shape, device=x.device)
        for t in range(self.step):
            spikes[t] = (x > (t / self.step)).float()
        return spikes

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.encoding == "poisson":
            return self.poisson_encode(x)
        elif self.encoding == "temporal":
            return self.temporal_encode(x)
        else:
            return x
