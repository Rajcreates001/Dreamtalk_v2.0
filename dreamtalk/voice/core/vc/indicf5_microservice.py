"""
IndicF5 Microservice — Standalone FastAPI service for IndicF5 voice cloning.

Designed to run in a Docker container (Linux) to avoid the Windows torch DLL
conflict (OMP: libomp.dll vs libiomp5md.dll). Exposes a clean HTTP API that
the main DreamTalk application calls instead of importing IndicF5 directly.

Endpoints:
  GET  /health       -> {"status": "ok", "model_loaded": bool, "device": str}
  POST /synthesize   -> WAV audio (voice-cloned speech from reference + text)
  GET  /models       -> {"type": "F5-TTS", "supported_languages": [...]}
"""

import asyncio
import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

# ---------------------------------------------------------------------------
# Fix OpenMP before any torch import
# ---------------------------------------------------------------------------
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dreamtalk.indicf5.microservice")

# ---------------------------------------------------------------------------
# App + globals (set during startup)
# ---------------------------------------------------------------------------
app = FastAPI(title="IndicF5 Voice Cloning Service", version="0.1.0")
_engine = None
_device = "cpu"
_inference_lock = asyncio.Lock()
_active_requests = 0
_queued_requests = 0


# ==========================================================================
# Model Management
# ==========================================================================

def _find_weights_dir() -> Optional[Path]:
    """Locate the IndicF5 weights directory.

    Priority:
      1. INDICF5_WEIGHTS_DIR env var (for Docker volume mounts)
      2. Default path relative to this file
    """
    env_path = os.environ.get("INDICF5_WEIGHTS_DIR")
    if env_path:
        p = Path(env_path)
        if p.exists() and (p / "model.safetensors").exists():
            logger.info("Weights from env var: %s", p)
            return p

    # Relative path: voice/core/vc/ -> 4 up -> weights/voice/indic_tts/IndicF5
    rel = Path(__file__).resolve().parent.parent.parent.parent
    candidate = rel / "weights" / "voice" / "indic_tts" / "IndicF5"
    if candidate.exists() and (candidate / "model.safetensors").exists():
        logger.info("Weights from relative path: %s", candidate)
        return candidate

    logger.warning("IndicF5 weights not found at %s (env=%s)", candidate, env_path)
    return None


def _load_engine():
    """Load the IndicF5 engine on startup.

    Uses IndicF5TTSEngine (the project's own adapter) because it provides
    the .synthesize() method that the endpoint calls. The underlying F5TTS
    class from indicf5/api.py only has .infer().
    """
    global _engine, _device

    weights_dir = _find_weights_dir()
    if weights_dir is None:
        logger.error("Cannot load IndicF5: weights not found")
        return None, "cpu"

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Torch device: %s (CUDA available: %s)", device, torch.cuda.is_available())

    try:
        # Ensure the project root is on sys.path
        _root = str(Path(__file__).resolve().parent.parent.parent.parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)

        from dreamtalk.voice.core.tts.indicf5_engine import IndicF5TTSEngine

        engine = IndicF5TTSEngine(device=device)
        if not engine.is_loaded:
            logger.warning("IndicF5 engine loaded but not ready")
            return None, device

        logger.info("IndicF5 engine loaded successfully on %s", device)
        return engine, device
    except Exception as e:
        logger.error("Failed to load IndicF5 engine: %s", e, exc_info=True)
        return None, device


@app.on_event("startup")
async def startup():
    global _engine, _device
    logger.info("Starting IndicF5 microservice...")
    engine, device = _load_engine()
    _engine = engine
    _device = device
    if _engine is not None:
        logger.info("IndicF5 microservice ready on %s", device)
    else:
        logger.warning("IndicF5 microservice started WITHOUT model — synthesize will fail")


# ==========================================================================
# Endpoints
# ==========================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_loaded": _engine is not None,
        "device": _device,
        "busy": _active_requests > 0,
        "active_requests": _active_requests,
        "queued_requests": _queued_requests,
        "nfe_steps": int(os.environ.get("INDICF5_NFE_STEPS", "8" if _device == "cpu" else "16")),
    }


@app.get("/models")
async def models():
    """List supported models and languages."""
    if _engine is not None:
        langs = _engine.SUPPORTED_LANGUAGES
    else:
        langs = {
            "as": "Assamese", "bn": "Bengali", "gu": "Gujarati",
            "hi": "Hindi", "kn": "Kannada", "ml": "Malayalam",
            "mr": "Marathi", "or": "Odia", "pa": "Punjabi",
            "ta": "Tamil", "te": "Telugu", "en": "English",
        }
    return {
        "type": "F5-TTS (CFM-based)",
        "supported_languages": langs,
        "model_loaded": _engine is not None,
        "device": _device,
    }


@app.post("/synthesize")
async def synthesize(
    ref_audio: UploadFile = File(...),
    gen_text: str = Form(...),
    ref_text: str = Form(""),
    lang: str = Form("en"),
):
    """Synthesize speech in the voice of ref_audio speaking gen_text.

    Args:
        ref_audio: Reference audio file (WAV, speaker to clone)
        gen_text: Text to synthesize in the cloned voice
        ref_text: Transcript of the reference audio (optional)
        lang: Language code (default: "en")

    Returns:
        WAV audio file with voice-cloned speech
    """
    global _active_requests, _queued_requests

    if _engine is None:
        raise HTTPException(status_code=503, detail="IndicF5 model not loaded")
    gen_text = gen_text.strip()
    ref_text = ref_text.strip()
    if not gen_text:
        raise HTTPException(status_code=422, detail="gen_text cannot be empty")
    max_chars = int(os.environ.get("INDICF5_MAX_TEXT_CHARS", "500"))
    if len(gen_text) > max_chars:
        raise HTTPException(status_code=422, detail=f"gen_text exceeds {max_chars} characters")

    import tempfile
    import soundfile as sf
    import numpy as np

    tmp_path = None
    try:
        # Write uploaded file to a temp WAV
        audio_bytes = await ref_audio.read()
        max_reference_bytes = int(os.environ.get("INDICF5_MAX_REFERENCE_BYTES", str(50 * 1024 * 1024)))
        if not audio_bytes:
            raise HTTPException(status_code=422, detail="Reference audio is empty")
        if len(audio_bytes) > max_reference_bytes:
            raise HTTPException(status_code=413, detail="Reference audio is too large")
        suffix = Path(ref_audio.filename or "ref.wav").suffix or ".wav"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(audio_bytes)
        tmp_path = tmp.name
        tmp.close()

        logger.info(
            "Synthesizing: ref=%s (%d bytes), text=%s...",
            ref_audio.filename, len(audio_bytes), gen_text[:50],
        )

        # The model is not concurrency-safe and duplicate CPU inference can
        # exhaust RAM. Queue requests and run the blocking torch call in a
        # worker thread so /health remains responsive while speech is built.
        _queued_requests += 1
        entered_inference = False
        try:
            async with _inference_lock:
                _queued_requests -= 1
                _active_requests += 1
                entered_inference = True
                try:
                    wav, sr = await asyncio.to_thread(
                        _engine.synthesize,
                        text=gen_text,
                        ref_audio_path=tmp_path,
                        ref_text=ref_text,
                        lang=lang,
                    )
                finally:
                    _active_requests -= 1
        except BaseException:
            if not entered_inference:
                _queued_requests -= 1
            raise

        if wav is None or len(wav) == 0:
            raise HTTPException(status_code=500, detail="Synthesis produced no audio")

        # Normalise peak to 0 dBFS
        wav = np.asarray(wav, dtype=np.float32)
        peak = np.max(np.abs(wav))
        if peak > 0:
            wav = wav / peak * 0.95

        # Serialise to in-memory WAV
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, wav, sr, format="WAV")
        wav_bytes = wav_buffer.getvalue()

        logger.info(
            "Synthesis complete: %d samples @ %d Hz (%.1f s)",
            len(wav), sr, len(wav) / sr,
        )

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="indicf5_output.wav"',
                "X-Sample-Rate": str(sr),
                "X-Duration": f"{len(wav) / sr:.3f}",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Synthesis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@app.post("/clone_embedding")
async def clone_embedding(
    ref_audio: UploadFile = File(...),
    transcript: str = Form(""),
):
    """Extract voice embedding from reference audio for later use.

    Returns a JSON dict with ref_audio metadata.
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="IndicF5 model not loaded")

    import tempfile

    tmp_path = None
    try:
        audio_bytes = await ref_audio.read()
        suffix = Path(ref_audio.filename or "ref.wav").suffix or ".wav"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(audio_bytes)
        tmp_path = tmp.name
        tmp.close()

        result = _engine.clone_voice(tmp_path, transcript)
        return {
            "status": "ok",
            "ref_audio_path": tmp_path,
            "ref_text": transcript or "",
            "supported_languages": list(_engine.SUPPORTED_LANGUAGES.keys()),
        }
    except Exception as e:
        logger.error("Embedding extraction failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ==========================================================================
# Entry point
# ==========================================================================

if __name__ == "__main__":
    port = int(os.environ.get("INDICF5_PORT", "8002"))
    host = os.environ.get("INDICF5_HOST", "0.0.0.0")
    logger.info("Starting IndicF5 microservice on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
