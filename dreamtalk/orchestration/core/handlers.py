"""
DreamTalk Orchestration — Concrete Stage Handlers

Implements all 7 pipeline stages (ASR, Vision, LLM, Filter, TTS, Animation, Display)
with real model inference where available and graceful mock fallback.

Each handler extends StageHandler (from pipeline.py) and implements process().
Streaming handlers (LLM, TTS) implement process_streaming().
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from dreamtalk.orchestration.core.pipeline import StageHandler, PipelineStage

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ═══════════════════════════════════════════════════════════════════════
# Stage 1-2: ASR (Automatic Speech Recognition)
# ═══════════════════════════════════════════════════════════════════════

class ASRHandler(StageHandler):
    """Speech-to-text using Whisper (or mock fallback)."""

    def __init__(self, model_name: str = "base", language: str = "en"):
        self.model_name = model_name
        self.language = language
        self._model = None

    async def process(self, audio_input: Any = None) -> str:
        if audio_input is None:
            return ""

        # Try Whisper
        try:
            import whisper
            if self._model is None:
                self._model = whisper.load_model(self.model_name)
            result = self._model.transcribe(audio_input, language=self.language)
            text = result.get("text", "").strip()
            logger.info("ASR: transcribed %d chars from %s", len(text), audio_input)
            return text
        except ImportError:
            pass
        except Exception as e:
            logger.warning("Whisper failed: %s", e)

        # Fallback: return input as-is if it's already text
        if isinstance(audio_input, str) and len(audio_input) > 3:
            return audio_input

        logger.warning("ASR: no transcription available for %s", str(audio_input)[:50])
        return ""


# ═══════════════════════════════════════════════════════════════════════
# Stage 3: Vision (Contextual Awareness)
# ═══════════════════════════════════════════════════════════════════════

class VisionHandler(StageHandler):
    """Screen/context awareness — captures visual context from camera or screen."""

    def __init__(self):
        self._last_context = {}

    async def process(self, input_data: Any = None) -> dict:
        context = {}

        # Try screen capture
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                context["screen_width"] = screenshot.width
                context["screen_height"] = screenshot.height
                context["screen_captured"] = True
        except ImportError:
            context["screen_captured"] = False
        except Exception as e:
            logger.warning("Screen capture failed: %s", e)
            context["screen_captured"] = False

        self._last_context = context
        logger.debug("Vision context: %s", json.dumps(context, default=str)[:100])
        return context

    async def process_streaming(self) -> AsyncIterator[dict]:
        """Yield periodic context snapshots."""
        while True:
            yield await self.process()
            await asyncio.sleep(5.0)


# ═══════════════════════════════════════════════════════════════════════
# Stage 4-5: LLM (Language Model — Think + Respond)
# ═══════════════════════════════════════════════════════════════════════

class LLMHandler(StageHandler):
    """Large Language Model inference — streaming response generation."""

    def __init__(self, model_name: str = "rule_based", api_url: Optional[str] = None):
        self.model_name = model_name
        try:
            from dreamtalk.shared.config.settings import settings as _dt_settings
            _default_url = _dt_settings.GPU_SERVER_BASE_URL
        except Exception:
            _default_url = "http://localhost:11434/v1"
        self.api_url = api_url or os.environ.get("GPU_SERVER_BASE_URL", _default_url)

    async def process(self, input_data: tuple = None) -> str:
        """Non-streaming: return full response."""
        if input_data is None:
            return ""

        # If tuple, first element is transcription, second is context
        if isinstance(input_data, str):
            text = input_data
        else:
            text = str(input_data)

        # Try rule-based first (always available)
        try:
            from dreamtalk.brain.pipeline import BrainPipeline
            brain = BrainPipeline()
            result = await brain.make_decision(text=text, role="normal_user", model_name="rule_based")
            return result.response_text
        except Exception as e:
            logger.warning("Brain pipeline failed: %s", e)

        # Try LLM API
        if self.api_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=30) as client:
                    api_base = self.api_url.rstrip('/')
                    resp = await client.post(
                        f"{api_base}/chat/completions",
                        json={
                            "model": self.model_name,
                            "messages": [{"role": "user", "content": text}],
                            "stream": False,
                            "max_tokens": 256,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning("LLM API failed: %s", e)

        return f"Response to: {text[:100]}"

    async def process_streaming(self, text: str, context: dict = None) -> AsyncIterator[str]:
        """Streaming response generation."""
        # Try LLM API streaming
        if self.api_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=60) as client:
                    api_base = self.api_url.rstrip('/')
                    async with client.stream(
                        "POST",
                        f"{api_base}/chat/completions",
                        json={
                            "model": self.model_name,
                            "messages": [
                                {"role": "system", "content": "You are a helpful AI assistant."},
                                {"role": "user", "content": text},
                            ],
                            "stream": True,
                            "max_tokens": 256,
                        },
                    ) as resp:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                    content = chunk["choices"][0]["delta"].get("content", "")
                                    if content:
                                        yield content
                                except (json.JSONDecodeError, KeyError):
                                    pass
            except Exception as e:
                logger.warning("LLM streaming failed: %s", e)

        # Fallback: yield full response at once
        full = await self.process(text)
        yield full


# ═══════════════════════════════════════════════════════════════════════
# Stage 6: Filter (Profanity / Safety)
# ═══════════════════════════════════════════════════════════════════════

class FilterHandler(StageHandler):
    """Profanity filtering and content safety checks."""

    def __init__(self):
        self._bad_words = {"fuck", "shit", "damn", "ass", "bitch", "bastard", "crap"}

    async def process(self, text: str = "") -> str:
        if not text:
            return text

        filtered = text
        # Simple word-level filter
        words = filtered.split()
        cleaned = []
        for word in words:
            stripped = word.strip(".,!?;:\"'()[]{}").lower()
            if stripped in self._bad_words:
                # Preserve punctuation
                prefix = word[:len(word) - len(stripped)]
                suffix = word[-len(word) + len(stripped):]
                cleaned.append(prefix + "***" + suffix)
            else:
                cleaned.append(word)

        result = " ".join(cleaned)
        if result != text:
            logger.info("Filter: %d replacements made", sum(1 for i, j in zip(result.split(), text.split()) if i != j))
        return result

    async def process_streaming(self, input_stream: AsyncIterator[str]) -> AsyncIterator[str]:
        """Filter streaming content chunk by chunk."""
        async for chunk in input_stream:
            yield await self.process(chunk)


# ═══════════════════════════════════════════════════════════════════════
# Stage 7-8: TTS (Text-to-Speech + Voice Cloning)
# ═══════════════════════════════════════════════════════════════════════

class TTSHandler(StageHandler):
    """Text-to-Speech synthesis with voice cloning support."""

    def __init__(self, language: str = "en", voice: str = "en-US-JennyNeural"):
        self.language = language
        self.voice = voice
        self._output_dir = PROJECT_ROOT / "pipeline_outputs" / "tts"
        os.makedirs(str(self._output_dir), exist_ok=True)

    async def process(self, text: str = "") -> Optional[str]:
        """Generate TTS audio and return path to WAV file."""
        if not text:
            return None

        output_path = str(self._output_dir / f"tts_{uuid.uuid4().hex[:8]}.wav")

        # Try Edge-TTS
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                logger.info("TTS: generated %s (%d bytes)", output_path, os.path.getsize(output_path))
                return output_path
        except ImportError:
            pass
        except Exception as e:
            logger.warning("Edge-TTS failed: %s", e)

        # Try Kokoro
        try:
            from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
            engine = KokoroTTSEngine(device="cpu")
            import soundfile as sf
            audio = engine.synthesize_full(text, voice="af_heart", lang_code="a", speed=1.0)
            if audio is not None:
                sf.write(output_path, audio, 24000)
                return output_path
        except Exception as e:
            logger.warning("Kokoro TTS failed: %s", e)

        # Placeholder sine wave
        try:
            import numpy as np
            import soundfile as sf
            duration = min(max(len(text) * 0.08, 1.0), 15.0)
            sr = 22050
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)
            audio = 0.3 * np.sin(2 * np.pi * 180 * t)
            sf.write(output_path, audio, sr)
            logger.info("TTS: placeholder generated %s", output_path)
            return output_path
        except Exception as e:
            logger.error("TTS all methods failed: %s", e)
            return None

    async def process_streaming(self, text_stream: AsyncIterator[str]) -> AsyncIterator[str]:
        """Generate TTS for streaming text."""
        buffer = ""
        async for chunk in text_stream:
            buffer += chunk
            if len(buffer) > 50 and any(c in buffer[-3:] for c in ".!?"):
                path = await self.process(buffer)
                if path:
                    yield path
                buffer = ""

        if buffer.strip():
            path = await self.process(buffer)
            if path:
                yield path


# ═══════════════════════════════════════════════════════════════════════
# Stage 9: Animation (Live2D / 3D lip-sync and expressions)
# ═══════════════════════════════════════════════════════════════════════

class AnimationHandler(StageHandler):
    """Face animation — lip-sync and expression generation."""

    def __init__(self):
        self._musetalk = None
        self._liveportrait = None

    async def process(self, audio_path: str = None) -> dict:
        """Generate animation data from audio."""
        result = {
            "animation_type": "none",
            "parameters": {},
            "audio_path": audio_path,
        }

        if audio_path and os.path.exists(audio_path):
            # Try to extract timing for lip-sync
            try:
                import numpy as np
                import soundfile as sf
                data, sr = sf.read(audio_path)
                duration = len(data) / sr
                result["duration"] = duration
                result["audio_energy"] = float(np.mean(np.abs(data)))
                result["animation_type"] = "lip_sync"
                result["parameters"] = {
                    "duration": duration,
                    "energy": result["audio_energy"],
                    "sample_rate": sr,
                }
            except Exception as e:
                logger.warning("Audio analysis failed: %s", e)

        logger.debug("Animation: %s", json.dumps(result))
        return result


# ═══════════════════════════════════════════════════════════════════════
# Stage 10: Display (Output rendering)
# ═══════════════════════════════════════════════════════════════════════

class DisplayHandler(StageHandler):
    """Final output — displays avatar response to the user."""

    def __init__(self):
        self._last_display = {}

    async def process(self, animation_data: dict = None) -> dict:
        """Prepare the final display payload."""
        result = {
            "type": "avatar_response",
            "animation_data": animation_data or {},
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

        self._last_display = result
        logger.debug("Display: avatar response prepared")
        return result


# ═══════════════════════════════════════════════════════════════════════
# Factory: Register All Handlers
# ═══════════════════════════════════════════════════════════════════════

def register_all_handlers(pipeline):
    """Register all concrete handlers on a ProcessingPipeline instance."""
    from dreamtalk.orchestration.core.pipeline import ProcessingPipeline, PipelineStage

    handlers = {
        PipelineStage.ASR: ASRHandler(),
        PipelineStage.VISION: VisionHandler(),
        PipelineStage.LLM: LLMHandler(),
        PipelineStage.FILTER: FilterHandler(),
        PipelineStage.TTS: TTSHandler(),
        PipelineStage.ANIMATION: AnimationHandler(),
        PipelineStage.DISPLAY: DisplayHandler(),
    }

    for stage, handler in handlers.items():
        pipeline.register(stage, handler)

    logger.info("All 7 pipeline stage handlers registered")
    return pipeline
