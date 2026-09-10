# Dreamtalk - Memory Module
# Extracted from mem0

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"


class MemoryConfig(BaseModel):
    vector_store: Dict[str, Any] = Field(default_factory=lambda: {"provider": "chroma", "config": {"collection_name": "dreamtalk"}})
    llm: Optional[Dict[str, Any]] = None
    embedder: Dict[str, Any] = Field(default_factory=lambda: {"provider": "openai"})
    history_db: Optional[Dict[str, Any]] = None
    graph_store: Optional[Dict[str, Any]] = None
    version: str = "v1.0"
    custom_prompt: Optional[Dict[str, Any]] = None
    custom_categories: Optional[List[str]] = None
    compatible_providers: Optional[List[str]] = None

    class Config:
        extra = "allow"


class MemoryItem(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    categories: List[str] = Field(default_factory=list)
    context: Optional[str] = None
    event: Optional[str] = None


FACT_RETRIEVAL_PROMPT = (
    "You are an AI assistant specializing in memory extraction and retrieval. "
    "Given the user's input, extract the most relevant facts, entities, and relationships "
    "to store in memory. Output as a JSON object with 'facts', 'entities', and 'relations' keys."
)

ADDITIVE_EXTRACTION_PROMPT = (
    "Analyze the given text and extract all new information that should be added to memory. "
    "Focus on unique entities, events, preferences, and relationships not already present in existing memory."
)
