"""Stable v1 API for the complete DreamTalk avatar runtime."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket
from pydantic import BaseModel, Field

from dreamtalk.backend.services.avatar_runtime import get_avatar_runtime
from dreamtalk.backend.services.cloned_speech import INDICF5_LANGUAGES
from dreamtalk.backend.services.multimodal_language import (
    SUPPORTED_LANGUAGES,
    detect_text_language,
)

logger = logging.getLogger("dreamtalk.avatar.api.v1")

router = APIRouter(prefix="/api/v1/avatar", tags=["Avatar Runtime v1"])

MAX_AUDIO_BYTES = 100 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024


class AvatarChatRequest(BaseModel):
    message: Optional[str] = None
    text: Optional[str] = None
    profile_id: Optional[str] = None
    language: str = "auto"
    history: list[dict[str, str]] = Field(default_factory=list)
    synthesize: bool = True
    strict_clone: bool = True
    render_video: bool = False

    def resolved_message(self) -> str:
        return (self.message or self.text or "").strip()


class TTSRequest(BaseModel):
    text: str
    profile_id: Optional[str] = None
    language: str = "auto"
    emotion: str = "neutral"
    strict_clone: bool = True


class TwoDSpeakRequest(TTSRequest):
    engine: str = "auto"


class LanguageRequest(BaseModel):
    text: str
    preferred_language: Optional[str] = None


def _raise_api_error(exc: Exception) -> None:
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail="Avatar profile not found") from exc
    if isinstance(exc, (ValueError, FileNotFoundError)):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    logger.exception("Avatar runtime request failed")
    raise HTTPException(status_code=500, detail="Avatar runtime request failed") from exc


async def _save_upload(upload: UploadFile, directory: Path, max_bytes: int) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    filename = Path(upload.filename or "upload.bin").name
    destination = directory / filename
    if destination.exists():
        destination = directory / f"{destination.stem}_{len(list(directory.iterdir()))}{destination.suffix}"
    size = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                destination.unlink(missing_ok=True)
                raise ValueError(f"Upload '{filename}' exceeds the {max_bytes // (1024 * 1024)} MB limit")
            output.write(chunk)
    if size == 0:
        destination.unlink(missing_ok=True)
        raise ValueError(f"Upload '{filename}' is empty")
    return str(destination)


def _parse_history(raw: str) -> list[dict[str, str]]:
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("history must be valid JSON") from exc
    if not isinstance(data, list):
        raise ValueError("history must be a JSON array")
    return [item for item in data if isinstance(item, dict)]


@router.get("/status")
async def runtime_status():
    return await get_avatar_runtime().status()


@router.get("/languages")
async def supported_languages():
    return {
        "languages": SUPPORTED_LANGUAGES,
        "automatic_detection": True,
        "voice_clone_engine": "indicf5",
        "voice_clone_languages": {
            code: SUPPORTED_LANGUAGES[code] for code in sorted(INDICF5_LANGUAGES)
        },
        "english": {
            "asr": True,
            "conversation": True,
            "generic_tts": True,
            "indicf5_clone": False,
        },
    }


@router.post("/detect-language")
async def detect_language(request: LanguageRequest):
    return detect_text_language(request.text, request.preferred_language).to_dict()


@router.post("/profiles")
async def create_profile(
    name: str = Form("DreamTalk Avatar"),
    user_id: str = Form("default"),
    reference_text: str = Form(""),
    language: str = Form("auto"),
    validate_clone: bool = Form(True),
    voice_sample: UploadFile = File(...),
    face_images: list[UploadFile] = File(...),
):
    """Create and validate a human avatar from face image(s) and voice audio."""
    try:
        with tempfile.TemporaryDirectory(prefix="dreamtalk_profile_upload_") as temp:
            temp_root = Path(temp)
            voice_path = await _save_upload(voice_sample, temp_root / "voice", MAX_AUDIO_BYTES)
            image_paths = [
                await _save_upload(image, temp_root / "images", MAX_IMAGE_BYTES)
                for image in face_images
            ]
            return await get_avatar_runtime().create_profile(
                name=name,
                user_id=user_id,
                voice_sample_path=voice_path,
                face_image_paths=image_paths,
                reference_text=reference_text,
                language=language,
                validate_clone=validate_clone,
            )
    except Exception as exc:
        _raise_api_error(exc)


@router.get("/profiles")
async def list_profiles():
    runtime = get_avatar_runtime()
    return {"profiles": [runtime.public_profile(item) for item in runtime.store.list()]}


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    runtime = get_avatar_runtime()
    profile = runtime.store.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Avatar profile not found")
    return runtime.public_profile(profile)


@router.post("/profiles/{profile_id}/activate")
async def activate_profile(profile_id: str):
    runtime = get_avatar_runtime()
    try:
        return runtime.public_profile(runtime.store.activate(profile_id))
    except Exception as exc:
        _raise_api_error(exc)


@router.get("/profiles/{profile_id}/manifest")
async def avatar_manifest(profile_id: str):
    runtime = get_avatar_runtime()
    profile = runtime.store.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Avatar profile not found")
    public = runtime.public_profile(profile)
    return {
        "profile": public,
        "render": public.get("appearance", {}),
        "realtime": {
            "websocket": "/api/v1/avatar/ws/realtime",
            "chat": f"/api/v1/avatar/profiles/{profile_id}/respond",
            "audio_chat": f"/api/v1/avatar/profiles/{profile_id}/respond/audio",
        },
    }


async def _run_chat(request: AvatarChatRequest, forced_profile_id: Optional[str] = None) -> dict[str, Any]:
    message = request.resolved_message()
    if not message:
        raise HTTPException(status_code=422, detail="message or text is required")
    try:
        return await get_avatar_runtime().process_text(
            message=message,
            profile_id=forced_profile_id or request.profile_id,
            language=request.language,
            history=request.history,
            synthesize=request.synthesize,
            strict_clone=request.strict_clone,
            render_video=request.render_video,
        )
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/chat")
async def avatar_chat(request: AvatarChatRequest):
    """Compatibility chat endpoint using the active profile by default."""
    return await _run_chat(request)


@router.post("/profiles/{profile_id}/respond")
async def respond(profile_id: str, request: AvatarChatRequest):
    return await _run_chat(request, forced_profile_id=profile_id)


@router.post("/profiles/{profile_id}/respond/audio")
async def respond_to_audio(
    profile_id: str,
    audio: UploadFile = File(...),
    language: str = Form("auto"),
    history: str = Form("[]"),
    synthesize: bool = Form(True),
    strict_clone: bool = Form(True),
    render_video: bool = Form(False),
):
    try:
        parsed_history = _parse_history(history)
        with tempfile.TemporaryDirectory(prefix="dreamtalk_audio_input_") as temp:
            audio_path = await _save_upload(audio, Path(temp), MAX_AUDIO_BYTES)
            return await get_avatar_runtime().process_audio(
                audio_path=audio_path,
                profile_id=profile_id,
                language=language,
                history=parsed_history,
                synthesize=synthesize,
                strict_clone=strict_clone,
                render_video=render_video,
            )
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/profiles/{profile_id}/render-2d")
async def render_uploaded_audio_2d(
    profile_id: str,
    audio: UploadFile = File(...),
    emotion: str = Form("neutral"),
    engine: str = Form("auto"),
):
    """Lip-sync an existing speech track to the profile's appearance."""
    try:
        with tempfile.TemporaryDirectory(prefix="dreamtalk_2d_audio_") as temp:
            audio_path = await _save_upload(audio, Path(temp), MAX_AUDIO_BYTES)
            result = await get_avatar_runtime().render_2d(
                profile_id=profile_id,
                audio_path=audio_path,
                emotion=emotion,
                engine=engine,
            )
            if result.get("status") != "completed":
                raise RuntimeError(result.get("reason", "2D avatar rendering failed"))
            return result
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/profiles/{profile_id}/speak-2d")
async def speak_as_2d_avatar(profile_id: str, request: TwoDSpeakRequest):
    """Generate cloned speech and return a synchronized 2D talking-head MP4."""
    runtime = get_avatar_runtime()
    profile = runtime.store.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Avatar profile not found")
    language = request.language
    if language == "auto":
        language = detect_text_language(request.text).language
    try:
        speech = await runtime.speech.synthesize(
            text=request.text,
            language=language,
            emotion=request.emotion,
            profile=profile,
            strict_clone=request.strict_clone,
        )
        video = await runtime.render_2d(
            profile_id=profile_id,
            audio_path=speech.path,
            emotion=request.emotion,
            engine=request.engine,
        )
        if video.get("status") != "completed":
            raise RuntimeError(video.get("reason", "2D avatar rendering failed"))
        audio_result = speech.to_dict()
        audio_result.pop("path", None)
        audio_result.pop("service_url", None)
        return {
            "profile_id": profile_id,
            "text": request.text,
            "language": language,
            "emotion": request.emotion,
            "audio": audio_result,
            "video": video,
        }
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/tts/generate")
async def generate_tts(request: TTSRequest):
    runtime = get_avatar_runtime()
    profile = runtime.store.get(request.profile_id)
    language = request.language
    if language == "auto":
        language = detect_text_language(request.text).language
    try:
        result = await runtime.speech.synthesize(
            text=request.text,
            language=language,
            emotion=request.emotion,
            profile=profile,
            strict_clone=request.strict_clone,
        )
        payload = result.to_dict()
        payload.pop("path", None)
        payload.pop("service_url", None)
        return payload
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/lipsync/analyze")
async def analyze_lipsync(
    audio: UploadFile = File(...),
    emotion: str = Form("neutral"),
    text: str = Form(""),
):
    try:
        with tempfile.TemporaryDirectory(prefix="dreamtalk_lipsync_") as temp:
            audio_path = await _save_upload(audio, Path(temp), MAX_AUDIO_BYTES)
            return await asyncio.to_thread(
                get_avatar_runtime()._build_lipsync,
                audio_path,
                {"primary_mood": emotion, "arousal": 0.5},
                text,
            )
    except Exception as exc:
        _raise_api_error(exc)


_runtime_ws_handler = None


@router.websocket("/ws/realtime")
async def realtime_avatar(websocket: WebSocket):
    global _runtime_ws_handler
    if _runtime_ws_handler is None:
        from dreamtalk.backend.websocket.chat_handler import WebSocketChatHandler
        _runtime_ws_handler = WebSocketChatHandler()
    await websocket.accept()
    await _runtime_ws_handler.handle_connection(websocket)
