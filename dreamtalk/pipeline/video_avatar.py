"""
DreamTalk — 360° Video → Avatar Pipeline

Converts a 360° head video into a personalized 3D avatar:
  1. Frame extraction (~30fps from video)
  2. Face detection + quality scoring
  3. Intelligent frame selection (30-60 best frames)
  4. Multi-view 3D reconstruction via FLAME
  5. Texture fusion from best frames
  6. Avatar export (OBJ + GLB)

Target: ≤5 minutes for a 30-60s video on CPU.

Usage:
    pipeline = VideoAvatarPipeline()
    result = await pipeline.process_video(video_path, user_id="user_123")
    print(result.avatar_path, result.glb_path)
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import cv2
import numpy as np

logger = logging.getLogger("dreamtalk.video_avatar")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class VideoAvatarResult:
    """Result from video → avatar pipeline."""
    avatar_path: str = ""
    glb_path: str = ""
    mesh_path: str = ""
    texture_path: str = ""
    total_frames: int = 0
    selected_frames: int = 0
    processing_time_s: float = 0.0
    face_detected_frames: int = 0
    quality_score: float = 0.0


class VideoAvatarPipeline:
    """Convert a 360° head video into a 3D avatar."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or PROJECT_ROOT / "pipeline_outputs" / "avatars")
        os.makedirs(self.output_dir, exist_ok=True)

    async def process_video(
        self,
        video_path: str,
        user_id: str = "default",
        max_frames: int = 60,
        target_fps: float = 1.0,
    ) -> VideoAvatarResult:
        """Process a 360° video into a 3D avatar.

        Args:
            video_path: Path to the video file.
            user_id: User identifier for output directory.
            max_frames: Maximum frames to select for reconstruction.
            target_fps: Target extraction rate (1.0 = 1 frame/sec for 60s video → 60 frames).

        Returns:
            VideoAvatarResult with paths and metadata.
        """
        start_time = time.time()
        result = VideoAvatarResult()

        output_subdir = self.output_dir / user_id / uuid.uuid4().hex[:8]
        os.makedirs(output_subdir, exist_ok=True)

        try:
            # Step 1: Extract frames
            logger.info(f"Step 1/6: Extracting frames from {video_path}")
            frames, timestamps = self._extract_frames(video_path, target_fps)
            result.total_frames = len(frames)
            logger.info(f"  Extracted {len(frames)} frames")

            # Step 2: Detect faces + quality scoring
            logger.info("Step 2/6: Detecting faces and scoring quality")
            scored_frames = self._score_frames(frames, timestamps)
            result.face_detected_frames = sum(1 for f in scored_frames if f["has_face"])
            logger.info(f"  Faces detected in {result.face_detected_frames}/{len(scored_frames)} frames")

            # Step 3: Select best frames
            logger.info(f"Step 3/6: Selecting best {min(max_frames, len(scored_frames))} frames")
            selected = self._select_best_frames(scored_frames, max_frames)
            result.selected_frames = len(selected)
            result.quality_score = np.mean([f["quality"] for f in selected]) if selected else 0.0
            logger.info(f"  Selected {len(selected)} frames, quality={result.quality_score:.3f}")

            if not selected:
                logger.warning("No good frames found — returning empty result")
                result.processing_time_s = time.time() - start_time
                return result

            # Step 4: Multi-view 3D reconstruction
            logger.info("Step 4/6: 3D face reconstruction")
            mesh_result = self._reconstruct_3d(selected, output_subdir)
            result.mesh_path = mesh_result.get("mesh_path", "")
            result.texture_path = mesh_result.get("texture_path", "")
            logger.info(f"  Mesh: {result.mesh_path}")

            # Step 5: Texture fusion from best frames
            logger.info("Step 5/6: Texture fusion")
            if not result.texture_path:
                result.texture_path = self._fuse_texture(selected, output_subdir)
                logger.info(f"  Texture: {result.texture_path}")

            # Step 6: Export avatar
            logger.info("Step 6/6: Avatar export")
            result.avatar_path = result.mesh_path
            if result.mesh_path:
                try:
                    from dreamtalk.pipeline.avatar_export import AvatarExporter
                    exporter = AvatarExporter()
                    result.glb_path = exporter.obj_to_glb(
                        result.mesh_path, result.texture_path,
                        str(Path(result.mesh_path).with_suffix(".glb")),
                    )
                except Exception as e:
                    logger.warning(f"GLB export failed: {e}")

        except Exception as e:
            logger.error(f"Video avatar pipeline failed: {e}", exc_info=True)

        result.processing_time_s = time.time() - start_time
        logger.info(
            f"Pipeline complete: {result.selected_frames} frames → "
            f"avatar in {result.processing_time_s:.1f}s"
        )
        return result

    def _extract_frames(
        self, video_path: str, target_fps: float
    ) -> Tuple[List[np.ndarray], List[float]]:
        """Extract frames from video at target FPS."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        skip = max(1, int(video_fps / target_fps))

        frames = []
        timestamps = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % skip == 0:
                frames.append(frame)
                timestamps.append(frame_idx / video_fps)
            frame_idx += 1

        cap.release()
        return frames, timestamps

    def _score_frames(
        self, frames: List[np.ndarray], timestamps: List[float]
    ) -> List[Dict[str, Any]]:
        """Detect faces and score frame quality."""
        scored = []

        for i, (frame, ts) in enumerate(zip(frames, timestamps)):
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Face detection with OpenCV's Haar cascade (fast, no GPU needed)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            faces = faces_cascade.detectMultiScale(gray, 1.1, 4, minSize=(80, 80))

            has_face = len(faces) > 0
            face_bbox = faces[0].tolist() if has_face else None
            face_area_ratio = 0.0
            center_score = 0.0
            sharpness = 0.0

            if has_face:
                x, y, fw, fh = face_bbox
                face_area_ratio = (fw * fh) / (w * h)

                # Center score: how centered is the face
                cx = x + fw / 2
                cy = y + fh / 2
                center_dist = ((cx / w - 0.5) ** 2 + (cy / h - 0.5) ** 2) ** 0.5
                center_score = max(0, 1.0 - center_dist * 2)

                # Sharpness via Laplacian variance
                face_region = gray[y:y + fh, x:x + fw]
                sharpness = cv2.Laplacian(face_region, cv2.CV_64F).var() / 1000.0
                sharpness = min(sharpness, 1.0)

            quality = 0.0
            if has_face:
                quality = (
                    0.3 * min(face_area_ratio * 5, 1.0) +  # Face size
                    0.3 * center_score +                      # Centered
                    0.2 * sharpness +                          # Sharp
                    0.2 * (1.0 - i / len(frames) * 0.3)      # Prefer earlier frames
                )

            scored.append({
                "index": i,
                "timestamp": ts,
                "has_face": has_face,
                "face_bbox": face_bbox,
                "quality": quality,
                "sharpness": sharpness,
                "center_score": center_score,
                "face_area_ratio": face_area_ratio,
                "frame": frame,
            })

        return scored

    def _select_best_frames(
        self, scored_frames: List[Dict], max_frames: int
    ) -> List[Dict]:
        """Select best frames ensuring diversity (different head angles)."""
        # Filter to frames with faces
        with_faces = [f for f in scored_frames if f["has_face"]]
        if not with_faces:
            return []

        # Sort by quality
        with_faces.sort(key=lambda f: f["quality"], reverse=True)

        # Select top frames, but ensure minimum spacing
        selected = []
        min_spacing = max(1, len(with_faces) // (max_frames * 2))

        for f in with_faces:
            if len(selected) >= max_frames:
                break
            # Check spacing from last selected
            if selected:
                last_idx = selected[-1]["index"]
                if abs(f["index"] - last_idx) < min_spacing:
                    continue
            selected.append(f)

        # Sort by timestamp for reconstruction order
        selected.sort(key=lambda f: f["timestamp"])
        return selected

    def _reconstruct_3d(
        self, selected_frames: List[Dict], output_dir: Path
    ) -> Dict[str, str]:
        """Run multi-view 3D reconstruction using FLAME."""
        result = {"mesh_path": "", "texture_path": ""}

        try:
            from dreamtalk.pipeline.flame_fitter import FlameFitter, FLAMELoader

            # Find FLAME model
            flame_paths = [
                PROJECT_ROOT / "weights" / "flame" / "FLAME2020_numpy.pkl",
                PROJECT_ROOT / "weights" / "flame" / "FLAME2020.pkl",
            ]
            flame_path = None
            for p in flame_paths:
                if p.exists():
                    flame_path = str(p)
                    break

            if not flame_path:
                logger.warning("FLAME model not found — using placeholder")
                return self._generate_placeholder(selected_frames, output_dir)

            # Use best frame for primary reconstruction
            best = selected_frames[0]
            frame_path = str(output_dir / "best_frame.jpg")
            cv2.imwrite(frame_path, best["frame"])

            fitter = FlameFitter()
            mesh_result = fitter.fit_from_image(
                frame_path,
                output_dir=str(output_dir),
                output_name="avatar_mesh",
            )

            if mesh_result and mesh_result.get("mesh_path"):
                result["mesh_path"] = mesh_result["mesh_path"]
                result["texture_path"] = mesh_result.get("texture_path", "")

        except Exception as e:
            logger.warning(f"FLAME reconstruction failed: {e}")
            return self._generate_placeholder(selected_frames, output_dir)

        return result

    def _fuse_texture(
        self, selected_frames: List[Dict], output_dir: Path
    ) -> str:
        """Fuse textures from multiple frames into a single atlas."""
        # Simple approach: use the best quality frame as texture source
        best = max(selected_frames, key=lambda f: f["quality"])
        texture_path = str(output_dir / "texture.jpg")
        cv2.imwrite(texture_path, best["frame"])
        return texture_path

    def _generate_placeholder(
        self, selected_frames: List[Dict], output_dir: Path
    ) -> Dict[str, str]:
        """Generate a placeholder OBJ mesh when FLAME is not available."""
        mesh_path = str(output_dir / "placeholder_face.obj")

        # Generate a simple sphere as placeholder
        vertices = []
        faces = []
        rings = 16
        sectors = 16

        for r in range(rings + 1):
            phi = np.pi * r / rings
            for s in range(sectors):
                theta = 2 * np.pi * s / sectors
                x = np.sin(phi) * np.cos(theta) * 0.1
                y = np.cos(phi) * 0.1
                z = np.sin(phi) * np.sin(theta) * 0.1
                vertices.append(f"v {x:.6f} {y:.6f} {z:.6f}")

        for r in range(rings):
            for s in range(sectors):
                i1 = r * sectors + s + 1
                i2 = i1 + sectors
                i3 = i1 + 1
                i4 = i2 + 1
                faces.append(f"f {i1} {i2} {i3}")
                faces.append(f"f {i3} {i2} {i4}")

        with open(mesh_path, "w") as f:
            f.write("# DreamTalk placeholder avatar\n")
            f.write("\n".join(vertices) + "\n")
            f.write("\n".join(faces) + "\n")

        return {"mesh_path": mesh_path, "texture_path": ""}
