# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from dreamtalk.cognition.core.consciousness.aura.core.affect import (
    AffectiveCircumplex,
)
from dreamtalk.cognition.core.consciousness.aura.core.motivation import (
    MotivationEngine,
    Intention,
)

logger = logging.getLogger("Dreamtalk.Response")


class CognitiveMode(Enum):
    CONVERSATIONAL = "conversational"
    REFLECTIVE = "reflective"
    SLEEP = "sleep"
    CRITICAL = "critical"

    @property
    def interval(self) -> float:
        return {
            CognitiveMode.CONVERSATIONAL: 2.0,
            CognitiveMode.REFLECTIVE: 4.0,
            CognitiveMode.SLEEP: 10.0,
            CognitiveMode.CRITICAL: 0.5,
        }.get(self, 2.0)


class ResponseGenerator:
    def __init__(
        self,
        affect: AffectiveCircumplex | None = None,
        motivation: MotivationEngine | None = None,
    ):
        self.affect = affect or AffectiveCircumplex()
        self.motivation = motivation or MotivationEngine()
        self.mode = CognitiveMode.CONVERSATIONAL

    def set_mode(self, mode: CognitiveMode):
        self.mode = mode

    def generate_params(self) -> dict[str, Any]:
        llm_params = self.affect.get_llm_params()
        return {
            "temperature": llm_params["temperature"],
            "max_tokens": llm_params["max_tokens"],
            "rep_penalty": llm_params["rep_penalty"],
            "mood_narrative": llm_params["narrative"],
            "mode": self.mode.value,
            "tick_interval": self.mode.interval,
        }

    def generate_system_prompt_affix(self) -> str:
        affect_narrative = self.affect.describe()
        dominant = self.motivation.get_dominant_motivation()
        drive_vector = self.motivation.get_drive_vector()
        drive_str = ", ".join(
            f"{k}: {v:.0%}" for k, v in drive_vector.items()
        )

        return (
            f"Affective state: {affect_narrative}\n"
            f"Dominant motivation: {dominant}\n"
            f"Drive vector: [{drive_str}]\n"
            f"Cognitive mode: {self.mode.value}"
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "affect": self.affect.get_llm_params(),
            "motivation": self.motivation.get_status(),
            "dominant_drive": self.motivation.get_dominant_motivation(),
        }
