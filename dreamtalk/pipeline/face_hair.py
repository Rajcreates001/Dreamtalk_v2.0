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

    # Only width_ratio is used. top_ratio - how far the hair rises above the
    # skin - drove a vertical lift that measurement showed is harmful at every
    # offset tried, so it is measured and reported but no longer shapes the
    # shell. A segmentation can report absurd ratios when it mistakes a dark
    # background for hair, and an over-inflated shell is more damaging than an
    # under-inflated one, so it is clamped.
    width_ratio = float(np.clip(
        (metrics or {}).get("width_ratio", DEFAULT_WIDTH_RATIO), 1.0, 1.6))

    up, side = frame.up, frame.side
    head_w = float(vertices[:, side].max() - vertices[:, side].min())
    head_h = float(vertices[:, up].max() - vertices[:, up].min())
    scalp_top = float(vertices[np.asarray(scalp_idx, dtype=np.int64)][:, up].max())

    # What actually widens the visible silhouette is standing the shell OFF
    # the skull, not lifting it.
    #
    # The hair a viewer sees is only the part of the shell that projects
    # outside the head's own silhouette; the rest is occluded. Measured
    # against the subject's segmented hair, with the shipped construction as
    # the baseline (IoU 0.2178, recall 0.2212):
    #
    #     outward offset (of head width), lift 0      IoU     recall
    #         0.09                                  0.3261    0.3353
    #         0.12                                  0.3378    0.3495
    #         0.16                                  0.3369    0.3533
    #         0.20                                  0.3271    0.3484
    #
    #     offset 0.12, with lift added
    #         lift 0.06                             0.2849    0.2927
    #         lift 0.12                             0.2124    0.2169
    #         lift 0.20                             0.1041    0.1057
    #
    # Lift hurts monotonically at every offset tried. It raises the shell off
    # the crown, where the visible rim is thin, and away from the sides, where
    # it is wide. The backward pull is worse still: it grew in proportion to
    # the spread, so a larger shell was pushed behind the skull faster than it
    # grew, and uniformly scaling the old displacement - which is exactly what
    # relaxing the rise cap did - drove IoU from 0.2178 down to 0.0382.
    #
    # So: offset along the normals, sized from the photo's own width_ratio,
    # and nothing else.
    spread = head_w * float(np.clip((width_ratio - 1.0) * 0.5, 0.04, 0.18))

    normals = _vertex_normals(vertices, faces)
    scalp = vertices[scalp_idx].copy()
    n = normals[scalp_idx]

    # Weight by how high each scalp vertex already sits, so the shell grows
    # from the crown and tapers to nothing at the hairline rather than
    # detaching in a ring around the head.
    rel = (scalp[:, up] - scalp[:, up].min())
    rel /= max(1e-9, rel.max())
    w = np.clip(rel, 0.0, 1.0) ** 0.75

    displacement = n * (spread * w[:, None])

    # A cap purely as a guard against a segmentation that mistook a dark
    # background for hair. It used to be 20% of head height and it bound at
    # exactly 20.0% on a normal subject - i.e. it was setting the shape, not
    # catching a failure - so it now sits well clear of the measured range.
    max_rise = head_h * 0.35
    rise = float((scalp[:, up] + displacement[:, up]).max()) - scalp_top
    if rise > max_rise > 0:
        displacement *= max_rise / rise
        logger.info("Hair shell scaled %.2fx to cap rise at %.0f%% of head height",
                    max_rise / rise, 35)

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
        "Built hair shell: %d verts, %d faces (offset %.4f = %.2f of head "
        "width, width_ratio %.2f)",
        len(verts), len(shell_faces), spread, spread / max(head_w, 1e-9),
        width_ratio,
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
