# Dreamtalk - Memory Module
# Extracted from Letta

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Block(BaseModel):
    name: str
    value: str
    limit: int = 2048
    label: Optional[str] = None
    is_template: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_value(self, new_value: str):
        if len(new_value) > self.limit:
            new_value = new_value[:self.limit]
        self.value = new_value


class Memory(BaseModel):
    core: Optional[Block] = None
    persona: Optional[Block] = None
    human: Optional[Block] = None
    blocks: List[Block] = Field(default_factory=list)

    def get_block_by_name(self, name: str) -> Optional[Block]:
        for block in self.blocks:
            if block.name == name:
                return block
        return None


class RecallMemory(BaseModel):
    id: str
    content: str
    timestamp: str
    memory_type: str = "recall"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextWindowOverview(BaseModel):
    num_messages: int = 0
    total_tokens: int = 0
    num_archival_memories: int = 0
    num_recall_memories: int = 0
    blocks: List[Block] = Field(default_factory=list)
    memory: Optional[Memory] = None
    exceed_context_limit: bool = False


class Passage(BaseModel):
    id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"
