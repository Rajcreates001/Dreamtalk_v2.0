"""
DreamTalk — Conversation Memory

Persists chat messages to PostgreSQL and retrieves conversation history
for brain pipeline context. Supports:
  - Saving user/assistant messages with emotion metadata
  - Retrieving recent conversation history (last N messages)
  - Loading full conversation for session resume
  - Emotional state tracking across messages

Usage:
    memory = ConversationMemory()
    await memory.save_message(interaction_id, "user", "Hello!", emotion="neutral")
    history = await memory.get_history(interaction_id, limit=20)
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger("dreamtalk.memory")


class ConversationMemory:
    """Persist and retrieve conversation history from PostgreSQL."""

    async def create_interaction(
        self,
        user_id: str,
        title: Optional[str] = None,
        digital_human_id: Optional[str] = None,
    ) -> str:
        """Create a new interaction session. Returns interaction_id."""
        interaction_id = str(uuid.uuid4())
        try:
            from dreamtalk.backend.db.database import execute
            await execute(
                """INSERT INTO interactions (id, user_id, digital_human_id, title)
                   VALUES ($1, $2, $3, $4)""",
                uuid.UUID(interaction_id),
                uuid.UUID(user_id),
                uuid.UUID(digital_human_id) if digital_human_id else None,
                title or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            )
            return interaction_id
        except Exception as e:
            logger.warning(f"Failed to create interaction: {e}")
            return interaction_id

    async def save_message(
        self,
        interaction_id: str,
        role: str,
        content: str,
        emotion: Optional[str] = None,
        audio_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Save a message to the interaction."""
        try:
            import json
            from dreamtalk.backend.db.database import execute
            await execute(
                """INSERT INTO interaction_messages
                   (id, interaction_id, role, content, emotion, audio_url, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                uuid.uuid4(), uuid.UUID(interaction_id),
                role, content, emotion, audio_url,
                json.dumps(metadata or {}),
            )
            # Update message count
            await execute(
                """UPDATE interactions SET message_count = message_count + 1
                   WHERE id = $1""",
                uuid.UUID(interaction_id),
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to save message: {e}")
            return False

    async def get_history(
        self,
        interaction_id: str,
        limit: int = 20,
        include_system: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent message history for an interaction.

        Returns messages in chronological order (oldest first),
        suitable for feeding into the LLM context window.
        """
        try:
            from dreamtalk.backend.db.database import fetch
            query = """
                SELECT role, content, emotion, created_at
                FROM interaction_messages
                WHERE interaction_id = $1
            """
            if not include_system:
                query += " AND role != 'system'"
            query += " ORDER BY created_at DESC LIMIT $2"

            rows = await fetch(query, uuid.UUID(interaction_id), limit)
            # Reverse to get chronological order
            messages = [dict(r) for r in reversed(rows)]
            return messages
        except Exception as e:
            logger.warning(f"Failed to get history: {e}")
            return []

    async def get_recent_emotions(
        self, interaction_id: str, limit: int = 5
    ) -> List[str]:
        """Get the last N emotion labels for emotional continuity."""
        try:
            from dreamtalk.backend.db.database import fetch
            rows = await fetch(
                """SELECT emotion FROM interaction_messages
                   WHERE interaction_id = $1 AND emotion IS NOT NULL
                   ORDER BY created_at DESC LIMIT $2""",
                uuid.UUID(interaction_id), limit,
            )
            return [r["emotion"] for r in reversed(rows)]
        except Exception as e:
            return []

    async def end_interaction(self, interaction_id: str) -> bool:
        """Mark an interaction as ended."""
        try:
            from dreamtalk.backend.db.database import execute
            await execute(
                """UPDATE interactions SET ended_at = NOW(), status = 'completed'
                   WHERE id = $1""",
                uuid.UUID(interaction_id),
            )
            return True
        except Exception as e:
            return False

    def format_for_llm(self, messages: List[Dict], max_messages: int = 10) -> List[Dict]:
        """Format database messages into LLM chat format.

        Returns list of {"role": ..., "content": ...} dicts ready
        to be injected into the LLM context window.
        """
        recent = messages[-max_messages:]
        formatted = []
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content.strip():
                formatted.append({"role": role, "content": content})
        return formatted


# ── Singleton ──────────────────────────────────────────────────────────

_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    """Get or create the default conversation memory singleton."""
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory
