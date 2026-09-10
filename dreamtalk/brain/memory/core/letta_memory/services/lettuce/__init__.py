# Adapted from Letta (MemGPT) - Apache 2.0 License
try:
    from .lettuce_client import LettuceClient
except ImportError:
    from .lettuce_client_base import LettuceClient

__all__ = ["LettuceClient"]
