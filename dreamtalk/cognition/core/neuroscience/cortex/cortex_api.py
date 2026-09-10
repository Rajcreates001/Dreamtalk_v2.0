# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT

from __future__ import annotations

from typing import Any

from dreamtalk.cognition.core.neuroscience.cortex.config import CortexConfig, DEFAULT_CONFIG
from dreamtalk.cognition.core.neuroscience.cortex.inference import CortexInferenceEngine
from dreamtalk.cognition.core.neuroscience.cortex.core.memory import (
    compute_importance,
    compute_valence,
    compute_heat_decay,
    compute_surprise,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.emotion import (
    detect_emotions,
    tag_memory_emotions,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.hippocampus import (
    run_swr_replay,
    format_restoration,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.mcp_tools import (
    list_tools,
    get_tool,
)


class CortexAPI:
    def __init__(self, config: CortexConfig | None = None):
        self.config = config or DEFAULT_CONFIG
        self.inference_engine = CortexInferenceEngine(self.config)

    def remember(self, content: str, tags: list[str] | None = None, domain: str = "") -> dict[str, Any]:
        return self.inference_engine.ingest(content, tags, domain)

    def recall(self, query: str = "", top_k: int = 5) -> list[dict[str, Any]]:
        return self.inference_engine.recall(query, top_k)

    def consolidate(self) -> list[dict[str, Any]]:
        return self.inference_engine.decay()

    def replay(self) -> dict[str, Any]:
        return self.inference_engine.replay()

    def analyze_emotion(self, content: str) -> dict[str, Any]:
        return tag_memory_emotions(content)

    def score_importance(self, content: str, tags: list[str] | None = None) -> float:
        return compute_importance(content, tags)

    def score_valence(self, content: str) -> float:
        return compute_valence(content)

    def list_mcp_tools(self) -> dict[str, str]:
        return list_tools()

    def call_mcp_tool(self, tool_name: str, **kwargs) -> Any:
        fn = get_tool(tool_name)
        return fn(**kwargs)

    def get_status(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "memory": self.inference_engine.get_status(),
        }
