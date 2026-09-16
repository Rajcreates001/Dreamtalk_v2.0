# Dreamtalk - Face Engine
# Extracted from MuseTalk
import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


def _env_flag(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _default_float16() -> bool:
    """Half precision whenever we are on a CUDA device.

    MuseTalk was OOMing on every render — "RuntimeError: CUDA driver error:
    out of memory" inside the VAE encode — because it loaded in fp32. The
    UNet + VAE + Whisper stack in fp32 does not fit an 8 GB card alongside
    anything else, and the host LLM reloads between turns, so even a
    successful pre-load eviction is undone by the next reply. fp16 roughly
    halves the footprint and is the precision MuseTalk ships for.

    Override with MUSETALK_FP16=0 on a card with memory to spare.
    """
    try:
        import torch

        return _env_flag("MUSETALK_FP16", torch.cuda.is_available())
    except Exception:
        return False


def _default_batch_size() -> int:
    """Batch 8 in fp32 was another multiplier on an already-tight budget."""
    try:
        return int(os.environ.get("MUSETALK_BATCH_SIZE", "4"))
    except ValueError:
        return 4


def _weights(path: str) -> str:
    """Resolve path relative to project weights/ directory."""
    # From musetalk/config.py: musetalk/ → lipsync/ → core/ → face/ → dreamtalk/ → root (6 levels)
    p = Path(__file__).resolve().parent.parent.parent.parent.parent
    return str(p / path)


@dataclass
class MuseTalkConfig:
    ffmpeg_path: str = "ffmpeg"
    gpu_id: int = 0
    vae_type: str = _weights("weights/musetalk/sd-vae")
    unet_config: str = _weights("weights/musetalk/musetalk.json")
    unet_model_path: str = _weights("weights/musetalk/unet.pth")
    whisper_dir: str = _weights("weights/musetalk/whisper")
    bbox_shift: int = 0
    result_dir: str = "./results"
    extra_margin: int = 10
    fps: int = 25
    audio_padding_length_left: int = 2
    audio_padding_length_right: int = 2
    batch_size: int = field(default_factory=_default_batch_size)
    output_vid_name: Optional[str] = None
    use_saved_coord: bool = False
    saved_coord: bool = False
    use_float16: bool = field(default_factory=_default_float16)
    parsing_mode: str = field(default_factory=lambda: os.environ.get("MUSETALK_PARSING_MODE", "jaw"))
    left_cheek_width: int = 90
    right_cheek_width: int = 90
    version: str = "v15"
