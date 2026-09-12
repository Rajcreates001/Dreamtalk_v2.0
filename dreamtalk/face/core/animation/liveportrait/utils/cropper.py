"""Human-face cropping and landmark tracking for LivePortrait.

Uses the bundled 203-point ONNX landmark model, seeded by a local OpenCV face
detector, and preserves affine transforms required for paste-back.
"""

from __future__ import annotations

import cv2
import numpy as np

from .crop import crop_image
from .human_landmark_runner import LandmarkRunner


class Cropper:
    def __init__(self, crop_cfg):
        self.crop_cfg = crop_cfg
        providers = set()
        try:
            import onnxruntime
            providers = set(onnxruntime.get_available_providers())
        except Exception:
            pass
        provider = "cuda" if "CUDAExecutionProvider" in providers and not crop_cfg.flag_force_cpu else "cpu"
        self.landmark_runner = LandmarkRunner(
            ckpt_path=crop_cfg.landmark_ckpt_path,
            onnx_provider=provider,
            device_id=crop_cfg.device_id,
        )
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_detector = cv2.CascadeClassifier(cascade_path)

    def update_config(self, user_args):
        for key, value in user_args.items():
            if hasattr(self.crop_cfg, key):
                setattr(self.crop_cfg, key, value)

    def _seed_landmarks(self, img_rgb):
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        faces = self.face_detector.detectMultiScale(
            gray, scaleFactor=1.08, minNeighbors=5, minSize=(64, 64)
        ) if not self.face_detector.empty() else []
        if len(faces) == 0:
            return None
        x, y, width, height = max(faces, key=lambda item: item[2] * item[3])
        return np.array([
            [x + 0.32 * width, y + 0.40 * height],
            [x + 0.68 * width, y + 0.40 * height],
            [x + 0.50 * width, y + 0.57 * height],
            [x + 0.38 * width, y + 0.73 * height],
            [x + 0.62 * width, y + 0.73 * height],
        ], dtype=np.float32)

    def _landmarks(self, img_rgb, previous=None):
        seed = previous if previous is not None else self._seed_landmarks(img_rgb)
        return None if seed is None else self.landmark_runner.run(img_rgb, seed)

    @staticmethod
    def _crop(img_rgb, landmarks, *, dsize, scale, vx_ratio, vy_ratio, flag_do_rot):
        result = crop_image(
            img_rgb, landmarks, dsize=dsize, scale=scale,
            vx_ratio=vx_ratio, vy_ratio=vy_ratio, flag_do_rot=flag_do_rot,
        )
        result["img_crop_256x256"] = cv2.resize(
            result["img_crop"], (256, 256), interpolation=cv2.INTER_AREA
        )
        result["lmk_crop"] = result["pt_crop"]
        result["lmk_crop_256x256"] = result["pt_crop"] * (256.0 / dsize)
        return result

    def crop_source_image(self, img_rgb, crop_cfg):
        landmarks = self._landmarks(img_rgb)
        if landmarks is None:
            return None
        return self._crop(
            img_rgb, landmarks, dsize=crop_cfg.dsize, scale=crop_cfg.scale,
            vx_ratio=crop_cfg.vx_ratio, vy_ratio=crop_cfg.vy_ratio,
            flag_do_rot=crop_cfg.flag_do_rot,
        )

    def crop_source_video(self, rgb_lst, crop_cfg, **_kwargs):
        frames, landmarks_list, transforms = [], [], []
        previous = None
        for img_rgb in rgb_lst:
            landmarks = self._landmarks(img_rgb, previous)
            if landmarks is None:
                continue
            previous = landmarks
            result = self._crop(
                img_rgb, landmarks, dsize=crop_cfg.dsize, scale=crop_cfg.scale,
                vx_ratio=crop_cfg.vx_ratio, vy_ratio=crop_cfg.vy_ratio,
                flag_do_rot=crop_cfg.flag_do_rot,
            )
            frames.append(result["img_crop_256x256"])
            landmarks_list.append(result["lmk_crop_256x256"])
            transforms.append(result["M_c2o"])
        return {"frame_crop_lst": frames, "lmk_crop_lst": landmarks_list, "M_c2o_lst": transforms}

    def crop_driving_video(self, rgb_lst, **_kwargs):
        frames, landmarks_list = [], []
        previous = None
        config = self.crop_cfg
        for img_rgb in rgb_lst:
            landmarks = self._landmarks(img_rgb, previous)
            if landmarks is None:
                continue
            previous = landmarks
            result = self._crop(
                img_rgb, landmarks, dsize=config.dsize,
                scale=config.scale_crop_driving_video,
                vx_ratio=config.vx_ratio_crop_driving_video,
                vy_ratio=config.vy_ratio_crop_driving_video, flag_do_rot=False,
            )
            frames.append(result["img_crop"])
            landmarks_list.append(result["lmk_crop"])
        return {"frame_crop_lst": frames, "lmk_crop_lst": landmarks_list}

    def calc_lmk_from_cropped_image(self, img_rgb, **_kwargs):
        return self._landmarks(img_rgb)

    def calc_lmks_from_cropped_video(self, rgb_lst, **_kwargs):
        result, previous = [], None
        for img_rgb in rgb_lst:
            landmarks = self._landmarks(img_rgb, previous)
            if landmarks is None:
                raise RuntimeError("No face detected in a driving-video frame")
            result.append(landmarks)
            previous = landmarks
        return result
