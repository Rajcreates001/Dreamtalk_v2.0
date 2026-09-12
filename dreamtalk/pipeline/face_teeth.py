"""
DreamTalk — teeth and tongue for the FLAME head.

FLAME models skin only: it has a `lips` region but nothing behind it, so every
jaw-opening viseme (`aa`, `oh`, `surprised`) reveals an empty void where the
mouth should be. That is the single largest realism cost on the generated head.

This builds a simple upper/lower dental arch and a tongue, sized and placed
from the fitted face's own lip region, plus matching morph targets so the lower
arch and tongue travel with the jaw instead of hanging in mid-air.

Deliberately simple: at conversational framing the mouth interior is small and
partly shadowed, so a smooth arch with per-tooth relief reads correctly. Modelling
individual roots would cost geometry nobody sees.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger("dreamtalk.face_teeth")

# Shades: enamel is not pure white, and reading as white is a classic tell.
ENAMEL_RGB = (0.90, 0.88, 0.84)
TONGUE_RGB = (0.62, 0.32, 0.33)


def _arch_points(centre: np.ndarray, half_width: float, depth: float,
                 frame, n: int) -> np.ndarray:
    """Points along a parabolic dental arch, widest at the front."""
    t = np.linspace(-1.0, 1.0, n)
    pts = np.repeat(centre[None, :], n, axis=0)
    pts[:, frame.side] += t * half_width
    # Parabola receding at the corners — a real arch is not a straight line.
    pts[:, frame.fwd] += (depth * (1.0 - t ** 2)) * frame.fwd_sign
    return pts


def _ribbon(front: np.ndarray, back: np.ndarray, top: np.ndarray,
            bottom: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Build a closed quad strip between four parallel point rows."""
    rows = [front, top, back, bottom]
    n = len(front)
    verts = np.concatenate(rows, axis=0)
    faces = []
    for r in range(len(rows)):
        a, b = r * n, ((r + 1) % len(rows)) * n
        for i in range(n - 1):
            faces.append([a + i, b + i, b + i + 1])
            faces.append([a + i, b + i + 1, a + i + 1])
    return verts.astype(np.float32), np.asarray(faces, dtype=np.uint32)


def build_teeth(
    vertices: np.ndarray,
    masks: Dict[str, np.ndarray],
    frame,
    n_teeth: int = 12,
) -> Optional[Dict[str, object]]:
    """Build teeth + tongue sized from this face's lip region.

    Args:
        vertices: (N,3) fitted head vertices, at export scale.
        masks:    FLAME_masks.pkl contents.
        frame:    a `face_blendshapes._Frame` (detected up/fwd/side axes).

    Returns dict with `parts`: each {name, vertices, faces, color, jaw_follow}.
    `jaw_follow` is how much of the jaw's motion that part inherits (0 = fixed
    to the skull, 1 = moves fully with the jaw).
    """
    lips = masks.get("lips")
    if lips is None or len(lips) == 0:
        logger.warning("No lips region — cannot place teeth")
        return None
    lips = np.asarray(lips, dtype=np.int64)
    v = np.asarray(vertices, dtype=np.float32)
    up, fwd, side = frame.up, frame.fwd, frame.side

    lip_v = v[lips]
    centre = lip_v.mean(axis=0)
    half_w = float(np.abs(lip_v[:, side] - centre[side]).max()) * 0.72
    lip_span = float(lip_v[:, up].max() - lip_v[:, up].min())
    H = frame.height

    # Sit the arches just inside the lip line and behind it.
    inset = 0.35 * lip_span
    back = 0.55 * H * 0.06
    tooth_h = max(0.006 * H, 0.30 * lip_span)
    depth = 0.012 * H

    def shift(base, d_up=0.0, d_fwd=0.0):
        p = base.copy()
        p[:, up] += d_up * frame.up_sign
        p[:, fwd] += d_fwd * frame.fwd_sign
        return p

    parts = []
    for name, sign, follow in (("teeth_upper", +1.0, 0.0), ("teeth_lower", -1.0, 1.0)):
        gum = centre.copy()
        gum[up] += sign * inset * frame.up_sign
        gum[fwd] -= back * frame.fwd_sign
        arch = _arch_points(gum, half_w, depth, frame, n_teeth * 2 + 1)

        # Scalloped biting edge gives per-tooth relief without real geometry.
        edge = shift(arch, d_up=-sign * tooth_h)
        scallop = (np.arange(len(arch)) % 2) * (tooth_h * 0.18)
        edge[:, up] += sign * scallop * frame.up_sign

        verts, faces = _ribbon(
            front=arch,
            back=shift(arch, d_fwd=-0.9 * depth),
            top=edge,
            bottom=shift(edge, d_fwd=-0.9 * depth),
        )
        parts.append({
            "name": name, "vertices": verts, "faces": faces,
            "color": ENAMEL_RGB, "jaw_follow": follow,
        })

    # Tongue: a low dome on the floor of the mouth, mostly hidden but its
    # absence reads as a hole at wide openings.
    tongue_c = centre.copy()
    tongue_c[up] -= (inset + tooth_h * 0.6) * frame.up_sign
    tongue_c[fwd] -= (back + depth * 0.4) * frame.fwd_sign
    t_arch = _arch_points(tongue_c, half_w * 0.78, depth * 0.8, frame, n_teeth + 1)
    verts, faces = _ribbon(
        front=t_arch,
        back=shift(t_arch, d_fwd=-1.6 * depth),
        top=shift(t_arch, d_up=tooth_h * 0.35),
        bottom=shift(t_arch, d_up=-tooth_h * 0.25),
    )
    parts.append({
        "name": "tongue", "vertices": verts, "faces": faces,
        "color": TONGUE_RGB, "jaw_follow": 0.7,
    })

    total = sum(len(p["vertices"]) for p in parts)
    logger.info("Built mouth interior: %d parts, %d verts", len(parts), total)
    return {"parts": parts}


def teeth_morph_targets(
    part: Dict[str, object],
    head_targets: Dict[str, np.ndarray],
    head_vertices: np.ndarray,
    masks: Dict[str, np.ndarray],
    frame,
) -> Dict[str, np.ndarray]:
    """Morph targets that keep a mouth part with the jaw.

    For each head blendshape we measure how far the lower lip travels, then
    translate this part by that much scaled by its `jaw_follow`. Without this
    the jaw opens and the teeth stay put, which looks worse than no teeth.
    """
    lips = np.asarray(masks.get("lips", []), dtype=np.int64)
    if lips.size == 0:
        return {}
    follow = float(part.get("jaw_follow", 0.0))
    n = len(part["vertices"])
    out: Dict[str, np.ndarray] = {}

    # Lower lip = the lip vertices below the lip centre.
    lip_up = head_vertices[lips][:, frame.up] * frame.up_sign
    lower = lips[lip_up < np.median(lip_up)]

    for name, delta in head_targets.items():
        d = np.asarray(delta, dtype=np.float32)
        move = d[lower].mean(axis=0) * follow if lower.size else np.zeros(3, np.float32)
        if float(np.abs(move).max()) < 1e-7:
            out[name] = np.zeros((n, 3), dtype=np.float32)
        else:
            out[name] = np.repeat(move[None, :], n, axis=0).astype(np.float32)
    return out
