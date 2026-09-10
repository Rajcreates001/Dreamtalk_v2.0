# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""Provider abstraction layer.

Inspired by hermes-agent ``providers/__init__.py`` (191 LOC) and
``providers/base.py`` (214 LOC). Each inference backend (OpenAI,
local GPU server, etc.) exposes a ``ProviderProfile`` describing
auth, endpoints, and quirks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from dreamtalk.orchestration.agents.providers.base import ProviderProfile, OMIT_TEMPERATURE

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, ProviderProfile] = {}
_ALIASES: Dict[str, str] = {}


def register_provider(profile: ProviderProfile) -> None:
    """Register a provider profile by name and aliases."""
    _REGISTRY[profile.name] = profile
    for alias in profile.aliases:
        _ALIASES[alias] = profile.name


def get_provider_profile(name: str) -> Optional[ProviderProfile]:
    """Look up a provider profile by name or alias. Returns None if not found."""
    canonical = _ALIASES.get(name, name)
    return _REGISTRY.get(canonical)


def list_providers() -> list[ProviderProfile]:
    """Return all registered provider profiles."""
    return list(_REGISTRY.values())


def get_active_provider() -> ProviderProfile:
    """Return the currently active provider profile (default: openai).

    Reads from environment/config and falls back to the built-in
    OpenAI-compatible profile.
    """
    from dreamtalk.orchestration.agents.config import get_config
    cfg = get_config()
    profile = get_provider_profile(cfg.provider)
    if profile is None:
        # Build a generic OpenAI-compatible profile
        profile = ProviderProfile(
            name=cfg.provider or "openai",
            base_url=cfg.base_url,
            display_name=cfg.provider.title() if cfg.provider else "OpenAI",
        )
    return profile


# Register default OpenAI-compatible provider on import
register_provider(ProviderProfile(
    name="openai",
    aliases=("openai-compatible",),
    display_name="OpenAI Compatible",
    description="Any OpenAI-compatible API endpoint (OpenAI, local GPU servers, etc.)",
    base_url="https://api.openai.com/v1",
    auth_type="api_key",
    env_vars=("OPENAI_API_KEY",),
    supports_vision=True,
    fallback_models=("gpt-4o", "gpt-4o-mini", "gpt-4-turbo"),
))
