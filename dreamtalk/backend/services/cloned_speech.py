"""Verified multilingual voice-clone synthesis for the avatar runtime."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx
import numpy as np

from dreamtalk.backend.services.multimodal_language import SUPPORTED_LANGUAGES, normalize_language

logger = logging.getLogger("dreamtalk.avatar.speech")

# IndicF5 is published for these 11 Indian languages. English remains in the
# wider runtime because ASR, the LLM, and generic TTS support it, but it is not
# a documented IndicF5 reference/synthesis language.
INDICF5_LANGUAGES = frozenset(code for code in SUPPORTED_LANGUAGES if code != "en")


EDGE_VOICES = {
    "as": "as-IN-YashicaNeural",
    "bn": "bn-IN-TanishaaNeural",
    "en": "en-IN-NeerjaNeural",
    "gu": "gu-IN-DhwaniNeural",
    "hi": "hi-IN-SwaraNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "mr": "mr-IN-AarohiNeural",
    "or": "or-IN-SubhasiniNeural",
    "pa": "pa-IN-GurpreetNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
}


PROSODY_PRESETS = {
    "neutral": (1.00, 0.0, 1.00),
    "calm": (0.96, -0.2, 0.96),
    "happy": (1.05, 0.6, 1.04),
    "excited": (1.09, 1.0, 1.08),
    "sad": (0.92, -0.8, 0.88),
    "angry": (1.06, -0.2, 1.10),
    "surprised": (1.08, 1.2, 1.06),
    "fearful": (1.04, 1.0, 0.96),
    "disgusted": (0.95, -0.5, 0.94),
    "frustrated": (1.03, -0.3, 1.05),
    "confused": (0.98, 0.3, 0.98),
    "loving": (0.96, 0.2, 0.98),
}


@dataclass
class SpeechResult:
    path: str
    audio_url: str
    engine: str
    cloned: bool
    language: str
    duration: float
    sample_rate: int
    emotion: str
    service_url: Optional[str] = None
    fallback_reason: Optional[str] = None
    reference_language: Optional[str] = None
    cross_lingual: bool = False
    quality_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _default_output_dir() -> Path:
    configured = os.environ.get("TTS_OUTPUT_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent.parent / "pipeline_outputs" / "tts"


def _audio_metadata(path: Path) -> tuple[float, int]:
    import soundfile as sf

    info = sf.info(str(path))
    return round(float(info.duration), 3), int(info.samplerate)


def prepare_reference_audio(source_path: str, destination_path: str) -> dict[str, Any]:
    """Convert uploaded reference audio to trimmed mono 24 kHz WAV."""
    import librosa
    import soundfile as sf

    source = Path(source_path)
    destination = Path(destination_path)
    if not source.exists():
        raise FileNotFoundError(source)

    audio, _ = librosa.load(str(source), sr=24000, mono=True)
    if audio.size == 0:
        raise ValueError("Reference audio is empty")
    audio, _ = librosa.effects.trim(audio, top_db=35)
    duration = len(audio) / 24000.0
    if duration < 3.0:
        raise ValueError("Reference audio must contain at least 3 seconds of speech")
    max_seconds = float(os.environ.get("VOICE_REFERENCE_MAX_SECONDS", "45"))
    if duration > max_seconds:
        audio = audio[: int(max_seconds * 24000)]
        duration = max_seconds

    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio)) + 1e-10))
    clipping_ratio = float(np.mean(np.abs(audio) >= 0.995))
    if peak > 0:
        audio = audio / peak * 0.92

    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(destination), audio.astype(np.float32), 24000, subtype="PCM_16")
    quality = "good"
    warnings = []
    if rms < 0.015:
        quality = "low"
        warnings.append("Reference audio is quiet")
    if clipping_ratio > 0.01:
        quality = "low"
        warnings.append("Reference audio contains clipping")
    if duration < 10:
        quality = "acceptable" if quality == "good" else quality
        warnings.append("20-60 seconds of clean speech will improve similarity")

    return {
        "path": str(destination),
        "duration": round(duration, 3),
        "sample_rate": 24000,
        "channels": 1,
        "peak_before_normalization": round(peak, 5),
        "rms": round(rms, 5),
        "clipping_ratio": round(clipping_ratio, 6),
        "quality": quality,
        "warnings": warnings,
    }


class ClonedSpeechService:
    """IndicF5-first TTS service with explicit, observable fallback behavior."""

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else _default_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._active_url: Optional[str] = None
        self._health: dict[str, Any] = {}
        self._health_checked_at = 0.0
        self._discovery_lock = asyncio.Lock()
        self._synthesis_lock = asyncio.Lock()

    def _service_candidates(self) -> list[str]:
        values = [
            os.environ.get("INDICF5_BASE_URL"),
            os.environ.get("INDICF5_MICROSERVICE_URL"),
            "http://indicf5:8002",
            "http://indicf5:8003",
            "http://host.docker.internal:8002",
            "http://localhost:8002",
            "http://localhost:8003",
        ]
        candidates: list[str] = []
        for value in values:
            if value:
                normalized = value.rstrip("/")
                if normalized not in candidates:
                    candidates.append(normalized)
        return candidates

    async def discover(self, force: bool = False) -> dict[str, Any]:
        if not force and self._health and time.monotonic() - self._health_checked_at < 30:
            return self._health
        async with self._discovery_lock:
            failures = []
            timeout = httpx.Timeout(5.0, connect=2.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                for candidate in self._service_candidates():
                    try:
                        response = await client.get(f"{candidate}/health")
                        response.raise_for_status()
                        payload = response.json()
                        if payload.get("status") == "ok" and payload.get("model_loaded") is True:
                            self._active_url = candidate
                            self._health = {
                                "available": True,
                                "url": candidate,
                                "model_loaded": True,
                                "device": payload.get("device", "unknown"),
                                "busy": bool(payload.get("busy", False)),
                                "active_requests": int(payload.get("active_requests", 0)),
                                "queued_requests": int(payload.get("queued_requests", 0)),
                                "nfe_steps": payload.get("nfe_steps"),
                                "supported_languages": {
                                    code: SUPPORTED_LANGUAGES[code] for code in sorted(INDICF5_LANGUAGES)
                                },
                            }
                            self._health_checked_at = time.monotonic()
                            return self._health
                        failures.append(f"{candidate}: model not loaded")
                    except Exception as exc:
                        failures.append(f"{candidate}: {type(exc).__name__}")
            self._active_url = None
            self._health = {
                "available": False,
                "model_loaded": False,
                "supported_languages": {
                    code: SUPPORTED_LANGUAGES[code] for code in sorted(INDICF5_LANGUAGES)
                },
                "failures": failures,
            }
            self._health_checked_at = time.monotonic()
            return self._health

    async def synthesize_clone(
        self,
        text: str,
        reference_audio: str,
        reference_text: str,
        language: str,
        emotion: str = "neutral",
        reference_language: Optional[str] = None,
    ) -> SpeechResult:
        language = normalize_language(language)
        if language not in INDICF5_LANGUAGES:
            raise ValueError(f"IndicF5 does not support language '{language}'")
        if not text.strip():
            raise ValueError("Text to synthesize is empty")
        if not reference_text.strip():
            raise ValueError("Reference transcript is required for reliable voice cloning")
        reference_path = Path(reference_audio)
        if not reference_path.exists():
            raise FileNotFoundError(reference_path)

        normalized_reference_language = (
            normalize_language(reference_language) if reference_language else None
        )
        quality_warnings: list[str] = []
        if normalized_reference_language and normalized_reference_language not in INDICF5_LANGUAGES:
            quality_warnings.append(
                "The reference sample language is outside IndicF5's documented 11 Indian languages; "
                "speaker similarity or intelligibility may be reduced. Upload a clean reference in any "
                "supported Indian language for production cloning."
            )

        health = await self.discover()
        if not health.get("available") or not self._active_url:
            raise RuntimeError("IndicF5 voice-cloning service is unavailable or its model is not loaded")

        output_path = self.output_dir / f"clone_{language}_{uuid.uuid4().hex}.wav"
        default_timeout = "900" if health.get("device") == "cpu" else "300"
        timeout_seconds = float(os.environ.get("INDICF5_TIMEOUT", default_timeout))
        timeout = httpx.Timeout(timeout_seconds, connect=10.0)
        async with self._synthesis_lock:
            with reference_path.open("rb") as ref_file:
                files = {"ref_audio": (reference_path.name, ref_file, "audio/wav")}
                data = {"gen_text": text, "ref_text": reference_text, "lang": language}
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(f"{self._active_url}/synthesize", files=files, data=data)
                    if response.status_code >= 400:
                        detail = response.text[:500]
                        raise RuntimeError(f"IndicF5 synthesis failed ({response.status_code}): {detail}")
                    if len(response.content) < 256:
                        raise RuntimeError("IndicF5 returned an invalid audio payload")
                    output_path.write_bytes(response.content)

        await asyncio.to_thread(self._apply_emotional_prosody, output_path, emotion)
        duration, sample_rate = _audio_metadata(output_path)
        return SpeechResult(
            path=str(output_path),
            audio_url=f"/outputs/{output_path.name}",
            engine="indicf5",
            cloned=True,
            language=language,
            duration=duration,
            sample_rate=sample_rate,
            emotion=emotion,
            service_url=self._active_url,
            reference_language=normalized_reference_language,
            cross_lingual=bool(
                normalized_reference_language and normalized_reference_language != language
            ),
            quality_warnings=quality_warnings,
        )

    def _apply_emotional_prosody(self, path: Path, emotion: str) -> None:
        """Apply restrained prosody changes while preserving speaker identity."""
        preset = PROSODY_PRESETS.get(emotion, PROSODY_PRESETS["neutral"])
        rate, semitones, gain = preset
        if rate == 1.0 and semitones == 0.0 and gain == 1.0:
            return
        try:
            import librosa
            import soundfile as sf

            audio, sample_rate = sf.read(str(path), always_2d=False)
            audio = np.asarray(audio, dtype=np.float32)
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            if abs(rate - 1.0) > 0.005:
                audio = librosa.effects.time_stretch(audio, rate=rate)
            if abs(semitones) > 0.05:
                audio = librosa.effects.pitch_shift(audio, sr=sample_rate, n_steps=semitones)
            audio *= gain
            peak = float(np.max(np.abs(audio))) if audio.size else 0.0
            if peak > 0.98:
                audio = audio / peak * 0.95
            sf.write(str(path), audio, sample_rate, subtype="PCM_16")
        except Exception as exc:
            logger.warning("Emotion prosody post-processing skipped: %s", exc)

    async def synthesize_generic(
        self,
        text: str,
        language: str,
        emotion: str = "neutral",
        reason: Optional[str] = None,
    ) -> SpeechResult:
        """Generate clearly-labelled non-cloned fallback speech."""
        language = normalize_language(language)
        output_path = self.output_dir / f"generic_{language}_{uuid.uuid4().hex}.wav"
        mp3_path = output_path.with_suffix(".mp3")
        engine_used = "edge-tts"
        try:
            import edge_tts

            rate, semitones, _ = PROSODY_PRESETS.get(emotion, PROSODY_PRESETS["neutral"])
            rate_percent = int(round((rate - 1.0) * 100))
            pitch_hz = int(round(semitones * 3.0))
            communicate = edge_tts.Communicate(
                text=text,
                voice=EDGE_VOICES.get(language, EDGE_VOICES["en"]),
                rate=f"{rate_percent:+d}%",
                pitch=f"{pitch_hz:+d}Hz",
            )
            await communicate.save(str(mp3_path))
            await asyncio.to_thread(self._convert_to_wav, mp3_path, output_path)
        except Exception as edge_error:
            logger.warning("Edge TTS fallback failed: %s", edge_error)
            try:
                from dreamtalk.backend.services.voice_orchestrator import VoiceOrchestrator

                generated = await VoiceOrchestrator().generate_speech(
                    text=text,
                    voice_id="af_heart",
                    emotion=emotion,
                    language=language,
                )
                shutil.copy2(generated, output_path)
                engine_used = "kokoro"
            except Exception as kokoro_error:
                raise RuntimeError(
                    f"No speech engine available (Edge: {edge_error}; Kokoro: {kokoro_error})"
                ) from kokoro_error
        finally:
            mp3_path.unlink(missing_ok=True)

        duration, sample_rate = _audio_metadata(output_path)
        return SpeechResult(
            path=str(output_path),
            audio_url=f"/outputs/{output_path.name}",
            engine=engine_used,
            cloned=False,
            language=language,
            duration=duration,
            sample_rate=sample_rate,
            emotion=emotion,
            fallback_reason=reason,
        )

    @staticmethod
    def _convert_to_wav(source: Path, destination: Path) -> None:
        import librosa
        import soundfile as sf

        audio, sample_rate = librosa.load(str(source), sr=24000, mono=True)
        if audio.size == 0:
            raise RuntimeError("TTS audio conversion produced no samples")
        sf.write(str(destination), audio, sample_rate, subtype="PCM_16")

    async def synthesize(
        self,
        text: str,
        language: str,
        emotion: str,
        profile: Optional[dict[str, Any]],
        strict_clone: bool = True,
    ) -> SpeechResult:
        if profile:
            voice = profile.get("voice") or {}
            try:
                return await self.synthesize_clone(
                    text=text,
                    reference_audio=voice["reference_audio_path"],
                    reference_text=voice["reference_text"],
                    language=language,
                    emotion=emotion,
                    reference_language=voice.get("sample_language"),
                )
            except Exception as exc:
                if strict_clone:
                    raise
                return await self.synthesize_generic(text, language, emotion, reason=str(exc))
        if strict_clone:
            raise RuntimeError("A ready avatar profile is required for cloned speech")
        return await self.synthesize_generic(text, language, emotion, reason="No avatar profile selected")


_default_speech_service: Optional[ClonedSpeechService] = None


def get_cloned_speech_service() -> ClonedSpeechService:
    global _default_speech_service
    if _default_speech_service is None:
        _default_speech_service = ClonedSpeechService()
    return _default_speech_service
