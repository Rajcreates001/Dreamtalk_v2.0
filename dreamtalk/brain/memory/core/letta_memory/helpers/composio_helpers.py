# Adapted from Letta (MemGPT) - Apache 2.0 License
from logging import Logger
from typing import Optional

from dreamtalk.brain.memory.core.letta_memory.schemas.user import User
from dreamtalk.brain.memory.core.letta_memory.services.sandbox_config_manager import SandboxConfigManager
from dreamtalk.brain.memory.core.letta_memory.settings import tool_settings


def get_composio_api_key(actor: User, logger: Optional[Logger] = None) -> Optional[str]:
    api_keys = SandboxConfigManager().list_sandbox_env_vars_by_key(key="COMPOSIO_API_KEY", actor=actor)
    if not api_keys:
        if logger:
            logger.debug("No API keys found for Composio. Defaulting to the environment variable...")
        if tool_settings.composio_api_key:
            return tool_settings.composio_api_key
        else:
            return None
    else:
        # TODO: Add more protections around this
        # Ideally, not tied to a specific sandbox, but for now we just get the first one
        # Theoretically possible for someone to have different composio api keys per sandbox
        return api_keys[0].value


async def get_composio_api_key_async(actor: User, logger: Optional[Logger] = None) -> Optional[str]:
    api_keys = await SandboxConfigManager().list_sandbox_env_vars_by_key_async(key="COMPOSIO_API_KEY", actor=actor)
    if not api_keys:
        if logger:
            logger.debug("No API keys found for Composio. Defaulting to the environment variable...")
        if tool_settings.composio_api_key:
            return tool_settings.composio_api_key
        else:
            return None
    else:
        # TODO: Add more protections around this
        # Ideally, not tied to a specific sandbox, but for now we just get the first one
        # Theoretically possible for someone to have different composio api keys per sandbox
        return api_keys[0].value
