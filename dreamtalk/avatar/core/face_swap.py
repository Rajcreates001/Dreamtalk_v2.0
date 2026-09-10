"""DreamTalk - 3D Face Reconstruction Service (Real FlameFitter)

Replaces the old stub that returned hardcoded paths.
Now uses the improved FlameFitter from pipeline/flame_fitter.py with:
  - Real RetinaFace face detection
  - MediaPipe/PFLD landmark extraction
  - Joint camera + identity optimization
  - UV texture generation
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

import torch
import numpy as np

logger = logging.getLogger("dreamtalk.avatar.face_swap")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class FaceReconstructionService:
    """3D face reconstruction using FlameFitter with real model inference."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._fitter = None

    def _get_fitter(self):
        """Lazy-load the FlameFitter."""
        if self._fitter is not None:
            return self._fitter
        try:
            from dreamtalk.pipeline.flame_fitter import FlameFitter
            self._fitter = FlameFitter()
            logger.info(
                "FlameFitter loaded (%d verts, %d faces)",
                self._fitter.flame.num_vertices,
                self._fitter.flame.num_faces,
            )
        except Exception as e:
            logger.warning("FlameFitter load failed: %s", e)
        return self._fitter

    async def reconstruct_3d(self, image_path: str) -> dict:
        """Performs 3D face reconstruction using FlameFitter.

        Returns:
            dict with mesh_path, params_path, status, vertex_count, face_count
        """
        output_dir = str(PROJECT_ROOT / "avatar" / "static")
        os.makedirs(output_dir, exist_ok=True)

        fitter = self._get_fitter()
        if fitter is not None and os.path.exists(image_path):
            try:
                result = await asyncio.to_thread(
                    fitter.fit_from_photo,
                    image_path,
                    output_dir=output_dir,
                    fit_identity=True,
                    generate_texture=True,
                    n_components=30,
                )
                if result and result.get("obj_path") and os.path.exists(result["obj_path"]):
                    # Copy to names expected by the avatar static server
                    static_mesh = os.path.join(output_dir, "current_mesh.obj")
                    shutil.copy2(result["obj_path"], static_mesh)

                    tex = result.get("texture_path")
                    if tex and os.path.exists(tex):
                        tex_ext = os.path.splitext(tex)[1].lower()
                        static_tex = os.path.join(output_dir, f"current_texture{tex_ext}")
                        shutil.copy2(tex, static_tex)
                        # Create MTL
                        mtl_path = os.path.join(output_dir, "face_texture.mtl")
                        with open(mtl_path, "w") as f:
                            f.write(
                                "newmtl face_texture\n"
                                "Ka 1.0 1.0 1.0\n"
                                "Kd 1.0 1.0 1.0\n"
                                "Ks 0.0 0.0 0.0\n"
                                f"map_Kd current_texture{tex_ext}\n"
                            )

                    logger.info(
                        "Photo-fitted FLAME mesh: %s (%d verts, %d faces)",
                        result["obj_path"], result["vertex_count"], result["face_count"],
                    )
                    return {
                        "mesh_path": static_mesh,
                        "params_path": os.path.join(output_dir, "flame_params.json"),
                        "status": "success",
                        "vertex_count": result["vertex_count"],
                        "face_count": result["face_count"],
                        "identity_fitted": result.get("identity_fitted", True),
                    }
            except Exception as e:
                logger.warning("FlameFitter fit_from_photo failed: %s", e)

        # Fallback: generate mean FLAME mesh
        if fitter is not None:
            try:
                result = fitter.generate_mean_mesh(output_dir=output_dir)
                if result and result.get("obj_path") and os.path.exists(result["obj_path"]):
                    static_mesh = os.path.join(output_dir, "current_mesh.obj")
                    shutil.copy2(result["obj_path"], static_mesh)
                    return {
                        "mesh_path": static_mesh,
                        "params_path": "",
                        "status": "success",
                        "vertex_count": result["vertex_count"],
                        "face_count": result["face_count"],
                        "identity_fitted": False,
                    }
            except Exception as e:
                logger.warning("Mean FLAME mesh failed: %s", e)

        # Ultimate fallback
        logger.error("All 3D reconstruction methods failed for: %s", image_path)
        return {
            "mesh_path": "",
            "params_path": "",
            "status": "error",
            "vertex_count": 0,
            "face_count": 0,
            "identity_fitted": False,
        }

    async def extract_landmarks(self, image_path: str) -> dict:
        """Extracts 2D facial landmarks using MediaPipe."""
        try:
            import cv2
            import mediapipe as mp
            img = cv2.imread(image_path)
            if img is None:
                return {"landmarks": [], "count": 0}
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w = img.shape[:2]
            with mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True, max_num_faces=1, refine_landmarks=True,
            ) as face_mesh:
                results = face_mesh.process(rgb)
                if results and results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0]
                    pts = [(int(lm.x * w), int(lm.y * h), int(lm.z * w)) for lm in landmarks.landmark]
                    return {"landmarks": pts, "count": len(pts)}
        except Exception as e:
            logger.warning("Landmark extraction failed: %s", e)
        return {"landmarks": [], "count": 0}
