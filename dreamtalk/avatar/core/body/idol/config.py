# Dreamtalk - 3D Avatar Module
# Extracted from IDOL

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IDOLConfig:
    """Configuration for IDOL single-image 3D reconstruction pipeline."""

    # Model paths
    encoder_model_path: str = "work_dirs/ckpt/sapiens_1b_epoch_173_torchscript.pt2"
    resume_path: str = "work_dirs/ckpt/model.ckpt"
    config_path: str = "configs/idol_v0.yaml"

    # Image processing
    image_size: tuple = (640, 896)
    remove_bg: bool = True
    image_frame_ratio: float = 0.85

    # Camera
    focal_length: float = 600.0
    sensor_width: float = 32.0
    camera_distance: float = 20.0
    render_distance: float = 1.5

    # Rendering
    render_mode: str = "novel_pose"  # novel_pose, reconstruct, novel_pose_A
    render_image_size: tuple = (512, 512)
    num_frames: int = 60
    batch_size: int = 5

    # SMPL-X parameters
    num_betas: int = 10
    smpl_params_dim: int = 189
    use_hands_zero_offset: bool = True
    hands_offset_clamp: float = 0.02

    # Gender
    gender: str = "neutral"

    # Performance
    encoder_dtype: str = "bfloat16"
    use_uniform_coordinates: bool = True
    use_video_cam: bool = False

    # Output
    output_path: str = "outputs/"
    seed: int = 42

    # Cache directories
    cache_dir: str = "work_dirs/cache"
