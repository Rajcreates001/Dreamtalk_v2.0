"""
DreamTalk — hair volume for the FLAME head.

FLAME models a skull, not hair. Its `scalp` region hugs the cranium, so a
subject's hair only ever exists as pixels painted flat onto that surface:
the silhouette follows the bone, the crown reads as cut off, and curly or
voluminous hair looks shaved. Reported from a render as "the hairs and all
is not proper and the head shape only is not properly defined".

This builds a shell over the scalp, offset outward along the surface
normals, sized from the subject's OWN hair as segmented in their photo
rather than from a constant. Measured on one subject with BiSeNet:

    hair pixels          28.0% of the face crop   (skin 14.9%)
    hair reaches         195px above the topmost skin pixel, of 512
    hair width / face    1.35
    hair height / face   1.05

so the shell has to add real height above the crown and real width at the
sides, and those two numbers differ — a uniform inflation gets the
silhouette wrong in one axis or the other.

Deliberately a shell and not strands: at conversational framing the
silhouette and the parting carry almost all the perceived realism, and
strand geometry costs a great deal for detail nobody sees. This does not
claim to be modelled hair. It gives the head its volume back.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger("dreamtalk.face_hair")

# Fallback proportions when no photo segmentation is available. Chosen to be
# conservative: too little volume reads as short hair, too much reads as a
# helmet, and the former is the safer error.
DEFAULT_WIDTH_RATIO = 1.18
DEFAULT_TOP_RATIO = 0.22


def _vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals."""
    normals = np.zeros_like(vertices, dtype=np.float64)
    tri = vertices[faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    for i in range(3):
        np.add.at(normals, faces[:, i], fn)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(lengths, 1e-9)


def hair_metrics_from_parsing(parsing: np.ndarray, hair_label: int,
                              skin_label: int) -> Optional[Dict[str, float]]:
    """Measure hair extent against the face, from a BiSeNet parse.

    Returns ratios rather than pixels so they transfer to mesh units:
      width_ratio  hair bounding width  / skin bounding width
      top_ratio    how far hair rises above the topmost skin pixel,
                   as a fraction of the skin region's height
    """
    hair = parsing == hair_label
    skin = parsing == skin_label
    if not hair.any() or not skin.any():
        return None
    hy, hx = np.where(hair)
    sy, sx = np.where(skin)
    skin_h = max(1, int(sy.max() - sy.min()))
    skin_w = max(1, int(sx.max() - sx.min()))
    return {
        "width_ratio": float((hx.max() - hx.min()) / skin_w),
        "top_ratio": float(max(0, sy.min() - hy.min()) / skin_h),
        "hair_fraction": float(hair.mean()),
    }


def build_hair(
    vertices: np.ndarray,
    faces: np.ndarray,
    masks: Dict[str, np.ndarray],
    frame,
    metrics: Optional[Dict[str, float]] = None,
    colour: Tuple[float, float, float] = (0.07, 0.05, 0.04),
) -> Optional[Dict[str, object]]:
    """Build a hair shell over the scalp.

    `frame` is the `_Frame` from face_blendshapes, which knows which axis is
    up and which way the face points.
    """
    scalp_idx = masks.get("scalp")
    if scalp_idx is None or len(scalp_idx) == 0:
        logger.info("No scalp region in the FLAME masks — skipping hair")
        return None
    scalp_idx = np.asarray(scalp_idx, dtype=np.int64)

    width_ratio = (metrics or {}).get("width_ratio", DEFAULT_WIDTH_RATIO)
    top_ratio = (metrics or {}).get("top_ratio", DEFAULT_TOP_RATIO)
    # A segmentation can report absurd ratios when it mistakes a dark
    # background for hair, and an over-inflated shell is far more damaging
    # than an under-inflated one, so clamp both.
    width_ratio = float(np.clip(width_ratio, 1.0, 1.6))
    top_ratio = float(np.clip(top_ratio, 0.0, 0.85))

    up, side, fwd = frame.up, frame.side, frame.fwd
    head_w = float(vertices[:, side].max() - vertices[:, side].min())
    head_h = float(vertices[:, up].max() - vertices[:, up].min())

    # The photo measures hair rising above the topmost SKIN pixel, and the
    # skull already rises above the skin — forehead to crown is bone, not
    # hair. Subtracting that is the whole correction: taking the photo
    # number at face value double-counts the cranium and produced a shell
    # 0.3618 tall over a head whose crown sits at 0.3430, i.e. it more than
    # doubled the head's height into a cone.
    #
    # So: locate the top of the face skin on the mesh, project where the
    # photo says the hair should end, and lift only the remainder.
    face_idx = masks.get("face")
    if face_idx is not None and len(face_idx):
        face_v = vertices[np.asarray(face_idx, dtype=np.int64)]
        face_top = float(face_v[:, up].max())
        face_h = float(face_v[:, up].max() - face_v[:, up].min())
    else:
        face_top = float(vertices[:, up].max())
        face_h = float(vertices[:, up].max() - vertices[:, up].min())

    scalp_top = float(vertices[scalp_idx][:, up].max())
    target_top = face_top + top_ratio * face_h
    lift = max(0.0, target_top - scalp_top)
    # Even a correct measurement can be inflated by a dark background caught
    # in the hair mask, so never add more than a third of the face height.
    lift = min(lift, face_h * 0.33)
    spread = head_w * (width_ratio - 1.0) * 0.5

    normals = _vertex_normals(vertices, faces)
    scalp = vertices[scalp_idx].copy()
    n = normals[scalp_idx]

    # Weight the lift by how high each scalp vertex already sits, so the
    # shell grows from the crown and tapers to nothing at the hairline
    # rather than detaching in a ring around the head.
    rel = (scalp[:, up] - scalp[:, up].min())
    rel /= max(1e-9, rel.max())
    w = np.clip(rel, 0.0, 1.0) ** 0.75

    displacement = n * (spread * w[:, None])
    displacement[:, up] += frame.up_sign * lift * w
    # Pull the shell very slightly back: hair sits behind the forehead, and
    # without this the front edge can poke through the brow.
    displacement[:, fwd] -= frame.fwd_sign * spread * 0.25 * w

    # Clamp the RESULT, not the ingredients.
    #
    # At the crown the surface normal points up, so the sideways `spread`
    # term adds height too and stacks on top of `lift`. Clamping each part
    # separately still let them sum to 0.2653 over a skull whose crown sits
    # at 0.3430 — 77% taller than the head. Measuring the finished rise and
    # scaling the whole displacement keeps the shape and fixes the size.
    max_rise = head_h * 0.20
    rise = float((scalp[:, up] + displacement[:, up]).max()) - scalp_top
    if rise > max_rise > 0:
        displacement *= max_rise / rise
        logger.info("Hair shell scaled %.2fx to cap rise at %.0f%% of head height",
                    max_rise / rise, 20)

    shell = scalp + displacement

    # Keep only faces whose three corners are all scalp, then remap to the
    # compact vertex list.
    remap = -np.ones(len(vertices), dtype=np.int64)
    remap[scalp_idx] = np.arange(len(scalp_idx))
    keep = np.all(np.isin(faces, scalp_idx), axis=1)
    shell_faces = remap[faces[keep]]
    if len(shell_faces) == 0:
        logger.info("Scalp region has no complete faces — skipping hair")
        return None

    # Wind the shell outward. The scalp's own winding faces out of the skull;
    # the shell sits outside it and must face the same way to be lit and
    # culled correctly.
    verts = shell.astype(np.float32)
    tri = verts[shell_faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    centre = verts.mean(axis=0)
    outward = (tri.mean(axis=1) - centre)
    flipped = (fn * outward).sum(axis=1) < 0
    shell_faces[flipped] = shell_faces[flipped][:, ::-1]

    logger.info(
        "Built hair shell: %d verts, %d faces (lift %.4f, spread %.4f, "
        "width_ratio %.2f, top_ratio %.2f)",
        len(verts), len(shell_faces), lift, spread, width_ratio, top_ratio,
    )
    return {
        "parts": [{
            "name": "hair",
            "vertices": verts,
            "faces": shell_faces.astype(np.uint32),
            "color": colour,
            "jaw_follow": 0.0,
        }]
    }


def sample_hair_colour(image: np.ndarray, parsing: np.ndarray,
                       hair_label: int) -> Tuple[float, float, float]:
    """Median hair colour from the photo, as linear 0..1 RGB.

    Median, not mean: highlights and the background bleeding into the mask
    both drag a mean badly, and hair is the one region where a wrong colour
    is immediately obvious.
    """
    hair = parsing == hair_label
    if not hair.any():
        return (0.07, 0.05, 0.04)
    px = image[hair].astype(np.float32) / 255.0
    med = np.median(px, axis=0)
    # Photographed hair is rarely as dark as it looks; darken slightly so the
    # shell reads as hair rather than as a grey cap under scene lighting.
    return tuple(float(np.clip(c * 0.85, 0.02, 0.9)) for c in med[:3])
