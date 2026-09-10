"""Persistence layer for the brain index (cross-reference graph).

- load_brain_index always returns a valid structure (never None)
"""
# Adapted from Cortex (MIT License)

from __future__ import annotations

from .config import BRAIN_INDEX_PATH
from .file_io import read_json


def load_brain_index() -> dict:
    """Load the brain index from disk."""
    return read_json(BRAIN_INDEX_PATH) or {
        "version": 1,
        "updatedAt": None,
        "memories": {},
        "conversations": {},
        "threads": {},
    }
