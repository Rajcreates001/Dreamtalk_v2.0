# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# Personality profile: system prompt, voice, animation, and LLM configuration per persona.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from dreamtalk.orchestration.persona.core.types import (
    AnimationProfile,
    EmotionTag,
    LLMParameters,
    MemorySettings,
    PersonaTrait,
    VoiceProfile,
)


@dataclass
class PersonalityProfile:
    """A complete personality profile that defines a persona's behaviour.

    Ported from:
      - Handcrafted Personality Engine: personality.txt, ConversationContextOptions
      - Utsuwa: PersonaCard, CharacterState, PersonalityProfile, StageBehavior

    Each profile contains everything needed to drive the LLM, TTS, and
    Live2D animation systems for one character.
    """

    # Identity
    name: str
    description: str
    version: str = "1.0.0"

    # LLM configuration
    system_prompt: str = ""
    llm_parameters: LLMParameters = field(default_factory=LLMParameters)

    # Voice / TTS
    voice: VoiceProfile = field(default_factory=VoiceProfile)

    # Animation / Live2D
    animation: AnimationProfile = field(default_factory=AnimationProfile)

    # Emotion-to-expression mapping (from EmotionAnimationService.EmotionMap)
    emotion_map: dict[str, EmotionTag] = field(default_factory=dict)

    # Personality traits (from Utsuwa PersonalityProfile)
    traits: dict[str, PersonaTrait] = field(default_factory=dict)

    # Memory configuration
    memory: MemorySettings = field(default_factory=MemorySettings)

    # Conversation context steering (from ConversationContextOptions)
    current_context: str = ""
    topics: list[str] = field(default_factory=lambda: ["casual conversation"])

    def build_system_prompt(self) -> str:
        """Build the full system prompt by injecting traits/context into template.

        Mirrors Utsuwa prompt-builder.ts buildSystemPrompt() pattern.
        """
        parts = [self.system_prompt]

        if self.traits:
            trait_lines = "\n".join(
                f"- {k}: {v.description} ({v.min}-{v.max}, initial {v.initial})"
                for k, v in self.traits.items()
            )
            parts.append(f"\n[PERSONALITY TRAITS]\n{trait_lines}")

        if self.current_context:
            parts.append(f"\n[CURRENT CONTEXT]\n{self.current_context}")

        if self.topics:
            parts.append(f"\n[TOPICS]\n{', '.join(self.topics)}")

        return "\n\n".join(parts)

    def to_dict(self) -> dict:
        """Serialise the entire profile to a dictionary (for storage/exchange)."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "system_prompt": self.system_prompt,
            "llm_parameters": {
                "temperature": self.llm_parameters.temperature,
                "top_p": self.llm_parameters.top_p,
                "max_tokens": self.llm_parameters.max_tokens,
                "frequency_penalty": self.llm_parameters.frequency_penalty,
                "presence_penalty": self.llm_parameters.presence_penalty,
            },
            "voice": {
                "provider": self.voice.provider,
                "voice_id": self.voice.voice_id,
                "pitch": self.voice.pitch,
                "speed": self.voice.speed,
                "language": self.voice.language,
            },
            "animation": {
                "model_id": self.animation.model_id,
                "idle_motion_group": self.animation.idle_motion_group,
                "talking_motion_group": self.animation.talking_motion_group,
            },
            "emotion_map": {
                k: {"expression_id": v.expression_id, "motion_group": v.motion_group}
                for k, v in self.emotion_map.items()
            },
            "traits": {
                k: {
                    "description": v.description,
                    "min": v.min,
                    "max": v.max,
                    "initial": v.initial,
                }
                for k, v in self.traits.items()
            },
            "memory": {
                "type": self.memory.type,
                "max_turns": self.memory.max_turns,
                "max_facts": self.memory.max_facts,
            },
            "context": self.current_context,
            "topics": self.topics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PersonalityProfile:
        """Deserialise from a dictionary."""
        llm = data.get("llm_parameters", {})
        voice = data.get("voice", {})
        anim = data.get("animation", {})
        emap = data.get("emotion_map", {})
        traits_data = data.get("traits", {})
        mem = data.get("memory", {})

        return cls(
            name=data.get("name", "Unnamed"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            system_prompt=data.get("system_prompt", ""),
            llm_parameters=LLMParameters(
                temperature=llm.get("temperature", 0.7),
                top_p=llm.get("top_p", 0.9),
                max_tokens=llm.get("max_tokens", 1024),
                frequency_penalty=llm.get("frequency_penalty", 0.0),
                presence_penalty=llm.get("presence_penalty", 0.0),
            ),
            voice=VoiceProfile(
                provider=voice.get("provider", "kokoro"),
                voice_id=voice.get("voice_id", "af_heart"),
                pitch=voice.get("pitch", 1.0),
                speed=voice.get("speed", 1.0),
                language=voice.get("language", "english"),
            ),
            animation=AnimationProfile(
                model_id=anim.get("model_id", "aria"),
                idle_motion_group=anim.get("idle_motion_group", "Idle"),
                talking_motion_group=anim.get("talking_motion_group", "Talking"),
            ),
            emotion_map={
                k: EmotionTag(
                    expression_id=v.get("expression_id", ""),
                    motion_group=v.get("motion_group", ""),
                )
                for k, v in emap.items()
            },
            traits={
                k: PersonaTrait(
                    description=v.get("description", ""),
                    min=v.get("min", 0),
                    max=v.get("max", 100),
                    initial=v.get("initial", 50),
                )
                for k, v in traits_data.items()
            },
            memory=MemorySettings(
                type=mem.get("type", "conversation"),
                max_turns=mem.get("max_turns", 20),
                max_facts=mem.get("max_facts", 50),
            ),
            current_context=data.get("context", ""),
            topics=data.get("topics", ["casual conversation"]),
        )
