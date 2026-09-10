# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# Abstract base classes for persona subsystem.
#
# Sources:
#   - C#: IChatEngine, IVisualChatEngine, ITextFilter, ILive2DAnimationService,
#         IEmotionService, ILlmKernelProvider, IConversationOrchestrator
#   - Utsuwa TS: ModuleDefinition hooks (onEnable, onDisable)

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from dreamtalk.orchestration.persona.core.types import (
    ChatMessage,
    EmotionTiming,
)


# ---------------------------------------------------------------------------
# LLM / Chat Engine  (C# IChatEngine, IVisualChatEngine)
# ---------------------------------------------------------------------------

class IChatEngine(ABC):
    """Streaming chat completion engine (from C# IChatEngine).

    Accepts a conversation history and yields response chunks via an async
    generator.  Each chunk is a string fragment of the LLM's streaming reply.
    """

    @abstractmethod
    async def get_streaming_response(
        self,
        messages: list[ChatMessage],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        ...


class IVisualChatEngine(ABC):
    """Vision-capable chat engine (from C# IVisualChatEngine).

    Accepts a text query + image bytes and streams the response.
    """

    @abstractmethod
    async def get_streaming_response(
        self,
        query: str,
        image_data: bytes,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        ...


# ---------------------------------------------------------------------------
# Text Filter  (C# ITextFilter → EmotionProcessor, NameTextFilter)
# ---------------------------------------------------------------------------

class ITextFilter(ABC):
    """Pipeline filter that processes LLM output text before TTS.

    From C# ITextFilter.  The filter pipeline is ordered by priority;
    each filter can strip/modify text and attach metadata (e.g. emotion tags).
    """

    @property
    @abstractmethod
    def priority(self) -> int:
        ...

    @abstractmethod
    async def process(self, text: str) -> tuple[str, dict]:
        """Transform raw LLM output text; return (clean_text, metadata)."""
        ...


# ---------------------------------------------------------------------------
# Emotion Service  (C# IEmotionService)
# ---------------------------------------------------------------------------

class IEmotionService(ABC):
    """Tracks emotion-to-timestamp mappings for audio segments.

    From C# IEmotionService (Live2D.Behaviour.Emotion).
    """

    @abstractmethod
    def register_emotions(self, segment_id: str, emotions: list[EmotionTiming]) -> None:
        ...

    @abstractmethod
    def get_emotions(self, segment_id: str) -> list[EmotionTiming]:
        ...


# ---------------------------------------------------------------------------
# Animation Controller  (C# ILive2DAnimationService)
# ---------------------------------------------------------------------------

class IAnimationController(ABC):
    """Controls Live2D model animations (from C# ILive2DAnimationService).

    Sub-services include emotion animations, idle blinking, and lip-sync.
    """

    @abstractmethod
    def start(self) -> None:
        """Activate the animation service."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Deactivate the animation service."""
        ...

    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Per-frame update, applies parameter changes to the model."""
        ...


# ---------------------------------------------------------------------------
# Persona providers  (Utsuwa / C# persona store concept)
# ---------------------------------------------------------------------------

class IPersonaProvider(ABC):
    """Provides the current active persona profile."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...


class IPersonaRepository(ABC):
    """Persistence layer for persona profiles."""

    @abstractmethod
    async def load(self, name: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def save(self, name: str, profile: dict) -> None:
        ...

    @abstractmethod
    async def list_personas(self) -> list[str]:
        ...
