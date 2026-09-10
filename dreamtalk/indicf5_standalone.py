"""
IndicF5 Standalone Microservice — imports the vendored indicf5 module directly.

This script avoids the dreamtalk package init chain by adding the vendored
indicf5 directory to sys.path and importing F5TTS directly. Designed to run
in the dedicated venv (D:\\venvs\\indicf5) to avoid torch DLL conflicts.

Usage:
    "D:\\venvs\\indicf5\\Scripts\\python.exe" dreamtalk/indicf5_standalone.py [--port 8002]
"""

import io
import json
import logging
import os
import pathlib
import sys

# Fix OpenMP before any torch import
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# ── Add vendored indicf5 directory to sys.path ────────────────────────
# The vendored module is at dreamtalk/voice/core/tts/indicf5/
# We add its parent so we can `import indicf5` directly
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent  # dreamtalk/ -> Dreamtalk-Integrated/
_VENDORED_TTS_DIR = _PROJECT_ROOT / "dreamtalk" / "voice" / "core" / "tts"
sys.path.insert(0, str(_VENDORED_TTS_DIR))

# Also add project root for any cross-references
sys.path.insert(0, str(_PROJECT_ROOT / "dreamtalk"))

# ── Weights directory ─────────────────────────────────────────────────
_WEIGHTS_DIR = _PROJECT_ROOT / "dreamtalk" / "weights" / "voice" / "indic_tts" / "IndicF5"
_INDIC_MODEL_PATH = str(_WEIGHTS_DIR / "model.safetensors")
_INDIC_VOCAB_PATH = str(_WEIGHTS_DIR / "checkpoints" / "vocab.txt")

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("indicf5.standalone")

# ── FastAPI app (lazy — model loads on startup) ──────────────────────
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
import uvicorn

app = FastAPI(title="IndicF5 Standalone Microservice", version="0.2.0")

_model = None
_device = "cpu"


def _load_model():
    global _model, _device

    if not _WEIGHTS_DIR.exists():
        logger.error("Weights not found at %s", _WEIGHTS_DIR)
        return

    import torch

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    if _device == "cpu":
        # Default is physical cores only; use all logical cores (~12% faster on this box)
        torch.set_num_threads(os.cpu_count() or torch.get_num_threads())
    logger.info("Torch device: %s (torch threads: %d)", _device, torch.get_num_threads())

    try:
        import indicf5.api

        logger.info("Loading F5TTS model from %s ...", _INDIC_MODEL_PATH)
        _model = indicf5.api.F5TTS(
            model_type="F5-TTS",
            ckpt_file=_INDIC_MODEL_PATH,
            vocab_file=_INDIC_VOCAB_PATH,
            device=_device,
        )
        logger.info("IndicF5 model loaded successfully on %s", _device)
    except Exception as e:
        logger.error("Failed to load IndicF5 model: %s", e, exc_info=True)
        _model = None


@app.on_event("startup")
async def startup():
    logger.info("Starting IndicF5 standalone microservice...")
    _load_model()
    if _model is not None:
        logger.info("Ready!")
    else:
        logger.warning("Started WITHOUT model — synthesize will fail")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "device": _device,
    }


@app.get("/models")
async def models():
    langs = {
        "as": "Assamese", "bn": "Bengali", "gu": "Gujarati",
        "hi": "Hindi", "kn": "Kannada", "ml": "Malayalam",
        "mr": "Marathi", "or": "Odia", "pa": "Punjabi",
        "ta": "Tamil", "te": "Telugu", "en": "English",
    }
    return {
        "type": "F5-TTS (CFM-based)",
        "supported_languages": langs,
        "model_loaded": _model is not None,
        "device": _device,
    }


@app.post("/synthesize")
async def synthesize(
    ref_audio: UploadFile = File(...),
    gen_text: str = Form(...),
    ref_text: str = Form(""),
    lang: str = Form("en"),
):
    if _model is None:
        raise HTTPException(status_code=503, detail="IndicF5 model not loaded")

    import tempfile
    import soundfile as sf
    import numpy as np

    tmp_path = None
    try:
        audio_bytes = await ref_audio.read()
        suffix = pathlib.Path(ref_audio.filename or "ref.wav").suffix or ".wav"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(audio_bytes)
        tmp_path = tmp.name
        tmp.close()

        logger.info("Synthesizing: ref=%s (%d bytes), text=%s...",
                     ref_audio.filename, len(audio_bytes), gen_text[:50])

        # Run inference
        wav, sr, _ = _model.infer(
            ref_file=tmp_path,
            ref_text=ref_text,
            gen_text=gen_text,
        )

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

        logger.info("Synthesis complete: %d samples @ %d Hz (%.1f s)",
                     len(wav), sr, len(wav) / sr)

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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    logger.info("Starting on %s:%s", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
