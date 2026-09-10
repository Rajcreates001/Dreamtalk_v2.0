"""
DreamTalk — Prosody Controller

Exposes fine-grained prosody parameters for TTS synthesis:
  - speed: speech rate (0.5x - 2.0x)
  - pitch: pitch shift in semitones (-12 to +12)
  - intensity: speaking intensity (0.0 soft - 1.0 loud)
  - pause_duration: pause between sentences (ms)
  - emphasis_words: words to stress/emphasize

Usage:
    prosody = ProsodyParams(speed=1.2, pitch=2.0, intensity=0.8)
    adjusted = prosody.apply_to_text("Hello world!")
    # → "Hello world!" with speed/pitch annotations
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
import re


@dataclass
class ProsodyParams:
    """Prosody parameters for expressive TTS."""
    speed: float = 1.0           # 0.5 (slow) - 2.0 (fast)
    pitch_semitones: float = 0.0 # -12 to +12 semitones
    intensity: float = 0.5       # 0.0 (whisper) - 1.0 (shouting)
    pause_ms: int = 0            # Extra pause between sentences (ms)
    emphasis_words: List[str] = field(default_factory=list)
    breathiness: float = 0.0     # 0.0 (clear) - 1.0 (breathy)
    warmth: float = 0.5          # 0.0 (cold) - 1.0 (warm)

    def __post_init__(self):
        self.speed = max(0.5, min(2.0, self.speed))
        self.pitch_semitones = max(-12, min(12, self.pitch_semitones))
        self.intensity = max(0.0, min(1.0, self.intensity))
        self.breathiness = max(0.0, min(1.0, self.breathiness))
        self.warmth = max(0.0, min(1.0, self.warmth))

    @property
    def speed_multiplier(self) -> float:
        """Get the raw speed multiplier for Kokoro TTS."""
        return self.speed

    @property
    def pitch_multiplier(self) -> float:
        """Convert semitones to frequency multiplier."""
        return 2 ** (self.pitch_semitones / 12.0)

    def to_dict(self) -> Dict:
        return {
            "speed": self.speed,
            "pitch_semitones": self.pitch_semitones,
            "intensity": self.intensity,
            "pause_ms": self.pause_ms,
            "emphasis_words": self.emphasis_words,
            "breathiness": self.breathiness,
            "warmth": self.warmth,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "ProsodyParams":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Emotion → Prosody presets ─────────────────────────────────────────

EMOTION_PROSODY: Dict[str, ProsodyParams] = {
    "happy": ProsodyParams(speed=1.1, pitch_semitones=2.0, intensity=0.7, warmth=0.8),
    "sad": ProsodyParams(speed=0.85, pitch_semitones=-2.0, intensity=0.3, warmth=0.4),
    "angry": ProsodyParams(speed=1.2, pitch_semitones=3.0, intensity=0.9, warmth=0.2),
    "excited": ProsodyParams(speed=1.3, pitch_semitones=4.0, intensity=0.85, warmth=0.9),
    "calm": ProsodyParams(speed=0.95, pitch_semitones=0.0, intensity=0.4, warmth=0.7),
    "surprised": ProsodyParams(speed=1.0, pitch_semitones=5.0, intensity=0.75, warmth=0.6),
    "fearful": ProsodyParams(speed=1.15, pitch_semitones=3.0, intensity=0.5, warmth=0.3),
    "neutral": ProsodyParams(speed=1.0, pitch_semitones=0.0, intensity=0.5, warmth=0.5),
    "loving": ProsodyParams(speed=0.9, pitch_semitones=1.0, intensity=0.4, warmth=1.0, breathiness=0.3),
}


def prosody_for_emotion(emotion: str, intensity: float = 0.5) -> ProsodyParams:
    """Get prosody parameters for an emotion at a given intensity.

    Args:
        emotion: Emotion label (happy, sad, angry, etc.).
        intensity: 0-1 intensity of the emotion.

    Returns:
        ProsodyParams scaled by intensity.
    """
    base = EMOTION_PROSODY.get(emotion, EMOTION_PROSODY["neutral"])

    # Scale parameters by intensity
    scaled = ProsodyParams(
        speed=1.0 + (base.speed - 1.0) * intensity,
        pitch_semitones=base.pitch_semitones * intensity,
        intensity=0.5 + (base.intensity - 0.5) * intensity,
        emphasis_words=base.emphasis_words,
        breathiness=base.breathiness * intensity,
        warmth=0.5 + (base.warmth - 0.5) * intensity,
    )
    return scaled
