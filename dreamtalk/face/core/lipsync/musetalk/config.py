# Dreamtalk - Face Engine
# Extracted from MuseTalk
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


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
    batch_size: int = 8
    output_vid_name: Optional[str] = None
    use_saved_coord: bool = False
    saved_coord: bool = False
    use_float16: bool = False
    parsing_mode: str = "jaw"
    left_cheek_width: int = 90
    right_cheek_width: int = 90
    version: str = "v15"
