# Dreamtalk - 3D Avatar Module
# Extracted from FLAME-Avatar-Driver
# MIT License - Copyright (c) 2025

from dataclasses import dataclass
from typing import Optional
from pathlib import Path


def _resolve_weight(path: str) -> str:
    """Resolve weight path relative to project root."""
    p = Path(__file__).resolve().parent.parent.parent.parent.parent
    return str(p / path)


@dataclass
class FlameConfig:
    """Configuration for FLAME avatar driver."""

    # Model paths — resolved to project weights/
    flame_model_path: str = _resolve_weight("weights/flame/FLAME2020.pkl")
    mappings_path: str = _resolve_weight("weights/flame/mappings")

    # MediaPipe face landmarker
    landmarker_model_path: str = "face_landmarker.task"

    # Video input
    video_path: Optional[str] = None
    use_webcam: bool = False
    fps: int = 30

    # Expression amplification
    expression_amplification: float = 2.0

    # Manual mapping fallback multipliers
    manual_jaw_mult: float = 8.0
    manual_smile_mult: float = 6.0
    manual_brow_mult: float = 5.0
    manual_blink_mult: float = 8.0
    manual_funnel_mult: float = 6.0
    manual_pucker_mult: float = 6.0

    # FLAME model params
    num_flame_expression_params: int = 100
    num_mediapipe_blendshapes: int = 52

    # Expression basis range in shapedirs
    expression_start_idx: int = 300
    expression_end_idx: int = 400

    # Visualization
    use_visualizer: bool = True
    camera_position: tuple = (0.0, 0.0, 1.2)
    camera_focus: tuple = (0.0, 0.0, 0.0)
    camera_up: tuple = (0.0, 1.0, 0.0)
    mesh_color: str = "cyan"

    # Head rotation correction
    invert_yaw: bool = True
    base_rotation_z_deg: float = 180.0
    base_rotation_x_deg: float = -35.0
