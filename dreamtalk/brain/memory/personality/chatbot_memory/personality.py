# Dreamtalk - Memory Module
# Extracted from chatbot-memory

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from dreamtalk.brain.memory.personality.chatbot_memory.config import ChatbotMemoryConfig


class PersonalityProfile(BaseModel):
    name: str
    traits: List[str] = Field(default_factory=list)
    tone: str = "neutral"
    style: str = "conversational"
    values: List[str] = Field(default_factory=list)
    knowledge_domains: List[str] = Field(default_factory=list)
    response_guidelines: List[str] = Field(default_factory=list)
    examples: List[Dict[str, str]] = Field(default_factory=list)
    evolution_history: List[Dict[str, Any]] = Field(default_factory=list)
    interaction_count: int = 0


class PersonalityManager:
    def __init__(self, config: Optional[ChatbotMemoryConfig] = None):
        self.config = config or ChatbotMemoryConfig()
        self._profiles: Dict[str, PersonalityProfile] = {}
        self._current_profile: Optional[str] = None

    def load(self, name: str) -> Optional[PersonalityProfile]:
        filepath = os.path.join(self.config.personality_dir, f"{name}.json")
        if not os.path.exists(filepath):
            profile = self._create_default(name)
            self._profiles[name] = profile
            return profile
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        profile = PersonalityProfile(**data)
        self._profiles[name] = profile
        return profile

    def save(self, name: str):
        profile = self._profiles.get(name)
        if not profile:
            raise ValueError(f"Profile {name} not loaded")
        os.makedirs(self.config.personality_dir, exist_ok=True)
        filepath = os.path.join(self.config.personality_dir, f"{name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=2)

    def _create_default(self, name: str) -> PersonalityProfile:
        defaults = {
            "friendly": PersonalityProfile(name="friendly", traits=["warm", "approachable", "helpful"], tone="friendly"),
            "professional": PersonalityProfile(name="professional", traits=["formal", "precise", "efficient"], tone="professional"),
            "humorous": PersonalityProfile(name="humorous", traits=["witty", "playful", "clever"], tone="humorous"),
            "empathetic": PersonalityProfile(name="empathetic", traits=["caring", "understanding", "patient"], tone="empathetic"),
            "wise": PersonalityProfile(name="wise", traits=["thoughtful", "reflective", "philosophical"], tone="wise"),
        }
        return defaults.get(name, PersonalityProfile(name=name))

    def activate(self, name: str):
        if name not in self._profiles:
            self.load(name)
        self._current_profile = name

    def get_active(self) -> Optional[PersonalityProfile]:
        if self._current_profile:
            return self._profiles.get(self._current_profile)
        return None

    def list_profiles(self) -> List[str]:
        return list(self._profiles.keys())

    def update_profile(self, name: str, updates: Dict[str, Any]):
        profile = self._profiles.get(name)
        if not profile:
            raise ValueError(f"Profile {name} not found")
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.interaction_count += 1

    def get_prompt_prefix(self) -> str:
        profile = self.get_active()
        if not profile:
            return ""
        lines = [f"You are a {profile.name} assistant."]
        if profile.traits:
            lines.append(f"Traits: {', '.join(profile.traits)}")
        lines.append(f"Tone: {profile.tone}")
        lines.append(f"Style: {profile.style}")
        if profile.response_guidelines:
            lines.append("Guidelines:")
            for g in profile.response_guidelines:
                lines.append(f"- {g}")
        return "\n".join(lines)
