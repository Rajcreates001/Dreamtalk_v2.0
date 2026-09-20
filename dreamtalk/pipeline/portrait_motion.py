"""Let the head move, while the background stays where it is.

After the mouth and the eyes were fixed, a rendered clip still measured brow
motion 0.000 and forehead motion 0.005. That is not a still person - a person
sitting still still moves. It is a photograph with two animated regions cut
into it, and it is the last of the three things that made the render read as
a picture rather than a person.

## Why the head and not the frame

Nudging the whole frame is the easy version and it is wrong: the background
travels with the head, which reads as a shaking camera rather than a moving
person, and it destroys the one property the QA harness uses to detect a
broken warp, that background motion is zero.

So the displacement is rigid about the face centre and then multiplied by a
mask that is one over the head and falls to zero before the frame edge. The
neck deforms slightly rather than shearing, which at these amplitudes - a few
pixels on a 260 px face - is what a real neck does anyway.

## Why it runs after the mouth and the eyes

MuseTalk pastes its generated mouth at fixed coordinates, and the blink
composites its lid patches at fixed coordinates too. Both are computed
against the still photograph. Moving the head first would leave them behind;
moving it last carries them with it, so the mouth and the lids travel with
the face they belong to.

## Why the resampling filter and the sharpen are not incidental

Moving the head means resampling it, and resampling softens. Measured against
the photograph over the head mask, the first version cost 21% of its detail on
average and 33% on the worst frame - the whole head, hair and beard included,
not just the part that moved. That is a bad trade for 1.3 px of sway, and it
is what "the beard looks mushy" was pointing at.

INTER_LANCZOS4 recovers most of it, 89% against 79%. Supersampling was tried
and is worse, not better - 58% - because upscaling and downscaling adds two
resampling steps in place of one. The remaining 11% is restored by a small
unsharp mask, with its amount set by measurement rather than taste: 0.25 takes
the head to 124% of the photograph's detail and 0.0 leaves it at 89%, so 0.08
lands on 100%. Sharpening past the source is how a render starts to look
crunchy, so the target is the photograph, not more than it.

## The motion itself

Real head movement during speech is not periodic, and a sine wave reads as a
bobblehead within a second. The signal is a sum of three incommensurate
frequencies per axis with random phase, which does not repeat over a clip of
any reasonable length, low-pass by construction, and cheap.
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

# Amplitudes as a fraction of face width, so a bigger render moves further in
# pixels and the same amount in the viewer's eye.
SWAY_X = 0.010
SWAY_Y = 0.007
ROLL_DEGREES = 0.55
# Frequencies in Hz. Deliberately not harmonically related, so the sum does
# not repeat; conversational head motion sits around 0.2-1.2 Hz.
FREQUENCIES = (0.23, 0.41, 0.83)
# Chosen by measuring detail against the photograph; see the note above.
SHARPEN_AMOUNT = float(os.environ.get("AVATAR_HEAD_SHARPEN", "0.08"))
SHARPEN_RADIUS = 0.8


def enabled() -> bool:
    return os.environ.get("AVATAR_HEAD_MOTION", "true").lower() not in {
        "0", "false", "no", "off",
    }


def motion_schedule(n_frames: int, fps: float,
                    seed: int = 0) -> list[tuple[float, float, float]]:
    """Per frame (dx, dy, roll degrees), in face-width units for dx and dy."""
    rng = random.Random(seed)
    phases = [[rng.uniform(0, 2 * math.pi) for _ in FREQUENCIES]
              for _ in range(3)]
    weights = [[rng.uniform(0.6, 1.0) for _ in FREQUENCIES] for _ in range(3)]
    out = []
    for i in range(max(0, n_frames)):
        t = i / max(fps, 1e-6)

        def channel(k):
            total = sum(w * math.sin(2 * math.pi * f * t + p)
                        for f, p, w in zip(FREQUENCIES, phases[k], weights[k]))
            return total / sum(weights[k])

        out.append((SWAY_X * channel(0), SWAY_Y * channel(1),
                    ROLL_DEGREES * channel(2)))
    return out


class HeadMotion:
    """Precomputes a head mask, then warps the head per frame."""

    def __init__(self, frame_bgr: np.ndarray, force_cpu: bool = False) -> None:
        self._ready = False
        try:
            self._build(frame_bgr, force_cpu)
        except Exception as exc:
            # Never fatal. A still head is the previous behaviour.
            logger.warning("head motion unavailable (%s); the head will be still",
                           exc)

    @property
    def ready(self) -> bool:
        return self._ready

    def _build(self, frame_bgr: np.ndarray, force_cpu: bool) -> None:
        from dreamtalk.face.core.animation.liveportrait.config.crop_config import (
            CropConfig,
        )
        from dreamtalk.face.core.animation.liveportrait.utils.cropper import Cropper

        cfg = CropConfig(flag_force_cpu=force_cpu)
        crop = Cropper(cfg).crop_source_image(
            cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB), cfg)
        if crop is None:
            raise ValueError("no face found for head motion")
        matrix = np.asarray(crop["M_c2o"], np.float32)[:2]
        points = np.asarray(crop["lmk_crop_256x256"], np.float32) * 2.0
        lmk = (matrix @ np.hstack(
            [points, np.ones((len(points), 1), np.float32)]).T).T

        height, width = frame_bgr.shape[:2]
        self._face_w = float(lmk[:, 0].ptp())
        cx = float(lmk[:, 0].mean())
        cy = float(lmk[:, 1].mean())
        self._centre = (cx, cy)

        # An ellipse over the head. The landmarks stop at the brow, so the
        # upper radius is stretched to take in hair and skull; without that
        # the hairline is a stationary edge with a moving forehead under it.
        rx = self._face_w * 0.95
        ry = float(lmk[:, 1].ptp()) * 1.30
        mask = np.zeros((height, width), np.float32)
        cv2.ellipse(mask, (int(cx), int(cy - ry * 0.12)),
                    (int(rx), int(ry)), 0, 0, 360, 1.0, -1)
        # A wide falloff, so the neck and shoulders trail off rather than
        # shearing against a static torso.
        blur = max(3.0, self._face_w * 0.22)
        self._mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=blur)

        ys, xs = np.nonzero(self._mask > 0.004)
        if not len(ys):
            raise ValueError("head mask came out empty")
        self._y0, self._y1 = int(ys.min()), int(ys.max()) + 1
        self._x0, self._x1 = int(xs.min()), int(xs.max()) + 1
        gy, gx = np.mgrid[self._y0:self._y1, self._x0:self._x1]
        self._gx = gx.astype(np.float32)
        self._gy = gy.astype(np.float32)
        self._sub = self._mask[self._y0:self._y1, self._x0:self._x1]
        logger.info("head motion over a %dx%d region of a %dx%d frame, "
                    "face %.0f px", self._x1 - self._x0, self._y1 - self._y0,
                    width, height, self._face_w)
        self._ready = True

    def apply(self, frame_bgr: np.ndarray,
              params: tuple[float, float, float]) -> np.ndarray:
        """Move the head by (dx, dy, roll). Units of dx/dy are face widths."""
        if not self._ready:
            return frame_bgr
        dx, dy, roll = params
        tx = dx * self._face_w
        ty = dy * self._face_w
        if abs(tx) < 0.01 and abs(ty) < 0.01 and abs(roll) < 0.005:
            return frame_bgr

        cx, cy = self._centre
        theta = math.radians(roll)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        rel_x = self._gx - cx
        rel_y = self._gy - cy
        # Where each pixel came from: the inverse of a small rigid move is the
        # opposite move, which at these amplitudes is exact enough that the
        # error is far below a pixel.
        src_x = cx + (rel_x - tx) * cos_t + (rel_y - ty) * sin_t
        src_y = cy - (rel_x - tx) * sin_t + (rel_y - ty) * cos_t
        map_x = self._gx + (src_x - self._gx) * self._sub
        map_y = self._gy + (src_y - self._gy) * self._sub

        region = frame_bgr[self._y0:self._y1, self._x0:self._x1]
        warped = cv2.remap(region, (map_x - self._x0).astype(np.float32),
                           (map_y - self._y0).astype(np.float32),
                           cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        if SHARPEN_AMOUNT > 0:
            blurred = cv2.GaussianBlur(warped, (0, 0), SHARPEN_RADIUS)
            warped = cv2.addWeighted(warped, 1.0 + SHARPEN_AMOUNT,
                                     blurred, -SHARPEN_AMOUNT, 0)
        out = frame_bgr.copy()
        out[self._y0:self._y1, self._x0:self._x1] = warped
        return out


def for_frame(frame_bgr: np.ndarray,
              force_cpu: bool = False) -> Optional["HeadMotion"]:
    if not enabled():
        return None
    motion = HeadMotion(frame_bgr, force_cpu=force_cpu)
    return motion if motion.ready else None
