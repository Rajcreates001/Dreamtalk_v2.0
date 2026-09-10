# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""ProviderProfile — declarative description of an LLM inference backend.

From hermes-agent ``providers/base.py``. Profiles describe behavior
without owning client construction or streaming.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Sentinel for "omit temperature entirely"
OMIT_TEMPERATURE = object()


@dataclass
class ProviderProfile:
    """Declarative profile for an inference provider/backend.

    Fields describe auth, endpoints, client quirks, and model catalog.
    Subclass or instantiate with overrides for custom backends.
    """

    # Identity
    name: str = ""
    api_mode: str = "chat_completions"
    aliases: tuple = ()

    # Display metadata
    display_name: str = ""
    description: str = ""
    signup_url: str = ""

    # Auth & endpoints
    env_vars: tuple = ()
    base_url: str = ""
    models_url: str = ""
    auth_type: str = "api_key"

    # Capabilities
    supports_vision: bool = False
    supports_vision_tool_messages: bool = True

    # Model catalog
    fallback_models: tuple = ()
    hostname: str = ""

    # Client quirks
    default_headers: dict = field(default_factory=dict)

    # Request quirks
    fixed_temperature: Any = None
    default_max_tokens: Optional[int] = None

    def get_hostname(self) -> str:
        if self.hostname:
            return self.hostname
        if self.base_url:
            from urllib.parse import urlparse
            return urlparse(self.base_url).hostname or ""
        return ""

    def build_extra_body(self, **context) -> dict:
        """Provider-specific extra_body fields for the API request."""
        return {}

    def build_api_kwargs_extras(
        self, reasoning_config: Optional[dict] = None, **context
    ) -> tuple:
        """Return (extra_body_additions, top_level_kwargs)."""
        return {}, {}
