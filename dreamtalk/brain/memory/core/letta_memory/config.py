# Dreamtalk - Memory Module
# Extracted from Letta

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LettaConfig(BaseModel):
    model: str = "gpt-4"
    embedding_model: str = "text-embedding-ada-002"
    embedding_dim: int = 1536
    archival_storage_uri: Optional[str] = None
    archival_storage_type: str = "postgres"
    recall_storage_type: str = "sqlite"
    recall_storage_uri: Optional[str] = None
    memory_blocks: List[str] = Field(default_factory=lambda: ["core", "persona", "human"])
    max_tokens_in_context: int = 8000
    context_window_limit: int = 16000
    agent_name: Optional[str] = None
    system_prompt: Optional[str] = None
    functions: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = "allow"
