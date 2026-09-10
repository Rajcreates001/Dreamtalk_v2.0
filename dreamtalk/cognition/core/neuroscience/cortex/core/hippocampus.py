# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT
#
# Citations:
#   - Foster DJ & Wilson MA (2006) Nature 440:680-683
#   - Diba K & Buzsaki G (2007) Nature Neurosci 10:1241-1242
#   - Davidson TJ et al. (2009) Neuron 63:497-507

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReplayDirection(Enum):
    FORWARD = "forward"
    REVERSE = "reverse"


@dataclass
class ReplayEvent:
    memory_id: int
    content: str
    heat: float = 0.0
    created_at: str = ""
    entities: list[str] = field(default_factory=list)
    causal_edges: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class ReplaySequence:
    events: list[ReplayEvent] = field(default_factory=list)
    direction: ReplayDirection = ReplayDirection.FORWARD
    priority_score: float = 0.0
    stdp_pairs: list[tuple[int, int, float]] = field(default_factory=list)
    schema_update_signal: float = 0.0


@dataclass
class ReplayResult:
    sequences_generated: int = 0
    memories_replayed: int = 0
    stdp_updates: list[tuple[int, int, float]] = field(default_factory=list)
    schema_signals: list[dict] = field(default_factory=list)
    forward_count: int = 0
    reverse_count: int = 0


def should_micro_checkpoint(
    working_memory: list[dict], checkpoint_interval: int = 5
) -> bool:
    return len(working_memory) > 0 and len(working_memory) % checkpoint_interval == 0


def format_restoration(
    hot_memories: list[dict], max_memories: int = 5
) -> str:
    sorted_mem = sorted(
        hot_memories, key=lambda m: m.get("heat", 0), reverse=True
    )[:max_memories]
    if not sorted_mem:
        return ""
    parts = ["## Context Restoration"]
    for mem in sorted_mem:
        content = mem.get("content", "")[:200]
        heat = mem.get("heat", 0)
        importance = mem.get("importance", 0)
        parts.append(f"- [{heat:.2f}|{importance:.2f}] {content}")
    return "\n".join(parts)


def _build_causal_sequence(
    seed: dict,
    related: list[dict],
    relationships: list[dict],
    direction: ReplayDirection,
) -> list[ReplayEvent]:
    events = []
    seed_event = ReplayEvent(
        memory_id=seed.get("id", 0),
        content=seed.get("content", ""),
        heat=seed.get("heat", 0.0),
        created_at=str(seed.get("created_at", "")),
        entities=seed.get("entities", []),
    )
    events.append(seed_event)

    related_sorted = sorted(
        related, key=lambda m: m.get("heat", 0), reverse=True
    )
    for rel in related_sorted[:3]:
        events.append(
            ReplayEvent(
                memory_id=rel.get("id", 0),
                content=rel.get("content", ""),
                heat=rel.get("heat", 0.0),
                created_at=str(rel.get("created_at", "")),
                entities=rel.get("entities", []),
            )
        )
    if direction == ReplayDirection.REVERSE:
        events.reverse()
    return events


def _build_temporal_sequence(
    hot_memories: list[dict],
) -> list[ReplayEvent]:
    sorted_mem = sorted(
        hot_memories,
        key=lambda m: str(m.get("created_at", "")),
    )
    return [
        ReplayEvent(
            memory_id=m.get("id", 0),
            content=m.get("content", ""),
            heat=m.get("heat", 0.0),
            created_at=str(m.get("created_at", "")),
        )
        for m in sorted_mem[:5]
    ]


def compute_sequence_priority(
    events: list[ReplayEvent], dopamine_level: float = 1.0
) -> float:
    if not events:
        return 0.0
    avg_heat = sum(e.heat for e in events) / len(events)
    n_entities = sum(len(e.entities) for e in events)
    return min(1.0, avg_heat * 0.6 + (n_entities / 10.0) * 0.4) * dopamine_level


def compute_replay_stdp_pairs(
    events: list[ReplayEvent], direction: ReplayDirection
) -> list[tuple[int, int, float]]:
    pairs = []
    for i in range(len(events) - 1):
        src, dst = events[i], events[i + 1]
        for src_ent in src.entities:
            for dst_ent in dst.entities:
                delta_t = 10.0 if direction == ReplayDirection.FORWARD else -10.0
                pairs.append((hash(src_ent), hash(dst_ent), delta_t))
    return pairs


def select_replay_sequences(
    candidates: list[ReplaySequence], max_sequences: int = 5
) -> list[ReplaySequence]:
    scored = sorted(
        candidates, key=lambda s: s.priority_score, reverse=True
    )
    return scored[:max_sequences]


def run_swr_replay(
    hot_memories: list[dict],
    related_memories: list[dict],
    relationships: list[dict],
    dopamine_level: float = 1.0,
    swr_active: bool = True,
    max_sequences: int = 5,
) -> ReplayResult:
    if not swr_active or not hot_memories:
        return ReplayResult()

    seeds = sorted(
        hot_memories, key=lambda m: m.get("heat", 0), reverse=True
    )[: max_sequences * 2]

    candidates = []
    for seed in seeds:
        for direction in (ReplayDirection.FORWARD, ReplayDirection.REVERSE):
            events = _build_causal_sequence(
                seed, related_memories, relationships, direction
            )
            if len(events) >= 2:
                priority = compute_sequence_priority(events, dopamine_level)
                stdp = compute_replay_stdp_pairs(events, direction)
                candidates.append(
                    ReplaySequence(
                        events=events,
                        direction=direction,
                        priority_score=priority,
                        stdp_pairs=stdp,
                    )
                )

    temp_events = _build_temporal_sequence(hot_memories)
    if len(temp_events) >= 2:
        candidates.append(
            ReplaySequence(
                events=temp_events,
                direction=ReplayDirection.FORWARD,
                priority_score=compute_sequence_priority(temp_events, dopamine_level),
                stdp_pairs=compute_replay_stdp_pairs(
                    temp_events, ReplayDirection.FORWARD
                ),
            )
        )

    selected = select_replay_sequences(candidates, max_sequences)
    result = ReplayResult()
    all_stdp = []
    memory_ids = set()

    for seq in selected:
        all_stdp.extend(seq.stdp_pairs)
        memory_ids.update(e.memory_id for e in seq.events)
        if seq.direction == ReplayDirection.FORWARD:
            result.forward_count += 1
        else:
            result.reverse_count += 1
        if seq.priority_score > 0.5:
            result.schema_signals.append(
                {
                    "entities": [
                        e for ev in seq.events for e in ev.entities
                    ],
                    "priority": seq.priority_score,
                    "direction": seq.direction.value,
                }
            )

    result.sequences_generated = len(selected)
    result.memories_replayed = len(memory_ids)
    result.stdp_updates = all_stdp
    return result


def describe_replay_result(result: ReplayResult) -> dict:
    return {
        "sequences_generated": result.sequences_generated,
        "memories_replayed": result.memories_replayed,
        "forward_sequences": result.forward_count,
        "reverse_sequences": result.reverse_count,
        "stdp_updates_count": len(result.stdp_updates),
        "schema_signals_count": len(result.schema_signals),
    }
