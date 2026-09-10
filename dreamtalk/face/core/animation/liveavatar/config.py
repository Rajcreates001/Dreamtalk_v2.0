# Dreamtalk - Face Engine
# Extracted from LiveAvatar
from dataclasses import dataclass
import os
import torch


@dataclass
class LiveAvatarConfig:
    checkpoint_dir: str = "./checkpoints/liveavatar"
    device: str = os.environ.get("DREAMTALK_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    use_fp16: bool = True
