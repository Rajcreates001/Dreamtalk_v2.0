"""
DreamTalk — Voice-Face Sync Bridge

Maps audio features (volume, pitch, phonemes) to facial blendshape
parameters in real-time. Bridges the gap between TTS audio output
and avatar facial animation.

Architecture:
  Audio stream → Feature extraction → Blendshape mapping → Avatar animation

Features:
  - RMS volume → mouth openness, jaw movement
  - Pitch estimation → eyebrow height, head tilt
  - Energy → facial intensity, eye openness
  - Silence detection → resting face / blink

Usage:
    sync = VoiceFaceSync()
    params = sync.audio_to_face(audio_chunk, sample_rate=24000, emotion="happy")
    # params = {"mouth_open": 0.7, "eyebrow_raise": 0.3, ...}
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple

import numpy as np

logger = logging.getLogger("dreamtalk.voice_face_sync")


@dataclass
class FaceParams:
    """Facial animation parameters derived from audio."""
    mouth_open: float = 0.0       # 0-1, mouth openness
    jaw_open: float = 0.0         # 0-1, jaw drop
    mouth_width: float = 0.0      # 0-1, smile/frown width
    eyebrow_raise: float = 0.0    # 0-1, eyebrow height
    eye_open: float = 1.0         # 0-1, eye openness (1 = fully open)
    head_tilt: float = 0.0        # -1 to 1, head tilt left/right
    head_nod: float = 0.0         # -1 to 1, head nod up/down
    cheek_puff: float = 0.0       # 0-1, cheek fullness
    nose_wrinkle: float = 0.0     # 0-1, nose scrunch
    emotion_intensity: float = 0.5  # 0-1, overall emotional intensity

    def to_blendshapes(self) -> Dict[str, float]:
        """Convert to MediaPipe-compatible blendshape dict."""
        return {
            "mouthOpen": self.mouth_open,
            "jawOpen": self.jaw_open,
            "mouthSmileLeft": self.mouth_width,
            "mouthSmileRight": self.mouth_width,
            " browInnerUp": self.eyebrow_raise,
            "browOuterUpLeft": self.eyebrow_raise * 0.7,
            "browOuterUpRight": self.eyebrow_raise * 0.7,
            "eyeBlinkLeft": 1.0 - self.eye_open,
            "eyeBlinkRight": 1.0 - self.eye_open,
            "cheekPuff": self.cheek_puff,
            "noseSneerLeft": self.nose_wrinkle,
            "noseSneerRight": self.nose_wrinkle,
        }


class VoiceFaceSync:
    """Map audio features to facial animation parameters."""

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self._prev_rms = 0.0
        self._prev_pitch = 200.0  # Hz, typical speech center
        self._smoothing = 0.3     # EMA smoothing factor

    def audio_to_face(
        self,
        audio: np.ndarray,
        sample_rate: Optional[int] = None,
        emotion: str = "neutral",
        emotion_intensity: float = 0.5,
    ) -> FaceParams:
        """Convert an audio chunk to facial animation parameters.

        Args:
            audio: Float32 audio samples.
            sample_rate: Sample rate (defaults to self.sample_rate).
            emotion: Current emotion label.
            emotion_intensity: 0-1 intensity of the emotion.

        Returns:
            FaceParams with blendshape values.
        """
        sr = sample_rate or self.sample_rate
        if audio is None or len(audio) == 0:
            return self._resting_face(emotion, emotion_intensity)

        # ── Audio features ───────────────────────────────────────────
        rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0
        pitch_hz = self._estimate_pitch(audio, sr)
        energy = min(rms * 5.0, 1.0)  # Normalize to 0-1

        # Smooth transitions
        smooth_rms = self._smooth(self._prev_rms, rms)
        smooth_pitch = self._smooth(self._prev_pitch, pitch_hz)
        self._prev_rms = smooth_rms
        self._prev_pitch = smooth_pitch

        # ── Map to face ──────────────────────────────────────────────
        params = FaceParams(emotion_intensity=emotion_intensity)

        # Mouth: open based on volume
        params.mouth_open = min(smooth_rms * 8.0, 1.0)
        params.jaw_open = params.mouth_open * 0.6

        # Mouth shape: wider when louder/energetic
        params.mouth_width = energy * 0.8

        # Eyebrows: raise with pitch
        pitch_norm = (smooth_pitch - 150) / 200  # Normalize around typical speech
        params.eyebrow_raise = max(0, min(pitch_norm, 1.0))

        # Eyes: wider when pitch is high (excitement/surprise)
        if pitch_norm > 0.5:
            params.eye_open = 1.0
        elif pitch_norm < -0.3:
            params.eye_open = 0.7  # Slightly squinted
        else:
            params.eye_open = 0.9

        # ── Emotion modifiers ────────────────────────────────────────
        self._apply_emotion(params, emotion, emotion_intensity)

        return params

    def _resting_face(self, emotion: str, intensity: float) -> FaceParams:
        """Return resting face parameters when no audio is playing."""
        params = FaceParams(emotion_intensity=intensity)
        params.mouth_open = 0.0
        params.jaw_open = 0.0
        params.mouth_width = 0.0
        params.eye_open = 0.95  # Slightly relaxed
        self._apply_emotion(params, emotion, intensity)
        return params

    def _apply_emotion(self, params: FaceParams, emotion: str, intensity: float):
        """Modify face parameters based on emotional state."""
        e = intensity
        if emotion == "happy":
            params.mouth_width = max(params.mouth_width, 0.6 * e)
            params.eyebrow_raise = max(params.eyebrow_raise, 0.3 * e)
            params.eye_open = min(params.eye_open + 0.1 * e, 1.0)
        elif emotion == "sad":
            params.mouth_width = min(params.mouth_width, -0.2 * e)  # Frown
            params.eyebrow_raise = 0.0
            params.eye_open = max(params.eye_open - 0.2 * e, 0.3)
            params.head_nod = -0.1 * e
        elif emotion == "angry":
            params.eyebrow_raise = -0.3 * e  # Brow furrow
            params.nose_wrinkle = 0.4 * e
            params.mouth_width = max(params.mouth_width, 0.3 * e)
            params.eye_open = max(params.eye_open - 0.15 * e, 0.4)
        elif emotion == "surprised":
            params.eyebrow_raise = max(params.eyebrow_raise, 0.8 * e)
            params.eye_open = min(params.eye_open + 0.2 * e, 1.0)
            params.mouth_open = max(params.mouth_open, 0.5 * e)
            params.jaw_open = max(params.jaw_open, 0.4 * e)
        elif emotion == "fearful":
            params.eye_open = min(params.eye_open + 0.15 * e, 1.0)
            params.eyebrow_raise = max(params.eyebrow_raise, 0.5 * e)
            params.mouth_open = max(params.mouth_open, 0.2 * e)
        elif emotion == "calm":
            params.eye_open = 0.85
            params.mouth_width = 0.1 * e
            params.head_nod = 0.05 * e

    def audio_to_face_sequence(
        self,
        audio: np.ndarray,
        sample_rate: Optional[int] = None,
        chunk_size: int = 600,  # 25ms at 24kHz
        emotion: str = "neutral",
        emotion_intensity: float = 0.5,
    ) -> List[FaceParams]:
        """Convert a full audio file to a sequence of face parameters.

        Args:
            audio: Complete audio array.
            sample_rate: Sample rate.
            chunk_size: Samples per frame (600 = ~25ms at 24kHz = 40fps).
            emotion: Emotion label.
            emotion_intensity: 0-1 intensity.

        Returns:
            List of FaceParams, one per chunk.
        """
        sr = sample_rate or self.sample_rate
        params_list = []

        # Reset smoothing state for fresh sequence
        self._prev_rms = 0.0
        self._prev_pitch = 200.0

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i + chunk_size]
            params = self.audio_to_face(chunk, sr, emotion, emotion_intensity)
            params_list.append(params)

        return params_list

    def _smooth(self, prev: float, curr: float) -> float:
        """Exponential moving average smoothing."""
        return prev * (1 - self._smoothing) + curr * self._smoothing

    def _estimate_pitch(self, audio: np.ndarray, sr: int) -> float:
        """Simple pitch estimation using autocorrelation."""
        if len(audio) < sr * 0.02:  # Need at least 20ms
            return 200.0

        # Take a window of audio
        window = audio[:min(len(audio), int(sr * 0.05))]  # 50ms max
        if len(window) < 64:
            return 200.0

        # Autocorrelation
        corr = np.correlate(window, window, mode='full')
        corr = corr[len(corr) // 2:]

        # Find first peak after zero crossing
        min_lag = int(sr / 500)   # Max 500 Hz
        max_lag = int(sr / 80)    # Min 80 Hz

        if max_lag >= len(corr):
            return 200.0

        search = corr[min_lag:max_lag]
        if len(search) == 0:
            return 200.0

        peak_idx = np.argmax(search) + min_lag
        if peak_idx > 0:
            return float(sr / peak_idx)

        return 200.0
