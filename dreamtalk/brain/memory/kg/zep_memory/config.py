# Dreamtalk - Memory Module
# Extracted from Zep

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ZepConfig(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.zep.ai/api/v2"
    project_uuid: Optional[str] = None
    thread_pool_size: int = 4
    default_search_limit: int = 10
    default_search_min_score: float = 0.5
    auto_summarize: bool = True
    graph_search_k: int = 25
    fact_limits: int = 30
    enable_graph: bool = True
    enable_user_storage: bool = True

    class Config:
        extra = "allow"
