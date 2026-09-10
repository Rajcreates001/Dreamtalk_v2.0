# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT
#
# Citations:
#   - compute_decay: Ebbinghaus (1885) "Uber das Gedachtnis". R(t) = e^{-t/S}
#   - compute_importance: Edmundson HP (1969) JACM 16(2):264-285
#   - compute_valence: Hutto CJ & Gilbert E (2014) VADER. ICWSM.
#   - ACT-R: Anderson JR & Lebiere C (1998) "The Atomic Components of Thought"

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any


_BONUS_WORDS = frozenset({
    "error", "exception", "traceback", "failed", "failure",
    "bug", "crash", "broken", "timeout", "denied", "rejected",
    "deprecated", "decided", "chose", "switched", "migrated",
    "selected", "picked", "opted", "design", "pattern",
    "refactor", "architecture", "restructure", "modular",
    "decouple", "abstract", "breaking", "migration", "critical",
    "security", "vulnerability", "performance", "bottleneck",
    "regression", "root cause",
})

_STIGMA_WORDS = frozenset({
    "maybe", "minor", "trivial", "fyi", "note", "aside",
    "btw", "probably", "might", "perhaps", "just", "small",
})

_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)
_CODE_BLOCK_RE = re.compile(r"```|`[^`]+`")
_FILE_PATH_RE = re.compile(r"(?:\.{0,2}/)?(?:[\w@.-]+/)+[\w@.-]+\.\w+")


def compute_surprise(
    content: str, existing_similarities: list[float]
) -> float:
    if not existing_similarities:
        return 0.5
    return max(0.0, min(1.0, 1.0 - max(existing_similarities)))


def apply_surprise_boost(
    base_heat: float, surprise: float, boost_factor: float = 0.3
) -> float:
    return min(base_heat + surprise * boost_factor, 1.0)


def _edmundson_cue(words: list[str]) -> float:
    if not words:
        return 0.0
    bonus = sum(1 for w in words if w in _BONUS_WORDS)
    stigma = sum(1 for w in words if w in _STIGMA_WORDS)
    return max(0.0, min(1.0, (bonus - stigma) / len(words)))


def _edmundson_key(words: list[str]) -> float:
    if not words:
        return 0.0
    freq = Counter(words)
    if len(freq) < 2:
        return 0.0
    sorted_counts = sorted(freq.values(), reverse=True)
    total_mass = sum(sorted_counts)
    top_k = max(1, len(sorted_counts) // 4)
    top_mass = sum(sorted_counts[:top_k])
    return top_mass / total_mass


def compute_importance(
    content: str, tags: list[str] | None = None
) -> float:
    words = [m.group().lower() for m in _WORD_RE.finditer(content)]
    cue = _edmundson_cue(words)
    if _CODE_BLOCK_RE.search(content) or _FILE_PATH_RE.search(content):
        cue = min(1.0, cue + 0.15)
    key = _edmundson_key(words)
    title = 0.0
    if tags:
        tag_words = {t.lower() for t in tags}
        overlap = tag_words & _BONUS_WORDS
        title = len(overlap) / len(tags) if tags else 0.0
    w_cue, w_key, w_title = 2, 1, 1
    raw = w_cue * cue + w_key * key + w_title * title
    max_raw = w_cue + w_key + w_title
    return min(1.0, round(raw / max_raw, 4))


def compute_valence(content: str) -> float:
    words = [m.group().lower() for m in _WORD_RE.finditer(content)]
    pos_words = {
        "good", "great", "excellent", "amazing", "wonderful",
        "fantastic", "beautiful", "perfect", "love", "happy",
        "success", "fixed", "resolved", "working", "passed",
    }
    neg_words = {
        "bad", "terrible", "awful", "horrible", "hate", "sad",
        "angry", "frustrating", "failed", "broken", "crash",
        "error", "exception", "bug", "worse",
    }
    pos_count = sum(1 for w in words if w in pos_words)
    neg_count = sum(1 for w in words if w in neg_words)
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    compound = (pos_count - neg_count) / math.sqrt(total + 15.0)
    return max(-1.0, min(1.0, compound))


def compute_heat_decay(
    current_heat: float,
    hours_elapsed: float,
    importance: float = 0.5,
    valence: float = 0.0,
    confidence: float = 1.0,
    decay_factor: float = 0.95,
    importance_decay_factor: float = 0.998,
    emotional_decay_resistance: float = 0.5,
) -> float:
    if hours_elapsed <= 0:
        return current_heat

    base = importance_decay_factor if importance > 0.7 else decay_factor
    time_saturation = (
        1.0 - math.exp(-hours_elapsed) if hours_elapsed > 0 else 0.0
    )
    emotional_mod = 1.0 + abs(valence) * emotional_decay_resistance * time_saturation
    effective = 1.0 - (1.0 - base) / emotional_mod
    confidence_mod = 1.0 + confidence * 0.1
    effective = 1.0 - (1.0 - effective) / confidence_mod
    effective = max(0.0, min(effective, 1.0))
    return current_heat * (effective**hours_elapsed)


def compute_session_coherence(
    heat: float,
    created_at_iso: str,
    bonus: float = 0.2,
    window_hours: float = 4.0,
) -> float:
    try:
        mem_dt = datetime.fromisoformat(created_at_iso)
        if mem_dt.tzinfo is None:
            mem_dt = mem_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        hours = (now - mem_dt).total_seconds() / 3600.0
        if hours < window_hours:
            freshness = 1.0 - (hours / window_hours)
            return min(heat + bonus * freshness, 1.0)
    except (ValueError, TypeError):
        pass
    return heat


def compute_metamemory_confidence(
    access_count: int, useful_count: int
) -> float | None:
    if access_count <= 3:
        return None
    return useful_count / access_count


def compute_actr_decay(
    access_count: int,
    lifetime_hours: float,
    d: float = 0.5,
) -> float:
    n = max(1, access_count)
    L = max(0.01, lifetime_hours)
    base_level = math.log(n) - d * math.log(L)
    return 1.0 / (1.0 + math.exp(-base_level / 1.0))


def compute_decay_updates(
    memories: list[dict[str, Any]],
    decay_factor: float = 0.95,
    cold_threshold: float = 0.05,
) -> list[tuple[int, float]]:
    now = datetime.now(timezone.utc)
    updates: list[tuple[int, float]] = []
    for mem in memories:
        if mem.get("is_protected") or mem.get("heat", 0.0) < cold_threshold:
            continue
        current_heat = mem.get("heat", 0.0)
        last_accessed = mem.get("last_accessed") or mem.get("created_at", "")
        try:
            last_dt = datetime.fromisoformat(str(last_accessed))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        hours = max(0, (now - last_dt).total_seconds() / 3600.0)
        new_heat = compute_heat_decay(
            current_heat,
            hours,
            importance=mem.get("importance", 0.5),
            valence=mem.get("emotional_valence", 0.0),
            confidence=mem.get("confidence", 1.0),
            decay_factor=decay_factor,
        )
        if abs(new_heat - current_heat) > 0.001:
            updates.append((mem["id"], round(new_heat, 6)))
    return updates
