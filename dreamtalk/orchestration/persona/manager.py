# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# PersonaManager: loads, selects, and manages personas.
#
# Sources:
#   - C#: ConversationOrchestrator (session lifecycle), LlmKernelProvider (hot-reload)
#   - Utsuwa: personaStore, persona.svelte.ts (single-persona management)

from __future__ import annotations

import logging
from typing import Optional

from dreamtalk.orchestration.persona.config import PersonaConfig
from dreamtalk.orchestration.persona.core.state import PersonaState
from dreamtalk.orchestration.persona.core.types import ChatMessage
from dreamtalk.orchestration.persona.profile import PersonalityProfile

logger = logging.getLogger(__name__)


class PersonaManager:
    """Manages the active persona and coordinates its lifecycle.

    Responsibilities:
      - Load a PersonalityProfile by name
      - Maintain the active persona and its runtime state (PersonaState)
      - Provide persona context to the LLM / TTS / animation subsystems
      - Support hot-swapping between personas (in-flight turns complete first)

    Ported from:
      - C# ConversationOrchestrator (session creation, active-session pool)
      - Utsuwa personaStore (single-active-persona pattern)
      - C# LlmKernelProvider (hot-reload coordination via IsSafeToReloadNow)
    """

    def __init__(self, config: Optional[PersonaConfig] = None) -> None:
        self._config = config or PersonaConfig()
        self._profiles: dict[str, PersonalityProfile] = {}
        self._active_profile: Optional[PersonalityProfile] = None
        self._active_state: Optional[PersonaState] = None
        self._is_turn_in_flight: bool = False

    # ------------------------------------------------------------------
    # Profile registry
    # ------------------------------------------------------------------

    def register(self, profile: PersonalityProfile) -> None:
        """Register a persona profile so it can be activated later."""
        self._profiles[profile.name] = profile
        logger.info("Registered persona '%s'", profile.name)

    def list_personas(self) -> list[str]:
        """Return the names of all registered profiles."""
        return list(self._profiles.keys())

    def get_profile(self, name: str) -> Optional[PersonalityProfile]:
        """Look up a registered profile by name."""
        return self._profiles.get(name)

    # ------------------------------------------------------------------
    # Active persona
    # ------------------------------------------------------------------

    @property
    def active_profile(self) -> Optional[PersonalityProfile]:
        return self._active_profile

    @property
    def active_state(self) -> Optional[PersonaState]:
        return self._active_state

    @property
    def is_safe_to_switch(self) -> bool:
        """True when no conversation turn is in-flight (kernel-swap safety gate).

        From C# IKernelReloadCoordinator.IsSafeToReloadNow.
        """
        return not self._is_turn_in_flight

    async def activate(self, name: str) -> bool:
        """Switch the active persona to *name*.

        Returns False if the profile is not registered or if a turn is
        currently in-flight (caller must wait for completion).
        """
        if not self.is_safe_to_switch:
            logger.warning("Cannot switch persona while a turn is in-flight")
            return False

        profile = self._profiles.get(name)
        if profile is None:
            logger.error("Persona '%s' not found in registry", name)
            return False

        self._active_profile = profile
        self._active_state = PersonaState()
        logger.info("Activated persona '%s'", name)
        return True

    # ------------------------------------------------------------------
    # Conversation helpers
    # ------------------------------------------------------------------

    def build_system_messages(self) -> list[ChatMessage]:
        """Build the system-level messages for the LLM from the active persona.

        Returns a list with a single ChatMessage containing the full system
        prompt (including traits, current context, and topics).
        """
        if self._active_profile is None:
            return []

        prompt = self._active_profile.build_system_prompt()
        return [
            ChatMessage(
                message_id="system-001",
                participant_id="system",
                participant_name="System",
                text=prompt,
                timestamp=0.0,
                role="system",
            )
        ]

    def mark_turn_started(self) -> None:
        """Call when a new LLM turn begins (locks against persona switches)."""
        self._is_turn_in_flight = True

    def mark_turn_completed(self) -> None:
        """Call when the current LLM turn is done."""
        self._is_turn_in_flight = False

    def get_active_voice_id(self) -> str:
        """Return the TTS voice ID for the active persona."""
        if self._active_profile is None:
            return "af_heart"
        return self._active_profile.voice.voice_id

    def get_active_llm_params(self) -> dict:
        """Return generation parameters for the active persona."""
        if self._active_profile is None:
            return {"temperature": 0.7, "top_p": 0.9, "max_tokens": 1024}
        p = self._active_profile.llm_parameters
        return {
            "temperature": p.temperature,
            "top_p": p.top_p,
            "max_tokens": p.max_tokens,
            "frequency_penalty": p.frequency_penalty,
            "presence_penalty": p.presence_penalty,
        }
