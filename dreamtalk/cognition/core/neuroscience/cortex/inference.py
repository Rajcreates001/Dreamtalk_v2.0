# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT

from __future__ import annotations

from typing import Any

from dreamtalk.cognition.core.neuroscience.cortex.config import CortexConfig
from dreamtalk.cognition.core.neuroscience.cortex.core.memory import (
    compute_importance,
    compute_valence,
    compute_heat_decay,
    compute_surprise,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.emotion import (
    tag_memory_emotions,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.hippocampus import (
    run_swr_replay,
    format_restoration,
    describe_replay_result,
)


class CortexInferenceEngine:
    def __init__(self, config: CortexConfig | None = None):
        self.config = config or CortexConfig()
        self._memory_store: dict[int, dict[str, Any]] = {}
        self._next_id: int = 1

    def ingest(
        self,
        content: str,
        tags: list[str] | None = None,
        domain: str = "",
    ) -> dict[str, Any]:
        importance = compute_importance(content, tags)
        valence = compute_valence(content)
        emotions = tag_memory_emotions(content)

        memory = {
            "id": self._next_id,
            "content": content,
            "tags": tags or [],
            "domain": domain,
            "importance": importance,
            "valence": valence,
            "heat": 1.0,
            "access_count": 0,
            "useful_count": 0,
            "confidence": 1.0,
            "emotions": emotions["emotions"],
            "arousal": emotions["arousal"],
            "emotional_valence": emotions["valence"],
            "importance_boost": emotions["importance_boost"],
            "decay_resistance": emotions["decay_resistance"],
            "is_emotional": emotions["is_emotional"],
            "dominant_emotion": emotions["dominant_emotion"],
            "is_protected": False,
        }
        self._memory_store[self._next_id] = memory
        self._next_id += 1
        return memory

    def recall(
        self, query: str = "", top_k: int = 5
    ) -> list[dict[str, Any]]:
        scored = []
        for mem in self._memory_store.values():
            heat = mem.get("heat", 0.0)
            importance = mem.get("importance", 0.5)
            score = heat * 0.6 + importance * 0.4
            scored.append((score, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [dict(m) for _, m in scored[:top_k]]
        for r in results:
            r["access_count"] = r.get("access_count", 0) + 1
            if r["id"] in self._memory_store:
                self._memory_store[r["id"]]["access_count"] = r["access_count"]
        return results

    def decay(self) -> list[dict[str, Any]]:
        updates = []
        for mem_id, mem in self._memory_store.items():
            if mem.get("is_protected"):
                continue
            old_heat = mem["heat"]
            mem["heat"] = compute_heat_decay(
                old_heat,
                hours_elapsed=1.0,
                importance=mem.get("importance", 0.5),
                valence=mem.get("emotional_valence", 0.0),
                confidence=mem.get("confidence", 1.0),
                decay_factor=self.config.decay_factor,
            )
            if abs(mem["heat"] - old_heat) > 0.001:
                updates.append(
                    {"id": mem_id, "heat_before": old_heat, "heat_after": mem["heat"]}
                )
        return updates

    def replay(self) -> dict[str, Any]:
        hot = [
            m for m in self._memory_store.values() if m.get("heat", 0) > 0.3
        ]
        result = run_swr_replay(hot, [], [])
        return describe_replay_result(result)

    def get_status(self) -> dict[str, Any]:
        return {
            "total_memories": len(self._memory_store),
            "hot_memories": sum(
                1 for m in self._memory_store.values() if m.get("heat", 0) > 0.5
            ),
            "protected": sum(
                1 for m in self._memory_store.values() if m.get("is_protected")
            ),
        }
