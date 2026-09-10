"""
DreamTalk — Session Manager

Manages persistent chat sessions with:
- Conversation memory across requests
- Emotion history tracking
- Brain state persistence
- User preference learning
- Session timeout and cleanup
"""

import time
import uuid
import json
import logging
import asyncio
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path

logger = logging.getLogger("dreamtalk.pipeline.session")

# ── Session Storage ────────────────────────────────────────────────────

_sessions: Dict[str, "ChatSession"] = {}
_cleanup_task: Optional[asyncio.Task] = None
MAX_SESSIONS = 1000
SESSION_TIMEOUT = 3600  # 1 hour
MAX_HISTORY = 50
PERSIST_DIR = Path("pipeline_outputs/sessions")


@dataclass
class Message:
    """A single message in conversation history."""
    role: str  # user, assistant, system
    content: str
    timestamp: float = 0.0
    emotion: Optional[Dict] = None
    brain_state: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "emotion": self.emotion,
            "brain_state": self.brain_state,
            "metadata": self.metadata,
        }


@dataclass
class EmotionSnapshot:
    """Snapshot of emotional state at a point in time."""
    timestamp: float = 0.0
    mood: str = "neutral"
    valence: float = 0.0
    arousal: float = 0.5
    dominance: float = 0.5
    intensity: float = 0.3
    confidence: float = 0.5

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "mood": self.mood,
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "intensity": round(self.intensity, 3),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ChatSession:
    """A persistent chat session with memory."""
    session_id: str = ""
    user_id: str = ""
    twin_id: str = ""
    role: str = "normal_user"
    model_name: str = "deepseek-r1:7b"

    # Conversation state
    messages: List[Message] = field(default_factory=list)
    emotion_history: List[EmotionSnapshot] = field(default_factory=list)
    brain_state_history: List[Dict] = field(default_factory=list)

    # User learning
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_topics: List[str] = field(default_factory=list)
    interaction_count: int = 0

    # Session metadata
    created_at: float = 0.0
    last_active: float = 0.0
    total_tokens_used: int = 0
    total_messages: int = 0

    def __post_init__(self):
        if not self.session_id:
            self.session_id = uuid.uuid4().hex
        if not self.created_at:
            self.created_at = time.time()
        self.last_active = time.time()

    def add_message(
        self,
        role: str,
        content: str,
        emotion: Optional[Dict] = None,
        brain_state: Optional[Dict] = None,
        **metadata,
    ):
        """Add a message to conversation history."""
        msg = Message(
            role=role,
            content=content,
            emotion=emotion,
            brain_state=brain_state,
            metadata=metadata,
        )
        self.messages.append(msg)
        self.total_messages += 1
        self.last_active = time.time()

        # Trim history
        if len(self.messages) > MAX_HISTORY:
            self.messages = self.messages[-MAX_HISTORY:]

    def add_emotion_snapshot(self, emotion_data: Dict):
        """Record an emotional state snapshot."""
        snapshot = EmotionSnapshot(
            timestamp=time.time(),
            mood=emotion_data.get("primary_mood", "neutral"),
            valence=emotion_data.get("valence", 0.0),
            arousal=emotion_data.get("arousal", 0.5),
            dominance=emotion_data.get("dominance", 0.5),
            intensity=emotion_data.get("intensity_score", 0.3),
            confidence=emotion_data.get("confidence", 0.5),
        )
        self.emotion_history.append(snapshot)

        # Trim
        if len(self.emotion_history) > MAX_HISTORY:
            self.emotion_history = self.emotion_history[-MAX_HISTORY:]

    def add_brain_state(self, brain_data: Dict):
        """Record brain state snapshot."""
        self.brain_state_history.append({
            "timestamp": time.time(),
            "pfc_firing_rate": brain_data.get("pfc_firing_rate", 0),
            "dacc_conflict": brain_data.get("dacc_conflict", 0),
            "insula_valence": brain_data.get("insula_valence", 0),
            "basal_ganglia_action": brain_data.get("basal_ganglia_action", ""),
        })
        if len(self.brain_state_history) > MAX_HISTORY:
            self.brain_state_history = self.brain_state_history[-MAX_HISTORY:]

    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history for LLM context."""
        recent = self.messages[-limit:]
        return [{"role": m.role, "content": m.content} for m in recent]

    def get_emotion_trend(self, window: int = 5) -> Dict[str, float]:
        """Get recent emotion trend."""
        if not self.emotion_history:
            return {"mood": "neutral", "avg_valence": 0.0, "avg_arousal": 0.5}

        recent = self.emotion_history[-window:]
        avg_valence = sum(e.valence for e in recent) / len(recent)
        avg_arousal = sum(e.arousal for e in recent) / len(recent)
        avg_dominance = sum(e.dominance for e in recent) / len(recent)

        # Determine trend mood
        if avg_valence > 0.3 and avg_arousal > 0.5:
            mood = "excited"
        elif avg_valence > 0.2:
            mood = "happy"
        elif avg_valence < -0.3 and avg_arousal > 0.5:
            mood = "angry"
        elif avg_valence < -0.2:
            mood = "sad"
        elif avg_arousal < 0.3:
            mood = "calm"
        else:
            mood = "neutral"

        return {
            "mood": mood,
            "avg_valence": round(avg_valence, 3),
            "avg_arousal": round(avg_arousal, 3),
            "avg_dominance": round(avg_dominance, 3),
            "window_size": len(recent),
        }

    def update_user_preference(self, key: str, value: Any):
        """Learn a user preference from interaction."""
        self.user_preferences[key] = value

    def get_context_for_llm(self) -> Dict[str, Any]:
        """Build full context for LLM prompt."""
        emotion_trend = self.get_emotion_trend()
        return {
            "role": self.role,
            "model": self.model_name,
            "interaction_count": self.interaction_count,
            "emotion_trend": emotion_trend,
            "user_preferences": self.user_preferences,
            "conversation_topics": self.conversation_topics[-5:],
            "total_messages": self.total_messages,
        }

    def to_dict(self) -> Dict:
        """Serialize session to dict for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "twin_id": self.twin_id,
            "role": self.role,
            "model_name": self.model_name,
            "messages": [m.to_dict() for m in self.messages],
            "emotion_history": [e.to_dict() for e in self.emotion_history],
            "brain_state_history": self.brain_state_history[-20:],
            "user_preferences": self.user_preferences,
            "conversation_topics": self.conversation_topics,
            "interaction_count": self.interaction_count,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "total_tokens_used": self.total_tokens_used,
            "total_messages": self.total_messages,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChatSession":
        """Deserialize session from dict."""
        session = cls(
            session_id=data.get("session_id", ""),
            user_id=data.get("user_id", ""),
            twin_id=data.get("twin_id", ""),
            role=data.get("role", "normal_user"),
            model_name=data.get("model_name", "deepseek-r1:7b"),
            interaction_count=data.get("interaction_count", 0),
            created_at=data.get("created_at", 0),
            last_active=data.get("last_active", 0),
            total_tokens_used=data.get("total_tokens_used", 0),
            total_messages=data.get("total_messages", 0),
        )
        session.user_preferences = data.get("user_preferences", {})
        session.conversation_topics = data.get("conversation_topics", [])

        for m_data in data.get("messages", []):
            session.messages.append(Message(**m_data))

        for e_data in data.get("emotion_history", []):
            session.emotion_history.append(EmotionSnapshot(**e_data))

        session.brain_state_history = data.get("brain_state_history", [])
        return session


# ── Session Manager ────────────────────────────────────────────────────

class SessionManager:
    """Manages chat sessions with persistence and cleanup."""

    def __init__(self):
        self._sessions = _sessions
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    def get_or_create(
        self,
        session_id: Optional[str] = None,
        user_id: str = "",
        twin_id: str = "",
        role: str = "normal_user",
    ) -> ChatSession:
        """Get an existing session or create a new one."""
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_active = time.time()
            return session

        # Try loading from disk
        if session_id:
            loaded = self._load_session(session_id)
            if loaded:
                self._sessions[session_id] = loaded
                loaded.last_active = time.time()
                return loaded

        # Create new session
        session = ChatSession(
            session_id=session_id or uuid.uuid4().hex,
            user_id=user_id,
            twin_id=twin_id,
            role=role,
        )
        self._sessions[session.session_id] = session
        logger.info(f"Created session {session.session_id}")
        return session

    def get(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session:
            session.last_active = time.time()
        return session

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            self._delete_persisted(session_id)
            logger.info(f"Deleted session {session_id}")
            return True
        return False

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict]:
        """List all active sessions."""
        sessions = []
        for sid, session in self._sessions.items():
            if user_id and session.user_id != user_id:
                continue
            sessions.append({
                "session_id": session.session_id,
                "user_id": session.user_id,
                "twin_id": session.twin_id,
                "role": session.role,
                "total_messages": session.total_messages,
                "created_at": session.created_at,
                "last_active": session.last_active,
            })
        return sessions

    def persist_session(self, session: ChatSession):
        """Save session to disk."""
        try:
            path = PERSIST_DIR / f"{session.session_id}.json"
            path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist session: {e}")

    def _load_session(self, session_id: str) -> Optional[ChatSession]:
        """Load session from disk."""
        try:
            path = PERSIST_DIR / f"{session_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return ChatSession.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
        return None

    def _delete_persisted(self, session_id: str):
        """Delete persisted session file."""
        try:
            path = PERSIST_DIR / f"{session_id}.json"
            if path.exists():
                path.unlink()
        except Exception:
            pass

    async def cleanup_expired(self):
        """Remove expired sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.last_active > SESSION_TIMEOUT
        ]
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session:
                self.persist_session(session)
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    async def start_cleanup_task(self):
        """Start background cleanup task."""
        global _cleanup_task
        if _cleanup_task and not _cleanup_task.done():
            return

        async def _cleanup_loop():
            while True:
                await asyncio.sleep(300)  # Every 5 minutes
                await self.cleanup_expired()

        _cleanup_task = asyncio.create_task(_cleanup_loop())


# ── Singleton ──────────────────────────────────────────────────────────

_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the default session manager singleton."""
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
