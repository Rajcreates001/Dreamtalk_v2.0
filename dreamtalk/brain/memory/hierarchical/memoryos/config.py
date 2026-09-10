# Dreamtalk - Memory Module
# Extracted from MemoryOS

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryOSConfig(BaseModel):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    short_term_capacity: int = 20
    mid_term_top_k: int = 5
    mid_term_heat_threshold: float = 0.5
    mid_term_promotion_interval: int = 5
    long_term_summary_max_tokens: int = 500
    long_term_profile_max_tokens: int = 2000
    long_term_knowledge_chunk_size: int = 1000
    retrieval_short_term_weight: float = 0.4
    retrieval_mid_term_weight: float = 0.35
    retrieval_long_term_weight: float = 0.25
    chroma_collection: str = "memoryos_long_term"
    chroma_persist_dir: Optional[str] = None
    faiss_index_path: Optional[str] = None

    class Config:
        extra = "allow"
