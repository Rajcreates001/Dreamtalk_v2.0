# Dreamtalk - Cognition Module
# Extracted from Brain-Cog (https://github.com/BrainCog-X/Brain-Cog)
# License: MIT

import torch
from typing import Any

from dreamtalk.cognition.core.snn.brain_cog.config import BrainCogConfig
from dreamtalk.cognition.core.snn.brain_cog.models.neuron import IFNode, LIFNode
from dreamtalk.cognition.core.snn.brain_cog.models.perception import (
    SNNConvLayer,
    SNNLinearLayer,
    SNNEncoder,
)


class SNNInferenceEngine:
    def __init__(self, config: BrainCogConfig | None = None):
        self.config = config or BrainCogConfig()
        self.device = torch.device(self.config.device)
        self._networks: dict[str, torch.nn.Module] = {}

    def build_encoder(self, encoding: str | None = None) -> SNNEncoder:
        return SNNEncoder(
            encoding=encoding or self.config.encoder_type,
            step=self.config.step,
        ).to(self.device)

    def build_classifier(
        self,
        input_size: int,
        hidden_size: int,
        num_classes: int,
    ) -> torch.nn.Module:
        return torch.nn.Sequential(
            SNNLinearLayer(
                input_size, hidden_size,
                neuron_type="lif",
                threshold=self.config.threshold,
                tau=self.config.tau,
                step=self.config.step,
            ),
            SNNLinearLayer(
                hidden_size, num_classes,
                neuron_type="lif",
                threshold=self.config.threshold,
                tau=self.config.tau,
                step=self.config.step,
            ),
            VotingLayer(voter_num=1),
        ).to(self.device)

    def register_network(self, name: str, network: torch.nn.Module):
        self._networks[name] = network.to(self.device)

    def infer(
        self, name: str, input_tensor: torch.Tensor
    ) -> torch.Tensor:
        network = self._networks.get(name)
        if network is None:
            raise KeyError(f"Network '{name}' not found")
        network.eval()
        with torch.no_grad():
            return network(input_tensor.to(self.device))

    def reset_all(self):
        for net in self._networks.values():
            for module in net.modules():
                if hasattr(module, "n_reset"):
                    module.n_reset()
