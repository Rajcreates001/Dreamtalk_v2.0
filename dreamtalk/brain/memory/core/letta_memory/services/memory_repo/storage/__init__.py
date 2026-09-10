# Adapted from Letta (MemGPT) - Apache 2.0 License
"""Storage backends for memory repositories."""

from dreamtalk.brain.memory.core.letta_memory.services.memory_repo.storage.base import StorageBackend
from dreamtalk.brain.memory.core.letta_memory.services.memory_repo.storage.local import LocalStorageBackend

__all__ = [
    "LocalStorageBackend",
    "StorageBackend",
]
