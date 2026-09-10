# Dreamtalk - Face Engine
# Extracted from TalkingHead
from dataclasses import dataclass
from typing import Optional


@dataclass
class TalkingHeadConfig:
    model_path: str = "./avatars"
    model_root: str = "Armature"
    camera_view: str = "full"
    tts_lang: str = "en-US"
    lipsync_lang: str = "en"
    fps: int = 30
