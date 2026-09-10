# Dreamtalk - Memory Module
# Extracted from MemoryOS

from __future__ import annotations

import json
import uuid
from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from dreamtalk.brain.memory.hierarchical.memoryos.config import MemoryOSConfig


class MemoryRecord(BaseModel):
    id: str = ""
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    heat: float = 0.0
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0


class ShortTermMemory:
    def __init__(self, capacity: int = 20):
        self.capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)

    def add(self, text: str, embedding: Optional[List[float]] = None, metadata: Optional[Dict[str, Any]] = None) -> MemoryRecord:
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            created_at=__import__("time").time(),
            last_accessed=__import__("time").time(),
        )
        self._buffer.append(record)
        return record

    def get_all(self) -> List[MemoryRecord]:
        return list(self._buffer)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[MemoryRecord]:
        scored = []
        for record in self._buffer:
            if record.embedding:
                score = np.dot(query_embedding, record.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(record.embedding) + 1e-10
                )
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def is_full(self) -> bool:
        return len(self._buffer) >= self.capacity

    def clear(self):
        self._buffer.clear()

    def __len__(self):
        return len(self._buffer)


class MidTermMemory:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._records: List[MemoryRecord] = []
        self._heat_threshold = self.config.get("heat_threshold", 0.5)
        self._promotion_interval = self.config.get("promotion_interval", 5)

    def add(self, text: str, embedding: Optional[List[float]] = None, metadata: Optional[Dict[str, Any]] = None) -> MemoryRecord:
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            created_at=__import__("time").time(),
            last_accessed=__import__("time").time(),
        )
        self._records.append(record)
        return record

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[MemoryRecord]:
        scored = []
        for record in self._records:
            if record.embedding:
                score = np.dot(query_embedding, record.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(record.embedding) + 1e-10
                )
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def update_heat(self, record_id: str, delta: float = 0.1):
        for record in self._records:
            if record.id == record_id:
                record.heat = min(1.0, record.heat + delta)
                record.access_count += 1
                record.last_accessed = __import__("time").time()
                break

    def get_promotable(self) -> List[MemoryRecord]:
        return [r for r in self._records if r.heat >= self._heat_threshold]

    def remove(self, record_id: str):
        self._records = [r for r in self._records if r.id != record_id]

    def get_all(self) -> List[MemoryRecord]:
        return self._records.copy()

    def __len__(self):
        return len(self._records)


class LongTermMemory:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._profiles: Dict[str, Dict[str, Any]] = {}
        self._knowledge_base: List[MemoryRecord] = []

    def add_profile(self, user_id: str, profile_data: Dict[str, Any]):
        if user_id not in self._profiles:
            self._profiles[user_id] = {}
        self._profiles[user_id].update(profile_data)

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._profiles.get(user_id)

    def add_knowledge(self, text: str, embedding: Optional[List[float]] = None, metadata: Optional[Dict[str, Any]] = None) -> MemoryRecord:
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            created_at=__import__("time").time(),
        )
        self._knowledge_base.append(record)
        return record

    def search_knowledge(self, query_embedding: List[float], top_k: int = 10) -> List[MemoryRecord]:
        scored = []
        for record in self._knowledge_base:
            if record.embedding:
                score = np.dot(query_embedding, record.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(record.embedding) + 1e-10
                )
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def get_all_knowledge(self) -> List[MemoryRecord]:
        return self._knowledge_base.copy()

    def get_all_profiles(self) -> Dict[str, Any]:
        return self._profiles.copy()


class MemoryOS:
    def __init__(self, config: Optional[MemoryOSConfig] = None):
        self.config = config or MemoryOSConfig()
        self.short_term = ShortTermMemory(capacity=self.config.short_term_capacity)
        self.mid_term = MidTermMemory(config={
            "heat_threshold": self.config.mid_term_heat_threshold,
            "promotion_interval": self.config.mid_term_promotion_interval,
        })
        self.long_term = LongTermMemory(config={
            "summary_max_tokens": self.config.long_term_summary_max_tokens,
            "profile_max_tokens": self.config.long_term_profile_max_tokens,
        })
        self._client = None
        self._step_count = 0

    @property
    def client(self):
        if self._client is None and self.config.openai_api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.openai_api_key)
        return self._client

    def _get_embedding(self, text: str) -> List[float]:
        if self.client:
            resp = self.client.embeddings.create(
                model=self.config.embedding_model,
                input=[text],
            )
            return resp.data[0].embedding
        return [0.0] * 1536

    def remember(self, text: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> MemoryRecord:
        embedding = self._get_embedding(text)
        record = self.short_term.add(text, embedding, {"user_id": user_id, **(metadata or {})})
        self._step_count += 1
        if self._step_count % self.config.mid_term_promotion_interval == 0:
            self._promote()
        return record

    def recall(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        query_embedding = self._get_embedding(query)
        st_results = self.short_term.search(query_embedding, top_k=top_k)
        mt_results = self.mid_term.search(query_embedding, top_k=top_k)
        lt_results = self.long_term.search_knowledge(query_embedding, top_k=top_k)
        return {
            "short_term": [r.model_dump() for r in st_results],
            "mid_term": [r.model_dump() for r in mt_results],
            "long_term": [r.model_dump() for r in lt_results],
        }

    def _promote(self):
        promotable = self.mid_term.get_promotable()
        for record in promotable:
            self.long_term.add_knowledge(record.text, embedding=record.embedding, metadata={**record.metadata, "promoted_from": "mid_term"})
            self.mid_term.remove(record.id)
        if self.short_term.is_full():
            records = self.short_term.get_all()
            cutoff = len(records) // 2
            for record in records[:cutoff]:
                self.mid_term.add(record.text, embedding=record.embedding, metadata=record.metadata)
            self.short_term.clear()

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.long_term.get_profile(user_id)

    def update_user_profile(self, user_id: str, data: Dict[str, Any]):
        self.long_term.add_profile(user_id, data)

    def get_state(self) -> Dict[str, Any]:
        return {
            "short_term_size": len(self.short_term),
            "mid_term_size": len(self.mid_term),
            "long_term_knowledge_size": len(self.long_term.get_all_knowledge()),
            "long_term_profiles": list(self.long_term.get_all_profiles().keys()),
            "step": self._step_count,
        }
