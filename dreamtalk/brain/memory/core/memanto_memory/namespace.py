# Dreamtalk - Memory Module
# Extracted from Memanto

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.core.memanto_memory.core import MemoryScope, ScopeType


class NamespaceService:
    def __init__(self):
        self._namespaces: Dict[str, List[str]] = {}

    def resolve_namespace(self, scope: MemoryScope) -> str:
        parts = [scope.namespace]
        if scope.type == ScopeType.USER and scope.user_id:
            parts.append(f"user_{scope.user_id}")
        elif scope.type == ScopeType.SESSION and scope.session_id:
            parts.append(f"session_{scope.session_id}")
        elif scope.type == ScopeType.AGENT and scope.agent_id:
            parts.append(f"agent_{scope.agent_id}")
        elif scope.type == ScopeType.EPHEMERAL:
            parts.append("ephemeral")
        return "_".join(parts)

    def create_namespace(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        if name not in self._namespaces:
            self._namespaces[name] = []
        if metadata:
            self._namespaces[name].append(metadata)

    def list_namespaces(self) -> List[str]:
        return list(self._namespaces.keys())

    def namespace_exists(self, name: str) -> bool:
        return name in self._namespaces

    def delete_namespace(self, name: str):
        if name in self._namespaces:
            del self._namespaces[name]

    def get_namespace_metadata(self, name: str) -> List[Dict[str, Any]]:
        return self._namespaces.get(name, [])
