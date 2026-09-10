# Dreamtalk - Cognition Module
# Extracted from Brain-Cog (https://github.com/BrainCog-X/Brain-Cog)
# License: MIT

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrainCogConfig:
    threshold: float = 0.5
    v_reset: float = 0.0
    dt: float = 1.0
    step: int = 8
    tau: float = 2.0
    layer_by_layer: bool = False
    requires_thres_grad: bool = False
    sigmoid_thres: bool = False
    requires_fp: bool = False
    n_groups: int = 1
    mem_detach: bool = False
    device: str = "cpu"

    # Learning rule defaults
    stdp_decay: float = 0.99
    learning_rate: float = 0.01

    # Encoding defaults
    encoder_type: str = "poisson"  # poisson, temporal, rate

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


DEFAULT_CONFIG = BrainCogConfig()
