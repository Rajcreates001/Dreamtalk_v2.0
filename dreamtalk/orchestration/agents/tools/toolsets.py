# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Toolsets — named groups of tools for different scenarios.

Inspired by hermes-agent ``toolsets.py`` (~912 LOC). Toolsets let
agents enable/disable tool groups by name rather than individually.
"""

from __future__ import annotations

from typing import Dict, List, Set

# The default tool set — available on every platform
DREAMTALK_CORE_TOOLS = [
    "web_search", "web_extract",
    "read_file", "write_file", "patch", "search_files",
    "terminal", "process",
    "vision_analyze", "image_generate",
    "skills_list", "skill_view", "skill_manage",
    "delegate_task",
    "memory",
    "clarify",
]

TOOLSETS: Dict[str, dict] = {
    "web": {
        "description": "Web research and content extraction",
        "tools": ["web_search", "web_extract"],
    },
    "file": {
        "description": "File read, write, patch, and search",
        "tools": ["read_file", "write_file", "patch", "search_files"],
    },
    "terminal": {
        "description": "Terminal/command execution and process management",
        "tools": ["terminal", "process"],
    },
    "vision": {
        "description": "Image analysis and vision tools",
        "tools": ["vision_analyze"],
    },
    "image_gen": {
        "description": "Image generation tools",
        "tools": ["image_generate"],
    },
    "skills": {
        "description": "Access, create, and manage skill documents",
        "tools": ["skills_list", "skill_view", "skill_manage"],
    },
    "browser": {
        "description": "Browser automation (navigate, click, type, scroll)",
        "tools": [
            "browser_navigate", "browser_snapshot", "browser_click",
            "browser_type", "browser_scroll", "browser_back",
            "browser_press", "web_search",
        ],
    },
    "delegation": {
        "description": "Task delegation to sub-agents",
        "tools": ["delegate_task"],
    },
    "memory": {
        "description": "Session memory and recall",
        "tools": ["memory"],
    },
    "all": {
        "description": "All available tools",
        "tools": [],  # resolved dynamically
    },
}


def resolve_toolset(name: str) -> List[str]:
    """Resolve a toolset name to its list of tool names.

    Composition: if a toolset's ``includes`` field references other
    toolsets, those are merged in recursively.
    """
    ts = TOOLSETS.get(name)
    if ts is None:
        return []
    tools = list(ts.get("tools", []))
    for included in ts.get("includes", []):
        tools.extend(resolve_toolset(included))
    return tools


def get_all_toolsets() -> Dict[str, dict]:
    """Return the full toolsets dictionary."""
    return dict(TOOLSETS)


def get_toolset_info(name: str) -> Optional[dict]:
    """Return human-readable info for a toolset."""
    ts = TOOLSETS.get(name)
    if ts is None:
        return None
    resolved = resolve_toolset(name)
    return {
        "name": name,
        "description": ts.get("description", ""),
        "tools": resolved,
        "tool_count": len(resolved),
        "includes": ts.get("includes", []),
    }


def validate_toolset(name: str) -> bool:
    """Return True if the toolset name exists."""
    return name in TOOLSETS
