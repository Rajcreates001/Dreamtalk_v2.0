# Dreamtalk - Memory Module
# Extracted from Zep

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional


class ZepGraphStorage:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []
        self._facts: List[Dict[str, Any]] = []
        self._max_entities = self.config.get("graph_search_k", 25)

    def add_entity(self, name: str, entity_type: str = "unknown", metadata: Optional[Dict[str, Any]] = None) -> str:
        eid = str(uuid.uuid4())
        self._entities[eid] = {
            "id": eid,
            "name": name,
            "type": entity_type,
            "metadata": metadata or {},
        }
        return eid

    def add_edge(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0) -> str:
        eid = str(uuid.uuid4())
        self._edges.append({
            "id": eid,
            "source": source_id,
            "target": target_id,
            "relationship": relationship,
            "weight": weight,
        })
        return eid

    def add_fact(self, fact_text: str, entities: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        fid = str(uuid.uuid4())
        self._facts.append({
            "id": fid,
            "fact": fact_text,
            "entities": entities or [],
            "metadata": metadata or {},
        })
        return fid

    def search_entities(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        limit = limit or self._max_entities
        results = []
        query_lower = query.lower()
        for e in self._entities.values():
            if query_lower in e["name"].lower():
                results.append(e)
        return results[:limit]

    def search_facts(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        limit = limit or self.config.get("fact_limits", 30)
        results = []
        query_lower = query.lower()
        for f in self._facts:
            if query_lower in f["fact"].lower():
                results.append(f)
        return results[:limit]

    def get_entity_edges(self, entity_id: str) -> List[Dict[str, Any]]:
        return [
            e for e in self._edges
            if e["source"] == entity_id or e["target"] == entity_id
        ]

    def get_graph_state(self) -> Dict[str, Any]:
        return {
            "entities": len(self._entities),
            "edges": len(self._edges),
            "facts": len(self._facts),
        }


class ZepUserStorage:
    def __init__(self, user_id: str, config: Optional[Dict[str, Any]] = None):
        self.user_id = user_id
        self.config = config or {}
        self.graph = ZepGraphStorage(config)
        self._profile: Dict[str, Any] = {}

    def update_profile(self, data: Dict[str, Any]):
        self._profile.update(data)

    def get_profile(self) -> Dict[str, Any]:
        return self._profile.copy()

    def add_user_entity(self, name: str, entity_type: str = "user_attribute", metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.graph.add_entity(name, entity_type, {"user_id": self.user_id, **(metadata or {})})

    def add_user_fact(self, fact_text: str, entities: Optional[List[str]] = None) -> str:
        return self.graph.add_fact(fact_text, entities, {"user_id": self.user_id})

    def search_user_memory(self, query: str) -> Dict[str, Any]:
        entities = self.graph.search_entities(query)
        facts = self.graph.search_facts(query)
        return {
            "entities": entities,
            "facts": facts,
            "profile": self._profile,
        }
