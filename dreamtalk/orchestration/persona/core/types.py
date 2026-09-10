# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# Core type definitions for the persona subsystem.
#
# Sources:
#   - C#: ChatMessage, ParticipantInfo, InteractionTurn, EmotionMapping, EmotionMarker
#   - Utsuwa TS: CharacterState, Emotion, StateUpdates, PersonalityProfile (types)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# LLM / Conversation types  (C# IChatEngine, ChatMessage, ConversationState)
# ---------------------------------------------------------------------------

class CompletionReason(Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class ChatMessage:
    """A single message in a conversation (from C# ChatMessage)."""

    message_id: str
    participant_id: str
    participant_name: str
    text: str
    timestamp: float
    is_partial: bool = False
    role: str = "user"


@dataclass
class InteractionTurn:
    """A single turn in conversation history (from C# InteractionTurn)."""

    turn_id: str
    participant_ids: list[str] = field(default_factory=list)
    messages: list[ChatMessage] = field(default_factory=list)


@dataclass
class ParticipantInfo:
    """Information about a conversation participant (from C# ParticipantInfo)."""

    participant_id: str
    name: str
    role: str = "user"


# ---------------------------------------------------------------------------
# Emotion types  (C# EmotionMapping, EmotionMarker, EmotionTiming)
# ---------------------------------------------------------------------------

@dataclass
class EmotionTag:
    """Maps an emotion identifier (emoji) to Live2D expression and motion group.

    From C# EmotionAnimationService.EmotionMapping.
    """

    expression_id: str
    motion_group: str


@dataclass
class EmotionMarker:
    """Character-offset-based emotion data extracted from LLM output.

    From C# EmotionProcessor / EmotionMarker.
    """

    position: int
    emotion: str


@dataclass
class EmotionTiming:
    """Emotion with a timestamp resolved from audio timing.

    From C# EmotionTiming.
    """

    timestamp: float
    emotion: str


# ---------------------------------------------------------------------------
# Voice / TTS  (C# TtsConfiguration, KokoroVoiceOptions, Qwen3TtsOptions)
# ---------------------------------------------------------------------------

@dataclass
class VoiceProfile:
    """Voice / TTS settings for a persona."""

    provider: str = "kokoro"
    voice_id: str = "af_heart"
    pitch: float = 1.0
    speed: float = 1.0
    language: str = "english"


# ---------------------------------------------------------------------------
# Animation / Live2D  (C# Live2DOptions, EmotionAnimationService constants)
# ---------------------------------------------------------------------------

@dataclass
class AnimationProfile:
    """Animation settings for a persona's avatar."""

    model_id: str = "aria"
    idle_motion_group: str = "Idle"
    talking_motion_group: str = "Talking"
    expression_hold_seconds: float = 3.0
    neutral_expression_id: str = "neutral"


# ---------------------------------------------------------------------------
# Personality traits  (Utsuwa PersonalityProfile)
# ---------------------------------------------------------------------------

@dataclass
class PersonaTrait:
    """A scalar personality trait with range and initial value.

    Ported from Utsuwa's PersonalityProfile axes (openness, warmth, etc.).
    """

    description: str = ""
    min: int = -100
    max: int = 100
    initial: int = 0


# ---------------------------------------------------------------------------
# LLM Parameters
# ---------------------------------------------------------------------------

@dataclass
class LLMParameters:
    """Parameters passed to the LLM for generation."""

    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1024
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


# ---------------------------------------------------------------------------
# Memory settings  (Utsuwa Memory types)
# ---------------------------------------------------------------------------

@dataclass
class MemorySettings:
    """Long-term memory configuration for a persona."""

    type: str = "conversation"
    max_turns: int = 20
    max_facts: int = 50
