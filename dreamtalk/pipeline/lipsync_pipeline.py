"""
DreamTalk — Lip Sync Pipeline

Converts TTS audio output into avatar mouth animation parameters.
Pipeline: Audio → Phoneme Extraction → Viseme Mapping → Animation Keyframes

Supports:
- Phoneme extraction from audio via Montreal Forced Aligner or simple energy-based fallback
- IPA phoneme → Viseme mapping (VISMESES standard)
- Temporal alignment of visemes with audio timestamps
- Emotion-modulated mouth parameters
"""

import os
import time
import logging
import json
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("dreamtalk.pipeline.lipsync")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


# ── Viseme Definitions ─────────────────────────────────────────────────

# Standard viseme set (simplified from IPA)
VISEMES = {
    "SIL": {"mouth_open": 0.0, "mouth_width": 0.0, "lip_round": 0.0, "jaw_drop": 0.0},
    "PP":  {"mouth_open": 0.1, "mouth_width": 0.3, "lip_round": 0.8, "jaw_drop": 0.05},  # p, b, m
    "FF":  {"mouth_open": 0.1, "mouth_width": 0.4, "lip_round": 0.2, "jaw_drop": 0.05},  # f, v
    "TH":  {"mouth_open": 0.2, "mouth_width": 0.3, "lip_round": 0.1, "jaw_drop": 0.1},   # th
    "DD":  {"mouth_open": 0.2, "mouth_width": 0.3, "lip_round": 0.0, "jaw_drop": 0.15},  # t, d
    "kk":  {"mouth_open": 0.3, "mouth_width": 0.3, "lip_round": 0.0, "jaw_drop": 0.2},   # k, g
    "CH":  {"mouth_open": 0.25, "mouth_width": 0.35, "lip_round": 0.3, "jaw_drop": 0.15}, # ch, j, sh
    "SS":  {"mouth_open": 0.15, "mouth_width": 0.4, "lip_round": 0.0, "jaw_drop": 0.05},  # s, z
    "nn":  {"mouth_open": 0.1, "mouth_width": 0.3, "lip_round": 0.0, "jaw_drop": 0.05},   # n, l
    "RR":  {"mouth_open": 0.2, "mouth_width": 0.35, "lip_round": 0.2, "jaw_drop": 0.1},   # r
    "aa":  {"mouth_open": 0.8, "mouth_width": 0.6, "lip_round": 0.0, "jaw_drop": 0.7},    # ah
    "E":   {"mouth_open": 0.5, "mouth_width": 0.7, "lip_round": 0.0, "jaw_drop": 0.4},    # eh
    "IH":  {"mouth_open": 0.3, "mouth_width": 0.5, "lip_round": 0.0, "jaw_drop": 0.25},   # ih
    "OH":  {"mouth_open": 0.6, "mouth_width": 0.5, "lip_round": 0.7, "jaw_drop": 0.5},    # oh
    "UH":  {"mouth_open": 0.4, "mouth_width": 0.4, "lip_round": 0.8, "jaw_drop": 0.35},   # oo
    "OW":  {"mouth_open": 0.5, "mouth_width": 0.45, "lip_round": 0.6, "jaw_drop": 0.4},   # ow
    "AY":  {"mouth_open": 0.6, "mouth_width": 0.55, "lip_round": 0.0, "jaw_drop": 0.5},   # eye
    "OY":  {"mouth_open": 0.5, "mouth_width": 0.45, "lip_round": 0.5, "jaw_drop": 0.4},   # oy
    "AE":  {"mouth_open": 0.7, "mouth_width": 0.65, "lip_round": 0.0, "jaw_drop": 0.6},   # ah (cat)
    "AW":  {"mouth_open": 0.7, "mouth_width": 0.5, "lip_round": 0.3, "jaw_drop": 0.6},    # ow (how)
}

# Phoneme to viseme mapping (simplified English)
PHONEME_TO_VISEME = {
    # Silence
    "SIL": "SIL", "SPN": "SIL", "": "SIL",
    # Bilabial
    "p": "PP", "b": "PP", "m": "PP",
    # Labiodental
    "f": "FF", "v": "FF",
    # Dental
    "θ": "TH", "ð": "TH", "th": "TH",
    # Alveolar stop
    "t": "DD", "d": "DD",
    # Velar
    "k": "kk", "g": "kk",
    # Affricate
    "tʃ": "CH", "dʒ": "CH", "ch": "CH", "jh": "CH",
    # Fricative
    "s": "SS", "z": "SS", "ʃ": "SS", "ʒ": "SS", "sh": "SS", "zh": "SS", "s": "SS",
    # Nasal/Lateral
    "n": "nn", "l": "nn", "ŋ": "nn", "ng": "nn",
    # Rhotic
    "r": "RR", "ɹ": "RR",
    # Vowels
    "ɑ": "aa", "æ": "AE", "ʌ": "aa", "ə": "aa", "a": "aa",
    "ɛ": "E", "e": "E",
    "ɪ": "IH", "i": "IH",
    "ɔ": "OH", "o": "OH",
    "ʊ": "UH", "u": "UH",
    "aʊ": "AW", "aɪ": "AY", "oɪ": "OY", "oʊ": "OW", "eɪ": "E",
}


@dataclass
class VisemeKeyframe:
    """A single viseme animation keyframe."""
    timestamp: float  # seconds
    duration: float   # seconds
    viseme_id: str
    mouth_open: float = 0.0
    mouth_width: float = 0.0
    lip_round: float = 0.0
    jaw_drop: float = 0.0
    intensity: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "timestamp": round(self.timestamp, 4),
            "duration": round(self.duration, 4),
            "viseme": self.viseme_id,
            "mouth_open": round(self.mouth_open * self.intensity, 3),
            "mouth_width": round(self.mouth_width * self.intensity, 3),
            "lip_round": round(self.lip_round * self.intensity, 3),
            "jaw_drop": round(self.jaw_drop * self.intensity, 3),
        }


@dataclass
class LipSyncResult:
    """Complete lip sync analysis result."""
    audio_path: str = ""
    duration: float = 0.0
    sample_rate: int = 22050
    keyframes: List[VisemeKeyframe] = field(default_factory=list)
    fps: float = 30.0
    total_frames: int = 0
    method: str = "energy_based"
    processing_time_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "audio_path": self.audio_path,
            "duration": round(self.duration, 3),
            "fps": self.fps,
            "total_frames": self.total_frames,
            "method": self.method,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
            "processing_time_ms": round(self.processing_time_ms, 2),
        }


class LipSyncPipeline:
    """Extracts viseme keyframes from audio for avatar lip animation.

    Pipeline:
        1. Load audio
        2. Extract phoneme timing (via energy-based VAD or forced aligner)
        3. Map phonemes to visemes
        4. Generate smooth animation keyframes
        5. Apply emotion modulation
    """

    def __init__(self, fps: float = 30.0):
        self.fps = fps

    def extract_from_audio(
        self,
        audio_path: str,
        emotion: Optional[Dict] = None,
        text: Optional[str] = None,
    ) -> LipSyncResult:
        """Extract lip sync keyframes from an audio file."""
        start = time.time()
        result = LipSyncResult(audio_path=audio_path, fps=self.fps)

        # Load audio
        try:
            if SOUNDFILE_AVAILABLE:
                data, sr = sf.read(audio_path)
                if data.ndim > 1:
                    data = np.mean(data, axis=1)
            elif LIBROSA_AVAILABLE:
                data, sr = librosa.load(audio_path, sr=None, mono=True)
            else:
                result.error = "No audio backend available"
                return result
        except Exception as e:
            result.error = f"Cannot load audio: {e}"
            return result

        result.sample_rate = sr
        result.duration = len(data) / sr

        # Extract phoneme timing using energy-based approach
        phoneme_segments = self._extract_phoneme_segments(data, sr)
        if not phoneme_segments:
            # Fallback: create generic viseme sequence
            phoneme_segments = self._generate_generic_visemes(result.duration)

        # Map to visemes
        keyframes = []
        emotion_intensity = self._get_emotion_intensity(emotion)

        for start_t, end_t, phoneme in phoneme_segments:
            # Try direct viseme lookup first (energy-based phonemes are already viseme IDs)
            if phoneme in VISEMES:
                viseme_id = phoneme
            else:
                viseme_id = PHONEME_TO_VISEME.get(phoneme, "SIL")
            viseme_params = VISEMES.get(viseme_id, VISEMES["SIL"]).copy()

            kf = VisemeKeyframe(
                timestamp=start_t,
                duration=end_t - start_t,
                viseme_id=viseme_id,
                mouth_open=viseme_params["mouth_open"],
                mouth_width=viseme_params["mouth_width"],
                lip_round=viseme_params["lip_round"],
                jaw_drop=viseme_params["jaw_drop"],
                intensity=emotion_intensity,
            )
            keyframes.append(kf)

        # Smooth keyframes
        keyframes = self._smooth_keyframes(keyframes)

        result.keyframes = keyframes
        result.total_frames = int(result.duration * self.fps)
        result.method = "energy_based"
        result.processing_time_ms = round((time.time() - start) * 1000, 2)

        logger.info(
            f"LipSync: {len(keyframes)} keyframes, {result.total_frames} frames, "
            f"{result.duration:.2f}s audio, {result.processing_time_ms:.1f}ms"
        )

        return result

    def extract_from_text(
        self,
        text: str,
        duration: float,
        emotion: Optional[Dict] = None,
    ) -> LipSyncResult:
        """Generate lip sync keyframes from text and duration (no audio needed)."""
        start = time.time()
        result = LipSyncResult(audio_path="<text>", duration=duration, fps=self.fps)

        if not text.strip():
            result.error = "Empty text"
            return result

        # Simple phoneme estimation from text
        phonemes = self._text_to_phonemes(text)
        if not phonemes:
            result.error = "No phonemes extracted"
            return result

        # Distribute phonemes evenly across duration
        phoneme_duration = duration / len(phonemes)
        emotion_intensity = self._get_emotion_intensity(emotion)

        keyframes = []
        for i, phoneme in enumerate(phonemes):
            viseme_id = PHONEME_TO_VISEME.get(phoneme, "SIL")
            viseme_params = VISEMES.get(viseme_id, VISEMES["SIL"]).copy()

            kf = VisemeKeyframe(
                timestamp=i * phoneme_duration,
                duration=phoneme_duration,
                viseme_id=viseme_id,
                mouth_open=viseme_params["mouth_open"],
                mouth_width=viseme_params["mouth_width"],
                lip_round=viseme_params["lip_round"],
                jaw_drop=viseme_params["jaw_drop"],
                intensity=emotion_intensity,
            )
            keyframes.append(kf)

        keyframes = self._smooth_keyframes(keyframes)
        result.keyframes = keyframes
        result.total_frames = int(duration * self.fps)
        result.method = "text_based"
        result.processing_time_ms = round((time.time() - start) * 1000, 2)

        return result

    def _extract_phoneme_segments(
        self, data: np.ndarray, sr: int
    ) -> List[Tuple[float, float, str]]:
        """Extract phoneme segments using energy-based VAD."""
        if not LIBROSA_AVAILABLE:
            return []

        try:
            frame_length = int(sr * 0.025)  # 25ms frames
            hop_length = int(sr * 0.010)     # 10ms hop

            # Compute RMS energy
            rms = librosa.feature.rms(
                y=data, frame_length=frame_length, hop_length=hop_length
            )[0]

            # Compute spectral centroid for voicing detection
            centroid = librosa.feature.spectral_centroid(
                y=data, sr=sr, n_fft=frame_length, hop_length=hop_length
            )[0]

            # Normalize
            rms_norm = rms / (np.max(rms) + 1e-8)
            centroid_norm = centroid / (np.max(centroid) + 1e-8)

            # Segment into voiced/unvoiced regions
            # Use lower threshold to capture more speech segments
            silence_thresh = np.percentile(rms_norm, 10) * 0.5
            # Ensure threshold isn't too high or too low
            silence_thresh = max(silence_thresh, 0.02)
            silence_thresh = min(silence_thresh, 0.15)
            voiced = rms_norm > silence_thresh

            # Find segment boundaries.
            #
            # One segment per contiguous voiced run is not enough: synthesized
            # speech has almost no internal silence, so a whole utterance came
            # out as a single run — one viseme held for seven seconds, which
            # froze the 3D avatar's mouth in one shape. Speech articulates at
            # roughly 10-14 phonemes/second, so long runs are subdivided and a
            # viseme is chosen from each sub-window's own energy and centroid.
            max_seg_s = float(os.environ.get("LIPSYNC_MAX_SEGMENT_S", "0.09"))
            max_frames = max(1, int(round(max_seg_s * sr / hop_length)))

            def emit(start_i: int, end_i: int, out: list) -> None:
                for a in range(start_i, end_i, max_frames):
                    b = min(a + max_frames, end_i)
                    if b <= a:
                        continue
                    e = float(np.mean(rms_norm[a:b]))
                    c = float(np.mean(centroid_norm[a:b]))
                    out.append((a * hop_length / sr, b * hop_length / sr,
                                self._energy_centroid_to_phoneme(e, c)))

            segments: List[Tuple[float, float, str]] = []
            in_segment = False
            seg_start = 0

            for i in range(len(voiced)):
                if voiced[i] and not in_segment:
                    seg_start = i
                    in_segment = True
                elif not voiced[i] and in_segment:
                    emit(seg_start, i, segments)
                    in_segment = False

            # Handle last segment
            if in_segment:
                emit(seg_start, len(voiced), segments)

            return segments

        except Exception as e:
            logger.warning(f"Phoneme extraction failed: {e}")
            return []

    def _energy_centroid_to_phoneme(self, energy: float, centroid: float) -> str:
        """Map energy and spectral centroid to a phoneme category."""
        # Cycle through common visemes for natural-looking lip sync
        # Use energy+centroid to select from varied options
        if energy < 0.05:
            return "SIL"
        elif energy < 0.15:
            if centroid > 0.6:
                return "SS"  # fricative
            else:
                return "nn"  # nasal/lateral
        elif energy < 0.3:
            if centroid > 0.7:
                return "aa"  # open vowel (ah)
            elif centroid > 0.4:
                return "E"   # mid vowel (eh)
            else:
                return "IH"  # close vowel (ih)
        elif energy < 0.5:
            if centroid > 0.6:
                return "DD"  # stop consonant
            elif centroid > 0.3:
                return "OH"  # rounded vowel
            else:
                return "UH"  # back vowel
        else:
            if centroid > 0.6:
                return "aa"  # loud open vowel
            elif centroid > 0.4:
                return "E"   # mid vowel
            else:
                return "OH"  # rounded vowel

    def _generate_generic_visemes(self, duration: float) -> List[Tuple[float, float, str]]:
        """Generate generic viseme sequence for unknown audio."""
        visemes = ["SIL", "aa", "E", "IH", "OH", "UH", "DD", "SS", "nn"]
        n_segments = max(5, int(duration / 0.15))
        seg_duration = duration / n_segments
        segments = []
        for i in range(n_segments):
            v = visemes[i % len(visemes)]
            segments.append((i * seg_duration, (i + 1) * seg_duration, v))
        return segments

    def _text_to_phonemes(self, text: str) -> List[str]:
        """Convert text to phoneme sequence (simplified)."""
        # Simple character-based phoneme estimation
        phonemes = []
        text = text.lower().strip()

        # Map common letter patterns to phonemes
        i = 0
        while i < len(text):
            c = text[i]

            if c in ' \t\n':
                phonemes.append("SIL")
                i += 1
                continue

            # Two-letter combos
            if i + 1 < len(text):
                bigram = text[i:i+2]
                if bigram in ("th", "sh", "ch"):
                    phonemes.append(bigram)
                    i += 2
                    continue
                if bigram in ("ou", "ow"):
                    phonemes.append("OW")
                    i += 2
                    continue
                if bigram in ("ay", "ai"):
                    phonemes.append("AY")
                    i += 2
                    continue
                if bigram in ("oy",):
                    phonemes.append("OY")
                    i += 2
                    continue
                if bigram in ("ee",):
                    phonemes.append("IH")
                    i += 2
                    continue
                if bigram in ("oo",):
                    phonemes.append("UH")
                    i += 2
                    continue

            # Single letter
            letter_map = {
                'a': 'aa', 'e': 'E', 'i': 'IH', 'o': 'OH', 'u': 'UH',
                'b': 'PP', 'p': 'PP', 'm': 'PP',
                'f': 'FF', 'v': 'FF',
                't': 'DD', 'd': 'DD',
                'k': 'kk', 'g': 'kk',
                's': 'SS', 'z': 'SS',
                'n': 'nn', 'l': 'nn', 'r': 'RR',
                'h': 'aa', 'w': 'UH', 'y': 'IH',
            }
            phonemes.append(letter_map.get(c, 'SIL'))
            i += 1

        return phonemes

    def _get_emotion_intensity(self, emotion: Optional[Dict]) -> float:
        """Map emotion to mouth animation intensity."""
        if not emotion:
            return 1.0

        mood = emotion.get("primary_mood", "neutral")
        arousal = emotion.get("arousal", 0.5)

        intensity_map = {
            "happy": 1.2, "excited": 1.3, "angry": 1.4,
            "sad": 0.7, "calm": 0.8, "neutral": 1.0,
            "fearful": 0.9, "surprised": 1.3, "disgusted": 0.9,
        }

        base = intensity_map.get(mood, 1.0)
        arousal_mod = 0.8 + 0.4 * arousal  # 0.8 to 1.2

        return min(max(base * arousal_mod, 0.5), 1.5)

    def _smooth_keyframes(
        self, keyframes: List[VisemeKeyframe]
    ) -> List[VisemeKeyframe]:
        """Apply temporal smoothing to viseme transitions."""
        if len(keyframes) < 3:
            return keyframes

        smoothed = [keyframes[0]]

        for i in range(1, len(keyframes) - 1):
            prev = keyframes[i - 1]
            curr = keyframes[i]
            next_kf = keyframes[i + 1]

            # Ease-in/ease-out for smooth transitions
            curr.mouth_open = 0.25 * prev.mouth_open + 0.5 * curr.mouth_open + 0.25 * next_kf.mouth_open
            curr.mouth_width = 0.25 * prev.mouth_width + 0.5 * curr.mouth_width + 0.25 * next_kf.mouth_width
            curr.lip_round = 0.25 * prev.lip_round + 0.5 * curr.lip_round + 0.25 * next_kf.lip_round
            curr.jaw_drop = 0.25 * prev.jaw_drop + 0.5 * curr.jaw_drop + 0.25 * next_kf.jaw_drop

            smoothed.append(curr)

        smoothed.append(keyframes[-1])
        return smoothed

    def keyframes_to_animation_params(
        self, result: LipSyncResult, frame_number: int
    ) -> Dict[str, float]:
        """Convert keyframes to animation parameters for a specific frame."""
        if not result.keyframes:
            return {"mouth_open": 0, "mouth_width": 0, "lip_round": 0, "jaw_drop": 0}

        timestamp = frame_number / result.fps

        # Find the keyframe closest to this timestamp
        best_kf = result.keyframes[0]
        best_dist = abs(timestamp - best_kf.timestamp)

        for kf in result.keyframes:
            dist = abs(timestamp - kf.timestamp)
            if dist < best_dist:
                best_dist = dist
                best_kf = kf

        return {
            "mouth_open": best_kf.mouth_open,
            "mouth_width": best_kf.mouth_width,
            "lip_round": best_kf.lip_round,
            "jaw_drop": best_kf.jaw_drop,
            "viseme": best_kf.viseme_id,
        }


# ── Singleton ──────────────────────────────────────────────────────────

_default_pipeline: Optional[LipSyncPipeline] = None


def get_lipsync_pipeline(fps: float = 30.0) -> LipSyncPipeline:
    """Get or create the default lip sync pipeline singleton."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = LipSyncPipeline(fps=fps)
    return _default_pipeline
