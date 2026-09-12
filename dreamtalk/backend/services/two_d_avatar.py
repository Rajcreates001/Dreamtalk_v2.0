"""Audio-driven 2D talking-avatar rendering.

MuseTalk is the preferred neural mouth renderer. A deterministic audio-reactive
renderer remains available for CPU-only deployments so requests still produce
an honestly-labelled, synchronized MP4 instead of a static image with audio.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import math
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

import cv2
import numpy as np

logger = logging.getLogger("dreamtalk.avatar.2d")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MUSE_ROOT = PROJECT_ROOT / "weights" / "musetalk"
MUSETALK_VALIDATION = PROJECT_ROOT / "media" / "avatar_runtime" / "validation" / "musetalk.json"


class TwoDAvatarRenderer:
    """Render speech-aligned 2D avatar videos with bounded concurrency."""

    def __init__(self) -> None:
        self._musetalk = None
        self._musetalk_error: Optional[str] = None
        self._render_lock = threading.Lock()

    def status(self) -> dict[str, Any]:
        required = {
            "unet": MUSE_ROOT / "unet.pth",
            "unet_config": MUSE_ROOT / "musetalk.json",
            "vae": MUSE_ROOT / "sd-vae" / "diffusion_pytorch_model.bin",
            "whisper": MUSE_ROOT / "whisper" / "pytorch_model.bin",
            "face_parser": PROJECT_ROOT / "weights" / "retinaface" / "79999_iter.pth",
        }
        dependencies = {
            name: importlib.util.find_spec(name) is not None
            for name in ("torch", "diffusers", "transformers", "cv2", "librosa")
        }
        weights = {name: path.exists() for name, path in required.items()}
        neural_ready = all(weights.values()) and all(dependencies.values())
        cuda = False
        try:
            import torch

            cuda = bool(torch.cuda.is_available())
        except Exception:
            pass
        allow_cpu_neural = os.environ.get("MUSETALK_ALLOW_CPU", "false").lower() == "true"
        neural_usable = neural_ready and (cuda or allow_cpu_neural)
        validation = None
        if MUSETALK_VALIDATION.exists():
            try:
                validation = json.loads(MUSETALK_VALIDATION.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        return {
            "ready": True,
            "preferred_engine": "musetalk",
            "neural_ready": neural_ready,
            "neural_usable": neural_usable,
            "neural_loaded": self._musetalk is not None,
            "neural_error": self._musetalk_error,
            "inference_validated": validation is not None,
            "last_validation": validation,
            "device": "cuda" if cuda else "cpu",
            "quality_tier": "neural_realtime" if cuda and neural_ready else "audio_reactive",
            "cpu_neural_enabled": allow_cpu_neural,
            "fallback_engine": "audio-reactive-2d",
            "weights": weights,
            "dependencies": dependencies,
        }

    @staticmethod
    def _release_host_llm_vram() -> bool:
        """Ask the host Ollama runtime to drop its model from VRAM.

        On a single-GPU box the LLM fallback (llama3.1:8b ≈ 5.3 GB) can occupy
        nearly all of an 8 GB card, which starves MuseTalk at load time. Ollama
        unloads a model when asked with ``keep_alive: 0``; it reloads on demand
        for the next reply. Returns True if we unloaded anything.
        """
        import json as _json
        import urllib.request

        base = os.environ.get("LLM_FALLBACK_BASE_URL", "http://host.docker.internal:11434/v1")
        base = base.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        try:
            with urllib.request.urlopen(f"{base}/api/ps", timeout=5) as resp:
                loaded = _json.loads(resp.read()).get("models") or []
        except Exception as exc:
            logger.debug("Could not query host LLM runtime for VRAM reclaim: %s", exc)
            return False

        released = False
        for model in loaded:
            name = model.get("model") or model.get("name")
            if not name or not model.get("size_vram"):
                continue
            try:
                payload = _json.dumps({"model": name, "keep_alive": 0}).encode()
                req = urllib.request.Request(
                    f"{base}/api/generate", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                urllib.request.urlopen(req, timeout=15).read()
                logger.info("Released host LLM '%s' (%.1f GB) to free VRAM for MuseTalk",
                            name, model["size_vram"] / 1e9)
                released = True
            except Exception as exc:
                logger.warning("Failed to unload host LLM '%s': %s", name, exc)
        return released

    def _ensure_vram_headroom(self) -> None:
        """Make room on the GPU *before* loading MuseTalk.

        Recovering from a CUDA OOM in-process is unreliable — PyTorch's caching
        allocator can be left in a state where even a freed GPU won't reload
        (INTERNAL ASSERT in CUDACachingAllocator) — so we check headroom up
        front and evict the host LLM rather than retrying after a failure.
        """
        try:
            import torch

            if not torch.cuda.is_available():
                return
            # MuseTalk's UNet+VAE+Whisper stack effectively wants the whole
            # card (measured: free drops to ~0 after load on an 8 GB GPU), so
            # the bar is high on purpose.
            need = float(os.environ.get("MUSETALK_MIN_FREE_VRAM_GB", "6.5")) * 1e9
            free, _total = torch.cuda.mem_get_info()
            if free >= need:
                return
            logger.info("Only %.1f GB VRAM free (need %.1f) — reclaiming before MuseTalk load",
                        free / 1e9, need / 1e9)
            if not self._release_host_llm_vram():
                return
            # The host driver (and WSL2's GPU paravirtualisation) can take
            # several seconds to actually hand the memory back, so poll rather
            # than guessing a fixed sleep.
            deadline = time.monotonic() + float(os.environ.get("VRAM_RECLAIM_TIMEOUT", "25"))
            while time.monotonic() < deadline:
                time.sleep(1.0)
                free, _total = torch.cuda.mem_get_info()
                if free >= need:
                    break
            logger.info("VRAM after reclaim: %.1f GB free", free / 1e9)
        except Exception as exc:
            logger.debug("VRAM headroom check skipped: %s", exc)

    def _get_musetalk(self):
        if self._musetalk is not None:
            return self._musetalk

        self._ensure_vram_headroom()
        try:
            from dreamtalk.face.core.lipsync.musetalk.musetalk_api import MuseTalkAPI

            api = MuseTalkAPI()
            api.load_models()
            self._musetalk = api
            self._musetalk_error = None
            return api
        except Exception as exc:
            if "out of memory" in str(exc).lower():
                self._musetalk_error = (
                    "CUDA out of memory — the GPU is shared with another process "
                    "(set MUSETALK_MIN_FREE_VRAM_GB or free the LLM). "
                    f"{exc}"
                )
                logger.error("MuseTalk OOM even after reclaim: %s", exc)
            else:
                self._musetalk_error = str(exc)
                logger.exception("MuseTalk initialization failed")
            self._unload_musetalk()
            return None

    def _unload_musetalk(self) -> None:
        api = self._musetalk
        self._musetalk = None
        if api is not None:
            try:
                engine = api.inference_engine
                for attribute in ("vae", "unet", "pe", "whisper", "fp", "timesteps"):
                    setattr(engine, attribute, None)
                api.inference_engine = None
            except Exception:
                pass
        try:
            import gc
            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            pass

    def render(
        self,
        source_image: str,
        audio_path: str,
        output_dir: str,
        emotion: str = "neutral",
        engine: str = "auto",
    ) -> dict[str, Any]:
        source = Path(source_image)
        audio = Path(audio_path)
        destination = Path(output_dir)
        if not source.exists():
            raise FileNotFoundError(source)
        if not audio.exists():
            raise FileNotFoundError(audio)
        destination.mkdir(parents=True, exist_ok=True)
        requested = (engine or "auto").strip().lower()
        if requested not in {"auto", "musetalk", "audio-reactive"}:
            raise ValueError("2D engine must be auto, musetalk, or audio-reactive")

        started = time.perf_counter()
        with self._render_lock:
            neural_error = None
            renderer_status = self.status()
            if requested in {"auto", "musetalk"} and renderer_status["neural_usable"]:
                api = self._get_musetalk()
                if api is not None:
                    try:
                        filename = f"avatar_2d_{uuid.uuid4().hex}.mp4"
                        result = api.generate(
                            video_path=str(source),
                            audio_path=str(audio),
                            result_dir=str(destination),
                            output_vid_name=filename,
                            batch_size=int(os.environ.get("MUSETALK_BATCH_SIZE", "4")),
                            hw_video_encode=True,
                        )
                        path = Path(result["video_path"])
                        if not path.exists() or path.stat().st_size < 1024:
                            raise RuntimeError("MuseTalk returned no usable video")
                        self._write_provenance_metadata(path)
                        rendered = self._result(
                            path, "musetalk", emotion, started,
                            neural=True, lipsync=True, fallback_reason=None,
                        )
                        self._record_validation(rendered)
                        if os.environ.get("AVATAR_GPU_UNLOAD_AFTER_RENDER", "true").lower() == "true":
                            self._unload_musetalk()
                        return rendered
                    except Exception as exc:
                        neural_error = str(exc)
                        self._musetalk_error = neural_error
                        if os.environ.get("AVATAR_GPU_UNLOAD_AFTER_RENDER", "true").lower() == "true":
                            self._unload_musetalk()
                        logger.exception("MuseTalk rendering failed; using audio-reactive renderer")
                else:
                    neural_error = self._musetalk_error or "MuseTalk failed to load"
            elif requested == "musetalk":
                neural_error = (
                    "MuseTalk CPU rendering is disabled because this model exceeds the current Docker memory headroom; "
                    "enable a container GPU or set MUSETALK_ALLOW_CPU=true with additional memory"
                    if renderer_status["neural_ready"] and renderer_status["device"] == "cpu"
                    else "MuseTalk weights or dependencies are incomplete"
                )

            if requested == "musetalk" and os.environ.get("AVATAR_2D_STRICT_NEURAL", "false").lower() == "true":
                raise RuntimeError(neural_error or "MuseTalk is unavailable")

            output = destination / f"avatar_2d_{uuid.uuid4().hex}.mp4"
            self._render_audio_reactive(source, audio, output, emotion)
            return self._result(
                output, "audio-reactive-2d", emotion, started,
                neural=False, lipsync=True, fallback_reason=neural_error,
            )

    @staticmethod
    def _record_validation(result: dict[str, Any]) -> None:
        MUSETALK_VALIDATION.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "engine": result.get("engine"),
            "frames": result.get("frames"),
            "fps": result.get("fps"),
            "duration": result.get("duration"),
            "neural": result.get("neural"),
        }
        temporary = MUSETALK_VALIDATION.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, MUSETALK_VALIDATION)

    @staticmethod
    def _audio_envelope(audio_path: Path, fps: int) -> tuple[np.ndarray, float]:
        import librosa

        signal, sample_rate = librosa.load(str(audio_path), sr=16000, mono=True)
        if signal.size == 0:
            raise ValueError("Speech audio is empty")
        duration = len(signal) / sample_rate
        frames = max(1, int(math.ceil(duration * fps)))
        envelope = np.zeros(frames, dtype=np.float32)
        for index in range(frames):
            start = int(index * sample_rate / fps)
            end = min(len(signal), int((index + 1) * sample_rate / fps))
            chunk = signal[start:end]
            envelope[index] = float(np.sqrt(np.mean(chunk * chunk) + 1e-9)) if chunk.size else 0.0
        floor = float(np.percentile(envelope, 15))
        ceiling = float(np.percentile(envelope, 95))
        envelope = np.clip((envelope - floor) / max(ceiling - floor, 1e-5), 0.0, 1.0)
        # Smooth attack/release while preserving consonant changes.
        for index in range(1, len(envelope)):
            coefficient = 0.62 if envelope[index] > envelope[index - 1] else 0.78
            envelope[index] = coefficient * envelope[index - 1] + (1.0 - coefficient) * envelope[index]
        return envelope, duration

    @staticmethod
    def _face_box(image: np.ndarray) -> tuple[int, int, int, int]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if Path(cascade_path).exists():
            cascade = cv2.CascadeClassifier(cascade_path)
            faces = [] if cascade.empty() else cascade.detectMultiScale(
                gray, scaleFactor=1.08, minNeighbors=5, minSize=(80, 80)
            )
        else:
            faces = []
        if len(faces):
            x, y, width, height = max(faces, key=lambda item: item[2] * item[3])
            return int(x), int(y), int(width), int(height)
        height, width = image.shape[:2]
        side = int(min(width, height) * 0.72)
        return (width - side) // 2, max(0, int(height * 0.08)), side, side

    @staticmethod
    def _emotion_tuning(emotion: str) -> tuple[float, float]:
        # mouth gain, head-motion gain
        return {
            "happy": (1.12, 1.15), "excited": (1.2, 1.4), "surprised": (1.25, 1.2),
            "angry": (1.08, 0.8), "frustrated": (1.05, 0.75), "sad": (0.82, 0.55),
            "fearful": (1.12, 0.9), "calm": (0.9, 0.45), "loving": (0.94, 0.55),
        }.get(emotion, (1.0, 0.65))

    def _render_audio_reactive(self, source: Path, audio: Path, output: Path, emotion: str) -> None:
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("The avatar source image cannot be decoded")
        max_side = int(os.environ.get("AVATAR_2D_MAX_SIDE", "768"))
        height, width = image.shape[:2]
        scale = min(1.0, max_side / max(height, width))
        if scale < 1.0:
            image = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        height, width = image.shape[:2]
        fps = int(os.environ.get("AVATAR_2D_FPS", "25"))
        envelope, _ = self._audio_envelope(audio, fps)
        face_x, face_y, face_w, face_h = self._face_box(image)
        mouth_x1 = max(0, int(face_x + face_w * 0.24))
        mouth_x2 = min(width, int(face_x + face_w * 0.76))
        mouth_y1 = max(0, int(face_y + face_h * 0.57))
        mouth_y2 = min(height, int(face_y + face_h * 0.86))
        mouth_gain, motion_gain = self._emotion_tuning(emotion)

        silent_path = output.with_suffix(".silent.mp4")
        writer = cv2.VideoWriter(
            str(silent_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            raise RuntimeError("OpenCV could not initialize the 2D video encoder")
        try:
            base_roi = image[mouth_y1:mouth_y2, mouth_x1:mouth_x2]
            roi_h, roi_w = base_roi.shape[:2]
            if roi_h < 8 or roi_w < 8:
                raise ValueError("Detected face is too small for lip animation")
            feather = np.zeros((roi_h, roi_w), dtype=np.float32)
            cv2.ellipse(
                feather, (roi_w // 2, roi_h // 2),
                (max(1, int(roi_w * 0.47)), max(1, int(roi_h * 0.45))),
                0, 0, 360, 1.0, -1,
            )
            feather = cv2.GaussianBlur(feather, (0, 0), sigmaX=max(2.0, roi_w * 0.035))[:, :, None]
            for index, energy in enumerate(envelope):
                openness = float(np.clip(energy * mouth_gain, 0.0, 1.0))
                stretch = 1.0 + 0.20 * openness
                stretched = cv2.resize(base_roi, (roi_w, max(1, int(roi_h * stretch))), interpolation=cv2.INTER_CUBIC)
                offset = max(0, (stretched.shape[0] - roi_h) // 2)
                animated = stretched[offset:offset + roi_h]
                if animated.shape[0] != roi_h:
                    animated = cv2.resize(animated, (roi_w, roi_h), interpolation=cv2.INTER_CUBIC)
                frame = image.copy()
                target = frame[mouth_y1:mouth_y2, mouth_x1:mouth_x2]
                target[:] = (animated * feather + target * (1.0 - feather)).astype(np.uint8)
                # Natural micro-motion keeps a still portrait from appearing frozen.
                phase = index / fps
                dx = int(round(math.sin(phase * 1.7) * 1.5 * motion_gain))
                dy = int(round(math.sin(phase * 2.1) * 1.0 * motion_gain))
                matrix = np.float32([[1, 0, dx], [0, 1, dy]])
                frame = cv2.warpAffine(frame, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)
                writer.write(frame)
        finally:
            writer.release()

        command = [
            "ffmpeg", "-y", "-v", "error", "-i", str(silent_path), "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            "-metadata", "title=DreamTalk AI Avatar",
            "-metadata", "comment=AI-generated synthetic talking-avatar media",
            "-metadata", "artist=DreamTalk", str(output),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=300)
        silent_path.unlink(missing_ok=True)
        if completed.returncode != 0 or not output.exists():
            raise RuntimeError(f"ffmpeg could not finalize avatar video: {completed.stderr[-400:]}")

    @staticmethod
    def _write_provenance_metadata(path: Path) -> None:
        """Embed a durable synthetic-media disclosure in the MP4 container."""
        stamped = path.with_suffix(".provenance.mp4")
        command = [
            "ffmpeg", "-y", "-v", "error", "-i", str(path), "-map", "0", "-c", "copy",
            "-metadata", "title=DreamTalk AI Avatar",
            "-metadata", "comment=AI-generated synthetic talking-avatar media",
            "-metadata", "artist=DreamTalk",
            str(stamped),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if completed.returncode == 0 and stamped.exists() and stamped.stat().st_size > 1024:
            os.replace(stamped, path)
        else:
            stamped.unlink(missing_ok=True)

    @staticmethod
    def _result(
        path: Path,
        engine: str,
        emotion: str,
        started: float,
        neural: bool,
        lipsync: bool,
        fallback_reason: Optional[str],
    ) -> dict[str, Any]:
        capture = cv2.VideoCapture(str(path))
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) if capture.isOpened() else 0
        fps = float(capture.get(cv2.CAP_PROP_FPS)) if capture.isOpened() else 0.0
        if capture.isOpened():
            capture.release()
        duration = frames / fps if frames and fps else 0.0
        return {
            "status": "completed",
            "path": str(path),
            "engine": engine,
            "neural": neural,
            "lip_sync": lipsync,
            "emotion": emotion,
            "duration": round(duration, 3),
            "fps": round(fps, 3),
            "frames": frames,
            "processing_ms": round((time.perf_counter() - started) * 1000, 2),
            "fallback_reason": fallback_reason,
            "provenance": {
                "synthetic_media": True,
                "generator": "DreamTalk",
                "disclosure": "AI-generated synthetic talking-avatar media",
            },
        }


_default_renderer: Optional[TwoDAvatarRenderer] = None


def get_two_d_avatar_renderer() -> TwoDAvatarRenderer:
    global _default_renderer
    if _default_renderer is None:
        _default_renderer = TwoDAvatarRenderer()
    return _default_renderer
