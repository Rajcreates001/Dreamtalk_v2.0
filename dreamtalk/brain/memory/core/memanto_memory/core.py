# Dreamtalk - Memory Module
# Extracted from Memanto

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    PREFERENCE = "preference"
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    EMOTIONAL = "emotional"
    RELATIONAL = "relational"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    INTENTIONAL = "intentional"
    REFLEXIVE = "reflexive"
    WORKING = "working"


class ScopeType(str, Enum):
    GLOBAL = "global"
    USER = "user"
    SESSION = "session"
    AGENT = "agent"
    EPHEMERAL = "ephemeral"


class SourceType(str, Enum):
    DIRECT_INPUT = "direct_input"
    LLM_EXTRACTION = "llm_extraction"
    SENSOR = "sensor"
    INFERENCE = "inference"
    SYSTEM = "system"


class MemoryScope(BaseModel):
    type: ScopeType = ScopeType.GLOBAL
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    namespace: str = "default"


class MemoryRecord(BaseModel):
    id: str = ""
    text: str
    memory_type: MemoryType = MemoryType.CONVERSATION
    scope: MemoryScope = Field(default_factory=MemoryScope)
    embedding: Optional[List[float]] = None
    source: SourceType = SourceType.DIRECT_INPUT
    confidence: float = 1.0
    importance: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        use_enum_values = True
