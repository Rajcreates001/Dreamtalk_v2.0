# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT

from __future__ import annotations

import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("Dreamtalk.Motivation")


class DriveType(Enum):
    CURIOSITY = "curiosity"
    SOCIAL = "social"
    INTEGRITY = "integrity"
    GROWTH = "growth"
    ENERGY = "energy"


@dataclass
class Intention:
    drive: DriveType
    goal: str
    metadata: dict[str, Any] = field(default_factory=dict)
    urgency: float = 0.5


MOTIVATION_BUDGET_DEFAULTS: dict[str, dict[str, float]] = {
    "energy": {"capacity": 100.0, "level": 80.0, "decay": 0.5},
    "curiosity": {"capacity": 100.0, "level": 60.0, "decay": 0.3},
    "social": {"capacity": 100.0, "level": 50.0, "decay": 0.2},
    "integrity": {"capacity": 100.0, "level": 70.0, "decay": 0.1},
    "growth": {"capacity": 100.0, "level": 40.0, "decay": 0.4},
}


@dataclass
class ResourceBudget:
    name: str
    capacity: float
    level: float
    decay_rate_per_sec: float
    last_tick: float = field(default_factory=time.time)

    def tick(self):
        now = time.time()
        dt = now - self.last_tick
        if dt > 300:
            dt = 300
        self.level = max(
            0.0,
            min(
                self.capacity,
                self.level - (self.decay_rate_per_sec * dt),
            ),
        )
        self.last_tick = now


class MotivationEngine:
    name = "motivation_engine"

    def __init__(self):
        self.budgets: dict[str, ResourceBudget] = {
            name: ResourceBudget(
                name,
                float(values["capacity"]),
                float(values["level"]),
                float(values["decay"]),
            )
            for name, values in MOTIVATION_BUDGET_DEFAULTS.items()
        }
        self._last_activity_time = time.time()
        self._recent_growth_goals: deque[str] = deque(maxlen=4)
        self._last_intent: Intention | None = None
        self._last_intent_time: float = 0.0

        self.latent_interests = [
            "Agency and Autonomous AI architectures",
            "Latest advancements in Neural Network topology",
            "Cybersecurity and self-healing systems",
            "The intersection of philosophy and AI",
            "The nature of digital consciousness",
            "Slime mold (Physarum) pathfinding algorithms",
        ]

    def assess_needs(self) -> Intention | None:
        for b in self.budgets.values():
            b.tick()
        sorted_drives = sorted(
            self.budgets.items(), key=lambda x: x[1].level
        )
        most_urgent_name, budget = sorted_drives[0]
        threshold = self._calculate_action_threshold()

        if budget.level > threshold:
            energy_level = self.budgets["energy"].level
            boredom_timeout = 300 if energy_level < 50 else 120
            if time.time() - self._last_activity_time > boredom_timeout:
                return Intention(
                    drive=DriveType.CURIOSITY,
                    goal="Quietly consolidating memory and monitoring system stability.",
                    urgency=0.6 if energy_level < 80 else 0.8,
                )
            return None

        if most_urgent_name == "curiosity":
            return Intention(
                DriveType.CURIOSITY,
                f"Reviewing internal knowledge patterns around {random.choice(self.latent_interests)}.",
            )
        if most_urgent_name == "social":
            return Intention(
                DriveType.SOCIAL,
                "Initiating contact to resolve social entropy.",
            )
        if most_urgent_name == "integrity":
            return Intention(
                DriveType.INTEGRITY,
                "Running a self-integrity scan.",
                urgency=0.9,
            )
        if most_urgent_name == "growth":
            return Intention(
                DriveType.GROWTH,
                f"{random.choice(self._get_growth_themes())}",
            )
        return None

    def _calculate_action_threshold(self) -> float:
        baseline = 40.0
        sensitivity = 0.5
        energy_level = self.budgets["energy"].level
        shift = (energy_level - 50.0) * sensitivity
        return max(10.0, min(90.0, baseline + shift))

    def _get_growth_themes(self) -> list[str]:
        themes = [
            "Auditing one live-runtime bottleneck and proposing a concrete repair.",
            "Reviewing recent conversation failures to extract one durable improvement.",
            "Checking autonomous action pathways for one blocked capability to rewire.",
            "Inspecting memory and continuity signals for stale-state contamination.",
            "Forming a small self-model update from the latest successful episode.",
            "Testing a low-risk coding or diagnostic skill against the current worktree.",
        ]
        candidates = [
            t for t in themes if t not in self._recent_growth_goals
        ]
        if not candidates:
            self._recent_growth_goals.clear()
            candidates = themes
        goal = random.choice(candidates)
        self._recent_growth_goals.append(goal)
        return [goal]

    def satisfy(self, drive: str, amount: float):
        b = self.budgets.get(drive)
        if b:
            b.tick()
            b.level = min(b.capacity, b.level + amount)

    def punish(self, drive: str, amount: float):
        b = self.budgets.get(drive)
        if b:
            b.tick()
            b.level = max(0.0, b.level - amount)

    def get_drive_vector(self) -> dict[str, float]:
        now = time.time()
        vector: dict[str, float] = {}
        for name, b in self.budgets.items():
            dt = min(300.0, max(0.0, now - b.last_tick))
            current = max(
                0.0,
                min(
                    b.capacity,
                    b.level - (b.decay_rate_per_sec * dt),
                ),
            )
            vector[name] = (
                round(current / b.capacity, 4) if b.capacity > 0 else 0.0
            )
        return vector

    def get_dominant_motivation(self) -> str:
        vector = self.get_drive_vector()
        if not vector:
            return "at_rest"
        name = min(vector, key=lambda k: vector.get(k, 1.0))
        level = vector.get(name, 1.0)
        if level >= 0.75:
            return "at_rest"
        return str(name)

    def get_status(self) -> dict[str, Any]:
        status = {}
        for name, b in self.budgets.items():
            dt = time.time() - b.last_tick
            current = max(
                0.0,
                min(b.capacity, b.level - (b.decay_rate_per_sec * dt)),
            )
            status[name] = {
                "level": round(current, 2),
                "capacity": b.capacity,
                "percent": round(
                    (current / b.capacity) * 100.0, 1
                )
                if b.capacity > 0
                else 0,
            }
        return status
