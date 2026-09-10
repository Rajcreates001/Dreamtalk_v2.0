# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT

from __future__ import annotations

import logging
import math
import time
from typing import Any

logger = logging.getLogger("Dreamtalk.Affect")

_TEMP_MIN = 0.50
_TEMP_BASE = 0.72
_TEMP_MAX = 0.95
_TOKENS_MIN = 256
_TOKENS_BASE = 512
_TOKENS_MAX = 768
_REP_MIN = 1.10
_REP_MAX = 1.35
_VALENCE_NEUTRAL = 0.55
_AROUSAL_NEUTRAL = 0.35


class AffectiveCircumplex:
    def __init__(self):
        self._last_compute: float = 0.0
        self._cache_ttl: float = 3.0
        self._cached: dict[str, Any] | None = None
        self._valence_offset: float = 0.0
        self._arousal_offset: float = 0.0
        self._last_decay: float = time.monotonic()
        self._decay_rate: float = 0.10

    def apply_event(
        self, valence_delta: float, arousal_delta: float
    ):
        def _clamp(x):
            return max(-0.40, min(0.40, x))

        self._valence_offset = _clamp(
            self._valence_offset + valence_delta
        )
        self._arousal_offset = _clamp(
            self._arousal_offset + arousal_delta
        )
        self._cached = None

    def get_coordinates(self) -> tuple[float, float]:
        params = self._compute()
        return params["valence"], params["arousal"]

    def get_llm_params(self) -> dict[str, Any]:
        return self._compute()

    def describe(self) -> str:
        p = self._compute()
        return p["narrative"]

    def _compute(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._cached and (now - self._last_compute) < self._cache_ttl:
            return self._cached

        valence, arousal = self._sample_raw_axes()
        arousal_dev = arousal - 0.5
        temperature = round(
            _TEMP_BASE + arousal_dev * (_TEMP_MAX - _TEMP_BASE) * 2.0, 3
        )
        temperature = max(_TEMP_MIN, min(_TEMP_MAX, temperature))

        token_range = _TOKENS_MAX - _TOKENS_MIN
        max_tokens = int(_TOKENS_MIN + valence * token_range)

        rep_range = _REP_MAX - _REP_MIN
        rep_penalty = round(_REP_MAX - valence * rep_range, 3)
        if arousal > 0.65:
            rep_penalty = min(
                _REP_MAX,
                rep_penalty + (arousal - 0.65) * 0.20,
            )
            rep_penalty = round(rep_penalty, 3)

        narrative = self._make_narrative(valence, arousal)
        result = {
            "valence": round(valence, 3),
            "arousal": round(arousal, 3),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "rep_penalty": rep_penalty,
            "narrative": narrative,
        }
        self._cached = result
        self._last_compute = now
        return result

    def _decay_offsets(self):
        now = time.monotonic()
        elapsed_min = (now - self._last_decay) / 60.0
        if elapsed_min < 0.1:
            return
        factor = (1.0 - self._decay_rate) ** elapsed_min
        self._valence_offset *= factor
        self._arousal_offset *= factor
        if abs(self._valence_offset) < 0.005:
            self._valence_offset = 0.0
        if abs(self._arousal_offset) < 0.005:
            self._arousal_offset = 0.0
        self._last_decay = now

    def _sample_raw_axes(self) -> tuple[float, float]:
        self._decay_offsets()
        valence = _VALENCE_NEUTRAL
        arousal = _AROUSAL_NEUTRAL
        valence = min(1.0, max(0.0, valence + self._valence_offset))
        arousal = min(1.0, max(0.0, arousal + self._arousal_offset))
        return valence, arousal

    @staticmethod
    def _make_narrative(valence: float, arousal: float) -> str:
        if arousal >= 0.65:
            mood = "alert and energized" if valence >= 0.55 else "tense and overloaded"
        elif arousal <= 0.35:
            mood = "calm and settled" if valence >= 0.55 else "tired and withdrawn"
        else:
            if valence >= 0.65:
                mood = "comfortable and engaged"
            elif valence <= 0.35:
                mood = "strained and low"
            else:
                mood = "stable"
        return f"Feeling {mood}."


_circumplex: AffectiveCircumplex | None = None


def get_circumplex() -> AffectiveCircumplex:
    global _circumplex
    if _circumplex is None:
        _circumplex = AffectiveCircumplex()
    return _circumplex
