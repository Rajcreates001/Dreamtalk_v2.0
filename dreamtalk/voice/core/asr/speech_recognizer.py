"""
DreamTalk — Speech Recognizer

Multi-backend ASR with automatic fallback:
  1. OpenAI Whisper API (fast, accurate, requires API key)
  2. faster-whisper local (CPU/GPU, no API key)
  3. Whisper via OpenAI-compatible endpoint (GPT-OSS, etc.)
  4. Stub (returns empty — for testing without ASR)

Usage:
    recognizer = get_recognizer()
    result = await recognizer.transcribe("path/to/audio.wav", language="hi")
    print(result.text, result.language, result.segments)
"""

import io
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger("dreamtalk.asr")


@dataclass
class TranscriptionResult:
    """Structured ASR output."""
    text: str = ""
    language: str = ""
    confidence: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    backend: str = "none"
    duration_seconds: float = 0.0

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class SpeechRecognizer:
    """Backend-agnostic speech recognizer with fallback chain."""

    def __init__(self):
        self._backends: List[str] = []
        self._available_backends: Dict[str, Any] = {}
        self._detect_backends()

    def _detect_backends(self):
        """Detect which ASR backends are available."""
        # 1. OpenAI Whisper API
        api_key = os.environ.get("OPENAI_API_KEY", "")
        api_base = os.environ.get("OPENAI_API_BASE", os.environ.get("GPU_SERVER_BASE_URL", ""))
        if api_key or "144.79.62.242" in api_base:
            self._available_backends["openai_api"] = {
                "api_key": api_key,
                "base_url": api_base.rstrip("/v1") + "/v1" if "/v1" not in api_base else api_base,
            }
            self._backends.append("openai_api")
            logger.info("ASR backend: OpenAI Whisper API available")

        # 2. faster-whisper local
        try:
            from faster_whisper import WhisperModel
            self._available_backends["faster_whisper"] = {"cls": WhisperModel}
            self._backends.append("faster_whisper")
            logger.info("ASR backend: faster-whisper available")
        except ImportError:
            pass

        # 3. OpenAI whisper Python package
        try:
            import whisper
            self._available_backends["openai_whisper"] = {"cls": whisper}
            self._backends.append("openai_whisper")
            logger.info("ASR backend: openai-whisper available")
        except ImportError:
            pass

        if not self._backends:
            self._backends.append("stub")
            logger.warning("No ASR backend available — using stub")

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to WAV/MP3/FLAC audio file.
            language: ISO 639-1 code (e.g. "hi", "ta", "en"). None = auto-detect.
            backend: Force a specific backend. None = auto (try all in order).

        Returns:
            TranscriptionResult with text, language, segments.
        """
        if not os.path.exists(audio_path):
            return TranscriptionResult(text="", backend="error",
                                       segments=[{"error": f"File not found: {audio_path}"}])

        # Get audio duration
        try:
            import soundfile as sf
            info = sf.info(audio_path)
            duration = info.duration
        except Exception:
            duration = 0.0

        # Try backends in order
        backends_to_try = [backend] if backend else self._backends

        for b in backends_to_try:
            try:
                if b == "openai_api":
                    result = await self._transcribe_openai_api(audio_path, language)
                elif b == "faster_whisper":
                    result = self._transcribe_faster_whisper(audio_path, language)
                elif b == "openai_whisper":
                    result = self._transcribe_openai_whisper(audio_path, language)
                elif b == "stub":
                    result = TranscriptionResult(text="[ASR not available]", backend="stub")
                else:
                    continue

                result.duration_seconds = duration
                if result.text and result.text != "[ASR not available]":
                    logger.info(
                        f"ASR [{result.backend}]: {len(result.text)} chars, "
                        f"lang={result.language}, {duration:.1f}s audio"
                    )
                    return result
            except Exception as e:
                logger.warning(f"ASR backend '{b}' failed: {e}")
                continue

        return TranscriptionResult(
            text="[ASR failed — no backend succeeded]",
            backend="error",
            duration_seconds=duration,
        )

    async def _transcribe_openai_api(
        self, audio_path: str, language: Optional[str]
    ) -> TranscriptionResult:
        """Transcribe using OpenAI-compatible Whisper API."""
        import httpx

        cfg = self._available_backends["openai_api"]
        url = f"{cfg['base_url']}/audio/transcriptions"
        headers = {}
        if cfg["api_key"]:
            headers["Authorization"] = f"Bearer {cfg['api_key']}"

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
            data = {"model": "whisper-1", "response_format": "verbose_json"}
            if language:
                data["language"] = language

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, files=files, data=data, headers=headers)
                resp.raise_for_status()
                result = resp.json()

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "text": seg.get("text", ""),
            })

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language", language or "unknown"),
            confidence=0.9,
            segments=segments,
            backend="openai_api",
        )

    def _transcribe_faster_whisper(
        self, audio_path: str, language: Optional[str]
    ) -> TranscriptionResult:
        """Transcribe using faster-whisper (CTranslate2)."""
        from faster_whisper import WhisperModel

        cfg = self._available_backends["faster_whisper"]
        model_size = os.environ.get("WHISPER_MODEL_SIZE", "base")
        device = os.environ.get("WHISPER_DEVICE", "cpu")
        compute = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

        model = WhisperModel(model_size, device=device, compute_type=compute)
        segments_gen, info = model.transcribe(
            audio_path, language=language, beam_size=5,
        )

        segments = []
        texts = []
        for seg in segments_gen:
            texts.append(seg.text)
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
            })

        return TranscriptionResult(
            text=" ".join(texts).strip(),
            language=info.language or language or "unknown",
            confidence=info.language_probability or 0.8,
            segments=segments,
            backend="faster_whisper",
        )

    def _transcribe_openai_whisper(
        self, audio_path: str, language: Optional[str]
    ) -> TranscriptionResult:
        """Transcribe using OpenAI whisper Python package."""
        import whisper

        cfg = self._available_backends["openai_whisper"]
        whisper_mod = cfg["cls"]
        model_size = os.environ.get("WHISPER_MODEL_SIZE", "base")
        model = whisper_mod.load_model(model_size, device="cpu")

        opts = {"fp16": False}
        if language:
            opts["language"] = language

        result = model.transcribe(audio_path, **opts)

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "text": seg.get("text", ""),
            })

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language", language or "unknown"),
            confidence=0.85,
            segments=segments,
            backend="openai_whisper",
        )

    def available_backends(self) -> List[str]:
        return list(self._backends)


# ── Singleton ──────────────────────────────────────────────────────────

_recognizer: Optional[SpeechRecognizer] = None


def get_recognizer() -> SpeechRecognizer:
    """Get or create the default speech recognizer singleton."""
    global _recognizer
    if _recognizer is None:
        _recognizer = SpeechRecognizer()
    return _recognizer
