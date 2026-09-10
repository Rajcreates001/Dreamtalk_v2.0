# Dreamtalk - Memory Module
# Extracted from Memanto

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.core.memanto_memory.config import MemantoConfig
from dreamtalk.brain.memory.core.memanto_memory.core import (
    MemoryRecord,
    MemoryScope,
    MemoryType,
    ScopeType,
    SourceType,
)


class MemoryWriteService:
    def __init__(self, config: Optional[MemantoConfig] = None):
        self.config = config or MemantoConfig()
        self._store: Dict[str, MemoryRecord] = {}
        self._embeddings: Dict[str, List[float]] = {}

    def write(
        self,
        text: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        scope: Optional[MemoryScope] = None,
        source: SourceType = SourceType.DIRECT_INPUT,
        confidence: float = 1.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        now = datetime.utcnow().isoformat()
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            text=text,
            memory_type=memory_type,
            scope=scope or MemoryScope(),
            source=source,
            confidence=confidence,
            importance=importance,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self._store[record.id] = record
        return record

    def write_batch(self, records: List[Dict[str, Any]]) -> List[MemoryRecord]:
        results = []
        for r in records:
            results.append(self.write(**r))
        return results

    def update(self, record_id: str, updates: Dict[str, Any]) -> Optional[MemoryRecord]:
        if record_id not in self._store:
            return None
        record = self._store[record_id]
        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.updated_at = datetime.utcnow().isoformat()
        return record

    def delete(self, record_id: str) -> bool:
        if record_id in self._store:
            del self._store[record_id]
            self._embeddings.pop(record_id, None)
            return True
        return False

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        return self._store.get(record_id)

    def get_all(self) -> List[MemoryRecord]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)

    def store_embedding(self, record_id: str, embedding: List[float]):
        self._embeddings[record_id] = embedding

    def get_embedding(self, record_id: str) -> Optional[List[float]]:
        return self._embeddings.get(record_id)


class MemoryReadService:
    def __init__(self, write_service: MemoryWriteService, config: Optional[MemantoConfig] = None):
        self.write_service = write_service
        self.config = config or MemantoConfig()

    def search_semantic(self, query_embedding: List[float], top_k: int = 10) -> List[MemoryRecord]:
        scored = []
        for record in self.write_service.get_all():
            emb = self.write_service.get_embedding(record.id)
            if emb:
                import numpy as np
                score = float(np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb) + 1e-10))
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def search_keyword(self, query: str, top_k: int = 10) -> List[MemoryRecord]:
        results = []
        query_lower = query.lower()
        for record in self.write_service.get_all():
            if query_lower in record.text.lower():
                results.append(record)
        return results[:top_k]

    def search_hybrid(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        semantic_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
    ) -> List[MemoryRecord]:
        sw = semantic_weight or self.config.semantic_weight
        kw = keyword_weight or self.config.keyword_weight
        gw = self.config.graph_weight
        query_lower = query.lower()
        scored = []
        for record in self.write_service.get_all():
            total = 0.0
            emb = self.write_service.get_embedding(record.id)
            if emb:
                import numpy as np
                semantic_score = float(np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb) + 1e-10))
                total += sw * semantic_score
            keyword_score = 1.0 if query_lower in record.text.lower() else 0.0
            total += kw * keyword_score
            total += gw * record.importance
            scored.append((total, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def filter_by_type(self, memory_type: MemoryType) -> List[MemoryRecord]:
        return [r for r in self.write_service.get_all() if r.memory_type == memory_type]

    def filter_by_scope(self, scope_type: ScopeType, scope_id: Optional[str] = None) -> List[MemoryRecord]:
        results = []
        for record in self.write_service.get_all():
            if record.scope.type != scope_type:
                continue
            if scope_type == ScopeType.USER and record.scope.user_id != scope_id:
                continue
            if scope_type == ScopeType.SESSION and record.scope.session_id != scope_id:
                continue
            results.append(record)
        return results
