from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import cv2
import numpy as np
import shutil
from fastapi import UploadFile

from dreamtalk.backend.db.database import execute, fetchrow
from dreamtalk.identity.models import AppearanceProfile
from dreamtalk.identity.engine import IdentityEngine

logger = logging.getLogger("dreamtalk.identity.appearance")

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "backend", "uploads", "appearance",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Lazy-loaded model singletons ───────────────────────────────────────
_retinaface_detector = None
_pfld_detector = None
_flame_model = None
_flame_driver = None


def _load_retinaface():
    """Load RetinaFace detector from weights/retinaface/RetinaFace-R50.pth."""
    global _retinaface_detector
    if _retinaface_detector is not None:
        return _retinaface_detector
    try:
        from retinaface import RetinaFace as rf_detector
        _retinaface_detector = rf_detector
        logger.info("RetinaFace detector loaded (Python package)")
        return _retinaface_detector
    except ImportError:
        try:
            from dreamtalk.face.core.animation.liveportrait.utils.dependencies.insightface.model_zoo.retinaface import RetinaFace as InsightRetinaFace
            weight_path = str(PROJECT_ROOT / "weights/retinaface/RetinaFace-R50.pth")
            if os.path.exists(weight_path):
                _retinaface_detector = InsightRetinaFace(model_file=weight_path)
                _retinaface_detector.prepare(-1)
                logger.info("RetinaFace detector loaded (InsightFace, weights: %s)", weight_path)
                return _retinaface_detector
        except Exception:
            pass
    logger.warning("RetinaFace not available")
    return None


def _load_pfld():
    """Load PFLD landmark detector using the proper model architecture."""
    global _pfld_detector
    if _pfld_detector is not None:
        return _pfld_detector
    try:
        from dreamtalk.face.models.landmarks.pfld.detector import PFLDFaceDetection
        weight_path = str(PROJECT_ROOT / "weights/flame/pfld_model.pth")
        _pfld_detector = PFLDFaceDetection(weight_path=weight_path, device="cpu")
        logger.info("PFLD detector initialized from %s", weight_path)
        return _pfld_detector
    except Exception as e:
        logger.warning("PFLD load failed: %s", e)
    return None


class AppearancePipeline:
    """Chains media upload -> face detection -> landmark extraction -> 3D reconstruction.

    All model calls now use real inference when weights are present,
    falling back to mock data gracefully.
    """

    def __init__(self):
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    async def process_upload(self, identity_id: str, file: UploadFile) -> dict:
        """Accept uploaded media, save to disk, then run analysis."""
        file_ext = os.path.splitext(file.filename or "upload.jpg")[1] or ".jpg"
        saved_path = os.path.join(UPLOAD_DIR, f"{identity_id}_{uuid.uuid4().hex}{file_ext}")
        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)

        appearance = await self._analyze_media([saved_path])
        updated = await IdentityEngine.update_appearance(identity_id, appearance)

        return {
            "status": "analyzed",
            "identity_id": identity_id,
            "source_media": [saved_path],
            "profile": updated.model_dump(),
        }

    async def analyze(self, identity_id: str, media_urls: list[str]) -> dict:
        """Analyze already-uploaded media URLs and update identity."""
        appearance = await self._analyze_media(media_urls)
        updated = await IdentityEngine.update_appearance(identity_id, appearance)
        return {
            "status": "analyzed",
            "identity_id": identity_id,
            "profile": updated.model_dump(),
        }

    async def _analyze_media(self, media_paths: list[str]) -> AppearanceProfile:
        """Run the appearance extraction pipeline with real model inference."""
        profile = AppearanceProfile(
            source_media=media_paths,
            capture_type="upload",
        )

        # --- Step 1: Face detection ---
        detection_result = await self._run_face_detection(media_paths[0] if media_paths else "")
        if not detection_result:
            return profile

        profile.quality_score = detection_result.get("quality", 0.85)

        # --- Step 2: Landmarks ---
        profile.landmarks = await self._extract_landmarks(media_paths[0] if media_paths else "")

        # --- Step 3: Blendshapes ---
        profile.blendshapes = await self._estimate_blendshapes(profile.landmarks)

        # --- Step 4: Head pose ---
        profile.head_pose = await self._estimate_head_pose(profile.landmarks)

        # --- Step 5: 3D reconstruction ---
        profile.reconstructed_3d_mesh_url = await self._run_flame_reconstruction(
            profile.landmarks, profile.blendshapes,
        )

        # --- Step 6: Face embedding ---
        profile.face_embedding = await self._generate_identity_embedding(
            media_paths[0] if media_paths else "",
        )

        # --- Step 7: Identity vector ---
        profile.identity_vector = profile.face_embedding[:128] if len(profile.face_embedding) >= 128 else profile.face_embedding

        return profile

    async def _run_face_detection(self, media_path: str) -> Optional[dict]:
        """Face detection — RetinaFace with weight fallback."""
        if not media_path or not os.path.exists(media_path):
            return None
        try:
            img = cv2.imread(media_path)
            if img is None:
                return None

            detector = _load_retinaface()
            if detector:
                # Use retinaface Python package (primary)
                if hasattr(detector, 'detect_faces'):
                    faces = detector.detect_faces(img)
                    if faces:
                        face = list(faces.values())[0]
                        score = face.get('score', 0.95)
                        facial_area = face.get('facial_area', [])
                        return {
                            "quality": float(score),
                            "faces": len(faces),
                            "face_count": len(faces),
                            "bbox": facial_area[:4] if len(facial_area) >= 4 else None,
                            "landmarks_5": face.get('landmarks', []),
                        }
                # Fallback: use insightface RetinaFace
                elif hasattr(detector, 'detect'):
                    det, kpss = detector.detect(img)
                    if det is not None and len(det) > 0:
                        return {
                            "quality": float(det[0][4]),
                            "faces": len(det),
                            "face_count": len(det),
                            "bbox": det[0][:4].tolist(),
                            "landmarks_5": kpss[0].tolist() if kpss is not None and len(kpss) > 0 else [],
                        }
        except Exception as e:
            logger.warning("Face detection error: %s", e)

        # Fallback: return mock data
        return {"quality": 0.85, "faces": 1, "face_count": 1}

    async def _extract_landmarks(self, media_path: str) -> list[list[float]]:
        """Landmark extraction — PFLD with fallback to MediaPipe."""
        if not media_path or not os.path.exists(media_path):
            return [[0.5, 0.5]] * 478
        try:
            # Try MediaPipe first (no weights needed, built-in)
            try:
                import mediapipe as mp
                img = cv2.imread(media_path)
                if img is not None:
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    with mp.solutions.face_mesh.FaceMesh(
                        static_image_mode=True,
                        max_num_faces=1,
                        refine_landmarks=True,
                        min_detection_confidence=0.5
                    ) as face_mesh:
                        results = face_mesh.process(rgb)
                        if results.multi_face_landmarks:
                            landmarks = results.multi_face_landmarks[0]
                            h, w = img.shape[:2]
                            return [[lm.x * w, lm.y * h] for lm in landmarks.landmark]
            except ImportError:
                pass

            # Fallback: PFLD model
            pfld = _load_pfld()
            if pfld is not None and pfld.model is not None:
                img = cv2.imread(media_path)
                if img is not None:
                    landmarks_list = pfld.extract_landmarks_from_face(img)
                    if landmarks_list and len(landmarks_list) >= 106:
                        logger.info("PFLD detected %d landmarks", len(landmarks_list))
                        return landmarks_list
        except Exception as e:
            logger.warning("Landmark extraction error: %s", e)

        return [[0.5, 0.5]] * 478

    async def _estimate_blendshapes(self, landmarks: list[list[float]]) -> dict[str, float]:
        """Blendshape estimation — MediaPipeToFlame converter."""
        try:
            from dreamtalk.avatar.core.face.flame.mediapipe_to_flame import MediaPipeToFlame
            converter = MediaPipeToFlame()
            blendshapes = converter.convert(landmarks)
            return blendshapes
        except Exception as e:
            logger.warning("Blendshape estimation unavailable: %s", e)
        return {f"blend_{i}": 0.0 for i in range(52)}

    async def _estimate_head_pose(self, landmarks: list[list[float]]) -> dict[str, float]:
        """Estimate head pose from landmarks using solvePnP."""
        if not landmarks or len(landmarks) < 6:
            return {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        try:
            landmarks_arr = np.array(landmarks[:6], dtype=np.float32)
            if landmarks_arr.shape[0] >= 4:
                # Simple head pose estimation via 2D-3D correspondences
                image_points = landmarks_arr[:4]
                model_points = np.array([
                    (0.0, 0.0, 0.0),
                    (0.0, -3.0, -1.0),
                    (3.0, 0.0, 0.0),
                    (-3.0, 0.0, 0.0),
                ], dtype=np.float32)[:len(image_points)]

                focal_length = 500.0
                center = (500.0, 500.0)
                camera_matrix = np.array([
                    [focal_length, 0, center[0]],
                    [0, focal_length, center[1]],
                    [0, 0, 1]
                ], dtype=np.float32)

                dist_coeffs = np.zeros((4, 1))
                _, rvec, tvec = cv2.solvePnP(
                    model_points, image_points,
                    camera_matrix, dist_coeffs,
                    flags=cv2.SOLVEPNP_ITERATIVE
                )
                rmat, _ = cv2.Rodrigues(rvec)
                return {
                    "roll": float(np.arctan2(-rmat[1, 0], rmat[0, 0])),
                    "pitch": float(np.arcsin(rmat[2, 0])),
                    "yaw": float(np.arctan2(rmat[2, 1], rmat[2, 2])),
                }
        except Exception as e:
            logger.warning("Head pose estimation error: %s", e)
        return {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}

    async def _run_flame_reconstruction(
        self, landmarks: list[list[float]], blendshapes: dict[str, float],
        photo_path: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a 3D FLAME mesh (.obj) using the FlameFitter.

        Uses the improved identity fitting pipeline:
        - Model-derived MediaPipe→FLAME landmark correspondences (no hardcoded indices)
        - Joint camera + identity optimization (learns scale, translation, rotation)
        - Confidence-weighted reprojection error

        When photo_path is provided, calls fit_from_photo() for photo-fitted mesh.
        Otherwise falls back to generate_mean_mesh().
        The result is copied to avatar/static/current_mesh.* for the viewer.
        """
        STATIC_DIR = PROJECT_ROOT / "avatar" / "static"
        os.makedirs(str(STATIC_DIR), exist_ok=True)

        try:
            from dreamtalk.pipeline.flame_fitter import FlameFitter
            fitter = FlameFitter()

            # Use photo-fitted mesh when a photo is available
            # Run fit_from_photo() in a thread to avoid blocking the event loop
            # (scipy L-BFGS-B optimization is CPU-bound, ~2-5s)
            if photo_path and os.path.exists(photo_path):
                result = await asyncio.to_thread(
                    fitter.fit_from_photo,
                    photo_path,
                    output_dir=str(STATIC_DIR),
                    fit_identity=True,
                    generate_texture=True,
                    n_components=30,
                )
                if result and result["obj_path"] and os.path.exists(result["obj_path"]):
                    # Copy to named files expected by the avatar viewer
                    shutil.copy2(result["obj_path"], STATIC_DIR / "current_mesh.obj")

                    if result.get("texture_path") and os.path.exists(result["texture_path"]):
                        # Detect actual extension from source file
                        src_ext = Path(result["texture_path"]).suffix.lower()
                        tex_name = f"current_texture{src_ext}"
                        shutil.copy2(result["texture_path"], STATIC_DIR / tex_name)
                        # Create matching MTL
                        (STATIC_DIR / "face_texture.mtl").write_text(
                            "newmtl face_texture\nKa 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\n"
                            f"map_Kd {tex_name}\n"
                        )

                    mesh_url = "/api/static/current_mesh.obj"
                    logger.info(
                        "Photo-fitted FLAME mesh: %s (%d verts, %d faces, identity=%s)",
                        result["obj_path"], result["vertex_count"],
                        result["face_count"], result.get("identity_fitted"),
                    )
                    return mesh_url

                logger.warning("Photo fitting produced no valid mesh, falling back to mean mesh")

            # Fallback: generate the mean FLAME mesh (in thread to avoid blocking)
            result = await asyncio.to_thread(
                fitter.generate_mean_mesh, output_dir=str(STATIC_DIR),
            )

            if result and result["obj_path"] and os.path.exists(result["obj_path"]):
                shutil.copy2(result["obj_path"], STATIC_DIR / "current_mesh.obj")
                mesh_url = "/api/static/current_mesh.obj"
                logger.info(
                    "Mean FLAME mesh: %s (%d verts, %d faces)",
                    result["obj_path"], result["vertex_count"], result["face_count"],
                )
                return mesh_url

        except Exception as e:
            logger.warning("FlameFitter reconstruction failed: %s", e)

        # Both FlameFitter paths failed — the FLAME model weights are likely missing.
        logger.error(
            "3D face reconstruction failed: FlameFitter unavailable or missing FLAME weights "
            "at %s", PROJECT_ROOT / "weights/flame/FLAME2020_numpy.pkl"
        )
        return None

    async def _generate_identity_embedding(self, media_path: str) -> list[float]:
        """Generate face recognition embedding using deepface."""
        if not media_path or not os.path.exists(media_path):
            return [0.0] * 512
        try:
            from deepface import DeepFace
            embedding = DeepFace.represent(
                img_path=media_path,
                model_name="Facenet",
                detector_backend="skip",
                enforce_detection=False,
            )
            if embedding and len(embedding) > 0:
                return embedding[0]["embedding"]
        except Exception as e:
            logger.warning("Identity embedding error: %s", e)
        return [0.0] * 512
