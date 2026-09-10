# Adapted from Letta (MemGPT) - Apache 2.0 License
import aiohttp

from dreamtalk.brain.memory.core.letta_memory.log import get_logger
from dreamtalk.brain.memory.core.letta_memory.utils import smart_urljoin

logger = get_logger(__name__)


async def mistral_get_model_list_async(url: str, api_key: str) -> dict:
    url = smart_urljoin(url, "models")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    logger.debug("Sending request to %s", url)

    async with aiohttp.ClientSession() as session:
        # TODO add query param "tool" to be true
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.json()
