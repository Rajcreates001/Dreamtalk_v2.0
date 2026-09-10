"""Device management utility for DreamTalk.

Provides a single source of truth for device selection across all
pipelines (face, voice, brain, avatar, cognition).

Usage:
    from dreamtalk.shared.utils.device import get_device, DEVICE

    device = get_device()          # auto-detect
    device = get_device("cpu")     # force CPU

Environment variable:
    DREAMTALK_DEVICE=cpu   or   DREAMTALK_DEVICE=cuda
"""

import os
import torch
import logging

logger = logging.getLogger("dreamtalk.device")

_DEFAULT_DEVICE = None


def _auto_detect_device() -> str:
    """Auto-detect best available device.

    Priority:
        1. DREAMTALK_DEVICE env var (if set and valid)
        2. CUDA (if torch.cuda.is_available())
        3. MPS (if torch.backends.mps.is_available() and macOS)
        4. CPU (fallback)
    """
    env_device = os.environ.get("DREAMTALK_DEVICE", "").lower().strip()

    if env_device in ("cuda", "gpu"):
        if torch.cuda.is_available():
            return "cuda"
        logger.warning(
            "DREAMTALK_DEVICE=cuda but CUDA is not available. "
            "Falling back to auto-detection."
        )
    elif env_device in ("cpu",):
        return "cpu"
    elif env_device and env_device != "":
        logger.warning(
            f"Unknown DREAMTALK_DEVICE={env_device!r}. "
            "Falling back to auto-detection."
        )

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_device(override: str = None) -> str:
    """Return the preferred torch device string.

    Args:
        override: If provided, use this device directly (no auto-detect).

    Returns:
        One of "cuda", "mps", or "cpu".
    """
    if override is not None:
        return override.lower()
    global _DEFAULT_DEVICE
    if _DEFAULT_DEVICE is None:
        _DEFAULT_DEVICE = _auto_detect_device()
        logger.info("Detected device: %s", _DEFAULT_DEVICE)
    return _DEFAULT_DEVICE


def get_torch_device(override: str = None) -> torch.device:
    """Return a torch.device instance for the preferred device."""
    return torch.device(get_device(override))


def get_device_count() -> int:
    """Return number of available GPU devices, or 0 on CPU."""
    if torch.cuda.is_available():
        return torch.cuda.device_count()
    return 0


def get_device_name(device_id: int = 0) -> str:
    """Return GPU device name, or 'CPU'."""
    if torch.cuda.is_available() and device_id < torch.cuda.device_count():
        return torch.cuda.get_device_name(device_id)
    return "CPU"


# Convenience constant - resolved at import time, but can be refreshed
# by calling get_device() with no argument.
DEVICE = get_device()
DEVICE_TORCH = get_torch_device()
