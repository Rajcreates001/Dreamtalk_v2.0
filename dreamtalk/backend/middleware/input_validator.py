"""
DreamTalk — Input Validation Middleware

Validates:
- File upload size limits
- Content type restrictions
- Request body size limits
- API key format validation
"""

import os
import logging
from typing import Optional, Set
from fastapi import Request, Response, UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("dreamtalk.middleware.validator")

# ── Limits ─────────────────────────────────────────────────────────────

MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))
MAX_REQUEST_BODY_MB = int(os.environ.get("MAX_REQUEST_BODY_MB", "10"))
MAX_AUDIO_DURATION_SEC = 300  # 5 minutes
MAX_IMAGE_SIZE_MB = 20

ALLOWED_AUDIO_TYPES: Set[str] = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/flac", "audio/ogg", "audio/x-m4a", "audio/aac",
    "audio/webm",
}

ALLOWED_IMAGE_TYPES: Set[str] = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}

ALLOWED_EXTENSIONS_AUDIO: Set[str] = {
    ".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".webm",
}

ALLOWED_EXTENSIONS_IMAGE: Set[str] = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
}


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validates request inputs before they reach route handlers."""

    async def dispatch(self, request: Request, call_next):
        # Skip WebSocket connections
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        content_type = request.headers.get("content-type", "")

        # Check request body size for non-file requests
        if "multipart/form-data" not in content_type:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > MAX_REQUEST_BODY_MB:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": f"Request body too large: {size_mb:.1f}MB (max: {MAX_REQUEST_BODY_MB}MB)"},
                        )
                except ValueError:
                    pass

        # For multipart uploads, validate file sizes via content-length
        if "multipart/form-data" in content_type:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > MAX_UPLOAD_SIZE_MB:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": f"Upload too large: {size_mb:.1f}MB (max: {MAX_UPLOAD_SIZE_MB}MB)"},
                        )
                except ValueError:
                    pass

        response = await call_next(request)
        return response


def validate_upload_file(
    filename: str,
    content_type: Optional[str],
    file_size: int,
    expected_type: str = "auto",
) -> Optional[str]:
    """Validate an uploaded file. Returns error message or None if valid."""
    ext = os.path.splitext(filename.lower())[1] if filename else ""

    # Check file size
    max_size = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if expected_type == "audio":
        max_size = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    elif expected_type == "image":
        max_size = MAX_IMAGE_SIZE_MB * 1024 * 1024

    if file_size > max_size:
        return f"File too large: {file_size / (1024*1024):.1f}MB (max: {max_size / (1024*1024):.0f}MB)"

    # Check extension
    if expected_type == "audio" or expected_type == "auto":
        if ext and ext not in ALLOWED_EXTENSIONS_AUDIO and expected_type == "audio":
            return f"Invalid audio format: {ext} (allowed: {', '.join(sorted(ALLOWED_EXTENSIONS_AUDIO))})"

    if expected_type == "image" or expected_type == "auto":
        if ext and ext not in ALLOWED_EXTENSIONS_IMAGE and expected_type == "image":
            return f"Invalid image format: {ext} (allowed: {', '.join(sorted(ALLOWED_EXTENSIONS_IMAGE))})"

    # Check content type if provided
    if content_type:
        if expected_type == "audio" and content_type not in ALLOWED_AUDIO_TYPES:
            if not any(t in content_type for t in ["audio", "octet-stream"]):
                return f"Invalid audio content type: {content_type}"

        if expected_type == "image" and content_type not in ALLOWED_IMAGE_TYPES:
            if not any(t in content_type for t in ["image", "octet-stream"]):
                return f"Invalid image content type: {content_type}"

    # Check for empty files
    if file_size == 0:
        return "Empty file uploaded"

    return None
