# Adapted from Letta (MemGPT) - Apache 2.0 License
"""Git-based memory repository services."""

from dreamtalk.brain.memory.core.letta_memory.services.memory_repo.storage.base import StorageBackend
from dreamtalk.brain.memory.core.letta_memory.services.memory_repo.storage.local import LocalStorageBackend

# MemfsClient: try cloud implementation first, fall back to local filesystem
try:
    from dreamtalk.brain.memory.core.letta_memory.services.memory_repo.memfs_client import MemfsClient
except ImportError:
    from dreamtalk.brain.memory.core.letta_memory.services.memory_repo.memfs_client_base import MemfsClient

__all__ = [
    "LocalStorageBackend",
    "MemfsClient",
    "StorageBackend",
]
