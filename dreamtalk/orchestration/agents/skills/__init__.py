# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Skill system — base class, loader, registry.

Skills are markdown files with YAML frontmatter that define
specialized instructions and workflows for the agent.
"""

from dreamtalk.orchestration.agents.skills.registry import (
    discover_skills,
    get_skill,
    list_skills,
    get_skill_commands,
    _skill_registry,
)

__all__ = [
    "discover_skills",
    "get_skill",
    "list_skills",
    "get_skill_commands",
]
