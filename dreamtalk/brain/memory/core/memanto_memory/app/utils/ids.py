# Extracted from Memanto
"""
ID Generation Utilities
"""

import time
import uuid


def generate_id() -> str:
    """Generate generic unique ID"""
    return uuid.uuid4().hex[:12]


def generate_memory_id(prefix: str = "mem") -> str:
    """Generate deterministic memory ID"""
    return f"{prefix}_{generate_id()}"


def generate_ulid() -> str:
    """Generate ULID (Universally Unique Lexicographically Sortable Identifier)"""
    # Simplified ULID implementation
    timestamp = int(time.time() * 1000)  # milliseconds
    random_part = uuid.uuid4().hex[:10]
    return f"{timestamp:013x}{random_part}"


def generate_session_id() -> str:
    """Generate session ID"""
    return f"s_{uuid.uuid4().hex[:8]}"


def generate_namespace_id(scope_type: str, scope_id: str) -> str:
    """Generate deterministic namespace ID"""
    return f"memanto:{scope_type}:{scope_id}"


def extract_scope_type_from_namespace(namespace: str) -> str | None:
    """Extract scope type from namespace"""
    parts = namespace.split(":")
    if len(parts) >= 2 and parts[0] == "memanto":
        return parts[1]
    return None


def is_valid_memory_id(memory_id: str) -> bool:
    """Validate memory ID format"""
    return bool(memory_id and len(memory_id) > 4 and "_" in memory_id)
