"""Give the rendered talking head eyes that blink.

Measured on a 4 second render before this existed: eye motion 0.000, eye
aperture range 0.000, zero blinks, 65.2% of every frame bit-identical to the
source photograph. A person blinks 15-20 times a minute and never holds
perfectly still. A photograph with a moving mouth is what "it doesn't look
real" was pointing at, and no amount of mouth work reaches it.

LivePortrait can retarget the eyes of a still portrait, which is exactly a
blink, and it is already vendored here with its weights. It returned a
saturated blob until two transcription faults were repaired - a headpose
offset of -1 where it should be -97.5, and a SPADE block missing its
normalization - so this could not have been built before now.

The approach is deliberately narrow. Blink frames are synthesised ONCE per
render, not per frame: the lid positions do not depend on what the mouth is
doing, so a handful of closure levels can be generated and reused. Each is
composited back into the MuseTalk frame through an eye-region mask, leaving
the mouth the lip-sync engine produced untouched. Cost is a few forward passes
per render rather than one per frame.
"""
from __future__ import annotations

import logging
import math
import os
import random
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Human blink statistics, used to place them rather than to fake a number.
# 15-20 per minute in conversation; a blink closes and reopens in about 150ms,
# which at 25fps is 4 frames.
BLINKS_PER_MINUTE = 17.0
BLINK_FRAMES = 4
# Closure levels to synthesise. More is smoother and costs one forward pass
# each; four covers a blink's shape without visible stepping.
LEVELS = (0.75, 0.45, 0.15, 0.0)


def enabled() -> bool:
    return os.environ.get("AVATAR_BLINK_ENABLED", "true").lower() not in {
        "0", "false", "no", "off",
    }


def blink_schedule(n_frames: int, fps: float, seed: int = 0) -> dict[int, float]:
    """Frame index -> eye-open ratio, for a natural-looking blink pattern.

    Blinks are placed at irregular intervals around the human average rather
    than on a fixed period, because a perfectly periodic blink reads as a
    machine just as clearly as no blink at all.
    """
    rng = random.Random(seed)
    schedule: dict[int, float] = {}
    mean_gap = fps * 60.0 / BLINKS_PER_MINUTE
    t = rng.uniform(0.25, 0.75) * mean_gap
    while t < n_frames:
        start = int(t)
        # Closing then opening, and not symmetric: a real blink shuts faster
        # than it reopens.
        shape = [0.45, 0.0, 0.0, 0.35, 0.7]
        for offset, openness in enumerate(shape):
            f = start + offset
            if 0 <= f < n_frames:
                schedule[f] = min(schedule.get(f, 1.0), openness)
        t += mean_gap * rng.uniform(0.6, 1.5)
    return schedule


class BlinkRenderer:
    """Synthesises closed-eye variants of one portrait and composites them."""

    def __init__(self, source_bgr: np.ndarray, force_cpu: bool = False):
        self.source = source_bgr
        self._variants: dict[float, np.ndarray] = {}
        self._mask: Optional[np.ndarray] = None
        self._ready = False
        try:
            self._prepare(force_cpu)
            self._ready = True
        except Exception as exc:
            logger.warning("blink unavailable (%s); the render will not blink",
                           exc)

    def _prepare(self, force_cpu: bool) -> None:
        import torch
        from dreamtalk.face.core.animation.liveportrait.config.crop_config import CropConfig
        from dreamtalk.face.core.animation.liveportrait.config.inference_config import InferenceConfig
        from dreamtalk.face.core.animation.liveportrait.live_portrait_wrapper import LivePortraitWrapper
        from dreamtalk.face.core.animation.liveportrait.utils.cropper import Cropper

        crop_cfg = CropConfig(flag_force_cpu=force_cpu)
        crop = Cropper(crop_cfg).crop_source_image(
            cv2.cvtColor(self.source, cv2.COLOR_BGR2RGB), crop_cfg)
        if crop is None:
            raise ValueError("no face in the source portrait")
        self._crop = crop

        model = LivePortraitWrapper(InferenceConfig(
            flag_force_cpu=force_cpu, flag_use_half_precision=False))
        with torch.inference_mode():
            image = model.prepare_source(crop["img_crop_256x256"])
            info = model.get_kp_info(image)
            kp = model.transform_keypoint(info)
            features = model.extract_feature_3d(image)
            # The open-eyed pass is the reference, not the source photograph.
            # Compositing a generated frame against a photographic one puts a
            # seam at the mask edge, because the generator's rendition of the
            # skin differs slightly everywhere. Both sides being generated
            # means the only difference inside the mask is the eyelids.
            self._variants[1.0] = self._decode(model, features, kp, kp)
            for level in LEVELS:
                ratio = model.calc_combined_eye_ratio(
                    np.array([[level]], np.float32), crop["lmk_crop"])
                driving = kp + model.retarget_eye(kp, ratio)
                self._variants[level] = self._decode(model, features, kp, driving)
        self._mask = self._eye_mask(crop)

    @staticmethod
    def _decode(model, features, kp_source, kp_driving) -> np.ndarray:
        out = model.parse_output(
            model.warp_decode(features, kp_source, kp_driving)["out"])[0]
        return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)

    def _eye_mask(self, crop) -> np.ndarray:
        """Soft mask over both eyes, in the generated crop's coordinates."""
        variant = self._variants[1.0]
        h, w = variant.shape[:2]
        lmk = np.asarray(crop["lmk_crop_256x256"], np.float32) * (w / 256.0)
        # Landmarks 33..41 and 87..95 are the eye contours in this 203-point
        # layout; fall back to a face-relative box if the count differs.
        mask = np.zeros((h, w), np.float32)
        try:
            for a, b in ((33, 42), (87, 96)):
                pts = lmk[a:b]
                cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
                rx = max(6.0, (pts[:, 0].max() - pts[:, 0].min()) * 1.5)
                ry = max(6.0, (pts[:, 1].max() - pts[:, 1].min()) * 2.6)
                cv2.ellipse(mask, (int(cx), int(cy)), (int(rx), int(ry)),
                            0, 0, 360, 1.0, -1)
            if mask.max() <= 0:
                raise ValueError("empty eye mask")
        except Exception:
            cv2.ellipse(mask, (w // 2, int(h * 0.38)),
                        (int(w * 0.34), int(h * 0.11)), 0, 0, 360, 1.0, -1)
        return cv2.GaussianBlur(mask, (0, 0), sigmaX=max(2.0, w * 0.012))

    @property
    def ready(self) -> bool:
        return self._ready

    def apply(self, frame_bgr: np.ndarray, openness: float) -> np.ndarray:
        """Composite the eyes at `openness` into one rendered frame."""
        if not self._ready or openness >= 0.999:
            return frame_bgr
        level = min(self._variants, key=lambda v: abs(v - openness))
        variant = self._variants[level]
        neutral = self._variants[1.0]

        m2o = np.asarray(self._crop["M_c2o"], np.float32)
        h, w = frame_bgr.shape[:2]
        # Only the DIFFERENCE between the closed and open generated frames is
        # warped back and added. Pasting the generated crop itself would
        # replace photographic skin with the generator's version of it across
        # the whole eye region; the difference carries the eyelids and nothing
        # else.
        delta = variant.astype(np.float32) - neutral.astype(np.float32)
        masked = delta * self._mask[..., None]
        warped = cv2.warpAffine(masked, m2o[:2], (w, h),
                                flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return np.clip(frame_bgr.astype(np.float32) + warped, 0, 255).astype(np.uint8)
