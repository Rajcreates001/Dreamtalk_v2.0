# Dreamtalk - Memory Module
# Extracted from Memanto

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemantoConfig(BaseModel):
    engine_endpoint: Optional[str] = None
    engine_api_key: Optional[str] = None
    default_namespace: str = "default"
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"
    enable_graph_rag: bool = True
    enable_multi_modal_search: bool = True
    enable_auto_classification: bool = True
    semantic_weight: float = 0.5
    keyword_weight: float = 0.3
    graph_weight: float = 0.2
    top_k: int = 10
    similarity_threshold: float = 0.6

    class Config:
        extra = "allow"
