# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT
#
# Citations:
#   - VADER: Hutto CJ & Gilbert E (2014) ICWSM
#   - Yerkes-Dodson: Yerkes & Dodson (1908)
#   - McGaugh (2004) Annual Review of Neuroscience

from __future__ import annotations

import math
import re
from typing import Any


_ERROR_RE = re.compile(
    r"\b(error|exception|traceback|failed|failure|bug|crash|broken|timeout|"
    r"denied|rejected|deprecated)\b",
    re.IGNORECASE,
)

_SUCCESS_RE = re.compile(
    r"\b(fixed|resolved|working|success|passed|deployed|completed|shipped|"
    r"merged|approved|nailed|breakthrough|elegant|beautiful|clean|perfect|"
    r"excellent|awesome|improvement)\b",
    re.IGNORECASE,
)

_QUESTION_RE = re.compile(
    r"\?|"
    r"\b(confus|unclear|don'?t understand|makes no sense|"
    r"weird|bizarre|unexpected|strange|mysterious|puzzling|"
    r"why does|how come)\b",
    re.IGNORECASE,
)

_URGENCY_RE = re.compile(
    r"\b(urgent|critical|blocking|deadline|asap|immediately|"
    r"production|outage|down|hotfix|p0|sev[- ]?1)\b",
    re.IGNORECASE,
)

_INSIGHT_RE = re.compile(
    r"\b(realized|discovered|found out|turns out|TIL|"
    r"interesting|insight|key finding|important lesson|"
    r"aha|eureka|lightbulb)\b",
    re.IGNORECASE,
)


def _vader_compound(content: str) -> float:
    pos_words = {
        "good": 1.5, "great": 2.0, "excellent": 2.5, "amazing": 2.5,
        "wonderful": 2.0, "fantastic": 2.5, "beautiful": 1.5,
        "perfect": 2.0, "love": 2.0, "happy": 1.5, "success": 2.0,
        "fixed": 1.5, "resolved": 1.5, "working": 1.0, "passed": 1.5,
        "elegant": 1.5, "clean": 1.0, "improvement": 1.5,
    }
    neg_words = {
        "bad": -1.5, "terrible": -2.5, "awful": -2.5, "horrible": -2.5,
        "hate": -2.0, "sad": -1.5, "angry": -2.0, "frustrating": -2.0,
        "failed": -2.0, "broken": -2.0, "crash": -2.5, "error": -1.5,
        "exception": -1.5, "bug": -1.5, "worse": -2.0, "timeout": -1.5,
        "denied": -1.5, "rejected": -1.5, "deprecated": -1.0,
    }
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", content.lower())
    score = sum(pos_words.get(w, 0) for w in words) + sum(neg_words.get(w, 0) for w in words)
    return score / math.sqrt(score * score + 15.0)


def detect_emotions(content: str) -> dict[str, float]:
    compound = _vader_compound(content)
    abs_compound = abs(compound)

    error_hits = min(len(_ERROR_RE.findall(content)), 3)
    success_hits = min(len(_SUCCESS_RE.findall(content)), 3)
    question_hits = min(len(_QUESTION_RE.findall(content)), 3)
    urgency_hits = min(len(_URGENCY_RE.findall(content)), 3)
    insight_hits = min(len(_INSIGHT_RE.findall(content)), 3)

    frustration = 0.0
    if compound < 0 and error_hits > 0:
        frustration = abs_compound * (error_hits / 3.0)
    elif error_hits >= 1:
        frustration = 0.2 * (error_hits / 3.0)

    satisfaction = 0.0
    if compound > 0 and success_hits > 0:
        satisfaction = abs_compound * (success_hits / 3.0)
    elif success_hits >= 1:
        satisfaction = 0.2 * (success_hits / 3.0)

    confusion = 0.0
    if question_hits > 0:
        certainty = max(0.0, 1.0 - abs_compound * 2)
        confusion = certainty * (question_hits / 3.0)

    urgency = 0.0
    if urgency_hits > 0:
        neg_weight = max(0.3, abs_compound) if compound <= 0 else 0.3
        urgency = neg_weight * (urgency_hits / 3.0)

    discovery = 0.0
    if insight_hits > 0:
        pos_weight = max(0.3, abs_compound) if compound >= 0 else 0.3
        discovery = pos_weight * (insight_hits / 3.0)

    return {
        "frustration": round(min(1.0, frustration), 4),
        "satisfaction": round(min(1.0, satisfaction), 4),
        "confusion": round(min(1.0, confusion), 4),
        "urgency": round(min(1.0, urgency), 4),
        "discovery": round(min(1.0, discovery), 4),
    }


def compute_arousal(emotions: dict[str, float]) -> float:
    values = [v for v in emotions.values() if v > 0]
    if not values:
        return 0.0
    rms = (sum(v * v for v in values) / len(values)) ** 0.5
    return round(min(1.0, rms), 4)


def compute_emotional_valence(emotions: dict[str, float]) -> float:
    positive = emotions.get("satisfaction", 0) + emotions.get("discovery", 0)
    negative = emotions.get("frustration", 0) + emotions.get("urgency", 0)
    total = positive + negative + emotions.get("confusion", 0)
    if total == 0:
        return 0.0
    return round(max(-1.0, min(1.0, (positive - negative) / max(total, 1.0))), 4)


def compute_importance_boost(
    emotions: dict[str, float], arousal: float
) -> float:
    _YD_B = 1.0 / 0.7
    _YD_C = 0.57 * _YD_B * math.e
    yd_curve = 1.0 + _YD_C * arousal * math.exp(-_YD_B * arousal)
    bonus = 0.0
    bonus += emotions.get("urgency", 0) * 0.3
    bonus += emotions.get("discovery", 0) * 0.2
    bonus += emotions.get("frustration", 0) * 0.1
    return round(min(2.0, max(1.0, yd_curve + bonus)), 4)


def compute_decay_resistance(
    emotions: dict[str, float], arousal: float
) -> float:
    if arousal < 0.1:
        return 1.0
    resistance = 1.0 + arousal * 0.6
    resistance += emotions.get("discovery", 0) * 0.2
    resistance += emotions.get("urgency", 0) * 0.2
    return round(min(2.0, resistance), 4)


def tag_memory_emotions(content: str) -> dict[str, Any]:
    emotions = detect_emotions(content)
    arousal = compute_arousal(emotions)
    valence = compute_emotional_valence(emotions)
    importance_boost = compute_importance_boost(emotions, arousal)
    decay_resistance = compute_decay_resistance(emotions, arousal)
    is_emotional = arousal > 0.2
    dominant = max(emotions, key=emotions.get) if is_emotional else "neutral"

    return {
        "emotions": emotions,
        "arousal": arousal,
        "valence": valence,
        "importance_boost": importance_boost,
        "decay_resistance": decay_resistance,
        "is_emotional": is_emotional,
        "dominant_emotion": dominant,
    }
