# Dreamtalk - Face Engine
# Extracted from LivePortrait
from dataclasses import dataclass
from .base_config import PrintableConfig, make_abs_path
from .inference_config import _resolve_weights


@dataclass(repr=False)
class CropConfig(PrintableConfig):
    insightface_root: str = make_abs_path("../../pretrained_weights/insightface")
    landmark_ckpt_path: str = _resolve_weights("weights/liveportrait/landmark.onnx")
    xpose_config_file_path: str = make_abs_path("../utils/dependencies/XPose/config_model/UniPose_SwinT.py")
    xpose_embedding_cache_path: str = make_abs_path('../utils/resources/clip_embedding')
    xpose_ckpt_path: str = make_abs_path("../../pretrained_weights/liveportrait_animals/xpose.pth")
    device_id: int = 0
    flag_force_cpu: bool = False
    det_thresh: float = 0.1
    dsize: int = 512
    scale: float = 2.3
    vx_ratio: float = 0
    vy_ratio: float = -0.125
    max_face_num: int = 0
    flag_do_rot: bool = True
    animal_face_type: str = "animal_face_9"
    scale_crop_driving_video: float = 2.2
    vx_ratio_crop_driving_video: float = 0.0
    vy_ratio_crop_driving_video: float = -0.1
    direction: str = "large-small"
