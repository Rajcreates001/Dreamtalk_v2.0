"""Realtime WebSocket protocol for the canonical DreamTalk avatar runtime."""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("dreamtalk.websocket")


@dataclass
class ChatSession:
    session_id: str = ""
    user_id: str = ""
    twin_id: str = ""
    role: str = "normal_user"
    model_name: str = ""
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    max_history: int = 20
    created_at: float = 0.0
    last_active: float = 0.0
    interaction_id: str = ""
    profile_id: str = ""
    language: str = "auto"
    synthesize: bool = True
    strict_clone: bool = True
    render_video: bool = False

    def __post_init__(self) -> None:
        self.session_id = self.session_id or uuid.uuid4().hex
        self.created_at = self.created_at or time.time()
        self.last_active = time.time()

    def add_message(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content, "timestamp": time.time()})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history :]
        self.last_active = time.time()


class WebSocketChatHandler:
    """Text and complete-audio-message realtime avatar protocol.

    Browser messages:
      {"type":"config", "profile_id":"...", "language":"auto"}
      {"type":"text", "text":"..."}
      {"type":"audio", "audio":"<base64>", "mime_type":"audio/webm"}
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._connections: dict[str, Any] = {}
        self._avatar_runtime = None

    def _get_avatar_runtime(self):
        if self._avatar_runtime is None:
            from dreamtalk.backend.services.avatar_runtime import get_avatar_runtime

            self._avatar_runtime = get_avatar_runtime()
        return self._avatar_runtime

    async def handle_connection(self, websocket, session_id: Optional[str] = None) -> None:
        session = ChatSession(session_id=session_id or "")
        self._sessions[session.session_id] = session
        self._connections[session.session_id] = websocket
        await self._start_persistence(session)

        try:
            await websocket.send_json({
                "type": "session_info",
                "session_id": session.session_id,
                "status": "connected",
                "message": "Connected to DreamTalk realtime avatar",
                "protocol_version": "1.0",
                "accepted_message_types": ["config", "text", "message", "audio", "voice", "history", "clear", "ping"],
            })
            while True:
                try:
                    raw = await websocket.receive_text()
                    data = json.loads(raw)
                    if not isinstance(data, dict):
                        raise ValueError("WebSocket message must be a JSON object")
                    await self._handle_message(websocket, session, data)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "code": "invalid_json", "message": "Invalid JSON"})
                except Exception as exc:
                    if type(exc).__name__ in {"WebSocketDisconnect", "ConnectionClosedOK", "ConnectionClosedError"}:
                        break
                    logger.exception("WebSocket message failed")
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "code": "message_failed",
                            "message": str(exc),
                            "recoverable": True,
                        })
                    except Exception:
                        break
        except Exception as exc:
            if type(exc).__name__ not in {"WebSocketDisconnect", "ConnectionClosedOK", "ConnectionClosedError"}:
                logger.warning("WebSocket disconnected: %s", exc)
        finally:
            await self._end_persistence(session)
            self._connections.pop(session.session_id, None)
            self._sessions.pop(session.session_id, None)

    async def _handle_message(self, websocket, session: ChatSession, data: dict[str, Any]) -> None:
        message_type = str(data.get("type", "text")).lower()
        if message_type in {"text", "message"}:
            await self._handle_text(websocket, session, data)
        elif message_type in {"audio", "voice"}:
            await self._handle_audio(websocket, session, data)
        elif message_type == "config":
            await self._handle_config(websocket, session, data)
        elif message_type == "ping":
            await websocket.send_json({"type": "pong", "timestamp": time.time()})
        elif message_type == "history":
            await websocket.send_json({"type": "history", "data": session.conversation_history})
        elif message_type == "clear":
            session.conversation_history.clear()
            await websocket.send_json({"type": "history_cleared"})
        else:
            await websocket.send_json({"type": "error", "code": "unknown_type", "message": f"Unknown message type: {message_type}"})

    async def _handle_text(self, websocket, session: ChatSession, data: dict[str, Any]) -> None:
        text = str(data.get("text") or data.get("message") or "").strip()
        if not text:
            await websocket.send_json({"type": "error", "code": "empty_text", "message": "Empty text"})
            return
        history = list(session.conversation_history)
        session.add_message("user", text)
        await websocket.send_json({
            "type": "processing",
            "step": "language_emotion",
            "message": "Detecting language and emotional context...",
        })

        runtime = self._get_avatar_runtime()
        profile = runtime.store.get(session.profile_id or None)
        if session.synthesize and not profile:
            await websocket.send_json({
                "type": "notice",
                "code": "profile_required_for_voice",
                "message": "No active avatar profile; returning text and animation without synthesized audio.",
            })
        result = await runtime.process_text(
            message=text,
            profile_id=session.profile_id or None,
            language=session.language,
            history=history,
            synthesize=session.synthesize and profile is not None,
            strict_clone=session.strict_clone,
            render_video=session.render_video,
        )
        await self._send_result(websocket, session, text, result)

    async def _handle_audio(self, websocket, session: ChatSession, data: dict[str, Any]) -> None:
        encoded = data.get("audio") or data.get("data") or ""
        if not isinstance(encoded, str) or not encoded:
            raise ValueError("Audio payload is missing")
        if encoded.lstrip().startswith("data:") and "," in encoded:
            encoded = encoded.split(",", 1)[1]
        try:
            payload = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError("Audio payload is not valid base64") from exc
        max_bytes = int(os.environ.get("AVATAR_WS_MAX_AUDIO_BYTES", str(50 * 1024 * 1024)))
        if not payload:
            raise ValueError("Audio payload is empty")
        if len(payload) > max_bytes:
            raise ValueError(f"Audio payload exceeds {max_bytes // (1024 * 1024)} MB")

        runtime = self._get_avatar_runtime()
        profile = runtime.store.get(session.profile_id or None)
        if session.synthesize and session.strict_clone and not profile:
            raise RuntimeError("Create or activate an avatar profile before requesting cloned speech")

        mime = str(data.get("mime_type") or "audio/webm").lower()
        suffix = ".wav" if "wav" in mime else ".ogg" if "ogg" in mime else ".mp4" if "mp4" in mime else ".webm"
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                temp.write(payload)
                temp_path = temp.name
            await websocket.send_json({
                "type": "processing",
                "step": "speech_recognition",
                "message": "Transcribing speech and detecting language and vocal emotion...",
            })
            history = list(session.conversation_history)
            result = await runtime.process_audio(
                audio_path=temp_path,
                profile_id=session.profile_id or None,
                language=session.language,
                history=history,
                synthesize=session.synthesize,
                strict_clone=session.strict_clone,
                render_video=session.render_video,
            )
            user_text = str((result.get("transcription") or {}).get("text", "")).strip()
            session.add_message("user", user_text)
            await self._send_result(websocket, session, user_text, result)
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    async def _send_result(self, websocket, session: ChatSession, user_text: str, result: dict[str, Any]) -> None:
        response_text = str(result.get("response") or result.get("text") or "")
        session.add_message("assistant", response_text)

        await websocket.send_json({"type": "language", "data": result.get("language")})
        await websocket.send_json({"type": "emotion", "data": result.get("user_emotion")})
        await websocket.send_json({"type": "brain_state", "data": result.get("brain")})
        if result.get("audio"):
            await websocket.send_json({
                "type": "audio",
                "data": {
                    **result["audio"],
                    "lipsync": result.get("lipsync", []),
                    "duration": result.get("lipsync_duration", result["audio"].get("duration", 0.0)),
                },
            })
        await websocket.send_json({"type": "animation", "data": result.get("animation")})
        await self._persist_exchange(session, user_text, response_text, result)
        await websocket.send_json({
            "type": "response",
            "data": {
                **result,
                "confidence": (result.get("brain") or {}).get("brain_confidence", 1.0),
                "model": (result.get("brain") or {}).get("model", "unknown"),
                "session_id": session.session_id,
                "message_count": len(session.conversation_history),
            },
        })

    async def _handle_config(self, websocket, session: ChatSession, data: dict[str, Any]) -> None:
        runtime = self._get_avatar_runtime()
        if "profile_id" in data:
            requested = str(data.get("profile_id") or "")
            if requested and not runtime.store.get(requested):
                raise KeyError(f"Avatar profile '{requested}' was not found")
            session.profile_id = requested
        if "language" in data:
            session.language = str(data.get("language") or "auto")
        if "synthesize" in data:
            session.synthesize = bool(data["synthesize"])
        if "strict_clone" in data:
            session.strict_clone = bool(data["strict_clone"])
        if "render_video" in data:
            session.render_video = bool(data["render_video"])
        if "max_history" in data:
            session.max_history = max(2, min(int(data["max_history"]), 50))
        if "role" in data:
            session.role = str(data["role"])
        if "model_name" in data:
            session.model_name = str(data["model_name"])
        await websocket.send_json({
            "type": "config_updated",
            "data": {
                "profile_id": session.profile_id or (runtime.store.get() or {}).get("id"),
                "language": session.language,
                "synthesize": session.synthesize,
                "strict_clone": session.strict_clone,
                "render_video": session.render_video,
                "max_history": session.max_history,
            },
        })

    @staticmethod
    async def _start_persistence(session: ChatSession) -> None:
        try:
            from dreamtalk.backend.services.conversation_memory import get_conversation_memory

            user_id = session.user_id or "00000000-0000-0000-0000-000000000000"
            session.interaction_id = await get_conversation_memory().create_interaction(user_id)
        except Exception as exc:
            logger.debug("Conversation persistence unavailable: %s", exc)

    @staticmethod
    async def _persist_exchange(session: ChatSession, user_text: str, response_text: str, result: dict[str, Any]) -> None:
        if not session.interaction_id:
            return
        try:
            from dreamtalk.backend.services.conversation_memory import get_conversation_memory

            memory = get_conversation_memory()
            user_emotion = (result.get("user_emotion") or {}).get("primary_mood", "neutral")
            await memory.save_message(session.interaction_id, "user", user_text, emotion=user_emotion)
            await memory.save_message(session.interaction_id, "assistant", response_text, emotion=result.get("emotion", "neutral"))
        except Exception as exc:
            logger.debug("Conversation persistence skipped: %s", exc)

    @staticmethod
    async def _end_persistence(session: ChatSession) -> None:
        if not session.interaction_id:
            return
        try:
            from dreamtalk.backend.services.conversation_memory import get_conversation_memory

            await get_conversation_memory().end_interaction(session.interaction_id)
        except Exception:
            pass

    def get_active_sessions(self) -> int:
        return len(self._connections)
