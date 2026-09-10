# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT

from __future__ import annotations

from typing import Any

from dreamtalk.cognition.core.neuroscience.cortex.core.memory import (
    compute_importance,
    compute_heat_decay,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.emotion import (
    tag_memory_emotions,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.hippocampus import (
    run_swr_replay,
    format_restoration,
    describe_replay_result,
)


def tool_remember(
    content: str,
    tags: list[str] | None = None,
    domain: str = "",
    importance: float | None = None,
) -> dict[str, Any]:
    if importance is None:
        importance = compute_importance(content, tags)
    emotions = tag_memory_emotions(content)
    return {
        "content": content,
        "tags": tags or [],
        "domain": domain,
        "importance": importance,
        "emotions": emotions["emotions"],
        "arousal": emotions["arousal"],
        "emotional_valence": emotions["valence"],
        "importance_boost": emotions["importance_boost"],
        "decay_resistance": emotions["decay_resistance"],
        "heat": 1.0,
    }


def tool_recall(
    memories: list[dict[str, Any]],
    query: str = "",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    scored = []
    for mem in memories:
        heat = mem.get("heat", 0.0)
        importance = mem.get("importance", 0.5)
        score = heat * 0.6 + importance * 0.4
        scored.append((score, mem))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_k]]


def tool_consolidate(
    memories: list[dict[str, Any]],
    decay_factor: float = 0.95,
) -> dict[str, Any]:
    updates = []
    for mem in memories:
        new_heat = compute_heat_decay(
            mem.get("heat", 1.0),
            hours_elapsed=1.0,
            importance=mem.get("importance", 0.5),
            decay_factor=decay_factor,
        )
        if abs(new_heat - mem.get("heat", 0)) > 0.001:
            updates.append(
                {"id": mem.get("id"), "heat_before": mem.get("heat"), "heat_after": new_heat}
            )
    return {"decay_updates": updates, "n_updated": len(updates)}


def tool_replay(
    hot_memories: list[dict],
    related_memories: list[dict] | None = None,
    relationships: list[dict] | None = None,
) -> dict[str, Any]:
    result = run_swr_replay(
        hot_memories,
        related_memories or [],
        relationships or [],
    )
    return describe_replay_result(result)


def tool_restore_context(
    hot_memories: list[dict], max_memories: int = 5
) -> str:
    return format_restoration(hot_memories, max_memories)


MCP_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "remember": {
        "description": "Store a memory with emotional tagging and importance scoring",
        "fn": tool_remember,
    },
    "recall": {
        "description": "Retrieve memories by heat and importance",
        "fn": tool_recall,
    },
    "consolidate": {
        "description": "Apply thermodynamic decay to memories",
        "fn": tool_consolidate,
    },
    "replay": {
        "description": "Run hippocampal SWR replay for consolidation",
        "fn": tool_replay,
    },
    "restore_context": {
        "description": "Format context restoration from hot memories",
        "fn": tool_restore_context,
    },
}


def get_tool(tool_name: str):
    entry = MCP_TOOL_REGISTRY.get(tool_name)
    if entry is None:
        raise KeyError(f"Unknown MCP tool: {tool_name}")
    return entry["fn"]


def list_tools() -> dict[str, str]:
    return {
        name: entry["description"]
        for name, entry in MCP_TOOL_REGISTRY.items()
    }
