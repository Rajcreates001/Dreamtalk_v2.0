"""Language, ASR, and vocal-emotion utilities for the realtime avatar.

The module deliberately keeps model loading lazy.  Importing the FastAPI app
must remain cheap and must not download ASR weights during startup.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("dreamtalk.avatar.language")


SUPPORTED_LANGUAGES = {
    "as": "Assamese",
    "bn": "Bengali",
    "brx": "Bodo",
    "doi": "Dogri",
    "en": "English",
    "gu": "Gujarati",
    "hi": "Hindi",
    "kn": "Kannada",
    "kok": "Konkani",
    "ks": "Kashmiri",
    "mai": "Maithili",
    "ml": "Malayalam",
    "mni": "Manipuri",
    "mr": "Marathi",
    "ne": "Nepali",
    "or": "Odia",
    "pa": "Punjabi",
    "sa": "Sanskrit",
    "sat": "Santali",
    "sd": "Sindhi",
    "ta": "Tamil",
    "te": "Telugu",
    "ur": "Urdu",
}


SCRIPT_RANGES = {
    "devanagari": (0x0900, 0x097F),
    "bengali": (0x0980, 0x09FF),
    "gurmukhi": (0x0A00, 0x0A7F),
    "gujarati": (0x0A80, 0x0AFF),
    "odia": (0x0B00, 0x0B7F),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "kannada": (0x0C80, 0x0CFF),
    "malayalam": (0x0D00, 0x0D7F),
    "meetei_mayek": (0xABC0, 0xABFF),
    "ol_chiki": (0x1C50, 0x1C7F),
    "arabic": (0x0600, 0x06FF),
    "latin": (0x0041, 0x007A),
}


SCRIPT_TO_LANGUAGE = {
    "gurmukhi": "pa",
    "gujarati": "gu",
    "odia": "or",
    "tamil": "ta",
    "telugu": "te",
    "kannada": "kn",
    "malayalam": "ml",
    "meetei_mayek": "mni",
    "ol_chiki": "sat",
}


ROMANIZED_MARKERS = {
    "hi": {"hai", "hain", "nahi", "kya", "mera", "meri", "aap", "kaise", "kyun", "accha"},
    "ta": {"vanakkam", "enna", "eppadi", "ungal", "nandri", "illa", "irukku", "romba"},
    "te": {"namaskaram", "ela", "meeru", "nenu", "ledu", "undi", "bagunnara", "dhanyavadalu"},
    "kn": {"namaskara", "hegiddira", "nanu", "neevu", "illa", "ide", "dhanyavadagalu"},
    "ml": {"namaskaram", "sukhamano", "ningal", "njan", "illa", "undu", "nanni"},
    "bn": {"nomoskar", "kemon", "ami", "apni", "nei", "ache", "dhonnobad"},
    "mr": {"namaskar", "kase", "mi", "tumhi", "nahi", "aahe", "dhanyavad"},
    "gu": {"namaste", "kem", "chho", "hu", "tame", "nathi", "aabhar"},
    "pa": {"sat", "sri", "akal", "tusi", "mainu", "nahi", "dhannvaad"},
    "ur": {"salaam", "aap", "kaise", "hain", "shukriya", "mujhe", "nahi"},
    "ne": {"namaste", "tapai", "sanchai", "chha", "dhanyabad", "chaina"},
    "kok": {"dev", "bare", "asa", "tumkam", "namaskar", "deu"},
}


@dataclass
class LanguageDetection:
    language: str
    confidence: float
    method: str
    script: str = "unknown"
    alternatives: Optional[dict[str, float]] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    duration: float
    segments: list[dict[str, Any]]
    engine: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VocalEmotion:
    emotion: str
    confidence: float
    valence: float
    arousal: float
    dominance: float
    metrics: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_language(code: Optional[str], default: str = "en") -> str:
    if not code:
        return default
    normalized = code.strip().lower().replace("_", "-").split("-")[0]
    if normalized == "od":
        normalized = "or"
    return normalized if normalized in SUPPORTED_LANGUAGES else default


def _shared_script_language(script: str, text: str, preferred: Optional[str]) -> tuple[str, float]:
    if script == "devanagari":
        marathi = ("आहे", "नाही", "आणि", "तुम्ही", "कसे", "माझ", "काय रे", "धन्यवाद")
        hindi = ("है", "हैं", "नहीं", "और", "आप", "कैसे", "मेरा", "क्या", "धन्यवाद")
        mr_score = sum(token in text for token in marathi)
        hi_score = sum(token in text for token in hindi)
        if mr_score > hi_score:
            return "mr", min(0.98, 0.76 + mr_score * 0.06)
        if hi_score > mr_score:
            return "hi", min(0.98, 0.76 + hi_score * 0.06)
        if preferred in {"hi", "mr", "brx", "doi", "kok", "mai", "ne", "sa"}:
            return preferred, 0.68
        return "hi", 0.58

    if script == "arabic":
        if preferred in {"ur", "ks", "sd"}:
            return preferred, 0.72
        return "ur", 0.62

    # Assamese has two characters not normally used in Bengali.
    if any(ch in text for ch in ("ৰ", "ৱ")):
        return "as", 0.94
    if preferred in {"as", "bn", "mni"}:
        return preferred, 0.68
    return "bn", 0.72


def detect_text_language(text: str, preferred: Optional[str] = None) -> LanguageDetection:
    """Detect supported Indian languages from script and romanized markers."""
    text = (text or "").strip()
    preferred = normalize_language(preferred, "en") if preferred else None
    if not text:
        return LanguageDetection(preferred or "en", 0.0, "empty", "unknown", {})

    counts: dict[str, int] = {}
    for name, (start, end) in SCRIPT_RANGES.items():
        counts[name] = sum(start <= ord(ch) <= end for ch in text)

    indic_counts = {k: v for k, v in counts.items() if k != "latin" and v > 0}
    if indic_counts:
        script, count = max(indic_counts.items(), key=lambda item: item[1])
        total_letters = max(1, sum(counts.values()))
        script_confidence = min(0.99, 0.72 + 0.27 * count / total_letters)
        if script in SCRIPT_TO_LANGUAGE:
            language = SCRIPT_TO_LANGUAGE[script]
            return LanguageDetection(language, script_confidence, "unicode_script", script, {language: script_confidence})
        language, shared_confidence = _shared_script_language(script, text, preferred)
        confidence = min(script_confidence, shared_confidence)
        return LanguageDetection(language, confidence, "unicode_script_lexical", script, {language: confidence})

    words = set(re.findall(r"[a-zA-Z']+", text.lower()))
    marker_scores = {
        language: len(words.intersection(markers))
        for language, markers in ROMANIZED_MARKERS.items()
    }
    best_language, best_score = max(marker_scores.items(), key=lambda item: item[1])
    if best_score >= 2:
        confidence = min(0.88, 0.55 + best_score * 0.08)
        return LanguageDetection(best_language, confidence, "romanized_lexical", "latin", {best_language: confidence})
    if best_score == 1 and preferred and preferred != "en":
        return LanguageDetection(preferred, 0.52, "session_preference", "latin", {preferred: 0.52, "en": 0.48})
    return LanguageDetection("en", 0.9 if len(words) >= 3 else 0.62, "unicode_script", "latin", {"en": 0.9})


class MultilingualASR:
    """Lazy Faster-Whisper ASR with a Transformers fallback."""

    def __init__(self) -> None:
        self._model = None
        self._engine = "none"
        self._model_lock = asyncio.Lock()

    async def _ensure_model(self) -> None:
        if self._model is not None:
            return
        async with self._model_lock:
            if self._model is not None:
                return
            await asyncio.to_thread(self._load_model)

    def _load_model(self) -> None:
        model_name = os.environ.get("WHISPER_MODEL_SIZE", "small")
        device = os.environ.get("WHISPER_DEVICE", "auto")
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"

        try:
            from faster_whisper import WhisperModel
            compute_type = os.environ.get(
                "WHISPER_COMPUTE_TYPE", "float16" if device == "cuda" else "int8"
            )
            self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
            self._engine = "faster-whisper"
            logger.info("ASR loaded: faster-whisper/%s on %s", model_name, device)
            return
        except Exception as exc:
            logger.warning("Faster-Whisper unavailable: %s", exc)

        try:
            from transformers import pipeline
            torch_device = 0 if device == "cuda" else -1
            model_id = os.environ.get("WHISPER_TRANSFORMERS_MODEL", "openai/whisper-small")
            self._model = pipeline(
                "automatic-speech-recognition",
                model=model_id,
                device=torch_device,
                chunk_length_s=30,
                return_timestamps=True,
            )
            self._engine = "transformers-whisper"
            logger.info("ASR loaded: %s on %s", model_id, device)
        except Exception as exc:
            raise RuntimeError(
                "No ASR engine is available. Install faster-whisper or configure a Transformers Whisper model."
            ) from exc

    async def transcribe(self, audio_path: str, language_hint: Optional[str] = None) -> TranscriptionResult:
        await self._ensure_model()
        return await asyncio.to_thread(self._transcribe_sync, audio_path, language_hint)

    def _transcribe_sync(self, audio_path: str, language_hint: Optional[str]) -> TranscriptionResult:
        if not Path(audio_path).exists():
            raise FileNotFoundError(audio_path)
        hint = None if not language_hint or language_hint == "auto" else normalize_language(language_hint)

        if self._engine == "faster-whisper":
            segments_iter, info = self._model.transcribe(
                audio_path,
                language=hint,
                beam_size=int(os.environ.get("WHISPER_BEAM_SIZE", "5")),
                vad_filter=True,
                condition_on_previous_text=True,
            )
            segments = []
            text_parts = []
            for segment in segments_iter:
                value = segment.text.strip()
                if value:
                    text_parts.append(value)
                segments.append({
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "text": value,
                })
            detected = normalize_language(getattr(info, "language", None), hint or "en")
            return TranscriptionResult(
                text=" ".join(text_parts).strip(),
                language=detected,
                confidence=round(float(getattr(info, "language_probability", 0.0)), 4),
                duration=round(float(getattr(info, "duration", 0.0) or 0.0), 3),
                segments=segments,
                engine=self._engine,
            )

        result = self._model(audio_path, generate_kwargs={"language": hint} if hint else None)
        chunks = result.get("chunks") or []
        segments = []
        for chunk in chunks:
            timestamp = chunk.get("timestamp") or (0.0, 0.0)
            segments.append({"start": timestamp[0] or 0.0, "end": timestamp[1] or 0.0, "text": chunk.get("text", "").strip()})
        text = result.get("text", "").strip()
        detection = detect_text_language(text, preferred=hint)
        duration = segments[-1]["end"] if segments else 0.0
        return TranscriptionResult(text, detection.language, detection.confidence, duration, segments, self._engine)

    @property
    def engine(self) -> str:
        return self._engine


def analyze_vocal_emotion(audio_path: str) -> VocalEmotion:
    """Estimate vocal affect from energy, pitch, dynamics, and speech activity.

    This is a transparent prosody classifier, not a claim of clinical emotion
    recognition.  Text emotion is fused with this signal by AvatarRuntimeService.
    """
    import soundfile as sf

    data, sample_rate = sf.read(audio_path, always_2d=False)
    data = np.asarray(data, dtype=np.float32)
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    if data.size == 0:
        return VocalEmotion("neutral", 0.0, 0.0, 0.0, 0.5, {})
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(np.square(data)) + 1e-10))
    duration = float(len(data) / max(sample_rate, 1))

    pitch_values = np.array([], dtype=np.float32)
    speaking_ratio = 0.0
    tempo = 0.0
    try:
        import librosa
        frame_length = min(2048, max(256, 2 ** int(np.log2(max(256, sample_rate // 20)))))
        hop_length = max(128, frame_length // 4)
        rms_frames = librosa.feature.rms(y=data, frame_length=frame_length, hop_length=hop_length)[0]
        threshold = max(float(np.percentile(rms_frames, 20)) * 1.6, 0.008)
        speaking_ratio = float(np.mean(rms_frames > threshold))
        f0 = librosa.yin(data, fmin=65, fmax=500, sr=sample_rate, frame_length=frame_length, hop_length=hop_length)
        pitch_values = f0[np.isfinite(f0)]
        onset = librosa.onset.onset_strength(y=data, sr=sample_rate, hop_length=hop_length)
        tempo_value = librosa.feature.tempo(onset_envelope=onset, sr=sample_rate, hop_length=hop_length)
        tempo = float(tempo_value[0]) if len(tempo_value) else 0.0
    except Exception as exc:
        logger.debug("Detailed vocal emotion features unavailable: %s", exc)

    pitch_mean = float(np.mean(pitch_values)) if pitch_values.size else 0.0
    pitch_std = float(np.std(pitch_values)) if pitch_values.size else 0.0
    energy_db = float(20 * np.log10(max(rms, 1e-5)))
    energy_norm = float(np.clip((energy_db + 45.0) / 35.0, 0.0, 1.0))
    pitch_norm = float(np.clip((pitch_mean - 90.0) / 190.0, 0.0, 1.0)) if pitch_mean else 0.45
    variation_norm = float(np.clip(pitch_std / 75.0, 0.0, 1.0)) if pitch_std else 0.25
    tempo_norm = float(np.clip((tempo - 60.0) / 140.0, 0.0, 1.0)) if tempo else speaking_ratio
    arousal = float(np.clip(0.45 * energy_norm + 0.25 * variation_norm + 0.3 * tempo_norm, 0.0, 1.0))
    dominance = float(np.clip(0.55 * energy_norm + 0.25 * (1.0 - pitch_norm) + 0.2 * speaking_ratio, 0.0, 1.0))

    if arousal > 0.7 and energy_norm > 0.62:
        emotion = "angry" if pitch_norm < 0.55 else "excited"
        valence = -0.55 if emotion == "angry" else 0.65
    elif arousal > 0.62 and pitch_norm > 0.68:
        emotion, valence = "surprised", 0.2
    elif arousal < 0.32 and energy_norm < 0.38:
        emotion, valence = "sad", -0.55
    elif arousal < 0.4 and variation_norm < 0.35:
        emotion, valence = "calm", 0.25
    elif pitch_norm > 0.72 and dominance < 0.45:
        emotion, valence = "fearful", -0.45
    else:
        emotion, valence = "neutral", 0.0

    confidence = float(np.clip(0.38 + abs(arousal - 0.5) * 0.7 + min(duration, 8.0) / 40.0, 0.35, 0.86))
    return VocalEmotion(
        emotion=emotion,
        confidence=round(confidence, 4),
        valence=round(valence, 4),
        arousal=round(arousal, 4),
        dominance=round(dominance, 4),
        metrics={
            "duration": round(duration, 3),
            "peak": round(peak, 5),
            "rms": round(rms, 5),
            "energy_db": round(energy_db, 3),
            "pitch_mean_hz": round(pitch_mean, 3),
            "pitch_std_hz": round(pitch_std, 3),
            "speaking_ratio": round(speaking_ratio, 4),
            "tempo_bpm": round(tempo, 3),
        },
    )


_default_asr: Optional[MultilingualASR] = None


def get_multilingual_asr() -> MultilingualASR:
    global _default_asr
    if _default_asr is None:
        _default_asr = MultilingualASR()
    return _default_asr
