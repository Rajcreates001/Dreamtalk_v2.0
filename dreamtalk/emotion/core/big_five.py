# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
Multi-layer Brain Simulation for DreamTalk.
Amygdala (Emotional), Hippocampus (Memory), Prefrontal Cortex (Rational), Neocortex (Creative).
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class BigFiveTraits:
    extroversion: float      # 0 to 1
    agreeableness: float     # 0 to 1
    neuroticism: float       # 0 to 1
    openness: float          # 0 to 1
    conscientiousness: float # 0 to 1


class NeuralBrainSimulation:
    def __init__(self, traits: Optional[BigFiveTraits] = None):
        self.traits = traits or BigFiveTraits(0.5, 0.5, 0.4, 0.8, 0.5)
        self.arousal_baseline = self.traits.neuroticism * 0.5
        self.cognitive_load = 0.0

    def process_decision(self, user_input: str, emotion: Dict, context: Dict) -> Dict:
        """Process decision through multi-layer brain model."""

        emotional_intensity = abs(emotion["vad"][1])
        is_hostile = emotion["vad"][0] < -0.6 and emotion["vad"][1] > 0.5

        memory_resonance = self._calculate_memory_resonance(context["ltm"])

        rational_override = self._calculate_rational_override(emotional_intensity)

        creativity_level = self.traits.openness * (1.0 - rational_override)

        spontaneity = random.uniform(0, 0.2) * self.traits.openness

        delay = self._calculate_response_delay(len(user_input), emotional_intensity)

        return {
            "layers": {
                "amygdala": {"intensity": emotional_intensity, "hostile": is_hostile},
                "hippocampus": {"resonance": memory_resonance},
                "pfc": {"rational_override": rational_override},
                "neocortex": {"creativity": creativity_level}
            },
            "spontaneity": spontaneity,
            "delay_ms": int(delay * 1000)
        }

    def _calculate_memory_resonance(self, ltm: List[Dict]) -> float:
        if not ltm: return 0.0
        return min(1.0, len(ltm) * 0.1)

    def _calculate_rational_override(self, emotional_intensity: float) -> float:
        base_override = self.traits.conscientiousness * 0.7
        emotion_impact = emotional_intensity * (1.0 + self.traits.neuroticism)
        return max(0.1, base_override - (emotion_impact * 0.5))

    def _calculate_response_delay(self, input_len: int, emotional_intensity: float) -> float:
        base_delay = 0.5
        complexity_delay = (input_len / 100) * 0.5
        emotional_delay = emotional_intensity * 1.5
        extroversion_bonus = self.traits.extroversion * 0.5

        total_delay = base_delay + complexity_delay + emotional_delay - extroversion_bonus
        return max(0.5, min(4.0, total_delay))

    def update_traits(self, new_traits: BigFiveTraits):
        self.traits = new_traits
