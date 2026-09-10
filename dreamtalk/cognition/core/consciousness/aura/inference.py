# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT

from __future__ import annotations

from typing import Any

import numpy as np

from dreamtalk.cognition.core.consciousness.aura.config import AuraConfig
from dreamtalk.cognition.core.consciousness.aura.core.consciousness import (
    RIIU,
    PhiCore,
    PhiComputer,
)
from dreamtalk.cognition.core.consciousness.aura.core.affect import (
    AffectiveCircumplex,
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
)


class AuraInferenceEngine:
    def __init__(self, config: AuraConfig | None = None):
        self.config = config or AuraConfig()
        self.consciousness = PhiCore()
        self.riiu = RIIU(
            neuron_count=self.config.neuron_count,
            buffer_size=self.config.buffer_size,
        )
        self.phi_computer = PhiComputer()
        self.affect = AffectiveCircumplex()
        self.motivation = MotivationEngine()
        self.response = ResponseGenerator(
            affect=self.affect, motivation=self.motivation
        )
        self.caa = ProductionCAA(
            base_alpha=self.config.caa_base_alpha
        )
        self._tick_count: int = 0

    def tick(
        self,
        state_vector: np.ndarray | None = None,
        cognitive_values: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        self._tick_count += 1
        if state_vector is not None:
            self.consciousness.record_state(
                state_vector, cognitive_values
            )
            phi_surrogate = self.consciousness.compute_surrogate_phi()
            self.riiu.compute_phi(state_vector)

        intention = self.motivation.assess_needs()
        response_params = self.response.generate_params()

        return {
            "tick": self._tick_count,
            "mode": self.response.mode.value,
            "phi_surrogate": round(
                self.consciousness.compute_surrogate_phi(), 6
            ),
            "riiu_phi": round(self.riiu.get_phi(), 6),
            "affect": {
                "valence": self.affect.get_coordinates()[0],
                "arousal": self.affect.get_coordinates()[1],
            },
            "motivation": {
                "dominant": self.motivation.get_dominant_motivation(),
                "drive_vector": self.motivation.get_drive_vector(),
                "intention": intention.goal if intention else None,
            },
            "response_params": response_params,
        }

    def get_consciousness_status(self) -> dict[str, Any]:
        return self.consciousness.get_status()

    def get_caa_status(self) -> dict[str, Any]:
        return self.caa.status()

    def get_status(self) -> dict[str, Any]:
        return {
            "consciousness": self.consciousness.get_status(),
            "riiu": self.riiu.get_stats(),
            "affect": dict(
                zip(
                    ["valence", "arousal"],
                    self.affect.get_coordinates(),
                )
            ),
            "motivation": self.motivation.get_status(),
            "caa": self.caa.status(),
            "tick_count": self._tick_count,
        }
