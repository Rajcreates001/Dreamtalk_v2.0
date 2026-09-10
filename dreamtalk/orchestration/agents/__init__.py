# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Dreamtalk agent orchestration — agent core, tools, providers, skills."""

from dreamtalk.orchestration.agents.config import get_config, AgentConfig
from dreamtalk.orchestration.agents.core.agent_loop import AIAgent

__all__ = ["AIAgent", "get_config", "AgentConfig"]
