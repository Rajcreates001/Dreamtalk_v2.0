# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""OpenAI-compatible provider — for local GPU servers and OpenAI API."""

from __future__ import annotations

from dreamtalk.orchestration.agents.providers import register_provider
from dreamtalk.orchestration.agents.providers.base import ProviderProfile

# Register the standard OpenAI provider
register_provider(ProviderProfile(
    name="openai",
    aliases=("openai-compatible",),
    display_name="OpenAI Compatible",
    description="Any OpenAI-compatible API (OpenAI, local GPU server, vLLM, Ollama, etc.)",
    base_url="https://api.openai.com/v1",
    auth_type="api_key",
    env_vars=("OPENAI_API_KEY",),
    supports_vision=True,
    fallback_models=("gpt-4o", "gpt-4o-mini", "gpt-4-turbo"),
))

# Local GPU server profile (no API key required)
register_provider(ProviderProfile(
    name="local",
    aliases=("local-gpu", "vllm", "ollama"),
    display_name="Local GPU Server",
    description="Local or self-hosted OpenAI-compatible inference server",
    base_url="http://localhost:8000/v1",
    auth_type="api_key",
    env_vars=(),
    supports_vision=False,
    fallback_models=("local-model",),
))
