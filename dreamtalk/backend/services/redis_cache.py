# ── Redis Cache Service ───────────────────────────────────────────────
# Provides TTL-based caching for LLM responses, TTS audio, pipeline results.

import os
import json
import hashlib
import logging
from typing import Optional, Any

logger = logging.getLogger("dreamtalk.cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # default 1 hour

_cache_client = None


def _get_client():
    global _cache_client
    if _cache_client is not None:
        return _cache_client
    try:
        import redis.asyncio as aioredis
        _cache_client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        logger.info(f"Redis cache connected: {REDIS_URL}")
    except Exception as e:
        logger.warning(f"Redis cache unavailable: {e}")
        _cache_client = None
    return _cache_client


def _make_key(prefix: str, *parts) -> str:
    raw = ":".join(str(p) for p in parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"dreamtalk:{prefix}:{h}"


async def get_cache(prefix: str, *parts) -> Optional[Any]:
    """Get cached value by prefix + key parts."""
    client = _get_client()
    if client is None:
        return None
    try:
        key = _make_key(prefix, *parts)
        val = await client.get(key)
        if val:
            return json.loads(val)
        return None
    except Exception as e:
        logger.debug(f"Cache get error: {e}")
        return None


async def set_cache(prefix: str, value: Any, ttl: int = CACHE_TTL, *parts) -> bool:
    """Set cached value with TTL."""
    client = _get_client()
    if client is None:
        return False
    try:
        key = _make_key(prefix, *parts)
        await client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.debug(f"Cache set error: {e}")
        return False


async def invalidate_cache(prefix: str, *parts) -> bool:
    """Invalidate a specific cache entry."""
    client = _get_client()
    if client is None:
        return False
    try:
        key = _make_key(prefix, *parts)
        await client.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Cache invalidate error: {e}")
        return False


async def invalidate_prefix(prefix: str) -> int:
    """Invalidate all cache entries with a given prefix."""
    client = _get_client()
    if client is None:
        return 0
    try:
        pattern = f"dreamtalk:{prefix}:*"
        keys = await client.keys(pattern)
        if keys:
            return await client.delete(*keys)
        return 0
    except Exception as e:
        logger.debug(f"Cache invalidate prefix error: {e}")
        return 0
