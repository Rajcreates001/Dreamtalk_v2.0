# Dreamtalk - Face Engine
# Extracted from LivePortrait
from dataclasses import dataclass
from typing import Optional, Literal
from .base_config import PrintableConfig, make_abs_path


@dataclass(repr=False)
class ArgumentConfig(PrintableConfig):
    source: str = make_abs_path('../../assets/examples/source/s0.jpg')
    driving: str = make_abs_path('../../assets/examples/driving/d0.mp4')
    output_dir: str = 'animations/'

    flag_use_half_precision: bool = True
    flag_crop_driving_video: bool = False
    device_id: int = 0
    flag_force_cpu: bool = False
    flag_normalize_lip: bool = False
    flag_source_video_eye_retargeting: bool = False
    flag_eye_retargeting: bool = False
    flag_lip_retargeting: bool = False
    flag_stitching: bool = True
    flag_relative_motion: bool = True
    flag_pasteback: bool = True
    flag_do_crop: bool = True
    driving_option: Literal["expression-friendly", "pose-friendly"] = "expression-friendly"
    driving_multiplier: float = 1.0
    driving_smooth_observation_variance: float = 3e-7
    audio_priority: Literal['source', 'driving'] = 'driving'
    animation_region: Literal["exp", "pose", "lip", "eyes", "all"] = "all"

    det_thresh: float = 0.15
    scale: float = 2.3
    vx_ratio: float = 0
    vy_ratio: float = -0.125
    flag_do_rot: bool = True
    source_max_dim: int = 1280
    source_division: int = 2

    scale_crop_driving_video: float = 2.2
    vx_ratio_crop_driving_video: float = 0.
    vy_ratio_crop_driving_video: float = -0.1

    server_port: int = 8890
    share: bool = False
    server_name: Optional[str] = "127.0.0.1"
    flag_do_torch_compile: bool = False
    gradio_temp_dir: Optional[str] = None
