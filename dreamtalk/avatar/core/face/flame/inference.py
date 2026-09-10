# Dreamtalk - 3D Avatar Module
# Extracted from FLAME-Avatar-Driver
# MIT License - Copyright (c) 2025
#
# Inference utilities: MediaPipe face tracking, head rotation, mesh export

import cv2
import numpy as np
from typing import Optional, Callable, List


def get_head_rotation_from_landmarks(landmarks) -> tuple:
    """Extract yaw and pitch from MediaPipe face landmarks.

    Uses nose (idx 1) and eye centers (idx 33, 263).

    Args:
        landmarks: MediaPipe face_landmarks list

    Returns:
        (yaw, pitch) in radians
    """
    nose = np.array([landmarks[1].x, landmarks[1].y, landmarks[1].z])
    left_eye = np.array([landmarks[33].x, landmarks[33].y, landmarks[33].z])
    right_eye = np.array([landmarks[263].x, landmarks[263].y, landmarks[263].z])
    eye_center = (left_eye + right_eye) / 2
    forward = nose - eye_center
    yaw = np.arctan2(forward[0], forward[2])
    pitch = np.arctan2(forward[1], forward[2])
    return yaw, pitch


def build_head_rotation_matrix(yaw: float, pitch: float,
                                invert_yaw: bool = True,
                                base_z_deg: float = 180.0,
                                base_x_deg: float = -35.0) -> np.ndarray:
    """Build combined rotation matrix for head pose.

    Applies: base_Z @ base_X @ yaw @ pitch

    Args:
        yaw: Yaw angle in radians
        pitch: Pitch angle in radians
        invert_yaw: Whether to negate yaw (FLAME coordinate system)
        base_z_deg: Z-axis base rotation in degrees
        base_x_deg: X-axis base rotation in degrees

    Returns:
        (3, 3) combined rotation matrix (for applying on right side: V @ R.T)
    """
    if invert_yaw:
        yaw = -yaw

    R_pitch = np.array([
        [1, 0, 0],
        [0, np.cos(pitch), -np.sin(pitch)],
        [0, np.sin(pitch), np.cos(pitch)],
    ])
    R_yaw = np.array([
        [np.cos(yaw), 0, np.sin(yaw)],
        [0, 1, 0],
        [-np.sin(yaw), 0, np.cos(yaw)],
    ])
    R_z = np.array([
        [np.cos(np.radians(base_z_deg)), -np.sin(np.radians(base_z_deg)), 0],
        [np.sin(np.radians(base_z_deg)), np.cos(np.radians(base_z_deg)), 0],
        [0, 0, 1],
    ])
    R_x = np.array([
        [1, 0, 0],
        [0, np.cos(np.radians(base_x_deg)), -np.sin(np.radians(base_x_deg))],
        [0, np.sin(np.radians(base_x_deg)), np.cos(np.radians(base_x_deg))],
    ])
    return R_z @ R_x @ R_yaw @ R_pitch


def setup_mediapipe_face_detector(model_path: str):
    """Create MediaPipe FaceLandmarker with blendshape output.

    Args:
        model_path: Path to face_landmarker.task model

    Returns:
        FaceLandmarker instance
    """
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        running_mode=vision.RunningMode.VIDEO,
    )
    return vision.FaceLandmarker.create_from_options(options)


def process_video_frames(
    video_path: str,
    frame_callback: Callable,
    max_frames: Optional[int] = None,
) -> None:
    """Process video frames with a callback.

    Args:
        video_path: Path to video file
        frame_callback: Callable(frame_bgr, frame_idx, timestamp_ms) -> bool
                        Return False to stop processing
        max_frames: Maximum number of frames to process
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if max_frames and frame_count >= max_frames:
                break

            timestamp = int(1000 * frame_count / fps) if fps > 0 else frame_count
            should_continue = frame_callback(frame, frame_count, timestamp)
            frame_count += 1

            if not should_continue:
                break
    finally:
        cap.release()


def format_active_expressions(expression: np.ndarray, threshold: float = 0.1) -> list:
    """Get list of (index, value) pairs for active expression coefficients.

    Args:
        expression: (100,) expression array
        threshold: Minimum absolute value to consider active

    Returns:
        List of (index, value) tuples sorted by absolute value descending
    """
    active = [(i, v) for i, v in enumerate(expression) if abs(v) > threshold]
    active.sort(key=lambda x: abs(x[1]), reverse=True)
    return active
