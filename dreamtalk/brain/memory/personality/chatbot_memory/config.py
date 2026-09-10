# Dreamtalk - Memory Module
# Extracted from chatbot-memory

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatbotMemoryConfig(BaseModel):
    personality_dir: str = "personalities"
    default_personality: str = "friendly"
    evolution_interval: int = 5
    evolution_model: str = "gpt-4o-mini"
    max_history_for_summary: int = 20
    summary_max_tokens: int = 500
    enable_evolution: bool = True
    enable_sentiment_tracking: bool = True
    enable_goal_tracking: bool = True
    personality_templates: List[str] = Field(default_factory=lambda: [
        "friendly", "professional", "humorous", "empathetic", "wise", "custom"
    ])

    class Config:
        extra = "allow"
