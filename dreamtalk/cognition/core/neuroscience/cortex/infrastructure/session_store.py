"""Persistence layer for the session log.

- load_session_log always returns { sessions: [] } at minimum
- save_session_log persists the log
"""
# Adapted from Cortex (MIT License)

from __future__ import annotations

from .config import SESSION_LOG_PATH
from .file_io import read_json, write_json


def load_session_log() -> dict:
    """Load the session log from disk."""
    return read_json(SESSION_LOG_PATH) or {"sessions": []}


def save_session_log(log: dict) -> None:
    """Save the session log to disk."""
    write_json(SESSION_LOG_PATH, log)
