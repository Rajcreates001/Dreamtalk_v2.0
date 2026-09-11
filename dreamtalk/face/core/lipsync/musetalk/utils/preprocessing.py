"""Face crop preprocessing for MuseTalk using bundled MediaPipe Tasks.

The upstream helper expected mmpose, DWPose weights, and a top-level
``face_detection`` package. DreamTalk already ships MediaPipe's 478-point face
landmarker, so this module uses that single validated dependency instead.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from tqdm import tqdm

logger = logging.getLogger("dreamtalk.face.musetalk.preprocessing")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
LANDMARK_MODEL = PROJECT_ROOT / "weights" / "face" / "face_landmarker.task"
coord_placeholder = (0.0, 0.0, 0.0, 0.0)
_landmarker = None


def _get_landmarker():
    global _landmarker
    if _landmarker is not None:
        return _landmarker
    if not LANDMARK_MODEL.exists():
        raise FileNotFoundError(f"MediaPipe face landmarker not found: {LANDMARK_MODEL}")
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(LANDMARK_MODEL)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.4,
        min_face_presence_confidence=0.4,
        min_tracking_confidence=0.4,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    _landmarker = vision.FaceLandmarker.create_from_options(options)
    return _landmarker


def read_imgs(img_list):
    frames = []
    for image_path in tqdm(img_list, desc="MuseTalk frames"):
        frame = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError(f"Cannot decode MuseTalk frame: {image_path}")
        frames.append(frame)
    return frames


def _detect_landmarks(frame: np.ndarray) -> Optional[np.ndarray]:
    import mediapipe as mp

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = _get_landmarker().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not result.face_landmarks:
        return None
    height, width = frame.shape[:2]
    return np.asarray(
        [(point.x * width, point.y * height) for point in result.face_landmarks[0]],
        dtype=np.float32,
    )


def _landmarks_to_crop(
    landmarks: np.ndarray,
    frame_shape: tuple[int, ...],
    upperbondrange: int = 0,
) -> tuple[int, int, int, int]:
    height, width = frame_shape[:2]
    x1, y1 = np.min(landmarks, axis=0)
    x2, y2 = np.max(landmarks, axis=0)
    face_w = max(1.0, x2 - x1)
    face_h = max(1.0, y2 - y1)
    x1 -= face_w * 0.10
    x2 += face_w * 0.10
    y1 -= face_h * 0.12
    y2 += face_h * 0.13
    y1 += int(upperbondrange)
    x1 = int(np.clip(x1, 0, width - 2))
    y1 = int(np.clip(y1, 0, height - 2))
    x2 = int(np.clip(x2, x1 + 2, width))
    y2 = int(np.clip(y2, y1 + 2, height))
    return x1, y1, x2, y2


def get_landmark_and_bbox(img_list, upperbondrange=0):
    frames = read_imgs(img_list)
    coordinates = []
    for frame in tqdm(frames, desc="MuseTalk landmarks"):
        landmarks = _detect_landmarks(frame)
        if landmarks is None:
            logger.warning("MediaPipe did not find a face in one MuseTalk frame")
            coordinates.append(coord_placeholder)
        else:
            coordinates.append(_landmarks_to_crop(landmarks, frame.shape, upperbondrange))
    return coordinates, frames


def get_bbox_range(img_list, upperbondrange=0):
    coordinates, _ = get_landmark_and_bbox(img_list, upperbondrange)
    valid = [item for item in coordinates if item != coord_placeholder]
    return (
        f"Total frames: {len(coordinates)}; detected faces: {len(valid)}; "
        f"current bbox shift: {upperbondrange}"
    )
