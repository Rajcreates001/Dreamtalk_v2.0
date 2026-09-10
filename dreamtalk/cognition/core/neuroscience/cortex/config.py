# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CortexConfig:
    # Thermodynamic memory
    decay_factor: float = 0.95
    importance_decay_factor: float = 0.998
    emotional_decay_resistance: float = 0.5
    cold_threshold: float = 0.05
    adaptive_decay: bool = False

    # Emotional tagging
    emotion_threshold: float = 0.2

    # Hippocampal replay
    min_sequence_length: int = 2
    max_sequences_per_swr: int = 5
    dopamine_level: float = 1.0

    # Oscillatory clock
    theta_freq: float = 6.0
    gamma_freq: float = 40.0
    swr_freq: float = 0.1

    # Consolidation stages
    labile_decay_multiplier: float = 2.0
    consolidated_decay_multiplier: float = 0.5

    # Embedding
    embedding_dim: int = 384

    # PostgreSQL
    database_url: str = "postgresql://localhost:5432/cortex"

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


DEFAULT_CONFIG = CortexConfig()
