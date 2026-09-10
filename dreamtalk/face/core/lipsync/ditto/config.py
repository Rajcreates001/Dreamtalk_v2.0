# Dreamtalk - Face Engine
# Extracted from Ditto
from dataclasses import dataclass
import os
import torch
from typing import Optional


@dataclass
class DittoConfig:
    data_root: str = "./checkpoints/ditto_trt_Ampere_Plus"
    cfg_pkl: str = "./checkpoints/ditto_cfg/v0.4_hubert_cfg_trt.pkl"
    device: str = os.environ.get("DREAMTALK_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    online: bool = False
    seq_frames: int = 25
    valid_clip_len: int = 5
    overlap_v2: int = 10
    sampling_timesteps: int = 50
