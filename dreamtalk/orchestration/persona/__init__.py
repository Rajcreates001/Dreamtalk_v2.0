# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# Persona management: loading, selecting, and configuring personality profiles.

from dreamtalk.orchestration.persona.config import PersonaConfig
from dreamtalk.orchestration.persona.profile import PersonalityProfile
from dreamtalk.orchestration.persona.manager import PersonaManager
from dreamtalk.orchestration.persona.core.types import (
    PersonaTrait,
    EmotionTag,
    VoiceProfile,
    AnimationProfile,
    MemorySettings,
    LLMParameters,
)
from dreamtalk.orchestration.persona.core.state import PersonaState
from dreamtalk.orchestration.persona.core.interfaces import (
    IPersonaProvider,
    IPersonaRepository,
    IEmotionService,
    IAnimationController,
)

__all__ = [
    "PersonaConfig",
    "PersonalityProfile",
    "PersonaManager",
    "PersonaTrait",
    "EmotionTag",
    "VoiceProfile",
    "AnimationProfile",
    "MemorySettings",
    "LLMParameters",
    "PersonaState",
    "IPersonaProvider",
    "IPersonaRepository",
    "IEmotionService",
    "IAnimationController",
]
