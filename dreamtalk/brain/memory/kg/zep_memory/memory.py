# Dreamtalk - Memory Module
# Extracted from Zep

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional


class ZepThreadMemory:
    def __init__(self, session_id: str, config: Optional[Dict[str, Any]] = None):
        self.session_id = session_id
        self.config = config or {}
        self._messages: List[Dict[str, Any]] = []
        self._summaries: List[Dict[str, Any]] = []
        self._auto_summarize = self.config.get("auto_summarize", True)
        self._summary_threshold = self.config.get("summary_threshold", 10)

    def add(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "session_id": self.session_id,
        }
        self._messages.append(message)
        if self._auto_summarize and len(self._messages) >= self._summary_threshold:
            self._summarize()
        return message

    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for m in self._messages:
            score = self._score(m["content"], query_lower)
            if score >= min_score:
                results.append({**m, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _score(self, text: str, query_lower: str) -> float:
        text_lower = text.lower()
        words = query_lower.split()
        if not words:
            return 0.0
        matches = sum(1 for w in words if w in text_lower)
        return matches / len(words)

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if limit:
            return self._messages[-limit:]
        return self._messages.copy()

    def get_summaries(self) -> List[Dict[str, Any]]:
        return self._summaries.copy()

    def _summarize(self):
        summary_id = str(uuid.uuid4())
        text = " ".join(m["content"] for m in self._messages[-self._summary_threshold:])
        self._summaries.append({
            "id": summary_id,
            "content": text[:500] + "..." if len(text) > 500 else text,
            "session_id": self.session_id,
        })

    def clear(self):
        self._messages.clear()
        self._summaries.clear()


class ZepEpisodeMemory:
    def __init__(self, episode_id: str, config: Optional[Dict[str, Any]] = None):
        self.episode_id = episode_id
        self.config = config or {}
        self._episodes: Dict[str, List[Dict[str, Any]]] = {}

    def create_episode(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        episode_uuid = str(uuid.uuid4())
        self._episodes[episode_uuid] = {
            "episode_id": episode_uuid,
            "name": name,
            "metadata": metadata or {},
            "messages": [],
        }
        return episode_uuid

    def add_message(self, episode_uuid: str, role: str, content: str) -> Dict[str, Any]:
        if episode_uuid not in self._episodes:
            raise ValueError(f"Episode {episode_uuid} not found")
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "episode_id": episode_uuid,
        }
        self._episodes[episode_uuid]["messages"].append(message)
        return message

    def get_episode(self, episode_uuid: str) -> Optional[Dict[str, Any]]:
        return self._episodes.get(episode_uuid)

    def list_episodes(self) -> List[str]:
        return list(self._episodes.keys())

    def search_across_episodes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        results = []
        for eid, ep in self._episodes.items():
            for m in ep["messages"]:
                if query.lower() in m["content"].lower():
                    results.append({**m, "episode_name": ep["name"]})
        return results[:limit]
