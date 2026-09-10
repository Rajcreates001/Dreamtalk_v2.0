# Dreamtalk - Face Engine
# Extracted from LivePortrait
import torch
import os.path as osp
import numpy as np
import cv2

from .live_portrait_wrapper import LivePortraitWrapper
from .config.inference_config import InferenceConfig
from .config.crop_config import CropConfig
from .config.argument_config import ArgumentConfig


class LivePortraitAPI:
    def __init__(self, inference_cfg: InferenceConfig = None, crop_cfg: CropConfig = None):
        self.inference_cfg = inference_cfg or InferenceConfig()
        self.crop_cfg = crop_cfg or CropConfig()
        self.wrapper = LivePortraitWrapper(inference_cfg=self.inference_cfg)
        self._loaded = True

    @classmethod
    def from_args(cls, args: ArgumentConfig):
        inference_cfg = InferenceConfig(**{k: v for k, v in args.__dict__.items() if hasattr(InferenceConfig, k)})
        crop_cfg = CropConfig(**{k: v for k, v in args.__dict__.items() if hasattr(CropConfig, k)})
        return cls(inference_cfg=inference_cfg, crop_cfg=crop_cfg)

    def prepare_source(self, img: np.ndarray) -> torch.Tensor:
        return self.wrapper.prepare_source(img)

    def get_kp_info(self, x: torch.Tensor) -> dict:
        return self.wrapper.get_kp_info(x)

    def extract_feature_3d(self, x: torch.Tensor) -> torch.Tensor:
        return self.wrapper.extract_feature_3d(x)

    def transform_keypoint(self, kp_info: dict) -> torch.Tensor:
        return self.wrapper.transform_keypoint(kp_info)

    def warp_decode(self, feature_3d, kp_source, kp_driving):
        return self.wrapper.warp_decode(feature_3d, kp_source, kp_driving)

    def stitching(self, kp_source, kp_driving):
        return self.wrapper.stitching(kp_source, kp_driving)

    def retarget_eye(self, kp_source, eye_close_ratio):
        return self.wrapper.retarget_eye(kp_source, eye_close_ratio)

    def retarget_lip(self, kp_source, lip_close_ratio):
        return self.wrapper.retarget_lip(kp_source, lip_close_ratio)

    def parse_output(self, out: torch.Tensor) -> np.ndarray:
        return self.wrapper.parse_output(out)
