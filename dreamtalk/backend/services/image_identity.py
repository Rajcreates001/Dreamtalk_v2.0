"""Face restoration and identity-verification services for avatar creation.

All neural models load lazily. Missing weights or dependencies are reported as
unavailable; they are never replaced with fake biometric vectors.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import threading
import types
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

logger = logging.getLogger("dreamtalk.avatar.identity")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESTORATION_ROOT = Path(
    os.environ.get("FACE_RESTORATION_WEIGHTS_DIR", PROJECT_ROOT / "weights" / "face" / "restoration")
)
GFPGAN_WEIGHT = RESTORATION_ROOT / "GFPGANv1.4.pth"
REALESRGAN_WEIGHT = RESTORATION_ROOT / "RealESRGAN_x2plus.pth"
FACE_DETECTOR_WEIGHT = RESTORATION_ROOT / "detection_Resnet50_Final.pth"
FACE_PARSER_WEIGHT = RESTORATION_ROOT / "parsing_parsenet.pth"


def _install_basicsr_torchvision_compatibility() -> None:
    """Provide the one legacy TorchVision symbol expected by BasicSR 1.4.2."""
    module_name = "torchvision.transforms.functional_tensor"
    if module_name in sys.modules:
        return
    try:
        from torchvision.transforms.functional import rgb_to_grayscale

        shim = types.ModuleType(module_name)
        shim.rgb_to_grayscale = rgb_to_grayscale
        sys.modules[module_name] = shim
    except Exception:
        return


class FaceRestorationService:
    """GFPGAN face restoration with optional Real-ESRGAN background upscaling."""

    def __init__(self) -> None:
        self._restorer = None
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def status(self) -> dict[str, Any]:
        dependencies = {
            name: importlib.util.find_spec(name) is not None
            for name in ("torch", "torchvision", "basicsr", "facexlib", "gfpgan", "realesrgan")
        }
        weights = {
            "gfpgan_v1_4": GFPGAN_WEIGHT.exists(),
            "realesrgan_x2plus": REALESRGAN_WEIGHT.exists(),
            "facexlib_detector": FACE_DETECTOR_WEIGHT.exists(),
            "facexlib_parser": FACE_PARSER_WEIGHT.exists(),
        }
        return {
            "ready": all(dependencies.values()) and all(weights.values()),
            "loaded": self._restorer is not None,
            "device": "cuda" if self._cuda_available() else "cpu",
            "dependencies": dependencies,
            "weights": weights,
            "load_error": self._load_error,
        }

    @staticmethod
    def needs_restoration(image_path: str) -> dict[str, Any]:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Image-quality input cannot be decoded")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = image.shape[:2]
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))
        reasons = []
        if min(width, height) < 512:
            reasons.append("low_resolution")
        if sharpness < 80.0:
            reasons.append("blur")
        if brightness < 45.0:
            reasons.append("low_light")
        return {
            "required": bool(reasons),
            "reasons": reasons,
            "width": int(width),
            "height": int(height),
            "laplacian_variance": round(sharpness, 3),
            "brightness": round(brightness, 3),
        }

    def _load(self):
        if self._restorer is not None:
            return self._restorer
        with self._lock:
            if self._restorer is not None:
                return self._restorer
            status = self.status()
            if not status["ready"]:
                raise RuntimeError(f"GFPGAN restoration is not ready: {status}")
            try:
                _install_basicsr_torchvision_compatibility()
                from basicsr.archs.rrdbnet_arch import RRDBNet
                from gfpgan import GFPGANer
                from realesrgan import RealESRGANer

                background = None
                if REALESRGAN_WEIGHT.exists():
                    model = RRDBNet(
                        num_in_ch=3,
                        num_out_ch=3,
                        num_feat=64,
                        num_block=23,
                        num_grow_ch=32,
                        scale=2,
                    )
                    background = RealESRGANer(
                        scale=2,
                        model_path=str(REALESRGAN_WEIGHT),
                        model=model,
                        tile=int(os.environ.get("REALESRGAN_TILE", "400")),
                        tile_pad=10,
                        pre_pad=0,
                        half=self._cuda_available(),
                    )
                # GFPGAN 1.3.8 hard-codes this relative auxiliary-weight
                # directory. Link our checksum-verified persistent files so it
                # never performs an untracked network download at inference.
                auxiliary_dir = Path.cwd() / "gfpgan" / "weights"
                auxiliary_dir.mkdir(parents=True, exist_ok=True)
                for source in (FACE_DETECTOR_WEIGHT, FACE_PARSER_WEIGHT):
                    destination = auxiliary_dir / source.name
                    if not destination.exists():
                        try:
                            destination.symlink_to(source.resolve())
                        except OSError:
                            import shutil

                            shutil.copy2(source, destination)

                self._restorer = GFPGANer(
                    model_path=str(GFPGAN_WEIGHT),
                    upscale=int(os.environ.get("GFPGAN_UPSCALE", "2")),
                    arch="clean",
                    channel_multiplier=2,
                    bg_upsampler=background,
                )
                self._load_error = None
                return self._restorer
            except Exception as exc:
                self._load_error = str(exc)
                raise

    def restore(self, source_path: str, destination_path: str) -> dict[str, Any]:
        source = Path(source_path)
        destination = Path(destination_path)
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Face-restoration input cannot be decoded")
        restorer = self._load()
        with self._lock:
            _, restored_faces, restored = restorer.enhance(
                image,
                has_aligned=False,
                only_center_face=False,
                paste_back=True,
                weight=float(os.environ.get("GFPGAN_FIDELITY_WEIGHT", "0.65")),
            )
        if restored is None:
            raise RuntimeError("GFPGAN returned no restored image")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(destination), restored):
            raise RuntimeError("Could not save restored face image")
        return {
            "path": str(destination),
            "engine": "gfpgan-v1.4",
            "background_engine": "realesrgan-x2plus" if REALESRGAN_WEIGHT.exists() else None,
            "face_count": len(restored_faces or []),
            "device": "cuda" if self._cuda_available() else "cpu",
            "width": int(restored.shape[1]),
            "height": int(restored.shape[0]),
        }


class FaceIdentityService:
    """Real face embeddings and cosine-similarity quality gates."""

    def __init__(self) -> None:
        self.model_name = os.environ.get("FACE_EMBEDDING_MODEL", "Facenet512")
        self._lock = threading.Lock()

    def status(self) -> dict[str, Any]:
        dependencies = {
            name: importlib.util.find_spec(name) is not None
            for name in ("deepface", "tensorflow", "tf_keras")
        }
        available = all(dependencies.values())
        return {
            "ready": available,
            "engine": "deepface" if available else None,
            "model": self.model_name if available else None,
            "threshold": float(os.environ.get("FACE_IDENTITY_THRESHOLD", "0.68")),
            "dependencies": dependencies,
            "device": "gpu" if os.environ.get("FACE_IDENTITY_USE_GPU", "false").lower() == "true" else "cpu",
            "device_reason": "isolated from PyTorch cuDNN runtime" if available else None,
        }

    def embed(self, image_path: str) -> np.ndarray:
        if not self.status()["ready"]:
            raise RuntimeError("No real face-identity encoder is installed")
        # TensorFlow 2.21 and PyTorch 2.5 require different cuDNN minor
        # versions in this shared image. Identity embedding is an enrollment-
        # time operation, so isolate TensorFlow on CPU unless explicitly
        # overridden while leaving all Torch inference on CUDA.
        if os.environ.get("FACE_IDENTITY_USE_GPU", "false").lower() != "true":
            import tensorflow as tf

            try:
                tf.config.set_visible_devices([], "GPU")
            except RuntimeError:
                pass
        from deepface import DeepFace

        with self._lock:
            result = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=os.environ.get("FACE_IDENTITY_DETECTOR", "opencv"),
                enforce_detection=True,
                align=True,
            )
        if not result or not result[0].get("embedding"):
            raise RuntimeError("Identity encoder returned no face embedding")
        embedding = np.asarray(result[0]["embedding"], dtype=np.float32)
        norm = float(np.linalg.norm(embedding))
        if embedding.ndim != 1 or norm <= 1e-8:
            raise RuntimeError("Identity encoder returned an invalid embedding")
        return embedding / norm

    def verify(self, reference_path: str, candidate_path: str) -> dict[str, Any]:
        reference = self.embed(reference_path)
        candidate = self.embed(candidate_path)
        return self.compare_embeddings(reference, candidate)

    def compare_embeddings(self, reference: np.ndarray, candidate: np.ndarray) -> dict[str, Any]:
        reference = np.asarray(reference, dtype=np.float32)
        candidate = np.asarray(candidate, dtype=np.float32)
        if reference.shape != candidate.shape:
            raise RuntimeError("Identity embeddings have incompatible dimensions")
        reference_norm = float(np.linalg.norm(reference))
        candidate_norm = float(np.linalg.norm(candidate))
        if reference.ndim != 1 or reference_norm <= 1e-8 or candidate_norm <= 1e-8:
            raise RuntimeError("Identity embeddings are invalid")
        similarity = float(np.dot(reference / reference_norm, candidate / candidate_norm))
        threshold = float(os.environ.get("FACE_IDENTITY_THRESHOLD", "0.68"))
        return {
            "verified": similarity >= threshold,
            "similarity": round(similarity, 6),
            "threshold": threshold,
            "model": self.model_name,
            "embedding_dim": int(reference.size),
        }


_restoration_service: Optional[FaceRestorationService] = None
_identity_service: Optional[FaceIdentityService] = None


def get_face_restoration_service() -> FaceRestorationService:
    global _restoration_service
    if _restoration_service is None:
        _restoration_service = FaceRestorationService()
    return _restoration_service


def get_face_identity_service() -> FaceIdentityService:
    global _identity_service
    if _identity_service is None:
        _identity_service = FaceIdentityService()
    return _identity_service
