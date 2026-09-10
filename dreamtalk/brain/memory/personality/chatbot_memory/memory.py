# Dreamtalk - Memory Module
# Extracted from chatbot-memory

from __future__ import annotations

import json
from collections import deque
from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.personality.chatbot_memory.config import ChatbotMemoryConfig


class MemoryManager:
    def __init__(self, config: Optional[ChatbotMemoryConfig] = None):
        self.config = config or ChatbotMemoryConfig()
        self._conversations: Dict[str, deque] = {}
        self._summaries: Dict[str, List[str]] = {}
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def add_message(self, conversation_id: str, role: str, content: str):
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = deque(maxlen=self.config.max_history_for_summary)
            self._summaries[conversation_id] = []
        self._conversations[conversation_id].append({"role": role, "content": content})
        if len(self._conversations[conversation_id]) >= self.config.max_history_for_summary:
            self._summarize(conversation_id)

    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        return list(self._conversations.get(conversation_id, []))

    def get_summary(self, conversation_id: str) -> Optional[str]:
        summaries = self._summaries.get(conversation_id, [])
        if not summaries:
            return None
        return " ".join(summaries[-3:])

    def get_context(self, conversation_id: str, include_summary: bool = True) -> str:
        history = self.get_history(conversation_id)
        parts = []
        if include_summary:
            summary = self.get_summary(conversation_id)
            if summary:
                parts.append(f"Summary: {summary}")
        for msg in history:
            parts.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(parts)

    def _summarize(self, conversation_id: str):
        history = self.get_history(conversation_id)
        if not history:
            return
        text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        prompt = (
            f"Summarize the following conversation concisely (max {self.config.summary_max_tokens} tokens):\n\n{text}"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.config.evolution_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.summary_max_tokens,
            )
            summary = response.choices[0].message.content
            self._summaries[conversation_id].append(summary)
            self._conversations[conversation_id].clear()
        except Exception as e:
            self._summaries[conversation_id].append(f"[Summary error: {e}]")

    def clear_conversation(self, conversation_id: str):
        self._conversations.pop(conversation_id, None)
        self._summaries.pop(conversation_id, None)

    def list_conversations(self) -> List[str]:
        return list(self._conversations.keys())
