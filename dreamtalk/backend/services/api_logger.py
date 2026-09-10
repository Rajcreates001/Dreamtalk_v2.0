"""API call logging middleware for the DreamTalk backend."""

import json
import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("dreamtalk.api_logger")


class APILoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        # Extract relevant path prefix
        area = "api"
        if path.startswith("/api/v1/"):
            area = path.split("/")[3]
        elif path.startswith("/api/avatar"):
            area = "avatar"
        elif path.startswith("/ws/"):
            area = "ws"

        response = await call_next(request)
        elapsed = time.perf_counter() - start
        status = response.status_code

        log_line = f"[{area:>10}] {method:>6} {path:<40} {status} ({elapsed*1000:>7.1f}ms)"

        if status >= 400:
            logger.warning(log_line)
        elif elapsed > 2.0:
            logger.info(log_line + " SLOW")
        else:
            logger.info(log_line)

        return response
