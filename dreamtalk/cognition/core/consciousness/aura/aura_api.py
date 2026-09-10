# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT

from __future__ import annotations

from typing import Any

import numpy as np

from dreamtalk.cognition.core.consciousness.aura.config import (
    AuraConfig,
    DEFAULT_CONFIG,
)
from dreamtalk.cognition.core.consciousness.aura.inference import (
    AuraInferenceEngine,
)
from dreamtalk.cognition.core.consciousness.aura.core.consciousness import (
    RIIU,
    PhiCore,
    PhiComputer,
)
from dreamtalk.cognition.core.consciousness.aura.core.affect import (
    AffectiveCircumplex,
    get_circumplex,
)
from dreamtalk.cognition.core.consciousness.aura.core.motivation import (
    MotivationEngine,
)
from dreamtalk.cognition.core.consciousness.aura.core.response import (
    ResponseGenerator,
    CognitiveMode,
)
from dreamtalk.cognition.core.consciousness.aura.core.caa import (
    ProductionCAA,
    VectorRegistry,
)


class AuraAPI:
    def __init__(self, config: AuraConfig | None = None):
        self.config = config or DEFAULT_CONFIG
        self.inference_engine = AuraInferenceEngine(self.config)

    def tick(
        self,
        state_vector: np.ndarray | None = None,
        cognitive_values: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        return self.inference_engine.tick(state_vector, cognitive_values)

    def compute_phi(self, state_vector: np.ndarray) -> float:
        return self.inference_engine.riiu.compute_phi(state_vector)

    def get_phi_riiu(self) -> float:
        return self.inference_engine.riiu.get_phi()

    def get_affect_coordinates(self) -> tuple[float, float]:
        return self.inference_engine.affect.get_coordinates()

    def apply_affect_event(
        self, valence_delta: float, arousal_delta: float
    ):
        self.inference_engine.affect.apply_event(
            valence_delta, arousal_delta
        )

    def get_llm_params(self) -> dict[str, Any]:
        return self.inference_engine.response.generate_params()

    def get_system_prompt_affix(self) -> str:
        return self.inference_engine.response.generate_system_prompt_affix()

    def assess_motivation(self) -> dict[str, Any]:
        intention = self.inference_engine.motivation.assess_needs()
        return {
            "intention": intention.goal if intention else None,
            "drive": intention.drive.value if intention else None,
            "dominant": self.inference_engine.motivation.get_dominant_motivation(),
            "drive_vector": self.inference_engine.motivation.get_drive_vector(),
        }

    def set_cognitive_mode(self, mode: str):
        try:
            cm = CognitiveMode(mode)
            self.inference_engine.response.set_mode(cm)
        except ValueError:
            pass

    def get_status(self) -> dict[str, Any]:
        return self.inference_engine.get_status()
