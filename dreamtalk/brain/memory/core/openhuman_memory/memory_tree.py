# Dreamtalk - Memory Module
# Extracted from OpenHuman (Rust -> Python port)

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.core.openhuman_memory.config import OpenHumanConfig
from dreamtalk.brain.memory.core.openhuman_memory.models import MemoryNode, MemoryTreeData


class MemoryTree:
    def __init__(self, config: Optional[OpenHumanConfig] = None):
        self.config = config or OpenHumanConfig()
        self.data = MemoryTreeData(
            max_depth=self.config.max_tree_depth,
            max_children=self.config.max_children_per_node,
        )

    def add_node(self, text: str, parent_id: Optional[str] = None, importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryNode:
        now = datetime.utcnow().isoformat()
        node = MemoryNode(
            id=str(uuid.uuid4()),
            text=text,
            depth=0,
            parent_id=parent_id,
            importance=importance,
            created_at=now,
            last_accessed=now,
            metadata=metadata or {},
        )
        if parent_id and parent_id in self.data.nodes:
            parent = self.data.nodes[parent_id]
            if len(parent.children_ids) >= self.data.max_children:
                raise ValueError(f"Parent node {parent_id} already has max children ({self.data.max_children})")
            node.depth = parent.depth + 1
            if node.depth > self.data.max_depth:
                raise ValueError(f"Cannot add node: max depth {self.data.max_depth} exceeded")
            parent.children_ids.append(node.id)
        elif parent_id is None and self.data.root_id is None:
            self.data.root_id = node.id
        self.data.nodes[node.id] = node
        return node

    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        node = self.data.nodes.get(node_id)
        if node:
            node.access_count += 1
            node.last_accessed = datetime.utcnow().isoformat()
        return node

    def get_children(self, node_id: str) -> List[MemoryNode]:
        node = self.data.nodes.get(node_id)
        if not node:
            return []
        return [self.data.nodes[cid] for cid in node.children_ids if cid in self.data.nodes]

    def get_path_to_root(self, node_id: str) -> List[MemoryNode]:
        path = []
        current = self.data.nodes.get(node_id)
        while current:
            path.append(current)
            current = self.data.nodes.get(current.parent_id) if current.parent_id else None
        return path

    def search(self, query: str, top_k: int = 5) -> List[MemoryNode]:
        query_lower = query.lower()
        scored = []
        for node in self.data.nodes.values():
            score = 0.0
            if query_lower in node.text.lower():
                score += 1.0
            if node.summary and query_lower in node.summary.lower():
                score += 0.5
            score += node.importance * 0.3
            if score > 0:
                scored.append((score, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]

    def prune(self, threshold: Optional[float] = None):
        threshold = threshold or self.config.prune_threshold
        to_remove = []
        for nid, node in self.data.nodes.items():
            if node.importance < threshold and nid != self.data.root_id:
                to_remove.append(nid)
        for nid in to_remove:
            self._remove_node(nid)

    def _remove_node(self, node_id: str):
        node = self.data.nodes.get(node_id)
        if not node:
            return
        if node.parent_id and node.parent_id in self.data.nodes:
            parent = self.data.nodes[node.parent_id]
            parent.children_ids = [c for c in parent.children_ids if c != node_id]
        for cid in node.children_ids:
            self._remove_node(cid)
        del self.data.nodes[node_id]

    def get_stats(self) -> Dict[str, Any]:
        depths = [n.depth for n in self.data.nodes.values()]
        return {
            "total_nodes": len(self.data.nodes),
            "max_depth": max(depths) if depths else 0,
            "avg_depth": sum(depths) / len(depths) if depths else 0,
            "root_id": self.data.root_id,
        }
