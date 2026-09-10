# Dreamtalk - Memory Module
# Extracted from MemoryOS

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.hierarchical.memoryos.memoryos import MemoryOS, MemoryRecord


class MemoryOSRetriever:
    def __init__(self, memoryos: MemoryOS):
        self.memoryos = memoryos

    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryRecord]:
        query_embedding = self.memoryos._get_embedding(query)
        scored: List[tuple] = []
        st_weight = self.memoryos.config.retrieval_short_term_weight
        mt_weight = self.memoryos.config.retrieval_mid_term_weight
        lt_weight = self.memoryos.config.retrieval_long_term_weight

        for record in self.memoryos.short_term.get_all():
            if record.embedding:
                score = self._cosine_sim(query_embedding, record.embedding) * st_weight
                scored.append((score, record))

        for record in self.memoryos.mid_term.get_all():
            if record.embedding:
                score = self._cosine_sim(query_embedding, record.embedding) * mt_weight + record.heat * 0.1
                scored.append((score, record))

        for record in self.memoryos.long_term.get_all_knowledge():
            if record.embedding:
                score = self._cosine_sim(query_embedding, record.embedding) * lt_weight
                scored.append((score, record))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def retrieve_by_tier(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        query_embedding = self.memoryos._get_embedding(query)
        st_results = self.memoryos.short_term.search(query_embedding, top_k)
        mt_results = self.memoryos.mid_term.search(query_embedding, top_k)
        lt_results = self.memoryos.long_term.search_knowledge(query_embedding, top_k)
        return {
            "short_term": [r.model_dump() for r in st_results],
            "mid_term": [r.model_dump() for r in mt_results],
            "long_term": [r.model_dump() for r in lt_results],
        }

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        import numpy as np
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

    def update_heat(self, record_ids: List[str], delta: float = 0.1):
        for rid in record_ids:
            self.memoryos.mid_term.update_heat(rid, delta)
