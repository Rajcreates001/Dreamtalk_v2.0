"""Make the requested emotion change the picture.

Until now it did not. In the MuseTalk path `emotion` travelled from the API
straight into the response metadata and nowhere else - `api.generate` is never
given it - so a render requested as "happy" was pixel-for-pixel the render
requested as "neutral", and the response said `"emotion": "happy"` about it.
Only the audio-reactive fallback, which runs when MuseTalk is unavailable,
ever consulted it.

## What moves

The brows, and only the brows. The mouth belongs to MuseTalk: it is
regenerated from the audio every frame, so warping it would fight the lip
sync rather than add to it. The brows are in the region MuseTalk leaves
alone, they carry most of what separates these expressions on a real face,
and they can be moved by resampling skin that already exists.

## Why there is no squint

Narrowing the eye was tried, reusing the blink's lid warp at a fraction of
full closure, and removed. The muscle is wrong: a warm expression raises the
LOWER lid and crinkles the outer corner, while that warp lowers the UPPER
lid, which is what a tired face does. Swept on this subject, 0.16 and above
reads as half-shut, and 0.10 - the most that still looks awake - moves the
iris measurement by 0.6 grey levels, which is nothing. There is no setting
where it both looks right and does anything, so "happy" would only have
become "sleepy". Raising the lower lid would need its own geometry, not this
one turned down.

Each brow is selected by the eye it sits above rather than by landmark group
index. The groups do not split cleanly - 144:160 is the left brow plus a
stray point out at the temple, and 160:176 is the right brow plus five points
lying along the left brow's lower edge - so indexing them directly would drag
the temple into the warp.

## Why it is applied to the source

A static expression for the clip is what the emotion parameter means, so it
is baked into the fitted source once, before MuseTalk sees it, instead of
being recomputed per frame. Everything downstream - the generated mouth, the
composited lids, the head motion - then inherits it for free.
"""
from __future__ import annotations

import logging
import os

import cv2
import numpy as np

logger = logging.getLogger(__name__)

BROW_GROUP = (144, 176)
EYE_GROUPS = {"left": (0, 24), "right": (24, 48)}

# Brow shift as a fraction of the brow-to-eye distance; positive is up.
# Tilt is the extra shift given to the INNER end, which is what separates
# sadness from anger - both lower the brow, but sadness lifts its inner end
# and anger drives it down and in.
EXPRESSIONS: dict[str, dict[str, float]] = {
    "neutral": {"lift": 0.00, "tilt": 0.00},
    "calm": {"lift": 0.04, "tilt": 0.05},
    "happy": {"lift": 0.16, "tilt": 0.00},
    "excited": {"lift": 0.28, "tilt": 0.00},
    "surprised": {"lift": 0.42, "tilt": 0.00},
    "fearful": {"lift": 0.30, "tilt": 0.22},
    "sad": {"lift": -0.10, "tilt": 0.30},
    "loving": {"lift": 0.10, "tilt": 0.10},
    # Capped, not chosen freely. A brow driven lower than this darkens the
    # band of skin the blink stretches over the iris, and the blink's own
    # guard then refuses to build - so the strongest angry face shipped with
    # no blink at all. Swept against that guard: -0.20 fails, -0.15 holds.
    "angry": {"lift": -0.15, "tilt": -0.18},
    "serious": {"lift": -0.12, "tilt": -0.10},
}


def enabled() -> bool:
    return os.environ.get("AVATAR_EXPRESSION", "true").lower() not in {
        "0", "false", "no", "off",
    }


def _landmarks(image: np.ndarray, force_cpu: bool = False) -> np.ndarray:
    from dreamtalk.face.core.animation.liveportrait.config.crop_config import (
        CropConfig,
    )
    from dreamtalk.face.core.animation.liveportrait.utils.cropper import Cropper

    cfg = CropConfig(flag_force_cpu=force_cpu)
    crop = Cropper(cfg).crop_source_image(
        cv2.cvtColor(image, cv2.COLOR_BGR2RGB), cfg)
    if crop is None:
        raise ValueError("no face found for the expression landmarks")
    matrix = np.asarray(crop["M_c2o"], np.float32)[:2]
    points = np.asarray(crop["lmk_crop_256x256"], np.float32) * 2.0
    return (matrix @ np.hstack(
        [points, np.ones((len(points), 1), np.float32)]).T).T


def _brow_for_eye(lmk: np.ndarray, eye: np.ndarray) -> np.ndarray:
    """The brow arc sitting above one eye."""
    brow = lmk[BROW_GROUP[0]:BROW_GROUP[1]]
    width = eye[:, 0].ptp()
    keep = ((brow[:, 0] >= eye[:, 0].min() - width * 0.15)
            & (brow[:, 0] <= eye[:, 0].max() + width * 0.15)
            & (brow[:, 1] < eye[:, 1].min()))
    return brow[keep]


def _shift_brow(image: np.ndarray, brow: np.ndarray, eye: np.ndarray,
                lift: float, tilt: float, inner_is_right: bool) -> np.ndarray:
    """Move one brow up or down, with the inner end optionally moved further.

    The displacement tapers to zero towards the forehead above and towards the
    eyelid below, so the brow travels through skin instead of cutting a band
    out of it.
    """
    if len(brow) < 4:
        return image
    height, width = image.shape[:2]
    gap = float(eye[:, 1].min() - brow[:, 1].mean())
    if gap <= 1.0:
        return image
    shift = lift * gap
    if abs(shift) < 0.15 and abs(tilt * gap) < 0.15:
        return image

    x0, x1 = float(brow[:, 0].min()), float(brow[:, 0].max())
    span_up = gap * 1.9
    # How far the warp reaches toward the eyelid. A brow moving DOWN pushes
    # its own darkness ahead of it, and at 0.75 of the way to the lash line
    # that darkness lands in the band of skin the blink later stretches over
    # the iris - which is why an angry face measured -58.5 grey levels of
    # "closure", i.e. brow hair dragged across an eye, and shipped with the
    # blink disabled by the guard. A lifted brow pulls away from the eye and
    # has no such problem, so only the downward case is shortened.
    span_down = gap * (0.75 if lift >= 0 else 0.34)
    pad = (x1 - x0) * 0.28

    # Displacement runs from `shift` at the outer end to `shift + tilt * gap`
    # at the inner one, so those two are its extremes along the brow. They
    # size both the region and the plateau, so neither clips the moved brow.
    ends = (shift, shift + tilt * gap)
    travel_up = max(0.0, max(ends))
    travel_down = max(0.0, -min(ends))
    ya = int(max(0, np.floor(brow[:, 1].min() - span_up - travel_up)))
    yb = int(min(height - 1,
                 np.ceil(brow[:, 1].max() + span_down + travel_down)))
    xa = int(max(0, np.floor(x0 - pad)))
    xb = int(min(width - 1, np.ceil(x1 + pad)))
    if yb <= ya or xb <= xa:
        return image

    mx, my = np.meshgrid(np.arange(xa, xb + 1, dtype=np.float32),
                         np.arange(ya, yb + 1, dtype=np.float32))
    # Vertical profile: a plateau over the brow's own thickness, tapering only
    # in the skin above and below it. A triangular profile peaking at the brow
    # line moves the middle of the brow further than its edges, which stretches
    # the hair instead of translating it - visible as a smear at the larger
    # lifts. The plateau is extended along the direction of travel so the
    # destination of the brow is inside it too.
    brow_top = float(brow[:, 1].min()) - travel_up
    brow_bot = float(brow[:, 1].max()) + travel_down
    above = np.clip((my - (brow_top - span_up)) / max(span_up, 1e-3), 0, 1)
    below = np.clip(((brow_bot + span_down) - my) / max(span_down, 1e-3), 0, 1)
    wy = np.minimum(above, below)
    # Horizontal taper so the warp dies out before the temple and the bridge.
    wx = (np.clip((mx - (x0 - pad)) / max(pad, 1.0), 0, 1)
          * np.clip(((x1 + pad) - mx) / max(pad, 1.0), 0, 1))

    # Inner end of the brow, in normalised x across the arc.
    across = np.clip((mx - x0) / max(x1 - x0, 1e-3), 0, 1)
    inner = across if inner_is_right else (1.0 - across)
    total = shift + tilt * gap * inner

    source_y = my + total * wy * wx
    warped = cv2.remap(image[ya:yb + 1, xa:xb + 1],
                       (mx - xa).astype(np.float32),
                       (source_y - ya).astype(np.float32),
                       cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    out = image.copy()
    out[ya:yb + 1, xa:xb + 1] = warped
    return out


def apply_expression(image: np.ndarray, emotion: str,
                     force_cpu: bool = False) -> tuple[np.ndarray, dict]:
    """Return the image with `emotion` applied, and what was measured.

    Never raises: an unrecognised emotion, or a face the landmarker cannot
    read, returns the image untouched. A render with a neutral face is the
    previous behaviour and better than no render.
    """
    report = {"emotion": emotion, "applied": False, "brow_shift_px": 0.0}
    if not enabled():
        return image, report
    params = EXPRESSIONS.get((emotion or "neutral").strip().lower())
    if params is None:
        logger.info("no expression defined for %r; leaving the face neutral",
                    emotion)
        return image, report
    if abs(params["lift"]) < 1e-6 and abs(params["tilt"]) < 1e-6:
        return image, report
    try:
        lmk = _landmarks(image, force_cpu)
    except Exception as exc:
        logger.warning("expression skipped (%s); the face stays neutral", exc)
        return image, report

    out = image
    shifts = []
    centre_x = float(lmk[:, 0].mean())
    for name, (a, b) in EYE_GROUPS.items():
        eye = lmk[a:b]
        brow = _brow_for_eye(lmk, eye)
        if len(brow) < 4:
            logger.info("expression: only %d brow points above the %s eye; "
                        "leaving it alone", len(brow), name)
            continue
        gap = float(eye[:, 1].min() - brow[:, 1].mean())
        # "Inner" is the end nearest the middle of the face.
        inner_is_right = float(brow[:, 0].mean()) < centre_x
        out = _shift_brow(out, brow, eye, params["lift"], params["tilt"],
                          inner_is_right)
        shifts.append(abs(params["lift"]) * gap)

    if shifts:
        report["applied"] = True
        report["brow_shift_px"] = round(float(np.mean(shifts)), 2)
        logger.info("expression %s: brows moved %.1f px (lift %.2f tilt %.2f)",
                    emotion, report["brow_shift_px"], params["lift"],
                    params["tilt"])
    return out, report
