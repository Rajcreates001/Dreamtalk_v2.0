# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# Persona state: emotional state, conversation context, and dynamic state tracking.
#
# Sources:
#   - C#: ConversationState (FSM enum), ConversationContext (runtime context)
#   - Utsuwa TS: CharacterState, MoodState, StateUpdates, PersonalityProfile runtime

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EmotionalState(str, Enum):
    """Primary emotional states for a persona (from Utsuwa Emotion type)."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    ANXIOUS = "anxious"
    CONTENT = "content"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    AFFECTIONATE = "affectionate"
    PLAYFUL = "playful"
    MELANCHOLY = "melancholy"
    FLUSTERED = "flustered"
    ANGRY = "angry"
    SURPRISED = "surprised"


@dataclass
class MoodState:
    """Current mood with intensity and causality tracking (from Utsuwa MoodState)."""
    primary: EmotionalState = EmotionalState.NEUTRAL
    intensity: int = 50
    secondary: Optional[EmotionalState] = None
    causes: list[str] = field(default_factory=list)


@dataclass
class RelationshipState:
    """Multi-axis relationship state (from Utsuwa CharacterState stats)."""
    affection: int = 0       # 0-1000
    trust: int = 0           # 0-100
    intimacy: int = 0        # 0-100
    comfort: int = 0         # 0-100
    respect: int = 0         # 0-100
    energy: int = 100        # 0-100
    stage: str = "stranger"  # relationship stage label


@dataclass
class PersonaState:
    """Runtime state of an active persona.

    Combines:
      - C# ConversationContext (participants, history, pending turn)
      - Utsuwa CharacterState runtime fields (mood, relationship, temporal)

    This object is mutable and updated throughout a conversation session.
    """

    # Emotional state
    mood: MoodState = field(default_factory=MoodState)

    # Relationship metrics
    relationship: RelationshipState = field(default_factory=RelationshipState)

    # Personality trait drift (from Utsuwa, values can shift over time)
    trait_values: dict[str, int] = field(default_factory=dict)

    # Conversation context
    session_id: str = ""
    turn_count: int = 0
    message_count: int = 0
    last_interaction_time: Optional[float] = None

    # Temporal tracking
    days_known: int = 0
    current_streak: int = 0
    longest_streak: int = 0

    # Event tracking
    completed_events: list[str] = field(default_factory=list)

    def apply_update(self, updates: dict) -> None:
        """Apply a dictionary of deltas (from Utsuwa StateUpdates pattern).

        Accepted keys: mood_change, affection_delta, trust_delta,
        intimacy_delta, comfort_delta, respect_delta, energy_delta.
        """
        mc = updates.get("mood_change")
        if mc:
            self.mood.primary = EmotionalState(mc.get("emotion", "neutral"))
            self.mood.intensity = max(0, min(100, self.mood.intensity + mc.get("intensity_delta", 0)))
            if mc.get("cause"):
                self.mood.causes.append(mc["cause"])

        if "affection_delta" in updates:
            self.relationship.affection = max(0, min(1000, self.relationship.affection + updates["affection_delta"]))
        if "trust_delta" in updates:
            self.relationship.trust = max(0, min(100, self.relationship.trust + updates["trust_delta"]))
        if "intimacy_delta" in updates:
            self.relationship.intimacy = max(0, min(100, self.relationship.intimacy + updates["intimacy_delta"]))
        if "comfort_delta" in updates:
            self.relationship.comfort = max(0, min(100, self.relationship.comfort + updates["comfort_delta"]))
        if "respect_delta" in updates:
            self.relationship.respect = max(0, min(100, self.relationship.respect + updates["respect_delta"]))
        if "energy_delta" in updates:
            self.relationship.energy = max(0, min(100, self.relationship.energy + updates["energy_delta"]))

    def to_dict(self) -> dict:
        """Serialize current state for persistence."""
        return {
            "mood": {
                "primary": self.mood.primary.value,
                "intensity": self.mood.intensity,
                "causes": self.mood.causes,
            },
            "relationship": {
                "affection": self.relationship.affection,
                "trust": self.relationship.trust,
                "intimacy": self.relationship.intimacy,
                "comfort": self.relationship.comfort,
                "respect": self.relationship.respect,
                "energy": self.relationship.energy,
                "stage": self.relationship.stage,
            },
            "trait_values": dict(self.trait_values),
            "turn_count": self.turn_count,
            "message_count": self.message_count,
            "days_known": self.days_known,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
        }
