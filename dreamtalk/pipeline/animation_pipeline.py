"""LivePortrait Animation Pipeline — expression-driven facial animation for DreamTalk.

Wraps LivePortrait's face animation engine into a pipeline-compatible interface
that can be driven by:
  - A driving video (expression transfer from another face)
  - TTS-generated audio with emotion parameters
  - Real-time blendshape/expression coefficients from the brain pipeline

The pipeline outputs animated face video with optional paste-back onto the
original source image.
"""

import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import cv2
import numpy as np

logger = logging.getLogger("dreamtalk.pipeline.animation")

# ── Venv path for DLL isolation (avoids fbgemm.dll / OMP conflict) ───
LIVEPORTRAIT_VENV_PYTHON = os.environ.get(
    "LIVEPORTRAIT_VENV_PYTHON",
    "D:/venvs/liveportrait/Scripts/python.exe",
)
LIVEPORTRAIT_VENV_FALLBACK = os.environ.get(
    "LIVEPORTRAIT_VENV_FALLBACK",
    "D:/venvs/indicf5/Scripts/python.exe",
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Lazy LivePortrait imports (heavy torch deps) ──────────────────────
_live_portrait_api = None
_live_portrait_pipeline = None
_LP_VENV_MODE = False  # True when using venv subprocess instead of direct import


def _find_venv_python() -> Optional[str]:
    """Find a usable venv Python for LivePortrait isolation."""
    candidates = [
        LIVEPORTRAIT_VENV_PYTHON,
        LIVEPORTRAIT_VENV_FALLBACK,
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _run_via_venv(source_path: str, driving_path: str, output_path: str,
                   mode: str = "video", region: str = "all",
                   pasteback: bool = True) -> Dict[str, Any]:
    """Run LivePortrait in an isolated venv subprocess to avoid DLL conflicts."""
    venv_python = _find_venv_python()
    if not venv_python:
        return {"video_path": None, "status": "failed: no venv found", "frame_count": 0, "fps": 0}

    runner_script = str(PROJECT_ROOT / "face" / "core" / "animation" / "liveportrait" / "liveportrait_venv_runner.py")

    if not os.path.exists(runner_script):
        return {"video_path": None, "status": f"failed: runner not found at {runner_script}", "frame_count": 0, "fps": 0}

    cmd = [
        venv_python, runner_script,
        "--source", source_path,
        "--driving", driving_path,
        "--output", output_path,
        "--mode", mode,
        "--region", region,
    ]
    if not pasteback:
        cmd.append("--no-pasteback")

    logger.info(f"Spawning LivePortrait venv subprocess: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout for video generation
            cwd=str(PROJECT_ROOT),
        )

        # Parse the last line of stdout for RESULT:ok or RESULT:error
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0:
            logger.error(f"Venv runner failed (exit={result.returncode}): {stderr[-500:]}")
            return {
                "video_path": None,
                "status": f"venv_failed: {stderr[-200:].strip()}",
                "frame_count": 0, "fps": 0,
                "stderr": stderr[-500:],
            }

        # Find RESULT: line
        for line in stdout.strip().split("\n"):
            if line.startswith("RESULT:ok "):
                out_path = line[10:].strip()
                if os.path.exists(out_path):
                    # Read video info
                    cap = cv2.VideoCapture(out_path)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else 0
                    fps = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 25
                    if cap.isOpened():
                        cap.release()
                    return {
                        "video_path": out_path,
                        "frame_count": frame_count,
                        "fps": fps,
                        "duration_seconds": frame_count / max(fps, 1),
                        "status": "completed",
                        "method": "venv",
                    }

            if line.startswith("RESULT:error "):
                err_msg = line[13:].strip()
                return {"video_path": None, "status": f"venv_error: {err_msg}", "frame_count": 0, "fps": 0}

        # Fallback: check if output was written anyway
        if os.path.exists(output_path):
            cap = cv2.VideoCapture(output_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else 0
            fps = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 25
            if cap.isOpened():
                cap.release()
            return {
                "video_path": output_path,
                "frame_count": frame_count,
                "fps": fps,
                "duration_seconds": frame_count / max(fps, 1),
                "status": "completed",
                "method": "venv",
            }

        return {
            "video_path": None,
            "status": "venv_no_output",
            "frame_count": 0, "fps": 0,
            "stdout": stdout[-500:],
            "stderr": stderr[-500:],
        }

    except subprocess.TimeoutExpired:
        logger.error("LivePortrait venv subprocess timed out after 300s")
        return {"video_path": None, "status": "timeout", "frame_count": 0, "fps": 0}
    except Exception as e:
        logger.error(f"LivePortrait venv subprocess error: {e}")
        return {"video_path": None, "status": f"venv_exception: {e}", "frame_count": 0, "fps": 0}


def _can_import_direct() -> bool:
    """Check if LivePortrait can be imported directly (no DLL conflict).

    Returns False on Windows when fbgemm.dll or OMP conflict prevents loading.
    """
    try:
        from dreamtalk.face.core.animation.liveportrait import LivePortraitAPI
        return True
    except (ImportError, OSError) as e:
        err_str = str(e).lower()
        # Known DLL conflict patterns
        if any(tok in err_str for tok in ["dll", "fbgemm", "libomp", "libiomp", "omp", "specified procedure"]):
            logger.warning(f"Direct LivePortrait import blocked by DLL conflict: {e}")
            return False
        logger.warning(f"LivePortrait import unavailable: {e}")
        return False
    except Exception:
        return False


def _get_live_portrait_api():
    global _live_portrait_api, _LP_VENV_MODE
    if not _can_import_direct():
        _LP_VENV_MODE = True
        logger.info("LivePortrait will use venv subprocess isolation")
        return None
    if _live_portrait_api is None:
        try:
            from dreamtalk.face.core.animation.liveportrait import LivePortraitAPI, InferenceConfig, CropConfig
            import torch
            import os as _os
            inf_cfg = InferenceConfig()
            inf_cfg.flag_use_half_precision = False
            inf_cfg.flag_do_crop = True
            inf_cfg.flag_pasteback = True
            inf_cfg.flag_stitching = True
            inf_cfg.flag_relative_motion = True
            inf_cfg.animation_region = "all"
            # Check env override: LIVEPORTRAIT_DEVICE=cpu|cuda
            env_device = _os.environ.get("LIVEPORTRAIT_DEVICE", "auto").lower()
            if env_device == "cpu":
                logger.info("LIVEPORTRAIT_DEVICE=cpu — forcing LivePortrait to CPU")
                inf_cfg.flag_force_cpu = True
            elif env_device == "auto" and torch.cuda.is_available():
                free_mem, total_mem = torch.cuda.mem_get_info(0)
                free_gb = free_mem / (1024**3)
                logger.info(f"GPU free memory: {free_gb:.1f}GB / {total_mem/(1024**3):.1f}GB")
                if free_gb < 2.0:
                    logger.warning(f"Only {free_gb:.1f}GB GPU free — forcing LivePortrait to CPU")
                    inf_cfg.flag_force_cpu = True
            elif not torch.cuda.is_available():
                logger.info("No CUDA available — using CPU for LivePortrait")
                inf_cfg.flag_force_cpu = True
            crop_cfg = CropConfig()
            _live_portrait_api = LivePortraitAPI(inference_cfg=inf_cfg, crop_cfg=crop_cfg)
            device_str = "cpu" if getattr(inf_cfg, 'flag_force_cpu', False) else "cuda"
            logger.info(f"LivePortraitAPI loaded successfully (device={device_str})")
        except Exception as e:
            logger.error(f"LivePortraitAPI load failed: {e}")
            _LP_VENV_MODE = True
            logger.info("Falling back to venv subprocess isolation")
            return None
    return _live_portrait_api


def _get_live_portrait_pipeline():
    global _live_portrait_pipeline, _LP_VENV_MODE
    if _LP_VENV_MODE:
        return None
    if _live_portrait_pipeline is None:
        try:
            import torch
            from dreamtalk.face.core.animation.liveportrait import LivePortraitPipeline, InferenceConfig, CropConfig
            inf_cfg = InferenceConfig()
            inf_cfg.flag_use_half_precision = False
            if torch.cuda.is_available():
                free_mem, _ = torch.cuda.mem_get_info(0)
                if free_mem / (1024**3) < 2.0:
                    logger.warning("Insufficient GPU memory for LivePortraitPipeline — forcing CPU")
                    inf_cfg.flag_force_cpu = True
            else:
                inf_cfg.flag_force_cpu = True
            crop_cfg = CropConfig()
            _live_portrait_pipeline = LivePortraitPipeline(inference_cfg=inf_cfg, crop_cfg=crop_cfg)
            logger.info("LivePortraitPipeline loaded successfully (direct import)")
        except Exception as e:
            logger.error(f"LivePortraitPipeline load failed: {e}")
            _LP_VENV_MODE = True
            return None
    return _live_portrait_pipeline


class LivePortraitAnimationPipeline:
    """High-level wrapper for LivePortrait-driven facial animation.

    Auto-detects the best execution mode:
      1. Direct import — if torch imports cleanly (Linux/macOS)
      2. Venv subprocess — on Windows when fbgemm.dll / OMP conflict detected

    Pipelines modes:
      1. drive_from_video(source_img, driving_video) — Transfer expression from a driving video
      2. drive_from_parameters(source_img, expression_params, num_frames) — Synthetic expression drive
      3. drive_from_audio(source_img, audio_path) — Expression estimated from audio (if available)

    Returns: dict with 'video_path', 'frame_count', 'fps', 'status', 'method'
    """

    def __init__(self, device: str = "auto"):
        self.device = device
        self._api = None
        self._pipeline = None

    @property
    def is_available(self) -> bool:
        if _can_import_direct():
            return True
        return _find_venv_python() is not None

    @property
    def execution_method(self) -> str:
        """Return 'direct' if LivePortrait can import in-process, 'venv' otherwise."""
        if _can_import_direct():
            return "direct"
        if _find_venv_python():
            return "venv"
        return "unavailable"

    def _lazy_load(self):
        if _LP_VENV_MODE:
            return  # No in-process loading needed
        if self._pipeline is None:
            self._pipeline = _get_live_portrait_pipeline()
        # Only load API separately if pipeline unavailable
        if self._api is None and self._pipeline is None:
            self._api = _get_live_portrait_api()

    # ─── Mode 1: Drive from a driving video ───────────────────────────────

    def drive_from_video(
        self,
        source_image_path: str,
        driving_video_path: str,
        output_dir: str = None,
        output_name: str = None,
        animation_region: str = "all",
        do_pasteback: bool = True,
    ) -> Dict[str, Any]:
        """Animate source face using expressions from a driving video.

        Auto-detects execution mode:
          - Direct import if torch loads cleanly (Linux/macOS)
          - Venv subprocess if DLL conflict detected (Windows)

        Args:
            source_image_path: Path to the source face image.
            driving_video_path: Path to the driving video (expression source).
            output_dir: Directory for output files.
            output_name: Output filename (without extension).
            animation_region: "all", "exp", "pose", "lip", or "eyes".
            do_pasteback: Whether to paste the animated face back onto the source.

        Returns:
            Dict with keys: video_path, frame_count, fps, status, method
        """
        self._lazy_load()

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="liveportrait_")
        os.makedirs(output_dir, exist_ok=True)

        out_name = output_name or f"animation_{uuid.uuid4().hex[:8]}"
        final_path = os.path.join(output_dir, f"{out_name}.mp4")

        # ── Venv mode: run in isolated subprocess ──────────────────────────
        if _LP_VENV_MODE or self._pipeline is None:
            return _run_via_venv(
                source_path=source_image_path,
                driving_path=driving_video_path,
                output_path=final_path,
                mode="video",
                region=animation_region,
                pasteback=do_pasteback,
            )

        # ── Direct import mode ────────────────────────────────────────────
        from dreamtalk.face.core.animation.liveportrait import ArgumentConfig

        args = ArgumentConfig(
            source=source_image_path,
            driving=driving_video_path,
            output_dir=output_dir,
            flag_pasteback=do_pasteback,
            flag_do_crop=True,
            flag_stitching=True,
            flag_relative_motion=True,
            animation_region=animation_region,
            flag_normalize_lip=True,
        )

        try:
            wfp, wfp_concat = self._pipeline.execute(args)

            frame_count = 0
            fps = 25
            if wfp and os.path.exists(wfp):
                cap = cv2.VideoCapture(wfp)
                if cap.isOpened():
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    cap.release()

            if wfp and os.path.exists(wfp) and wfp != final_path:
                import shutil
                shutil.copy2(wfp, final_path)

            return {
                "video_path": final_path if os.path.exists(final_path) else wfp,
                "concat_video_path": wfp_concat,
                "frame_count": frame_count,
                "fps": fps,
                "duration_seconds": frame_count / max(fps, 1),
                "status": "completed",
                "output_dir": output_dir,
                "method": "direct",
            }

        except Exception as e:
            logger.error(f"LivePortrait drive_from_video (direct) failed: {e}. Trying venv...")
            return _run_via_venv(
                source_path=source_image_path,
                driving_path=driving_video_path,
                output_path=final_path,
                mode="video",
                region=animation_region,
                pasteback=do_pasteback,
            )

    # ─── Mode 2: Drive from a single driving image (static expression) ─────

    def drive_from_image(
        self,
        source_image_path: str,
        driving_image_path: str,
        output_dir: str = None,
        output_name: str = None,
        num_frames: int = 60,
        do_pasteback: bool = True,
    ) -> Dict[str, Any]:
        """Transfer expression from a single driving image to the source.

        Produces a short video loop with the transferred expression.

        Note: `num_frames` is accepted for API compatibility but is currently
        unused — the LivePortrait pipeline determines frame count from the
        driving input.

        Args:
            source_image_path: Path to the source face image.
            driving_image_path: Path to the driving face image (expression source).
            output_dir: Directory for output files.
            output_name: Output filename.
            num_frames: Unused (frame count determined by driving input).
            do_pasteback: Whether to paste back onto source.

        Returns:
            Dict with keys: video_path, output_dir, status, method
        """
        self._lazy_load()

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="liveportrait_")
        os.makedirs(output_dir, exist_ok=True)

        out_name = output_name or f"animation_{uuid.uuid4().hex[:8]}"
        final_path = os.path.join(output_dir, f"{out_name}.mp4")

        # ── Venv mode: run in isolated subprocess ──────────────────────────
        if _LP_VENV_MODE or self._pipeline is None:
            return _run_via_venv(
                source_path=source_image_path,
                driving_path=driving_image_path,
                output_path=final_path,
                mode="image",
                region="all",
                pasteback=do_pasteback,
            )

        # ── Direct import mode ────────────────────────────────────────────
        from dreamtalk.face.core.animation.liveportrait import ArgumentConfig

        args = ArgumentConfig(
            source=source_image_path,
            driving=driving_image_path,
            output_dir=output_dir,
            flag_pasteback=do_pasteback,
            flag_do_crop=True,
            flag_stitching=True,
            flag_relative_motion=True,
        )

        try:
            wfp, wfp_concat = self._pipeline.execute(args)

            if wfp and os.path.exists(wfp) and wfp != final_path:
                import shutil
                shutil.copy2(wfp, final_path)

            return {
                "video_path": final_path if os.path.exists(final_path) else wfp,
                "concat_video_path": wfp_concat,
                "status": "completed",
                "output_dir": output_dir,
                "method": "direct",
            }

        except Exception as e:
            logger.error(f"LivePortrait drive_from_image (direct) failed: {e}. Trying venv...")
            return _run_via_venv(
                source_path=source_image_path,
                driving_path=driving_image_path,
                output_path=final_path,
                mode="image",
                region="all",
                pasteback=do_pasteback,
            )

    # ─── Mode 3: Drive from emotion parameters / blendshapes ───────────────
    # Uses pre-built motion template .pkl files from weights/liveportrait/templates/
    # to drive the source face with the target expression. Templates were generated
    # by scripts/generate_emotion_templates.py and contain synthetic expression
    # coefficient sequences for each supported emotion.

    TEMPLATES_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "weights", "liveportrait", "templates",
    )

    def _get_emotion_template_path(self, emotion_label: str) -> Optional[str]:
        """Get the path to an emotion template .pkl file if it exists.

        Fallback chain: emotion-specific → neutral → None
        """
        for candidate in [emotion_label, "neutral"]:
            template_path = os.path.join(self.TEMPLATES_DIR, f"{candidate}.pkl")
            if os.path.exists(template_path):
                return template_path
        return None

    def list_available_templates(self) -> List[str]:
        """List available emotion template files."""
        if not os.path.isdir(self.TEMPLATES_DIR):
            return []
        templates = []
        for f in sorted(os.listdir(self.TEMPLATES_DIR)):
            if f.endswith(".pkl"):
                name = f[:-4]
                size_kb = os.path.getsize(os.path.join(self.TEMPLATES_DIR, f)) / 1024
                templates.append(f"{name} ({size_kb:.0f} KB)")
        return templates

    def drive_from_emotion(
        self,
        source_image_path: str,
        output_dir: str = None,
        output_name: str = None,
        emotion_label: str = "neutral",
        num_frames: int = 75,
        do_pasteback: bool = True,
    ) -> Dict[str, Any]:
        """Animate the source face with a given emotion label.

        Uses pre-built motion template .pkl files stored in
        weights/liveportrait/templates/<emotion>.pkl to drive the source
        face with the target expression. Each template encodes a looping
        sequence of expression coefficients for that emotion.

        If a template is not found for the given emotion, falls back to
        the neutral template, or finally to a self-loop (no animation).

        Args:
            source_image_path: Path to the source face image.
            output_dir: Output directory.
            output_name: Output filename.
            emotion_label: Target emotion (neutral, happy, sad, angry,
                          surprised, fearful, disgusted).
            num_frames: Unused (frame count determined by template).
            do_pasteback: Whether to paste back onto source.

        Returns:
            Dict with keys: video_path, emotion_label, method, status
        """
        self._lazy_load()

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="liveportrait_")
        os.makedirs(output_dir, exist_ok=True)

        out_name = output_name or f"emotion_{emotion_label}_{uuid.uuid4().hex[:8]}"

        # Look for emotion template
        template_path = self._get_emotion_template_path(emotion_label)

        if template_path is not None:
            # Use the motion template to drive expression
            actual_label = os.path.basename(template_path)[:-4]
            logger.info(f"Driving with emotion template: {actual_label} (path={template_path})")

            # The pipeline's execute() method detects .pkl files via
            # is_template() and loads them directly. We can reuse
            # drive_from_video() with the .pkl as the "driving" input
            # since the venv runner and direct pipeline both support it.
            result = self.drive_from_video(
                source_image_path=source_image_path,
                driving_video_path=template_path,
                output_dir=output_dir,
                output_name=out_name,
                animation_region="all",
                do_pasteback=do_pasteback,
            )

            result["emotion_label"] = emotion_label
            result["template_used"] = actual_label
            result["method"] = "emotion_template"
            return result

        # Fallback: no template available — self-drive
        logger.warning(f"No emotion template found for '{emotion_label}', "
                       f"using self-drive. Templates dir: {self.TEMPLATES_DIR}")
        result = self.drive_from_image(
            source_image_path=source_image_path,
            driving_image_path=source_image_path,
            output_dir=output_dir,
            output_name=out_name,
            num_frames=num_frames,
            do_pasteback=do_pasteback,
        )

        result["emotion_label"] = emotion_label
        result["method"] = "self_drive"
        return result

    # ─── Utility: Check model availability ────────────────────────────────

    @staticmethod
    def check_weights() -> Dict[str, bool]:
        """Check which LivePortrait weight files are present."""
        import os
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        weight_dir = root / "weights" / "liveportrait"

        required = [
            "appearance_feature_extractor.pth",
            "motion_extractor.pth",
            "spade_generator.pth",
            "warping_module.pth",
            "landmark.onnx",
        ]

        status = {}
        for fname in required:
            status[fname] = (weight_dir / fname).exists()

        weight_values = [v for k, v in status.items() if k in required]
        status["all_present"] = all(weight_values)
        status["count"] = sum(1 for v in weight_values if v)
        status["total"] = len(required)
        return status

    @staticmethod
    def list_models() -> List[str]:
        """List available LivePortrait model files with sizes."""
        import os
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        weight_dir = root / "weights" / "liveportrait"

        if not weight_dir.exists():
            return []

        models = []
        for f in sorted(weight_dir.iterdir()):
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                models.append(f"{f.name} ({size_mb:.1f} MB)")
        return models


# ─── Convenience functions for quick use ──────────────────────────────

def animate_from_video(
    source_image: str,
    driving_video: str,
    output_dir: str = None,
) -> Dict[str, Any]:
    """One-shot: animate source face from driving video."""
    pipeline = LivePortraitAnimationPipeline()
    return pipeline.drive_from_video(source_image, driving_video, output_dir)


def animate_from_image(
    source_image: str,
    driving_image: str,
    output_dir: str = None,
) -> Dict[str, Any]:
    """One-shot: transfer expression from driving image to source."""
    pipeline = LivePortraitAnimationPipeline()
    return pipeline.drive_from_image(source_image, driving_image, output_dir)


def check_liveportrait_ready() -> Dict[str, Any]:
    """Check if LivePortrait is operational.

    Reports both direct import status and venv availability so the caller
    can decide which execution method to use.
    """
    weights = LivePortraitAnimationPipeline.check_weights()

    # Check direct import availability (quick check, no model loading)
    direct_ok = _can_import_direct()

    # Check venv fallback availability
    venv_ok = _find_venv_python() is not None

    # Check if we can actually load the API
    # Use _can_import_direct first to avoid triggering DLL conflict warnings
    api_ok = False
    if direct_ok:
        try:
            _get_live_portrait_api()
            api_ok = True
        except Exception:
            pass

    return {
        "api_loaded": api_ok,
        "direct_available": direct_ok,
        "venv_available": venv_ok,
        "venv_python": _find_venv_python(),
        "weights": weights,
        "models": LivePortraitAnimationPipeline.list_models(),
        "ready": (api_ok or venv_ok) and weights.get("all_present", False),
    }
