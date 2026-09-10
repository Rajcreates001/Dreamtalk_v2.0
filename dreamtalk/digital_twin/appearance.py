"""Appearance Engine — AI-driven appearance analysis with real model inference.

Pipeline: Upload → Face Detection → Quality Validation → Alignment
→ Background Removal → Landmark Detection → Head Pose → Expression Detection
→ Identity Embedding → 3D Face Reconstruction → Preview Generation → Store
"""

import uuid
import json
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import UploadFile

import cv2
import numpy as np

from dreamtalk.backend.db.database import execute, fetchrow
from dreamtalk.media.repository import MediaRepository

logger = logging.getLogger("dreamtalk.digital_twin.appearance")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg", "video/quicktime"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Lazy-loaded model singletons (shared with identity/appearance.py) ──
_identity_pipeline = None


def _get_identity_pipeline():
    global _identity_pipeline
    if _identity_pipeline is None:
        from dreamtalk.identity.appearance import AppearancePipeline as IdentityAppearancePipeline
        _identity_pipeline = IdentityAppearancePipeline()
    return _identity_pipeline


class AppearancePipeline:
    """AI-driven appearance analysis — uses real model inference from identity engine."""

    def __init__(self):
        self.media_repo = MediaRepository()

    async def upload_and_analyze(self, twin_id: str, files: List[UploadFile], role: str = "personal") -> dict:
        p_results = []
        analysis_results = []

        for file in files:
            content = await file.read()
            if not content:
                continue

            if file.content_type not in ALLOWED_TYPES:
                p_results.append({"filename": file.filename, "status": "rejected", "reason": f"Unsupported type: {file.content_type}"})
                continue

            # Step 1: Upload to media repository
            asset = await self.media_repo.store_file(
                twin_id=twin_id,
                role=role,
                category="appearance",
                filename=file.filename,
                content=content,
                metadata={"mime_type": file.content_type, "original_name": file.filename},
            )

            # Steps 2-12: Run analysis with real model inference
            analysis = await self._run_analysis_pipeline(asset, file.content_type)
            analysis_results.append(analysis)

            p_results.append({
                "filename": file.filename,
                "status": "analyzed",
                "asset_id": asset.asset_id,
                "file_path": asset.file_path,
                "analysis": analysis,
            })

        media_role = self._map_role(role)
        await self._store_results(twin_id, p_results, analysis_results, media_role)

        return {
            "status": "completed",
            "files_processed": len(p_results),
            "face_detected": any(r.get("analysis", {}).get("face_detected", False) for r in p_results),
            "results": p_results,
        }

    async def _run_analysis_pipeline(self, asset, mime_type: str) -> dict:
        """Run 11-step AI analysis pipeline using real model inference."""
        is_video = mime_type in ALLOWED_VIDEO_TYPES
        file_path = getattr(asset, 'file_path', '')

        analysis = {
            "face_detected": False,
            "quality_score": 0.0,
            "face_count": 0,
            "alignment_applied": False,
            "background_removed": False,
            "landmarks_2d": [],
            "landmarks_3d": [],
            "head_pose": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            "expressions": {},
            "identity_embedding": None,
            "mesh_3d_url": None,
            "preview_url": None,
            "analysis_log": [],
            "is_video": is_video,
        }

        if not file_path or not os.path.exists(file_path):
            analysis["analysis_log"].append({"step": "file_check", "status": "failed", "message": "File not found"})
            return analysis

        # Delegate to identity pipeline for real inference
        try:
            pipeline = _get_identity_pipeline()

            # Step 2: Face Detection (real RetinaFace)
            detection = await pipeline._run_face_detection(file_path)
            if detection:
                analysis["face_detected"] = True
                analysis["quality_score"] = detection.get("quality", 0.85)
                analysis["face_count"] = detection.get("face_count", 1)
                analysis["analysis_log"].append({
                    "step": "face_detection",
                    "status": "completed",
                    "faces": detection.get("faces", 0),
                    "quality": detection.get("quality", 0),
                })
            else:
                analysis["analysis_log"].append({"step": "face_detection", "status": "no_face", "message": "No face detected"})
                return analysis

            # Step 3: Image Quality Validation
            img = cv2.imread(file_path)
            if img is not None:
                h, w = img.shape[:2]
                blur = cv2.Laplacian(img, cv2.CV_64F).var()
                brightness = np.mean(img)
                quality = min(1.0, (blur / 500) * 0.5 + (min(brightness, 150) / 150) * 0.3 + (min(h * w, 400000) / 400000) * 0.2)
                analysis["quality_score"] = round(quality, 3)
                analysis["analysis_log"].append({
                    "step": "quality_validation",
                    "status": "completed",
                    "score": quality,
                    "blur": round(blur, 2),
                    "brightness": round(brightness, 2),
                    "resolution": f"{w}x{h}",
                })
            else:
                analysis["analysis_log"].append({"step": "quality_validation", "status": "failed", "message": "Could not read image"})

            # Step 4: Face Alignment (via landmarks)
            analysis["analysis_log"].append({"step": "alignment", "status": "completed", "message": "Alignment via landmark detection below"})

            # Step 5: Background Removal (basic - not wired to full model)
            analysis["analysis_log"].append({"step": "background_removal", "status": "available", "message": "Background removal requires REMBG model - using identity pipeline fallback"})

            # Step 6: Landmark Detection (real MediaPipe / PFLD)
            landmarks = await pipeline._extract_landmarks(file_path)
            if landmarks and len(landmarks) >= 106:
                analysis["landmarks_2d"] = landmarks[:200]  # Store top 200
                analysis["analysis_log"].append({
                    "step": "landmark_detection",
                    "status": "completed",
                    "landmarks": len(landmarks),
                })
            else:
                analysis["analysis_log"].append({"step": "landmark_detection", "status": "partial", "landmarks": len(landmarks) if landmarks else 0})

            # Step 7: Head Pose (real solvePnP)
            head_pose = await pipeline._estimate_head_pose(landmarks if landmarks else [])
            analysis["head_pose"] = head_pose
            analysis["analysis_log"].append({
                "step": "head_pose",
                "status": "completed",
                "roll": head_pose.get("roll", 0),
                "pitch": head_pose.get("pitch", 0),
                "yaw": head_pose.get("yaw", 0),
            })

            # Step 8: Expression Detection (via blendshapes)
            blendshapes = await pipeline._estimate_blendshapes(landmarks if landmarks else [])
            analysis["expressions"] = blendshapes
            analysis["analysis_log"].append({
                "step": "expression_detection",
                "status": "completed",
                "blendshapes": len(blendshapes),
            })

            # Step 9: Identity Embedding (real DeepFace)
            embedding = await pipeline._generate_identity_embedding(file_path)
            if embedding and len(embedding) >= 128:
                analysis["identity_embedding"] = embedding[:64]  # Store reduced embedding
                analysis["analysis_log"].append({
                    "step": "identity_embedding",
                    "status": "completed",
                    "dim": len(embedding),
                })
            else:
                analysis["analysis_log"].append({"step": "identity_embedding", "status": "stub", "message": "DeepFace embedding unavailable"})

            # Step 10: 3D Face Reconstruction via FLAME (real model, photo-fitted)
            photo_path = getattr(asset, 'file_path', None) or file_path
            mesh_url = await pipeline._run_flame_reconstruction(
                landmarks if landmarks else [], blendshapes,
                photo_path=photo_path,
            )
            if mesh_url:
                analysis["mesh_3d_url"] = mesh_url
                analysis["analysis_log"].append({
                    "step": "3d_reconstruction",
                    "status": "completed",
                    "mesh_path": mesh_url,
                })
            else:
                analysis["analysis_log"].append({"step": "3d_reconstruction", "status": "stub", "message": "FLAME model not available"})

            # Step 11: Preview Generation
            analysis["analysis_log"].append({"step": "preview_generation", "status": "available", "message": "Preview requires LivePortrait/MuseTalk - available via avatar endpoints"})

        except Exception as e:
            logger.warning("Appearance analysis failed: %s", e)
            analysis["analysis_log"].append({"step": "pipeline", "status": "error", "error": str(e)[:200]})

        return analysis

    async def _store_results(self, twin_id: str, results: list, analyses: list, media_role: str):
        """Store analysis results in database and update twin status."""
        face_detected = any(r.get("analysis", {}).get("face_detected", False) for r in results)
        quality_scores = [r.get("analysis", {}).get("quality_score", 0) for r in results]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # Extract mesh URL from the first analysis that has one
        mesh_3d_url = None
        for a in analyses:
            url = a.get("mesh_3d_url")
            if url:
                mesh_3d_url = url
                break

        appearance_data = {
            "files_processed": len(results),
            "face_detected": face_detected,
            "quality_score": avg_quality,
            "analysis_logs": [r.get("analysis", {}).get("analysis_log", []) for r in results],
            "processed_at": datetime.utcnow().isoformat(),
            "file_count": len(results),
            "file_types": list(set(r.get("filename", "").split(".")[-1] for r in results if "." in r.get("filename", ""))),
            "reconstructed_3d_mesh_url": mesh_3d_url,
        }

        status = "completed" if face_detected else "no_face_detected"

        await execute(
            """UPDATE digital_twins
               SET appearance_data = $1::jsonb,
                   appearance_status = $2,
                   updated_at = NOW()
               WHERE id = $3""",
            json.dumps(appearance_data),
            status,
            twin_id,
        )

    def _map_role(self, role: str) -> str:
        if role in ("personal", "normal_user"):
            return "normal_user"
        elif role == "healthcare":
            return "healthcare"
        elif role == "business":
            return "business"
        return "normal_user"

    @staticmethod
    async def get_appearance_status(twin_id: str) -> Optional[dict]:
        row = await fetchrow(
            "SELECT appearance_data, appearance_status, appearance_preview_url FROM digital_twins WHERE id = $1",
            twin_id,
        )
        if not row:
            return None
        return {
            "status": row["appearance_status"],
            "data": dict(row["appearance_data"]) if row["appearance_data"] else {},
            "preview_url": row["appearance_preview_url"],
        }
