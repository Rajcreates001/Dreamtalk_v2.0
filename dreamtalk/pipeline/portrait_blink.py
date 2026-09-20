"""Give the rendered talking head eyes that blink.

Measured on a 4 second render before this existed: eye motion 0.000, eye
aperture range 0.000, zero blinks, 65.3% of every frame bit-identical to the
source photograph. A person blinks 15-20 times a minute and never holds
perfectly still. A photograph with a moving mouth is what "it doesn't look
real" was pointing at, and no amount of mouth work reaches it.

## Why this is a warp and not a generative model

The previous version drove the photograph with LivePortrait, using the
expression delta between the subject's own FLAME head rendered with its blink
morph target open and shut. It produced numbers that looked like a blink and
an image that was not one. Rendered in LivePortrait's own crop space, the
"closed" eye keeps its iris fully visible and gains Laplacian detail, 148.6 ->
172.6 - the signature of displacement, not closure.

That failure is structural rather than a tuning problem. LivePortrait warps
the pixels of the source photograph; it cannot paint pixels that are not
there. A closed eyelid is skin where the iris was, the photograph has no such
skin at that location, and so the warp drags neighbouring pixels across and
smears. No gain, mask or driving signal fixes that.

So the lid is built from the one place the necessary skin actually exists:
the subject's own upper lid. The band of skin above the lash line is
stretched downward until the lash line lands below the lower lid, occluding
the aperture. Everything in the result is resampled from the photograph, so
the closed eye carries the subject's real lid crease and real lashes.

## Why it happens at the photograph's resolution

The render frame is sized so the face arrives at MuseTalk's working scale,
which leaves the eye aperture about eight pixels tall. Warping eight pixels
of skin produces a smudge whatever the geometry says. The photograph behind
it is 1832 px wide, with an aperture near nineteen.

Nothing requires the warp to happen after the downscale. It is applied to the
photograph and the result is resampled into the frame, so the frame gets an
eight pixel lid computed from nineteen pixels of real skin while the mouth
keeps the scale MuseTalk wants. Measured on the iris footprint: warping in
the frame moved the left eye -15.3 grey levels, i.e. darker, which is a smear;
warping at full resolution moved it +38.0, which is skin over an iris.

## How closure is measured

Four metrics reported a shut eye on a picture plainly showing an iris - box
brightness, sclera fraction, socket dynamic range, and lid Laplacian, the
last of which actively penalised the variant that worked, because a closed
lid is smooth skin where an open eye has a catchlight.

What they had in common is that none was ever shown a closed eye and an open
one and asked to tell them apart. The metric here is validated before use: it
has to rank the full-resolution warp above the in-frame warp on the left eye,
an ordering that is visible by eye. It locates the iris in the open
photograph - the darkest connected blob inside the socket - and asks how much
brighter that exact footprint becomes. A smear dragged across a generous box
does not move it, because the footprint is the iris and not a box around it.

## Why the geometry is calibrated per eye

The landmark ring sits inside the eye, by a different amount on each side,
and a lash line that stops at the landmark lower lid leaves the bottom of the
iris bare. On this subject the left eye closes with a short lid band and the
right, turned further from camera, needs a longer one. Hard-coding either set
shuts one eye and winks with the other, so both are searched at build time
against the validated metric rather than fixed to one face.
"""
from __future__ import annotations

import glob
import logging
import os
import random
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# 15-20 blinks a minute in conversation; a blink closes and reopens in about
# 150ms, which at 25fps is four frames.
BLINKS_PER_MINUTE = 17.0
# Openness levels rendered once and reused. A blink shuts faster than it
# reopens, so the schedule below spends more frames on the way back up.
LEVELS = (0.75, 0.5, 0.25, 0.0)
# Searched per eye at build time; these bound the search, they are not the
# answer. Band is the depth of lid skin drawn on, as a multiple of aperture;
# extra is how far past the landmark lower lid the lash line is driven.
BAND_CANDIDATES = (1.0, 1.4, 1.9, 2.4)
EXTRA_CANDIDATES = (0.8, 1.4, 2.0)
EYE_GROUPS = {"left": (0, 24), "right": (24, 48)}
# Below this the closure is a smear rather than a lid, and shipping a smear is
# what this module exists to stop doing.
MIN_CLOSURE_LEVELS = 8.0


def enabled() -> bool:
    return os.environ.get("AVATAR_BLINK_ENABLED", "true").lower() not in {
        "0", "false", "no", "off",
    }


def blink_schedule(n_frames: int, fps: float, seed: int = 0) -> dict[int, float]:
    """Frame index -> eye-open ratio.

    Irregular on purpose. A perfectly periodic blink reads as a machine just
    as clearly as no blink at all, and the shape is asymmetric because a real
    eye shuts faster than it reopens.
    """
    rng = random.Random(seed)
    schedule: dict[int, float] = {}
    mean_gap = fps * 60.0 / BLINKS_PER_MINUTE
    t = rng.uniform(0.25, 0.75) * mean_gap
    while t < n_frames:
        start = int(t)
        for offset, openness in enumerate([0.5, 0.0, 0.0, 0.25, 0.75]):
            frame = start + offset
            if 0 <= frame < n_frames:
                schedule[frame] = min(schedule.get(frame, 1.0), openness)
        t += mean_gap * rng.uniform(0.6, 1.5)
    return schedule


def _lid_lines(points: np.ndarray):
    """Upper and lower lid y per column, from one eye's landmark ring."""
    x0, x1 = points[:, 0].min(), points[:, 0].max()
    cols = np.arange(int(np.floor(x0)), int(np.ceil(x1)) + 1)
    centre_y = points[:, 1].mean()
    upper, lower = [], []
    for x in cols:
        near = points[np.abs(points[:, 0] - x) <= max(2.0, (x1 - x0) * 0.12)]
        if len(near) == 0:
            near = points
        above = near[near[:, 1] <= centre_y]
        below = near[near[:, 1] > centre_y]
        upper.append(above[:, 1].min() if len(above) else centre_y)
        lower.append(below[:, 1].max() if len(below) else centre_y)
    # Landmark noise column to column renders as a ragged lash line.
    k = max(3, (len(cols) // 6) * 2 + 1)

    def smooth(values):
        return cv2.GaussianBlur(
            np.asarray(values, np.float32).reshape(-1, 1), (1, k), 0).ravel()

    return cols, smooth(upper), smooth(lower)


def _warp_rect(cols, upper, lower, aperture, band_f, extra, shape):
    """The rectangle close_eye touches.

    The compositor needs this, not the eye socket. The lid band reaches well
    above the upper lid and the lash line is driven below the lower one, so
    the warp spans roughly forty pixels at frame scale where the socket spans
    sixteen. Compositing only the socket pastes a slice out of the middle of
    the lid and leaves a dark band with a hard edge, while the calibration -
    which scored the whole warped frame - reported a clean closure. Clipping
    the result to a different region than the one that was measured is how
    those two disagreed.

    Nothing has to be feathered at this boundary: close_eye's own horizontal
    and vertical falloffs reach identity at the edges of this rectangle, so
    the warped image already equals the original there.
    """
    height, width = shape[:2]
    band = aperture * band_f
    x0, x1 = cols[0], cols[-1]
    pad = int(max(4, (x1 - x0) * 0.25))
    y0 = int(max(0, np.floor(upper.min() - band - 2)))
    y1 = int(min(height - 1, np.ceil(lower.max() + aperture * extra + 4)))
    xa = int(max(0, x0 - pad))
    xb = int(min(width - 1, x1 + pad))
    return y0, y1, xa, xb


def close_eye(image: np.ndarray, points: np.ndarray, closure: float,
              band_f: float = 1.4, extra: float = 1.4,
              feather: float = 1.4) -> np.ndarray:
    """Slide the lid down over the eye. closure 0 leaves it open, 1 shuts it.

    The destination band samples only lid skin, so what was behind the lid is
    occluded rather than compressed. An earlier version kept the map
    continuous by sending the aperture into the shrinking gap below the lash
    line, and the iris survived as a squeezed sliver with its catchlight
    intact - closure has to remove the eye, not relocate it.
    """
    if closure <= 0:
        return image
    cols, upper, lower = _lid_lines(points)
    height, width = image.shape[:2]
    aperture = float(np.median(lower - upper))
    if aperture <= 0.5:
        return image
    band = aperture * band_f
    x0, x1 = cols[0], cols[-1]
    pad = int(max(4, (x1 - x0) * 0.25))
    y0, y1, xa, xb = _warp_rect(cols, upper, lower, aperture, band_f, extra,
                                (height, width))
    if y1 <= y0 or xb <= xa:
        return image

    mx, my = np.meshgrid(np.arange(xa, xb + 1, dtype=np.float32),
                         np.arange(y0, y1 + 1, dtype=np.float32))
    index = np.clip(np.arange(xa, xb + 1) - x0, 0, len(cols) - 1)
    upper_row = upper[index][None, :].astype(np.float32)
    lower_row = lower[index][None, :].astype(np.float32)
    # The landmark ring sits inside the eye, so full closure drives the lash
    # line past the landmark lower lid or the bottom of the iris stays bare.
    target = upper_row + (lower_row - upper_row + aperture * extra) * closure
    top = upper_row - band

    source_y = (top + (my - top) * np.maximum(upper_row - top, 1e-3)
                / np.maximum(target - top, 1e-3))
    source_y = np.where((my >= top) & (my <= target), source_y, my)

    # Horizontal falloff so the stretch dies before the box edge, and a
    # vertical one at the top so the brow is not dragged down with the lid.
    fx = (np.clip((mx - (x0 - pad)) / max(pad, 1.0), 0, 1)
          * np.clip(((x1 + pad) - mx) / max(pad, 1.0), 0, 1))
    fy = np.clip((my - top) / max(band * 0.35, 1.0), 0, 1)
    source_y = my + (source_y - my) * np.clip(fx, 0, 1) * np.clip(fy, 0, 1)

    warped = cv2.remap(image[y0:y1 + 1, xa:xb + 1],
                       (mx - xa).astype(np.float32),
                       (source_y - y0).astype(np.float32),
                       cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    # Feather across the lash line: a real closed eye has a dark line there,
    # not a cut. The width scales with the aperture so this behaves the same
    # at the photograph's resolution as at the frame's.
    alpha = np.clip((target - my) / max(feather * (aperture / 6.0), 1e-3),
                    0, 1)[..., None].astype(np.float32)
    patch = image[y0:y1 + 1, xa:xb + 1].astype(np.float32)
    out = image.copy()
    out[y0:y1 + 1, xa:xb + 1] = np.clip(
        warped.astype(np.float32) * alpha + patch * (1.0 - alpha),
        0, 255).astype(np.uint8)
    return out


def _socket_mask(shape, points: np.ndarray, grow: float = 1.45) -> np.ndarray:
    centre = points.mean(axis=0)
    grown = points.copy()
    grown[:, 1] = centre[1] + (points[:, 1] - centre[1]) * grow
    grown[:, 0] = centre[0] + (points[:, 0] - centre[0]) * 1.05
    mask = np.zeros(shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(grown.astype(np.int32)), 1)
    return mask


def _iris_footprint(open_image: np.ndarray, points: np.ndarray) -> np.ndarray:
    """The darkest connected blob inside the socket of the open eye."""
    mask = _socket_mask(open_image.shape, points)
    grey = cv2.cvtColor(open_image, cv2.COLOR_BGR2GRAY)
    inside = grey[mask == 1]
    if inside.size == 0:
        return np.zeros(grey.shape, bool)
    threshold = float(np.percentile(inside, 22))
    dark = ((grey <= threshold) & (mask == 1)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    if count <= 1:
        return dark.astype(bool)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return labels == largest


def _closure_score(open_image, candidate, footprint) -> float:
    """Grey levels the iris footprint gained. Skin over an iris moves this."""
    if not footprint.any():
        return 0.0
    before = cv2.cvtColor(open_image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    after = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(after[footprint].mean() - before[footprint].mean())


def _band_limit(lmk: np.ndarray, eye: np.ndarray) -> float:
    """How deep the lid band may go, in apertures, before it hits the brow."""
    brow = lmk[144:176]
    width = eye[:, 0].ptp()
    keep = ((brow[:, 0] >= eye[:, 0].min() - width * 0.15)
            & (brow[:, 0] <= eye[:, 0].max() + width * 0.15)
            & (brow[:, 1] < eye[:, 1].min()))
    chosen = brow[keep]
    _, upper, lower = _lid_lines(eye)
    aperture = float(np.median(lower - upper))
    if len(chosen) < 4 or aperture <= 0.5:
        return float(max(BAND_CANDIDATES))
    # Stop short of the brow's lower edge rather than touching it.
    gap = float(upper.min() - chosen[:, 1].max()) * 0.85
    return max(0.5, gap / aperture)


class BlinkRenderer:
    """Precomputes each eye at each openness, then composites them per frame."""

    def __init__(self, frame_bgr: np.ndarray, full_bgr: Optional[np.ndarray],
                 force_cpu: bool = False) -> None:
        self._ready = False
        self._patches: dict[float, list[tuple]] = {}
        self._scores: dict[str, float] = {}
        try:
            self._build(frame_bgr, full_bgr, force_cpu)
        except Exception as exc:
            # Never fatal: a render without a blink is the previous behaviour,
            # and that is better than no render.
            logger.warning("blink unavailable (%s); the render will not blink",
                           exc)

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def scores(self) -> dict[str, float]:
        """Grey levels each iris gained at full closure, for the QA harness."""
        return dict(self._scores)

    @staticmethod
    def _landmarks(image: np.ndarray, force_cpu: bool) -> np.ndarray:
        from dreamtalk.face.core.animation.liveportrait.config.crop_config import (
            CropConfig,
        )
        from dreamtalk.face.core.animation.liveportrait.utils.cropper import Cropper

        cfg = CropConfig(flag_force_cpu=force_cpu)
        crop = Cropper(cfg).crop_source_image(
            cv2.cvtColor(image, cv2.COLOR_BGR2RGB), cfg)
        if crop is None:
            raise ValueError("no face found for the blink landmarks")
        matrix = np.asarray(crop["M_c2o"], np.float32)[:2]
        points = np.asarray(crop["lmk_crop_256x256"], np.float32) * 2.0
        homogeneous = np.hstack([points, np.ones((len(points), 1), np.float32)])
        return (matrix @ homogeneous.T).T

    def _build(self, frame_bgr, full_bgr, force_cpu) -> None:
        frame_lmk = self._landmarks(frame_bgr, force_cpu)
        height, width = frame_bgr.shape[:2]

        # Work on the photograph when it is larger than the frame; fall back
        # to the frame itself, which still blinks, just more softly.
        if full_bgr is not None and full_bgr.shape[1] > width:
            work = full_bgr
            work_lmk = self._landmarks(full_bgr, force_cpu)
        else:
            work = frame_bgr
            work_lmk = frame_lmk
        logger.info("blink works at %dx%d for a %dx%d frame",
                    work.shape[1], work.shape[0], width, height)

        def to_frame(image):
            if image.shape[:2] == (height, width):
                return image
            return cv2.resize(image, (width, height),
                              interpolation=cv2.INTER_AREA)

        geometry: dict[str, tuple[float, float]] = {}
        for eye, (a, b) in EYE_GROUPS.items():
            footprint = _iris_footprint(frame_bgr, frame_lmk[a:b])
            # The lid band is the skin BETWEEN the lash line and the brow. On
            # a face whose brows are lowered - an angry expression drops them
            # 10.8 px here - a band sized only as a multiple of the aperture
            # reaches into the eyebrow, and the warp then drags brow hair down
            # over the eye. That darkens the iris instead of covering it: the
            # measured closure was -58.5 levels, the guard refused it, and an
            # angry avatar shipped with no blink at all.
            # Offered as an EXTRA candidate rather than as a ceiling. Capping
            # the list instead was tried and cost four expressions their blink
            # rather than saving one: the brow's lowest point sits far below
            # its arch, so a cap measured from it is much tighter than the lid
            # actually needs. Added to the search, the scoring picks it only
            # where it genuinely scores better.
            limit = _band_limit(work_lmk, work_lmk[a:b])
            bands = sorted({f for f in BAND_CANDIDATES + (limit,) if f >= 0.3})
            best = None
            for band_f in bands:
                for extra in EXTRA_CANDIDATES:
                    candidate = close_eye(work, work_lmk[a:b], 1.0,
                                          band_f, extra)
                    score = _closure_score(frame_bgr, to_frame(candidate),
                                           footprint)
                    if best is None or score > best[0]:
                        best = (score, band_f, extra)
            geometry[eye] = (best[1], best[2])
            if abs(best[1] - limit) < 1e-6:
                logger.info("blink %s eye: the brow-limited band %.2f won the "
                            "search", eye, limit)
            self._scores[eye] = round(best[0], 1)
            logger.info("blink %s eye: band %.1f extra %.1f, iris %+.1f levels",
                        eye, best[1], best[2], best[0])

        if self._scores and min(self._scores.values()) < MIN_CLOSURE_LEVELS:
            raise ValueError(
                "closure too weak to be a lid (%s)"
                % ", ".join("%s %+.1f" % kv for kv in self._scores.items()))

        for openness in LEVELS:
            composed = work.copy()
            for eye, (a, b) in EYE_GROUPS.items():
                band_f, extra = geometry[eye]
                composed = close_eye(composed, work_lmk[a:b], 1.0 - openness,
                                     band_f, extra)
            reduced = to_frame(composed)
            scale = width / float(work.shape[1])
            patches = []
            for eye, (a, b) in EYE_GROUPS.items():
                band_f, extra = geometry[eye]
                cols, upper, lower = _lid_lines(work_lmk[a:b])
                aperture = float(np.median(lower - upper))
                if aperture <= 0.5:
                    continue
                wy0, wy1, wxa, wxb = _warp_rect(cols, upper, lower, aperture,
                                                band_f, extra, work.shape)
                y0 = max(0, int(np.floor(wy0 * scale)))
                y1 = min(height, int(np.ceil(wy1 * scale)) + 1)
                x0 = max(0, int(np.floor(wxa * scale)))
                x1 = min(width, int(np.ceil(wxb * scale)) + 1)
                if y1 <= y0 or x1 <= x0:
                    continue
                patches.append((y0, y1, x0, x1,
                                reduced[y0:y1, x0:x1].astype(np.float32)))
            self._patches[openness] = patches

        self._ready = bool(self._patches)

    def apply(self, frame_bgr: np.ndarray, openness: float) -> np.ndarray:
        """Composite both eyes at `openness` into one rendered frame."""
        if not self._ready or openness >= 0.999:
            return frame_bgr
        level = min(self._patches, key=lambda v: abs(v - openness))
        out = frame_bgr.copy()
        for y0, y1, x0, x1, patch in self._patches[level]:
            out[y0:y1, x0:x1] = np.clip(patch, 0, 255).astype(np.uint8)
        return out


def for_profile(source_bgr: np.ndarray, runtime_dir: str,
                force_cpu: bool = False,
                full_path: Optional[str] = None) -> Optional["BlinkRenderer"]:
    """Build a renderer from a profile directory, or None if it cannot.

    The uploaded photograph is looked up alongside the render because the lid
    is warped at its resolution, not the frame's; without it the blink still
    works, from eight pixels of aperture instead of nineteen.
    """
    if not enabled():
        return None
    full = None
    # An explicit photograph wins: when an expression has been baked in, the
    # uploaded original no longer matches the frame, and lid patches warped
    # from it would paste a neutral brow back over an expressive face.
    if full_path:
        full = cv2.imread(full_path)
        if full is None:
            logger.info("could not read %s; falling back to the upload",
                        full_path)
    for pattern in ("*.jpg", "*.jpeg", "*.png"):
        if full is not None:
            break
        found = sorted(glob.glob(os.path.join(runtime_dir, "appearance",
                                              "source", pattern)))
        if found:
            full = cv2.imread(found[0])
            if full is not None:
                break
    if full is None:
        logger.info("no original photograph under %s; blinking from the frame",
                    runtime_dir)
    renderer = BlinkRenderer(source_bgr, full, force_cpu=force_cpu)
    return renderer if renderer.ready else None
