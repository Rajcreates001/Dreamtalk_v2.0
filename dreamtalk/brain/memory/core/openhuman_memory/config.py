# Dreamtalk - Memory Module
# Extracted from OpenHuman (Rust -> Python port)

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OpenHumanConfig(BaseModel):
    max_tree_depth: int = 5
    max_children_per_node: int = 10
    token_budget: int = 4096
    compression_ratio: float = 0.5
    summarization_model: str = "gpt-4o-mini"
    enable_token_juice: bool = True
    enable_memory_tree: bool = True
    auto_prune: bool = True
    prune_threshold: float = 0.3
    similarity_top_k: int = 5

    class Config:
        extra = "allow"
