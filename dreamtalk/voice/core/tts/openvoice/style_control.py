# Dreamtalk - Voice Engine
# Extracted from OpenVoice

from dataclasses import dataclass
from typing import Optional


@dataclass
class StyleControlParams:
    noise_scale: float = 0.667
    noise_scale_w: float = 0.6
    length_scale: float = 1.0
    sdp_ratio: float = 0.2
    speed: float = 1.0
    language: str = "English"
    speaker: Optional[str] = None
    tau: float = 0.3

    LANGUAGE_MARKS = {
        "english": "EN",
        "chinese": "ZH",
        "spanish": "ES",
        "french": "FR",
        "japanese": "JA",
        "korean": "KO",
    }

    @staticmethod
    def supported_languages():
        return list(StyleControlParams.LANGUAGE_MARKS.keys())
