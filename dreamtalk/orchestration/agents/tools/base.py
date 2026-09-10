# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Base tool class — every tool handler extends or conforms to this interface."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional


class BaseTool:
    """Base class for Dreamtalk agent tools.

    Each tool subclass defines its schema (name, description, parameters),
    an optional ``check_fn`` for availability gating, and the ``execute``
    handler that returns a JSON string.
    """

    name: str = ""
    toolset: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    emoji: str = "⚡"
    requires_env: List[str] = []
    is_async: bool = False

    def check_fn(self) -> bool:
        """Return True if this tool is available (env vars, deps present)."""
        return True

    def execute(self, args: Dict[str, Any], **kwargs) -> str:
        """Execute the tool. Must return a JSON string.

        Subclasses override this with the actual implementation.
        """
        raise NotImplementedError

    def to_schema(self) -> Dict[str, Any]:
        """Return the OpenAI-compatible function schema dict."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name and cls.__name__ != "BaseTool":
            cls.name = cls.__name__


def tool_result(data: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """Return a JSON success result string."""
    if data is not None:
        return json.dumps(data, ensure_ascii=False)
    return json.dumps(kwargs, ensure_ascii=False)


def tool_error(message: str, **extra) -> str:
    """Return a JSON error result string."""
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)
