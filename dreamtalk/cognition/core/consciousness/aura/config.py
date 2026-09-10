# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuraConfig:
    # Consciousness / IIT
    neuron_count: int = 64
    buffer_size: int = 64
    num_partitions: int = 16
    phi_compute_interval_s: float = 15.0

    # Affect
    temp_min: float = 0.50
    temp_base: float = 0.72
    temp_max: float = 0.95
    tokens_min: int = 256
    tokens_base: int = 512
    tokens_max: int = 768
    rep_min: float = 1.10
    rep_max: float = 1.35

    # Motivation
    baseline_volition: float = 40.0
    volition_sensitivity: float = 0.5
    boredom_timeout_s: int = 300

    # MindTick
    tick_mode: str = "conversational"  # conversational, reflective, sleep, critical
    tick_interval: float = 2.0

    # CAA
    caa_base_alpha: float = 5.0
    caa_steer_layer_start: float = 0.45
    caa_steer_layer_end: float = 0.60

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


DEFAULT_CONFIG = AuraConfig()
