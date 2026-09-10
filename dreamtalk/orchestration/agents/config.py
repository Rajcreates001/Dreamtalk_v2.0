# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Configuration for Dreamtalk agent orchestration.

Reads from ``config.yaml`` in the Dreamtalk config directory.
Environment variables override config values.
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent configuration — mirrors the subset hermes-agent reads from config.yaml."""

    # Model / provider
    model: str = "gpt-4o"
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    api_mode: str = "chat_completions"

    # Loop limits
    max_iterations: int = 30
    max_tokens: Optional[int] = None

    # Tool sets
    enabled_toolsets: List[str] = field(default_factory=lambda: ["web", "file", "terminal", "vision"])
    disabled_toolsets: List[str] = field(default_factory=list)

    # Session
    session_db_path: Optional[str] = None

    # Paths
    hermes_home: str = ""
    skills_dir: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> AgentConfig:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def resolve_api_key(self) -> str:
        key = self.api_key or os.environ.get("OPENAI_API_KEY", "")
        if key:
            return key
        try:
            config_dir = Path(os.environ.get("DREAMTALK_CONFIG", "~/.dreamtalk")).expanduser()
            auth_file = config_dir / "auth.json"
            if auth_file.exists():
                data = json.loads(auth_file.read_text())
                return data.get("api_key", "")
        except Exception:
            pass
        return ""


_default_config: Optional[AgentConfig] = None


def load_config() -> AgentConfig:
    """Load agent configuration from config.yaml and environment."""
    global _default_config
    if _default_config is not None:
        return _default_config

    cfg = AgentConfig()
    cfg.api_key = cfg.resolve_api_key()

    try:
        config_dir = Path(os.environ.get("DREAMTALK_CONFIG", "~/.dreamtalk")).expanduser()
        config_file = config_dir / "config.yaml"
        if config_file.exists():
            import yaml
            raw = yaml.safe_load(config_file.read_text()) or {}
            agent_cfg = raw.get("agent", {})
            if isinstance(agent_cfg, dict):
                for k, v in agent_cfg.items():
                    if hasattr(cfg, k) and v is not None:
                        setattr(cfg, k, v)
    except Exception as exc:
        logger.debug("config load skipped: %s", exc)

    _default_config = cfg
    return cfg


def get_config() -> AgentConfig:
    return load_config()
