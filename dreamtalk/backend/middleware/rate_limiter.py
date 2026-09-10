"""
DreamTalk — Rate Limiter Middleware

Token bucket rate limiting for FastAPI.
Supports per-IP and per-user rate limits.
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("dreamtalk.middleware.rate_limiter")


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max tokens
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = __import__("threading").Lock()

    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """Try to consume tokens. Returns (allowed, wait_time)."""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                wait = (tokens - self.tokens) / self.rate
                return False, wait


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware.

    Default limits:
    - 60 requests/minute for general API
    - 10 requests/minute for pipeline endpoints
    - 30 requests/minute for chat/websocket
    """

    def __init__(
        self,
        app,
        default_rate: float = 1.0,       # 1 request per second
        default_capacity: int = 60,       # burst of 60
        pipeline_rate: float = 0.167,     # 10 per minute
        pipeline_capacity: int = 10,
        chat_rate: float = 0.5,           # 30 per minute
        chat_capacity: int = 30,
    ):
        super().__init__(app)
        self._buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(default_rate, default_capacity)
        )
        self._pipeline_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(pipeline_rate, pipeline_capacity)
        )
        self._chat_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(chat_rate, chat_capacity)
        )
        self._default_rate = default_rate
        self._default_capacity = default_capacity

    async def dispatch(self, request: Request, call_next):
        # Skip WebSocket connections — BaseHTTPMiddleware doesn't support them
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None) if hasattr(request.state, "user_id") else None
        identifier = user_id or client_ip

        # Skip rate limiting for health checks and static files
        path = request.url.path
        if path in ("/health", "/livez", "/readyz", "/metrics") or path.startswith("/_next/"):
            return await call_next(request)

        # Select appropriate bucket
        if "/pipeline" in path:
            bucket = self._pipeline_buckets[identifier]
        elif "/ws" in path or "/chat" in path:
            bucket = self._chat_buckets[identifier]
        else:
            bucket = self._buckets[identifier]

        allowed, wait_time = bucket.consume()

        if not allowed:
            logger.warning(f"Rate limited: {identifier} on {path}")
            return Response(
                status_code=429,
                content=f'{{"detail":"Rate limit exceeded. Retry in {wait_time:.1f}s"}}',
                media_type="application/json",
                headers={
                    "Retry-After": str(int(wait_time) + 1),
                    "X-RateLimit-Limit": str(bucket.capacity),
                    "X-RateLimit-Remaining": str(int(bucket.tokens)),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(bucket.tokens)))
        return response
