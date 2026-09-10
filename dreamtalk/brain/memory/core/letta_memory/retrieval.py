# Dreamtalk - Memory Module
# Extracted from Letta

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ArchivalRetrieval:
    def __init__(self, storage_uri: Optional[str] = None, storage_type: str = "postgres"):
        self.storage_uri = storage_uri
        self.storage_type = storage_type
        self._passages: List[Dict[str, Any]] = []

    def insert(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        import uuid
        passage = {
            "id": str(uuid.uuid4()),
            "text": text,
            "metadata": metadata or {},
        }
        self._passages.append(passage)
        return passage

    def search(self, query: str, top_k: int = 10, threshold: float = 0.0) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for p in self._passages:
            score = self._score(p["text"], query_lower)
            if score >= threshold:
                results.append({**p, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _score(self, text: str, query_lower: str) -> float:
        text_lower = text.lower()
        words = query_lower.split()
        if not words:
            return 0.0
        matches = sum(1 for w in words if w in text_lower)
        return matches / len(words)

    def delete(self, passage_id: str) -> bool:
        for i, p in enumerate(self._passages):
            if p["id"] == passage_id:
                self._passages.pop(i)
                return True
        return False

    def get_all(self) -> List[Dict[str, Any]]:
        return self._passages.copy()

    def clear(self):
        self._passages.clear()
