# Dreamtalk - Memory Module
# Extracted from chatbot-memory

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.personality.chatbot_memory.config import ChatbotMemoryConfig
from dreamtalk.brain.memory.personality.chatbot_memory.personality import PersonalityManager, PersonalityProfile


class PersonalityUpdater:
    def __init__(self, personality_manager: PersonalityManager, config: Optional[ChatbotMemoryConfig] = None):
        self.manager = personality_manager
        self.config = config or ChatbotMemoryConfig()
        self._client = None
        self._model = self.config.evolution_model

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def evolve(self, name: str, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        profile = self.manager._profiles.get(name)
        if not profile:
            return None
        if profile.interaction_count < self.config.evolution_interval:
            return None
        prompt = self._build_evolution_prompt(profile, conversation_history)
        response = self.client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        try:
            evolution_data = json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, AttributeError):
            return None
        if "traits" in evolution_data:
            profile.traits = evolution_data["traits"]
        if "tone" in evolution_data:
            profile.tone = evolution_data["tone"]
        if "response_guidelines" in evolution_data:
            profile.response_guidelines = evolution_data["response_guidelines"]
        evolution_entry = {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "changes": evolution_data,
            "interaction_count": profile.interaction_count,
        }
        profile.evolution_history.append(evolution_entry)
        profile.interaction_count = 0
        self.manager.save(name)
        return evolution_entry

    def _build_evolution_prompt(self, profile: PersonalityProfile, history: List[Dict[str, str]]) -> str:
        recent = history[-10:] if len(history) > 10 else history
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in recent if "content" in m
        )
        return (
            f"You are evolving a {profile.name} personality.\n"
            f"Current traits: {', '.join(profile.traits)}\n"
            f"Current tone: {profile.tone}\n"
            f"Current guidelines: {'; '.join(profile.response_guidelines)}\n\n"
            f"Recent conversations:\n{history_text}\n\n"
            "Based on these interactions, suggest personality evolution as JSON with keys: "
            "'traits' (list), 'tone' (str), 'response_guidelines' (list). "
            "Make subtle adjustments, not radical changes."
        )

    def reset_evolution(self, name: str):
        profile = self.manager._profiles.get(name)
        if profile:
            profile.evolution_history.clear()
            profile.interaction_count = 0
