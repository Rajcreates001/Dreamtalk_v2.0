# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Skill registry — discover, load, and manage skills.

Inspired by hermes-agent ``agent/skill_commands.py`` and
``tools/skills_hub.py``. Skills are markdown files with YAML
frontmatter stored in a skills directory.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dreamtalk.orchestration.agents.config import get_config

logger = logging.getLogger(__name__)

# Regex for YAML frontmatter in SKILL.md files
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)

# Skill name sanitization
_INVALID_CHARS_RE = re.compile(r"[^a-z0-9-]")
_MULTI_HYPHEN_RE = re.compile(r"-{2,}")

_skill_registry: Dict[str, dict] = {}


def _sanitize_name(name: str) -> str:
    """Convert a skill name to a clean hyphen-separated slug."""
    name = name.lower().strip()
    name = name.replace(" ", "-").replace("_", "-")
    name = _INVALID_CHARS_RE.sub("", name)
    name = _MULTI_HYPHEN_RE.sub("-", name)
    return name.strip("-")


def discover_skills(skills_dir: Optional[Path] = None) -> Dict[str, dict]:
    """Scan a directory for SKILL.md files and load their metadata.

    Returns dict of {skill_name: skill_metadata}.
    """
    if skills_dir is None:
        cfg = get_config()
        skills_dir = Path(cfg.skills_dir or "~/.dreamtalk/skills").expanduser()

    discovered: Dict[str, dict] = {}

    if not skills_dir.exists():
        logger.debug("Skills directory does not exist: %s", skills_dir)
        return discovered

    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        meta = _load_skill_meta(skill_md)
        if meta:
            name = meta.get("name", _sanitize_name(skill_md.parent.name))
            discovered[name] = meta

    _skill_registry.update(discovered)
    logger.info("Discovered %d skills from %s", len(discovered), skills_dir)
    return discovered


def _load_skill_meta(skill_md: Path) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter from a SKILL.md file."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        logger.debug("Cannot read %s: %s", skill_md, e)
        return None

    m = FRONTMATTER_RE.match(text)
    if not m:
        return None

    try:
        import yaml
        frontmatter = yaml.safe_load(m.group(1)) or {}
    except Exception as e:
        logger.debug("Invalid frontmatter in %s: %s", skill_md, e)
        return None

    body = m.group(2).strip()
    meta = dict(frontmatter)
    meta["_path"] = str(skill_md)
    meta["_body"] = body
    meta["_dir"] = str(skill_md.parent)

    # Normalize name
    if "name" not in meta:
        meta["name"] = _sanitize_name(skill_md.parent.name)
    else:
        meta["name"] = _sanitize_name(str(meta["name"]))

    return meta


def get_skill(name: str) -> Optional[Dict[str, Any]]:
    """Get a skill's full metadata (including body content)."""
    skill = _skill_registry.get(name)
    if skill is not None:
        return skill

    # Try discovering from default directory
    discover_skills()
    return _skill_registry.get(name)


def list_skills() -> List[Dict[str, Any]]:
    """List all discovered skills (name, description, tags)."""
    if not _skill_registry:
        discover_skills()
    return [
        {
            "name": s.get("name", "?"),
            "description": s.get("description", ""),
            "tags": s.get("metadata", {}).get("hermes", {}).get("tags", []),
            "path": s.get("_path", ""),
        }
        for s in _skill_registry.values()
    ]


def get_skill_commands() -> Dict[str, Dict[str, Any]]:
    """Return skill commands in the format expected by the agent loop.

    Returns {skill_name: {description, args_hint, type: 'skill'}}.
    """
    if not _skill_registry:
        discover_skills()
    commands: Dict[str, Dict[str, Any]] = {}
    for name, meta in _skill_registry.items():
        commands[name] = {
            "description": meta.get("description", ""),
            "args_hint": "[prompt]",
            "type": "skill",
        }
    return commands
