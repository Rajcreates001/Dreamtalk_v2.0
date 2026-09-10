# Dreamtalk - Memory Module
# Extracted from Zep

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.kg.zep_memory.memory import ZepThreadMemory, ZepEpisodeMemory
from dreamtalk.brain.memory.kg.zep_memory.graph import ZepGraphStorage, ZepUserStorage


class ZepSearchTool:
    def __init__(self, thread_memory: Optional[ZepThreadMemory] = None, graph: Optional[ZepGraphStorage] = None):
        self.thread_memory = thread_memory
        self.graph = graph
        self.name = "zep_search"
        self.description = "Search through Zep memory stores (thread history and knowledge graph)"

    def __call__(self, query: str, source: str = "all", limit: int = 10) -> Dict[str, Any]:
        results = {}
        if source in ("all", "thread") and self.thread_memory:
            results["thread"] = self.thread_memory.search(query, limit=limit)
        if source in ("all", "graph") and self.graph:
            results["entities"] = self.graph.search_entities(query, limit=limit)
            results["facts"] = self.graph.search_facts(query, limit=limit)
        return results


class ZepAddMemoryTool:
    def __init__(self, thread_memory: ZepThreadMemory):
        self.thread_memory = thread_memory
        self.name = "zep_add_memory"
        self.description = "Add a message to Zep thread memory"

    def __call__(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.thread_memory.add(role, content, metadata)


class ZepAddGraphDataTool:
    def __init__(self, graph: ZepGraphStorage):
        self.graph = graph
        self.name = "zep_add_graph_data"
        self.description = "Add entities, edges, and facts to the Zep knowledge graph"

    def add_entity(self, name: str, entity_type: str = "unknown", metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.graph.add_entity(name, entity_type, metadata)

    def add_edge(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0) -> str:
        return self.graph.add_edge(source_id, target_id, relationship, weight)

    def add_fact(self, fact_text: str, entities: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.graph.add_fact(fact_text, entities, metadata)
