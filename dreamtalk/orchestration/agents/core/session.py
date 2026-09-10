# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""SessionDB — SQLite-backed session store with FTS5 full-text search.

Inspired by hermes-agent ``hermes_state.py`` (~4.8K LOC). Provides
session creation, message persistence, and full-text search across
messages.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dreamtalk.orchestration.agents.config import get_config

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    parent_session_id TEXT,
    source TEXT DEFAULT 'dreamtalk',
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    started_at REAL,
    ended_at REAL,
    end_reason TEXT,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
)
"""

CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_name TEXT,
    tool_calls TEXT,
    created_at REAL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
)
"""

CREATE_FTS_TABLES = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content, tool_name, tool_calls, content=messages, content_rowid=id
)
"""

FTS_TRIGGERS = [
    """
    CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages
    BEGIN
        INSERT INTO messages_fts(rowid, content, tool_name, tool_calls)
        VALUES (new.id, new.content, new.tool_name, new.tool_calls);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages
    BEGIN
        INSERT INTO messages_fts(messages_fts, rowid, content, tool_name, tool_calls)
        VALUES ('delete', old.id, old.content, old.tool_name, old.tool_calls);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages
    BEGIN
        INSERT INTO messages_fts(messages_fts, rowid, content, tool_name, tool_calls)
        VALUES ('delete', old.id, old.content, old.tool_name, old.tool_calls);
        INSERT INTO messages_fts(rowid, content, tool_name, tool_calls)
        VALUES (new.id, new.content, new.tool_name, new.tool_calls);
    END
    """,
]


class SessionDB:
    """SQLite-backed session storage with FTS5 full-text search.

    Thread-safe: each method opens its own cursor. WAL journal mode
    for concurrent readers + single writer.
    """

    def __init__(self, db_path: Optional[Path] = None, read_only: bool = False):
        cfg = get_config()
        default_path = Path(cfg.session_db_path or "~/.dreamtalk/state.db").expanduser()
        self.db_path = db_path or default_path
        self.read_only = read_only
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=3.0,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        if not self.read_only:
            self._init_schema()

    def _init_schema(self):
        cursor = self._conn.execute("PRAGMA user_version")
        version = cursor.fetchone()[0]

        self._conn.execute(CREATE_SESSIONS_TABLE)
        self._conn.execute(CREATE_MESSAGES_TABLE)

        if version < SCHEMA_VERSION:
            try:
                self._conn.execute(CREATE_FTS_TABLES)
                for sql in FTS_TRIGGERS:
                    self._conn.execute(sql)
            except sqlite3.OperationalError as e:
                if "no such module" in str(e) and "fts5" in str(e):
                    logger.warning("FTS5 not available; full-text search disabled.")
                else:
                    raise
            self._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Session CRUD ──

    def create_session(
        self,
        session_id: str,
        source: str = "dreamtalk",
        model: str = "",
        model_config: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        parent_session_id: Optional[str] = None,
    ) -> bool:
        try:
            self._conn.execute(
                """INSERT OR IGNORE INTO sessions
                   (id, parent_session_id, source, model, model_config, system_prompt, started_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, parent_session_id, source, model,
                 json.dumps(model_config) if model_config else None,
                 system_prompt, time.time()),
            )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error("create_session failed: %s", e)
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("model_config"):
            try:
                d["model_config"] = json.loads(d["model_config"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d

    def update_system_prompt(self, session_id: str, system_prompt: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET system_prompt = ? WHERE id = ?",
            (system_prompt, session_id),
        )
        self._conn.commit()

    def end_session(self, session_id: str, end_reason: str = "complete") -> None:
        self._conn.execute(
            "UPDATE sessions SET ended_at = ?, end_reason = ? WHERE id = ?",
            (time.time(), end_reason, session_id),
        )
        self._conn.commit()

    def list_sessions(
        self, limit: int = 50, offset: int = 0, source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if source:
            cursor = self._conn.execute(
                "SELECT * FROM sessions WHERE source = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (source, limit, offset),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [dict(row) for row in cursor.fetchall()]

    # ── Messages ──

    def save_messages(self, session_id: str, messages: List[Dict]) -> int:
        count = 0
        for msg in messages:
            if msg.get("role") in ("system",):
                continue
            self._conn.execute(
                """INSERT INTO messages (session_id, role, content, tool_name, tool_calls, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    msg.get("role", ""),
                    msg.get("content", ""),
                    msg.get("tool_name"),
                    json.dumps(msg.get("tool_calls")) if msg.get("tool_calls") else None,
                    time.time(),
                ),
            )
            count += 1
        self._conn.commit()
        return count

    def get_messages(self, session_id: str) -> List[Dict]:
        cursor = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        result = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("tool_calls"):
                try:
                    d["tool_calls"] = json.loads(d["tool_calls"])
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(d)
        return result

    # ── FTS5 Search ──

    def search_messages(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Full-text search across all session messages using FTS5."""
        try:
            cursor = self._conn.execute(
                """SELECT m.id, m.session_id, m.role, m.content, m.tool_name,
                          snippets(messages_fts, 1, '<mark>', '</mark>', '...', 40) AS snippet
                   FROM messages_fts
                   JOIN messages m ON m.id = messages_fts.rowid
                   WHERE messages_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                logger.debug("FTS table not available for search")
            else:
                logger.warning("FTS search failed: %s", e)
            return []

    def delete_session(self, session_id: str) -> bool:
        try:
            self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error("delete_session failed: %s", e)
            return False
