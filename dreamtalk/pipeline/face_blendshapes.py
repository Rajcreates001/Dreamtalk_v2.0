"""
DreamTalk — FLAME face blendshapes (morph targets)

Builds the animation blendshapes for a fitted FLAME head so a browser can
animate the user's *own* reconstructed face — visemes for lip-sync, a blink,
and emotion overlays — without any server-side re-rendering.

Why geometric rather than learned: the repo ships a `bs2exp` matrix, but its
row count (50) does not match the ARKit name list (52), so the row semantics
are ambiguous. The FLAME region masks (`FLAME_masks.pkl`) are unambiguous, so
we deform the named regions directly. Every shape is calibrated as a fraction
of head height, which keeps amplitudes sane for any fitted identity.

Usage:
    targets = build_blendshapes(vertices, masks)   # {name: (N,3) delta}
    # -> feed to AvatarExporter.obj_to_glb(morph_targets=targets)
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger("dreamtalk.face_blendshapes")

# Viseme set matches the VRM/standard mouth shapes the frontend drives.
VISEMES = ("aa", "ih", "ou", "ee", "oh")
EMOTIONS = ("happy", "sad", "angry", "surprised")
ALL_SHAPES = VISEMES + ("blink",) + EMOTIONS

# Peak displacement per shape, as a fraction of total head height.
AMPLITUDE = {
    "aa": 0.055, "ih": 0.022, "ou": 0.030, "ee": 0.026, "oh": 0.045,
    "blink": 0.030, "happy": 0.026, "sad": 0.020,
    "angry": 0.018, "surprised": 0.048,
}


class _Frame:
    """Canonical axes of the FLAME mesh, detected from the region masks."""

    def __init__(self, v: np.ndarray, masks: Dict[str, np.ndarray]):
        def centre(name: str) -> Optional[np.ndarray]:
            idx = masks.get(name)
            return v[np.asarray(idx, dtype=np.int64)].mean(axis=0) if idx is not None and len(idx) else None

        forehead, neck, nose = centre("forehead"), centre("neck"), centre("nose")
        overall = v.mean(axis=0)

        # Up = axis separating forehead from neck.
        if forehead is not None and neck is not None:
            self.up = int(np.argmax(np.abs(forehead - neck)))
            self.up_sign = 1.0 if forehead[self.up] > neck[self.up] else -1.0
        else:
            self.up, self.up_sign = 1, 1.0

        # Forward = axis where the nose protrudes most (excluding up).
        if nose is not None:
            d = np.abs(nose - overall)
            d[self.up] = -1.0
            self.fwd = int(np.argmax(d))
            self.fwd_sign = 1.0 if nose[self.fwd] > overall[self.fwd] else -1.0
        else:
            self.fwd = 2 if self.up != 2 else 1
            self.fwd_sign = 1.0

        self.side = ({0, 1, 2} - {self.up, self.fwd}).pop()
        self.height = float(v[:, self.up].max() - v[:, self.up].min())

    def vec(self, up: float = 0.0, fwd: float = 0.0, side: float = 0.0) -> np.ndarray:
        out = np.zeros(3, dtype=np.float32)
        out[self.up] = up * self.up_sign
        out[self.fwd] = fwd * self.fwd_sign
        out[self.side] = side
        return out


def _smooth(x: np.ndarray) -> np.ndarray:
    """Smoothstep on a 0..1 ramp — avoids hard creases at region borders."""
    t = np.clip(x, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _idx(masks: Dict[str, np.ndarray], name: str) -> np.ndarray:
    got = masks.get(name)
    return np.asarray(got, dtype=np.int64) if got is not None else np.zeros(0, dtype=np.int64)


def build_blendshapes(
    vertices: np.ndarray,
    masks: Dict[str, np.ndarray],
    shapes: Optional[tuple] = None,
) -> Dict[str, np.ndarray]:
    """Build morph-target deltas for a fitted FLAME head.

    Args:
        vertices: (N,3) base (neutral) vertex positions, already scaled the
            same way as the exported OBJ.
        masks: FLAME_masks.pkl contents (region name -> vertex indices).
        shapes: subset of ALL_SHAPES to build (default: all).

    Returns:
        ``{shape_name: (N,3) float32 delta}`` — add to base * weight.
    """
    v = np.asarray(vertices, dtype=np.float32)
    n = len(v)
    if n == 0:
        return {}

    F = _Frame(v, masks)
    up, fwd, side = F.up, F.fwd, F.side
    H = F.height or 1.0

    lips = _idx(masks, "lips")
    face = _idx(masks, "face")
    l_eye = _idx(masks, "left_eye_region")
    r_eye = _idx(masks, "right_eye_region")
    eyes = np.unique(np.concatenate([l_eye, r_eye])) if len(l_eye) or len(r_eye) else _idx(masks, "eye_region")
    forehead = _idx(masks, "forehead")
    eyeballs = np.unique(np.concatenate([_idx(masks, "left_eyeball"), _idx(masks, "right_eyeball")]))

    if len(lips) == 0:
        logger.warning("FLAME masks have no lips region — cannot build mouth shapes")
        return {}

    mouth_c = v[lips].mean(axis=0)
    # Movable head shell: exclude eyeballs (they are separate spheres) so we
    # never tear them out of their sockets.
    movable = np.ones(n, dtype=bool)
    movable[eyeballs] = False

    shell = face if len(face) else np.arange(n)
    chin_u = float(v[shell, up].min() if F.up_sign > 0 else v[shell, up].max())
    jaw_span = max(1e-6, abs(mouth_c[up] - chin_u))

    # Jaw weight: 0 above the mouth, ramping to 1 at the chin.
    below = (mouth_c[up] - v[:, up]) * F.up_sign
    w_jaw = _smooth(below / jaw_span) * movable
    w_lips = np.zeros(n, dtype=np.float32)
    w_lips[lips] = 1.0

    # Lateral position within the mouth, for corner-driven shapes.
    lip_x = np.zeros(n, dtype=np.float32)
    half = max(1e-6, float(np.abs(v[lips, side] - mouth_c[side]).max()))
    lip_x[lips] = (v[lips, side] - mouth_c[side]) / half        # -1..1
    corner = np.abs(lip_x)                                       # 0 centre, 1 corner

    out: Dict[str, np.ndarray] = {}
    want = shapes or ALL_SHAPES

    def emit(name: str, delta: np.ndarray) -> None:
        peak = float(np.abs(delta).max())
        if peak < 1e-9:
            logger.warning("blendshape %s is degenerate — skipped", name)
            return
        delta = delta * (AMPLITUDE.get(name, 0.03) * H / peak)   # calibrate
        out[name] = delta.astype(np.float32)

    def jaw_drop(weight: float) -> np.ndarray:
        """Open the jaw: lower face swings down and slightly back."""
        d = np.zeros((n, 3), dtype=np.float32)
        w = (w_jaw * weight)[:, None]
        d += w * F.vec(up=-1.0, fwd=-0.18)
        d[lips] += (w_lips[lips] * weight * 0.35)[:, None] * F.vec(up=-1.0)
        return d

    def lip_round(weight: float) -> np.ndarray:
        """Purse the lips: corners pull inward, lips push forward."""
        d = np.zeros((n, 3), dtype=np.float32)
        d[lips, side] -= (v[lips, side] - mouth_c[side]) * 0.55 * weight
        d[lips] += (weight * (1.0 - corner[lips] * 0.4))[:, None] * F.vec(fwd=0.9)
        return d

    def lip_spread(weight: float) -> np.ndarray:
        """Spread the lips wide (ee/ih), corners pull outward and slightly up."""
        d = np.zeros((n, 3), dtype=np.float32)
        d[lips, side] += (v[lips, side] - mouth_c[side]) * 0.42 * weight
        d[lips] += (corner[lips] * weight * 0.3)[:, None] * F.vec(up=1.0)
        return d

    def smile(weight: float) -> np.ndarray:
        """Mouth corners lift and widen; cheeks follow slightly."""
        d = np.zeros((n, 3), dtype=np.float32)
        c = (corner[lips] ** 1.5) * weight
        d[lips] += c[:, None] * F.vec(up=1.0, fwd=0.12)
        d[lips, side] += np.sign(lip_x[lips]) * c * 0.5
        return d

    def frown(weight: float) -> np.ndarray:
        d = np.zeros((n, 3), dtype=np.float32)
        c = (corner[lips] ** 1.5) * weight
        d[lips] += c[:, None] * F.vec(up=-1.0)
        return d

    def eyelid_close(weight: float) -> np.ndarray:
        """Upper lids sweep down over the eye."""
        d = np.zeros((n, 3), dtype=np.float32)
        for region in (l_eye, r_eye) if len(l_eye) and len(r_eye) else (eyes,):
            if len(region) == 0:
                continue
            c = v[region].mean(axis=0)
            rel = (v[region, up] - c[up]) * F.up_sign
            lid = max(1e-6, float(rel.max()))
            w = _smooth(rel / lid) * weight            # only the upper lid
            d[region] += w[:, None] * F.vec(up=-1.0)
        return d

    def brow(weight: float, direction: float, inner: bool) -> np.ndarray:
        """Raise/lower the brow ridge (forehead lower edge)."""
        d = np.zeros((n, 3), dtype=np.float32)
        if len(forehead) == 0:
            return d
        c = v[forehead].mean(axis=0)
        rel = (c[up] - v[forehead, up]) * F.up_sign
        span = max(1e-6, float(np.abs(rel).max()))
        w = _smooth(rel / span)                        # lower forehead = brow
        if inner:
            lat = np.abs(v[forehead, side] - c[side])
            w = w * _smooth(1.0 - lat / max(1e-6, float(lat.max())))
        d[forehead] += (w * weight)[:, None] * F.vec(up=direction)
        return d

    def eyes_wide(weight: float) -> np.ndarray:
        return -eyelid_close(weight) * 0.6

    builders = {
        "aa": lambda: jaw_drop(1.0) + lip_spread(0.15),
        "ih": lambda: jaw_drop(0.3) + lip_spread(0.55),
        "ee": lambda: jaw_drop(0.18) + lip_spread(1.0),
        "ou": lambda: jaw_drop(0.22) + lip_round(1.0),
        "oh": lambda: jaw_drop(0.75) + lip_round(0.55),
        "blink": lambda: eyelid_close(1.0),
        "happy": lambda: smile(1.0) + jaw_drop(0.10),
        "sad": lambda: frown(1.0) + brow(0.6, +1.0, inner=True),
        "angry": lambda: brow(1.0, -1.0, inner=False) + frown(0.3),
        "surprised": lambda: jaw_drop(0.6) + eyes_wide(1.0) + brow(0.8, +1.0, inner=False),
    }

    for name in want:
        fn = builders.get(name)
        if fn is None:
            continue
        try:
            emit(name, fn())
        except Exception as exc:                        # one bad shape must not kill the export
            logger.warning("blendshape %s failed: %s", name, exc)

    logger.info("Built %d FLAME blendshapes: %s", len(out), ", ".join(out))
    return out


def load_flame_masks(path: str) -> Dict[str, np.ndarray]:
    """Load FLAME_masks.pkl (latin1 — it was pickled under Python 2)."""
    import pickle

    with open(path, "rb") as fh:
        raw = pickle.load(fh, encoding="latin1")
    return {k: np.asarray(v, dtype=np.int64) for k, v in raw.items()}
