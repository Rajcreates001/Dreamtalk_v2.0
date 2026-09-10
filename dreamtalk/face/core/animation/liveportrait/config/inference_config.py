# Dreamtalk - Face Engine
# Extracted from LivePortrait
import cv2
from numpy import ndarray
import pickle as pkl
from dataclasses import dataclass, field
from typing import Literal, Tuple
from .base_config import PrintableConfig, make_abs_path


def load_lip_array():
    with open(make_abs_path('../utils/resources/lip_array.pkl'), 'rb') as f:
        return pkl.load(f)


def _resolve_weights(path: str) -> str:
    """Resolve weight path relative to project root, targeting weights/liveportrait/."""
    import os
    # From inference_config.py: config/ → liveportrait/ → animation/ → core/ → face/ → dreamtalk/ → root (7 levels)
    p = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    return str(p / path)


from pathlib import Path


@dataclass(repr=False)
class InferenceConfig(PrintableConfig):
    models_config: str = make_abs_path('./models.yaml')
    checkpoint_F: str = _resolve_weights("weights/liveportrait/appearance_feature_extractor.pth")
    checkpoint_M: str = _resolve_weights("weights/liveportrait/motion_extractor.pth")
    checkpoint_G: str = _resolve_weights("weights/liveportrait/spade_generator.pth")
    checkpoint_W: str = _resolve_weights("weights/liveportrait/warping_module.pth")
    checkpoint_S: str = _resolve_weights("weights/liveportrait/landmark.onnx")

    version_animals = "_v1.1"
    checkpoint_F_animal: str = make_abs_path(f'../../pretrained_weights/liveportrait_animals/base_models{version_animals}/appearance_feature_extractor.pth')
    checkpoint_M_animal: str = make_abs_path(f'../../pretrained_weights/liveportrait_animals/base_models{version_animals}/motion_extractor.pth')
    checkpoint_G_animal: str = make_abs_path(f'../../pretrained_weights/liveportrait_animals/base_models{version_animals}/spade_generator.pth')
    checkpoint_W_animal: str = make_abs_path(f'../../pretrained_weights/liveportrait_animals/base_models{version_animals}/warping_module.pth')
    checkpoint_S_animal: str = make_abs_path('../../pretrained_weights/liveportrait/retargeting_models/stitching_retargeting_module.pth')

    flag_use_half_precision: bool = True
    flag_crop_driving_video: bool = False
    device_id: int = 0
    flag_normalize_lip: bool = True
    flag_source_video_eye_retargeting: bool = False
    flag_eye_retargeting: bool = False
    flag_lip_retargeting: bool = False
    flag_stitching: bool = True
    flag_relative_motion: bool = True
    flag_pasteback: bool = True
    flag_do_crop: bool = True
    flag_do_rot: bool = True
    flag_force_cpu: bool = False
    flag_do_torch_compile: bool = False
    driving_option: str = "pose-friendly"
    driving_multiplier: float = 1.0
    driving_smooth_observation_variance: float = 3e-7
    source_max_dim: int = 1280
    source_division: int = 2
    animation_region: Literal["exp", "pose", "lip", "eyes", "all"] = "all"

    lip_normalize_threshold: float = 0.03
    source_video_eye_retargeting_threshold: float = 0.18
    anchor_frame: int = 0

    input_shape: Tuple[int, int] = (256, 256)
    output_format: Literal['mp4', 'gif'] = 'mp4'
    crf: int = 15
    output_fps: int = 25

    mask_crop: ndarray = field(default_factory=lambda: cv2.imread(make_abs_path('../utils/resources/mask_template.png'), cv2.IMREAD_COLOR))
    lip_array: ndarray = field(default_factory=load_lip_array)
    size_gif: int = 256
