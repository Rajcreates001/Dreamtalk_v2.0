"""
DreamTalk — WebSocket Chat Handler

Real-time bidirectional communication for the digital twin.
Handles: text chat, voice input, emotion streaming, brain state updates.
"""

import asyncio
import json
import time
import logging
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger("dreamtalk.websocket")


@dataclass
class ChatSession:
    """Persistent chat session state."""
    session_id: str = ""
    user_id: str = ""
    twin_id: str = ""
    role: str = "normal_user"
    model_name: str = "deepseek-r1:7b"
    conversation_history: List[Dict] = field(default_factory=list)
    max_history: int = 20
    created_at: float = 0.0
    last_active: float = 0.0
    interaction_id: str = ""  # DB-persisted interaction ID

    def __post_init__(self):
        if not self.session_id:
            self.session_id = uuid.uuid4().hex
        if not self.created_at:
            self.created_at = time.time()
        self.last_active = time.time()

    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        self.last_active = time.time()


class WebSocketChatHandler:
    """Handles WebSocket connections for real-time digital twin chat."""

    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}
        self._connections: Dict[str, Any] = {}  # session_id -> websocket
        self._brain_pipeline = None

    def _get_brain_pipeline(self):
        if self._brain_pipeline is None:
            try:
                from dreamtalk.pipeline.brain_pipeline import BrainPipeline
                self._brain_pipeline = BrainPipeline()
            except Exception as e:
                logger.warning(f"Failed to load BrainPipeline: {e}")
                return None
        return self._brain_pipeline

    async def handle_connection(self, websocket, session_id: str = None):
        """Handle a new WebSocket connection."""
        if not session_id:
            session_id = uuid.uuid4().hex

        session = ChatSession(session_id=session_id)
        self._sessions[session_id] = session
        self._connections[session_id] = websocket

        # Create persisted interaction in DB
        try:
            from dreamtalk.backend.services.conversation_memory import get_conversation_memory
            memory = get_conversation_memory()
            uid = session.user_id or "00000000-0000-0000-0000-000000000000"
            session.interaction_id = await memory.create_interaction(uid)
        except Exception as e:
            logger.debug(f"Memory init skipped: {e}")

        try:
            # Send session info
            await websocket.send_json({
                "type": "session_info",
                "session_id": session_id,
                "status": "connected",
                "message": "Connected to DreamTalk Digital Twin",
            })

            # Main message loop (FastAPI WebSocket uses receive_text/.receive_json)
            while True:
                try:
                    raw = await websocket.receive_text()
                    data = json.loads(raw)
                    await self._handle_message(websocket, session, data)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON",
                    })
                except Exception as e:
                    # WebSocketDisconnect is normal — client closed
                    err_name = type(e).__name__
                    if err_name in ("WebSocketDisconnect", "ConnectionClosedOK", "ConnectionClosedError"):
                        logger.info(f"Client disconnected: {err_name}")
                        break
                    logger.error(f"Message handling error: {e}")
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                        })
                    except Exception:
                        break  # Can't send — connection is dead

        except Exception as e:
            logger.warning(f"WebSocket disconnected: {e}")
        finally:
            # End interaction in DB
            try:
                from dreamtalk.backend.services.conversation_memory import get_conversation_memory
                mem = get_conversation_memory()
                if session.interaction_id:
                    await mem.end_interaction(session.interaction_id)
            except Exception:
                pass
            self._connections.pop(session_id, None)
            self._sessions.pop(session_id, None)
            logger.info(f"Session {session_id} cleaned up")

    async def _handle_message(self, websocket, session: ChatSession, data: Dict):
        """Route incoming messages to the appropriate handler."""
        msg_type = data.get("type", "text")

        # Accept both "text" and "message" types from clients
        if msg_type in ("text", "message"):
            await self._handle_text_message(websocket, session, data)
        elif msg_type == "config":
            await self._handle_config(websocket, session, data)
        elif msg_type == "ping":
            await websocket.send_json({"type": "pong", "timestamp": time.time()})
        elif msg_type == "history":
            await self._send_history(websocket, session)
        elif msg_type == "clear":
            session.conversation_history.clear()
            await websocket.send_json({"type": "history_cleared"})
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown message type: {msg_type}",
            })

    async def _handle_text_message(self, websocket, session: ChatSession, data: Dict):
        """Process a text message through the brain pipeline."""
        # Accept both "text" and "message" fields
        text = (data.get("text") or data.get("message") or "").strip()
        if not text:
            await websocket.send_json({"type": "error", "message": "Empty text"})
            return

        # Add user message to history
        session.add_message("user", text)

        # Send processing indicator
        await websocket.send_json({
            "type": "processing",
            "step": "emotion_detection",
            "message": "Analyzing emotional context...",
        })

        brain = self._get_brain_pipeline()
        if brain is None:
            # Fallback: return basic response without brain pipeline
            await websocket.send_json({
                "type": "response",
                "data": {
                    "text": f"I received your message: {text}",
                    "confidence": 0.3,
                    "model": "fallback",
                    "emotion": {"primary_mood": "neutral", "valence": 0.0, "arousal": 0.0},
                    "session_id": session.session_id,
                    "message_count": len(session.conversation_history),
                },
            })
            session.add_message("assistant", f"I received your message: {text}")
            return

        # Step 1: Detect emotion
        try:
            emotion_result = await brain.detect_emotion(text)
            emotion_data = {
                "primary_mood": emotion_result.primary_mood.value if emotion_result else "neutral",
                "valence": emotion_result.valence if emotion_result else 0.0,
                "arousal": emotion_result.arousal if emotion_result else 0.0,
                "dominance": emotion_result.dominance if emotion_result else 0.5,
                "intensity": emotion_result.intensity if emotion_result else "low",
                "is_hostile": emotion_result.is_hostile if emotion_result else False,
                "cognitive_appraisal": emotion_result.cognitive_appraisal if emotion_result else "baseline",
                "action_tendency": emotion_result.action_tendency if emotion_result else "observe_and_process",
            }
            await websocket.send_json({
                "type": "emotion",
                "data": emotion_data,
            })
        except Exception as e:
            logger.warning(f"Emotion detection failed: {e}")
            emotion_result = None
            emotion_data = {"primary_mood": "neutral", "valence": 0.0, "arousal": 0.0}

        # Step 2: Brain processing
        await websocket.send_json({
            "type": "processing",
            "step": "brain_processing",
            "message": "Processing through cognitive architecture...",
        })

        try:
            brain_result = await brain.make_decision(
                text=text,
                role=session.role,
                emotion=emotion_result,
                model_name=session.model_name,
            )

            # Send brain state updates
            await websocket.send_json({
                "type": "brain_state",
                "data": {
                    "pfc_firing_rate": brain_result.brain_region_activations[0].firing_rate_hz if brain_result.brain_region_activations else 0,
                    "dacc_conflict": brain_result.dacc_conflict_score,
                    "insula_valence": brain_result.insula_emotional_valence,
                    "basal_ganglia_action": brain_result.basal_ganglia_action,
                    "spiking_activity": {
                        "total_firing_rate": brain_result.spiking_activity.total_firing_rate_hz if brain_result.spiking_activity else 0,
                        "network_synchrony": brain_result.spiking_activity.network_synchrony if brain_result.spiking_activity else 0,
                    },
                    "encoding_method": brain_result.encoding_method,
                },
            })

            response_text = brain_result.response_text
            confidence = brain_result.confidence
            model_name = brain_result.model_name

        except Exception as e:
            logger.error(f"Brain processing failed: {e}")
            response_text = f"I encountered an issue processing your request. Let me try again. (Error: {str(e)[:100]})"
            confidence = 0.3
            model_name = "error_fallback"

        # Add assistant response to history
        session.add_message("assistant", response_text)

        # Persist to database
        try:
            from dreamtalk.backend.services.conversation_memory import get_conversation_memory
            mem = get_conversation_memory()
            if session.interaction_id:
                emotion_label = emotion_data.get("primary_mood", "neutral")
                await mem.save_message(session.interaction_id, "user", text, emotion=emotion_label)
                await mem.save_message(session.interaction_id, "assistant", response_text, emotion=emotion_label)
        except Exception as e:
            logger.debug(f"Memory persist skipped: {e}")

        # Send final response
        await websocket.send_json({
            "type": "response",
            "data": {
                "text": response_text,
                "confidence": round(confidence, 3),
                "model": model_name,
                "emotion": emotion_data,
                "session_id": session.session_id,
                "message_count": len(session.conversation_history),
            },
        })

    async def _handle_config(self, websocket, session: ChatSession, data: Dict):
        """Update session configuration."""
        if "role" in data:
            session.role = data["role"]
        if "model_name" in data:
            session.model_name = data["model_name"]
        if "max_history" in data:
            session.max_history = min(data["max_history"], 50)

        await websocket.send_json({
            "type": "config_updated",
            "data": {
                "role": session.role,
                "model_name": session.model_name,
                "max_history": session.max_history,
            },
        })

    async def _send_history(self, websocket, session: ChatSession):
        """Send conversation history."""
        await websocket.send_json({
            "type": "history",
            "data": session.conversation_history,
        })

    def get_active_sessions(self) -> int:
        return len(self._connections)
