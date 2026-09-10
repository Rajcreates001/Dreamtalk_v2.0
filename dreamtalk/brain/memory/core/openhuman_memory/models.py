# Dreamtalk - Memory Module
# Extracted from OpenHuman (Rust -> Python port)

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryNode(BaseModel):
    id: str
    text: str
    summary: Optional[str] = None
    depth: int = 0
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    importance: float = 0.5
    access_count: int = 0
    created_at: str = ""
    last_accessed: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryTreeData(BaseModel):
    root_id: Optional[str] = None
    nodes: Dict[str, MemoryNode] = Field(default_factory=dict)
    max_depth: int = 5
    max_children: int = 10
