# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Central tool registry — inspired by hermes-agent tools/registry.py.

Each tool module calls ``registry.register()`` at import time to declare
its schema, handler, and toolset. ``get_tool_definitions()`` and
``handle_function_call()`` in the orchestration layer query this registry.
"""

from __future__ import annotations

import ast
import importlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from dreamtalk.orchestration.agents.tools.base import BaseTool, tool_error

logger = logging.getLogger(__name__)


class ToolEntry:
    """Metadata for a single registered tool."""

    __slots__ = ("name", "toolset", "schema", "handler", "check_fn",
                 "requires_env", "is_async", "description", "emoji")

    def __init__(self, name: str, toolset: str, schema: dict, handler: Callable,
                 check_fn: Optional[Callable] = None,
                 requires_env: Optional[list] = None,
                 is_async: bool = False,
                 description: str = "", emoji: str = ""):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.requires_env = requires_env or []
        self.is_async = is_async
        self.description = description or schema.get("description", "")
        self.emoji = emoji


_CHECK_FN_TTL = 30.0
_check_fn_cache: Dict[Callable, tuple] = {}
_check_fn_cache_lock = threading.Lock()


def _check_fn_cached(fn: Callable) -> bool:
    now = time.monotonic()
    with _check_fn_cache_lock:
        cached = _check_fn_cache.get(fn)
        if cached is not None:
            ts, value = cached
            if now - ts < _CHECK_FN_TTL:
                return value
    try:
        value = bool(fn())
    except Exception:
        value = False
    with _check_fn_cache_lock:
        _check_fn_cache[fn] = (now, value)
    return value


def invalidate_check_fn_cache() -> None:
    with _check_fn_cache_lock:
        _check_fn_cache.clear()


def discover_builtin_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """Import tool modules from a directory. Each module self-registers."""
    tools_path = tools_dir or Path(__file__).resolve().parent
    imported: List[str] = []
    for path in sorted(tools_path.glob("*.py")):
        if path.name in {"__init__.py", "base.py", "registry.py"}:
            continue
        mod_name = f"dreamtalk.orchestration.agents.tools.{path.stem}"
        try:
            importlib.import_module(mod_name)
            imported.append(mod_name)
        except Exception as e:
            logger.warning("Could not import tool %s: %s", path.stem, e)
    return imported


class ToolRegistry:
    """Singleton registry — tools register here; queries resolve here."""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._toolset_checks: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self._generation = 0

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Optional[Callable] = None,
        requires_env: Optional[list] = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        tool_cls: Optional[type] = None,
    ):
        """Register a tool. Called at module-import time by each tool file.

        If *tool_cls* is given (a BaseTool subclass), extract schema/handler
        from it instead of requiring separate arguments.
        """
        with self._lock:
            if tool_cls is not None:
                inst = tool_cls()
                name = inst.name
                toolset = inst.toolset
                schema = inst.to_schema()["function"]
                handler = inst.execute
                check_fn = inst.check_fn
                requires_env = inst.requires_env
                is_async = inst.is_async
                description = inst.description
                emoji = inst.emoji

            self._tools[name] = ToolEntry(
                name=name, toolset=toolset, schema=schema,
                handler=handler, check_fn=check_fn,
                requires_env=requires_env or [],
                is_async=is_async,
                description=description,
                emoji=emoji,
            )
            if check_fn and toolset not in self._toolset_checks:
                self._toolset_checks[toolset] = check_fn
            self._generation += 1

    def deregister(self, name: str) -> None:
        with self._lock:
            entry = self._tools.pop(name, None)
            if entry is None:
                return
            still_exists = any(e.toolset == entry.toolset for e in self._tools.values())
            if not still_exists:
                self._toolset_checks.pop(entry.toolset, None)
            self._generation += 1

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        with self._lock:
            return self._tools.get(name)

    def get_definitions(self, tool_names: Set[str]) -> List[dict]:
        """Return OpenAI-format schemas for *tool_names* whose check_fn passes."""
        result: List[dict] = []
        check_results: Dict[Callable, bool] = {}
        with self._lock:
            entries = list(self._tools.values())
        by_name = {e.name: e for e in entries}
        for name in sorted(tool_names):
            entry = by_name.get(name)
            if not entry:
                continue
            if entry.check_fn:
                if entry.check_fn not in check_results:
                    check_results[entry.check_fn] = _check_fn_cached(entry.check_fn)
                if not check_results[entry.check_fn]:
                    continue
            schema = {**entry.schema, "name": entry.name}
            result.append({"type": "function", "function": schema})
        return result

    def dispatch(self, name: str, args: dict, **kwargs) -> str:
        """Execute a tool by name. Catches exceptions as JSON error strings."""
        entry = self.get_entry(name)
        if not entry:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            if entry.is_async:
                import asyncio
                return asyncio.run(entry.handler(args, **kwargs))
            return entry.handler(args, **kwargs)
        except Exception as e:
            logger.exception("Tool %s error: %s", name, e)
            return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

    def get_all_tool_names(self) -> List[str]:
        with self._lock:
            return sorted(e.name for e in self._tools.values())

    def get_tool_to_toolset_map(self) -> Dict[str, str]:
        with self._lock:
            return {e.name: e.toolset for e in self._tools.values()}

    def is_toolset_available(self, toolset: str) -> bool:
        with self._lock:
            check = self._toolset_checks.get(toolset)
        if not check:
            return True
        try:
            return bool(check())
        except Exception:
            return False

    def check_tool_availability(self) -> tuple:
        available, unavailable = [], []
        seen: set = set()
        with self._lock:
            for entry in self._tools.values():
                if entry.toolset in seen:
                    continue
                seen.add(entry.toolset)
                if self.is_toolset_available(entry.toolset):
                    available.append(entry.toolset)
                else:
                    unavailable.append({"name": entry.toolset, "tools": []})
        return available, unavailable


# Module-level singleton
registry = ToolRegistry()
