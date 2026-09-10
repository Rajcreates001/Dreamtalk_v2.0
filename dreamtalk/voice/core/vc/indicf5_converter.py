"""
IndicF5 Voice Cloning Converter — Triple-Mode Client.

Uses the IndicF5 CFM-based model (1.34 GB already downloaded) for voice cloning.
Takes a reference audio + transcript, then synthesizes speech in the same voice.

Modes (tried in order, fallback chain):
  1. HTTP client     -> calls the Docker IndicF5 microservice (no DLL conflicts)
  2. Venv subprocess -> runs isolated Python venv on D: drive (no DLL conflicts)
  3. Direct import   -> falls back to local Python import (DLL conflicts possible)

The modes are designed to avoid the Windows OMP DLL conflict
(libomp.dll vs libiomp5md.dll) by isolating IndicF5's torch from the
main application's torch.
"""

import io
import json
import logging
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Optional

logger = logging.getLogger("dreamtalk.voice.vc.indicf5")

# ── Configuration (overridable via env vars) ────────────────────────
INDICF5_MICROSERVICE_URL = os.environ.get(
    "INDICF5_MICROSERVICE_URL", "http://localhost:8003"
)
INDICF5_TIMEOUT = int(os.environ.get("INDICF5_TIMEOUT", "180"))  # seconds
INDICF5_VENV_DIR = os.environ.get(
    "INDICF5_VENV_DIR", "D:\\venvs\\indicf5"
)

# ── Project root & weight path detection ──────────────────────────
# voice/core/vc/indicf5_converter.py -> 4 levels up to dreamtalk/
_IF5_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
_IF5_WEIGHTS_DIR = _IF5_ROOT / "weights" / "voice" / "indic_tts" / "IndicF5"
_IF5_MODEL_PATH = str(_IF5_WEIGHTS_DIR / "model.safetensors")
_IF5_VOCAB_PATH = str(_IF5_WEIGHTS_DIR / "checkpoints" / "vocab.txt")
_IF5_CONFIG_PATH = str(_IF5_WEIGHTS_DIR / "config.json")


def check_indicf5_available() -> dict:
    """Check which IndicF5 assets are present locally."""
    return {
        "model.safetensors": os.path.exists(_IF5_MODEL_PATH),
        "vocab.txt": os.path.exists(_IF5_VOCAB_PATH),
        "config.json": os.path.exists(_IF5_CONFIG_PATH),
    }


# ─── Microservice helpers ───────────────────────────────────────────


def _check_microservice_health() -> bool:
    """Check if the Docker microservice is running and healthy."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{INDICF5_MICROSERVICE_URL}/health")
        resp = urllib.request.urlopen(req, timeout=3)
        if resp.status == 200:
            data = json.loads(resp.read())
            ok = data.get("status") == "ok"
            logger.info(
                "IndicF5 microservice available (model_loaded=%s, device=%s)",
                data.get("model_loaded"), data.get("device"),
            )
            return ok
        return False
    except Exception as e:
        logger.debug("IndicF5 microservice health check failed: %s", e)
        return False


def _synthesize_via_http(ref_audio_path, ref_text, gen_text, lang="en"):
    """Call the Docker microservice's /synthesize endpoint via multipart POST.

    Returns (wav_array, sample_rate) or (None, 0) on failure.
    """
    try:
        import urllib.request
        import numpy as np
        import soundfile as sf

        boundary = "----IndicF5FormBoundary"
        crlf = b"\r\n"

        with open(ref_audio_path, "rb") as f:
            audio_data = f.read()

        parts = []
        # ref_audio file
        parts.append(f"--{boundary}{crlf}".encode())
        parts.append(
            f'Content-Disposition: form-data; name="ref_audio"; '
            f'filename="{os.path.basename(ref_audio_path)}"{crlf}'.encode()
        )
        parts.append(b"Content-Type: audio/wav" + crlf + crlf)
        parts.append(audio_data + crlf)

        # gen_text
        parts.append(f"--{boundary}{crlf}".encode())
        parts.append(f'Content-Disposition: form-data; name="gen_text"{crlf}{crlf}'.encode())
        parts.append(gen_text.encode("utf-8") + crlf)

        # ref_text
        parts.append(f"--{boundary}{crlf}".encode())
        parts.append(f'Content-Disposition: form-data; name="ref_text"{crlf}{crlf}'.encode())
        parts.append(ref_text.encode("utf-8") + crlf)

        # lang
        parts.append(f"--{boundary}{crlf}".encode())
        parts.append(f'Content-Disposition: form-data; name="lang"{crlf}{crlf}'.encode())
        parts.append(lang.encode("utf-8") + crlf)

        parts.append(f"--{boundary}--{crlf}".encode())

        body = b"".join(parts)

        req = urllib.request.Request(
            f"{INDICF5_MICROSERVICE_URL}/synthesize",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=INDICF5_TIMEOUT)
        wav_bytes = resp.read()

        if len(wav_bytes) < 100:
            logger.warning("Microservice returned too little data: %d bytes", len(wav_bytes))
            return None, 0

        wav_data, sr = sf.read(io.BytesIO(wav_bytes))
        logger.info(
            "HTTP synthesis: %d samples @ %d Hz (%.1f s)",
            len(wav_data), sr, len(wav_data) / sr,
        )
        return wav_data, sr

    except Exception as e:
        logger.warning("HTTP synthesis failed: %s", e)
        return None, 0


# ─── Venv subprocess helpers ────────────────────────────────────────


def _check_venv_available() -> bool:
    """Check if the dedicated venv exists and has torch installed."""
    venv_python = os.path.join(INDICF5_VENV_DIR, "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        logger.debug("IndicF5 venv not found at %s", INDICF5_VENV_DIR)
        return False
    try:
        result = subprocess.run(
            [venv_python, "-c", "import torch; print(torch.__version__)"],
            capture_output=True, text=True, timeout=15,
        )
        ok = result.returncode == 0 and "torch" in result.stdout
        if ok:
            logger.info("IndicF5 venv available at %s (torch %s)",
                        INDICF5_VENV_DIR, result.stdout.strip())
        else:
            logger.debug("IndicF5 venv torch import failed: %s", result.stderr[:200])
        return ok
    except Exception as e:
        logger.debug("IndicF5 venv check failed: %s", e)
        return False


def _synthesize_via_venv(ref_audio_path, ref_text, gen_text, lang="en"):
    """Synthesize via the dedicated venv subprocess.

    Writes a temp script that the venv Python runs, outputting WAV bytes
    to stdout. Avoids DLL conflicts by running in a clean subprocess.

    Returns (wav_array, sample_rate) or (None, 0) on failure.
    """
    venv_python = os.path.join(INDICF5_VENV_DIR, "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        logger.warning("Venv python not found at %s", venv_python)
        return None, 0

    # Build a standalone script that will be run in the venv.
    # Writes output WAV to a temp file and prints the path => no binary-on-stdout fragility.
    project_root = str(_IF5_ROOT).replace("\\", "/")
    ref_path = ref_audio_path.replace("\\", "/")

    script = f'''import io, json, os, sys, tempfile
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, "{project_root}")

try:
    from dreamtalk.voice.core.tts.indicf5_engine import IndicF5TTSEngine
    engine = IndicF5TTSEngine(device="cpu")
    if not engine.is_loaded:
        print("RESULT:not_ready")
        sys.exit(0)
    import soundfile as sf
    import numpy as np
    wav, sr = engine.synthesize(
        text={json.dumps(gen_text)},
        ref_audio_path="{ref_path}",
        ref_text={json.dumps(ref_text)},
        lang={json.dumps(lang)},
    )
    if wav is None or len(wav) == 0:
        print("RESULT:no_audio")
        sys.exit(0)
    wav = np.asarray(wav, dtype=np.float32)
    peak = np.max(np.abs(wav))
    if peak > 0:
        wav = wav / peak * 0.95
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, wav, sr)
    tmp.close()
    print(f"RESULT:ok {{tmp.name}}")
except Exception as e:
    print(f"RESULT:error {{type(e).__name__}}: {{e}}")
    sys.exit(1)
'''

    try:
        result = subprocess.run(
            [venv_python, "-c", script],
            capture_output=True, text=True, timeout=INDICF5_TIMEOUT,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("RESULT:"):
                payload = line[7:]
                if payload.startswith("ok "):
                    wav_path = payload[3:].strip()
                    if os.path.exists(wav_path):
                        import soundfile as sf
                        wav_data, sr = sf.read(wav_path)
                        try:
                            os.unlink(wav_path)
                        except Exception:
                            pass
                        logger.info(
                            "Venv synthesis: %d samples @ %d Hz (%.1f s)",
                            len(wav_data), sr, len(wav_data) / sr,
                        )
                        return wav_data, sr
                    else:
                        logger.warning("Venv WAV temp file not found: %s", wav_path)
                elif "error" in payload:
                    logger.warning("Venv synthesis error: %s", payload)
                elif "not_ready" in payload:
                    logger.warning("Venv IndicF5 engine not ready")
                elif "no_audio" in payload:
                    logger.warning("Venv IndicF5 produced no audio")
                break
        else:
            logger.warning("Venv had no RESULT line. Stdout: %s | Stderr: %s",
                           stdout[:300] if stdout else "(empty)",
                           stderr[:300] if stderr else "(empty)")

    except subprocess.TimeoutExpired:
        logger.warning("Venv synthesis timed out after %ss", INDICF5_TIMEOUT)
    except Exception as e:
        logger.warning("Venv synthesis failed: %s", e)

    return None, 0


# ─── Main Converter Class ────────────────────────────────────────────


class IndicF5Converter:
    """IndicF5-based voice cloning converter with triple-mode fallback.

    Mode priority:
      1. Docker microservice (HTTP) — no DLL conflicts
      2. Dedicated venv (subprocess) — no DLL conflicts
      3. Direct import — DLL conflicts possible, last resort
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        self._engine = None
        self._loaded = False
        self._mode = "none"  # "microservice", "venv", "direct"

        # Try microservice first (Linux container, no DLL conflicts)
        if _check_microservice_health():
            self._loaded = True
            self._mode = "microservice"
            logger.info("IndicF5Converter mode: Docker microservice at %s",
                        INDICF5_MICROSERVICE_URL)
        # Try venv subprocess next (isolated Python process)
        elif _check_venv_available():
            self._loaded = True
            self._mode = "venv"
            logger.info("IndicF5Converter mode: venv subprocess at %s",
                        INDICF5_VENV_DIR)
        # Last resort: direct import (DLL conflicts possible)
        else:
            self._load_direct()

    def _load_direct(self):
        """Load directly in-process (DLL conflicts possible on Windows)."""
        try:
            from dreamtalk.voice.core.tts.indicf5_engine import IndicF5TTSEngine
            self._engine = IndicF5TTSEngine(device=self.device)
            self._loaded = self._engine.is_loaded
            self._mode = "direct"
            if self._loaded:
                logger.info("IndicF5Converter mode: direct import")
            else:
                logger.warning("IndicF5 engine loaded but not ready")
        except ImportError as e:
            logger.warning("IndicF5 engine import failed: %s", e)
            self._loaded = False
        except Exception as e:
            logger.warning("IndicF5 engine init failed: %s", e)
            self._loaded = False

    def clone_and_synthesize(
        self,
        ref_audio_path: str,
        ref_text: str,
        gen_text: str,
        output_path: str,
        lang: str = "en",
    ) -> Optional[str]:
        """Clone voice from ref_audio and synthesize gen_text.

        Args:
            ref_audio_path: Path to the reference audio (speaker to clone)
            ref_text: Transcript of the reference audio
            gen_text: Text to synthesize in the cloned voice
            output_path: Where to save the output WAV
            lang: Language code (en, hi, ta, etc.)

        Returns:
            Path to output WAV, or None on failure
        """
        if not self._loaded:
            logger.warning("IndicF5 not loaded")
            return None

        if not os.path.exists(ref_audio_path):
            logger.warning("Reference audio not found: %s", ref_audio_path)
            return None

        try:
            if self._mode == "microservice":
                wav, sr = _synthesize_via_http(
                    ref_audio_path=ref_audio_path,
                    ref_text=ref_text,
                    gen_text=gen_text,
                    lang=lang,
                )
            elif self._mode == "venv":
                wav, sr = _synthesize_via_venv(
                    ref_audio_path=ref_audio_path,
                    ref_text=ref_text,
                    gen_text=gen_text,
                    lang=lang,
                )
            else:
                if self._engine is None:
                    return None
                wav, sr = self._engine.synthesize(
                    text=gen_text,
                    ref_audio_path=ref_audio_path,
                    ref_text=ref_text,
                    lang=lang,
                )

            if wav is None or len(wav) == 0:
                return None

            import soundfile as sf
            sf.write(output_path, wav, sr)
            logger.info("IndicF5 clone complete: %s (mode=%s)", output_path, self._mode)
            return output_path

        except Exception as e:
            logger.error("IndicF5 synthesis failed: %s", e)
            return None

    def clone_voice(self, audio_path: str, transcript: Optional[str] = None) -> dict:
        """Prepare clone config for later synthesis."""
        if self._mode in ("microservice", "venv"):
            return {
                "ref_audio": audio_path,
                "ref_text": transcript or "",
                "mode": self._mode,
            }
        if self._engine:
            return self._engine.clone_voice(audio_path, transcript)
        return {"ref_audio": audio_path, "ref_text": transcript or ""}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def supported_languages(self) -> dict:
        if self._mode == "microservice":
            # The full list
            pass
        if self._mode in ("microservice", "venv"):
            return {
                "as": "Assamese", "bn": "Bengali", "gu": "Gujarati",
                "hi": "Hindi", "kn": "Kannada", "ml": "Malayalam",
                "mr": "Marathi", "or": "Odia", "pa": "Punjabi",
                "ta": "Tamil", "te": "Telugu", "en": "English",
            }
        if self._engine:
            return self._engine.SUPPORTED_LANGUAGES
        return {"en": "English"}
