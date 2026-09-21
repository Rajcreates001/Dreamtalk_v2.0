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

# How many directions the hair silhouette is measured in, starting below the
# brow line so the turn is continuous rather than split at the horizontal.
HAIR_PROFILE_BINS = 24
_PROFILE_START = -90.0

# The furthest the shell may be asked to reach, in face widths. This is the
# guard against a segmentation that mistook a dark background for hair; real
# hair on a real head does not reach a whole face-width and a third past the
# brow. It replaces the old cap on rise, which bound at exactly its own value
# on a normal subject - i.e. it was setting the shape, not catching a failure.
MAX_HAIR_RADIUS = 1.30

# The silhouette measurement constrains width and height. Hair has depth too,
# so a fraction of the same push is carried along the surface normal's forward
# component; without it the shell is a flat billboard seen from the side.
DEPTH_GAIN = 0.6


def _profile_edges() -> np.ndarray:
    return np.linspace(_PROFILE_START, _PROFILE_START + 360.0,
                       HAIR_PROFILE_BINS + 1)


def _wrap_deg(a: np.ndarray) -> np.ndarray:
    """Angles onto a single continuous turn starting at _PROFILE_START."""
    return ((np.asarray(a, dtype=np.float64) - _PROFILE_START) % 360.0
            + _PROFILE_START)


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
        "profile": _radial_profile(hx, hy, sx, sy),
    }


def _radial_profile(hx: np.ndarray, hy: np.ndarray,
                    sx: np.ndarray, sy: np.ndarray) -> Optional[list]:
    """How far the hair reaches in each direction, in face widths.

    Two scalars cannot describe a head of hair. `width_ratio` says how wide it
    is and nothing about how tall, and a shell inflated until it is wide enough
    is not tall enough - measured on one subject, the shell reached 0.43 face
    widths at the crown where the hair reaches 0.64, while at the sides it was
    already right. Anything uniform therefore has to overshoot one to reach the
    other.

    So measure a radius per direction about an origin at the middle of the top
    of the face, which is a landmark both the photograph and the mesh have. In
    face widths, so the numbers carry from one to the other without either
    knowing the other's scale - checked against the mesh-space truth through
    the harness's landmark fit, where it came out at a factor of 1.00.

    The 97th percentile rather than the maximum: a segmentation edge throws
    stray pixels well outside the mass, and a target set by the furthest of
    them is a target set by noise.

    This requires the parse to come from a SQUARE crop. A ratio along one axis
    survives an anisotropic resize; an angle does not.
    """
    sw = float(max(1, sx.max() - sx.min()))
    ox = float((sx.min() + sx.max()) / 2.0)
    oy = float(sy.min())
    ang = _wrap_deg(np.degrees(np.arctan2((oy - hy) / sw, (hx - ox) / sw)))
    rad = np.hypot((hx - ox) / sw, (oy - hy) / sw)

    edges = _profile_edges()
    prof = np.full(HAIR_PROFILE_BINS, np.nan)
    for i in range(HAIR_PROFILE_BINS):
        sel = (ang >= edges[i]) & (ang < edges[i + 1])
        if int(sel.sum()) > 20:
            prof[i] = float(np.percentile(rad[sel], 97))

    good = ~np.isnan(prof)
    if int(good.sum()) < HAIR_PROFILE_BINS // 3:
        logger.info("Hair visible in only %d of %d directions - no profile",
                    int(good.sum()), HAIR_PROFILE_BINS)
        return None
    idx = np.arange(HAIR_PROFILE_BINS)
    prof = np.interp(idx, idx[good], prof[good])
    # A per-bin maximum is noisy, and a jagged target makes a jagged
    # silhouette, so smooth across neighbouring directions.
    prof = np.convolve(np.r_[prof[0], prof, prof[-1]], np.ones(3) / 3.0,
                       mode="valid")
    return [float(v) for v in np.clip(prof, 0.0, MAX_HAIR_RADIUS)]


def _uniform_displacement(scalp: np.ndarray, normals: np.ndarray, frame,
                          head_w: float, width_ratio: float) -> np.ndarray:
    """One outward distance along the normals - the fallback construction.

    What widens the visible silhouette is standing the shell OFF the skull,
    not lifting it: the hair a viewer sees is only the part projecting outside
    the head's own outline, and lift moves the shell away from the sides,
    where that rim is widest. Measured, lift hurt at every offset tried, and a
    backward pull was worse - it grew in proportion to the spread, so a larger
    shell was pushed behind the skull faster than it grew.
    """
    spread = head_w * float(np.clip((width_ratio - 1.0) * 0.5, 0.04, 0.18))
    signed = scalp[:, frame.up] * frame.up_sign
    rel = signed - signed.min()
    rel /= max(1e-9, rel.max())
    # Weight by how high each vertex already sits, so the shell grows from the
    # crown and tapers to nothing at the hairline rather than detaching in a
    # ring around the head.
    return normals * (spread * (np.clip(rel, 0.0, 1.0) ** 0.75))[:, None]


def _radial_displacement(vertices: np.ndarray, scalp: np.ndarray,
                         normals: np.ndarray, masks: Dict[str, np.ndarray],
                         frame, profile: np.ndarray) -> np.ndarray:
    """Push each scalp vertex out to the radius the hair reaches there.

    The profile is in face widths about the middle of the top of the face, so
    the mesh needs the same origin in its own units. FLAME's face region is
    the counterpart of the parser's skin class: carried into mesh units
    through the harness's landmark fit, the parser's skin region measured
    0.96x the width of the FLAME face region with its top 5% of a face width
    away, which is close enough for the two to be read as one landmark.
    """
    up, side, fwd = frame.up, frame.side, frame.fwd
    face_idx = masks.get("face")
    ref = (vertices[np.asarray(face_idx, dtype=np.int64)]
           if face_idx is not None and len(face_idx) else vertices)
    across = ref[:, side]
    along = ref[:, up] * frame.up_sign
    width = max(float(across.max() - across.min()), 1e-9)
    ox = float((across.max() + across.min()) / 2.0)
    oy = float(along.max())

    dx = (scalp[:, side] - ox) / width
    dy = (scalp[:, up] * frame.up_sign - oy) / width
    rad = np.hypot(dx, dy)
    ang = _wrap_deg(np.degrees(np.arctan2(dy, dx)))

    edges = _profile_edges()
    centres = (edges[:-1] + edges[1:]) / 2.0
    target = np.interp(np.clip(ang, centres[0], centres[-1]), centres, profile)

    # Never pull a vertex in. Below the brow line the scalp already sits
    # further out than anything the profile describes - that is the nape,
    # hidden in any forward-facing view - so those vertices do not move at
    # all. That is what anchors the shell at the hairline, which is why no
    # separate taper is applied: one was tried at several strengths and every
    # strength scored worse than none.
    need = np.maximum(target - rad, 0.0) * width

    disp = np.zeros_like(scalp)
    disp[:, side] = (dx / np.maximum(rad, 1e-9)) * need
    disp[:, up] = (dy / np.maximum(rad, 1e-9)) * need * frame.up_sign
    forward = normals[:, fwd]
    disp[:, fwd] = np.sign(forward) * np.abs(forward) * DEPTH_GAIN * need
    return disp


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

    # Two constructions. The radial one, used when the photo segmentation
    # yielded a per-direction profile, pushes each scalp vertex out to the
    # radius the subject's own hair reaches in that vertex's direction. The
    # uniform one, used when it did not, offsets along the normals by a single
    # distance sized from width_ratio - the previous behaviour, kept as the
    # fallback so a failed parse still gives the head some volume.
    #
    # Measured against the subject's segmented hair, on the shipped mesh:
    #
    #                                  IoU     recall  precision   on face
    #     shipped (uniform offset)   0.4398   0.4645     0.8918      0.0%
    #     radial, 12 directions      0.8254   0.8418     0.9771      1.3%
    #     radial, 24 directions      0.8260   0.8442     0.9745      1.3%
    #     radial, 36 directions      0.8268   0.8449     0.9748      1.3%
    #
    # Recall nearly doubles and precision rises with it, so the coverage is
    # not being bought by spilling off the hair. The direction count barely
    # matters across that range; 24 is the middle of it. Growing the shell
    # beyond the scalp patch through face adjacency was tried at one, two and
    # three rings and moved IoU by less than 0.001, so it is not done.
    #
    # The remaining miss is the hair falling BELOW the jaw, which no shell
    # built on the scalp region can reach.
    #
    # The earlier figures for the shipped shell - IoU 0.2178, then 0.3411 -
    # were both measured in a canvas sized to the head, which silently clipped
    # any shell rising above it, so every candidate looked alike above a
    # certain height. Everything quoted here is from a canvas large enough to
    # hold the hair.
    width_ratio = float(np.clip(
        (metrics or {}).get("width_ratio", DEFAULT_WIDTH_RATIO), 1.0, 1.6))
    profile = (metrics or {}).get("profile")

    up, side = frame.up, frame.side
    head_w = float(vertices[:, side].max() - vertices[:, side].min())
    head_h = float(vertices[:, up].max() - vertices[:, up].min())

    normals = _vertex_normals(vertices, faces)
    scalp = vertices[scalp_idx].copy()
    n = normals[scalp_idx]

    if profile is not None and len(profile) == HAIR_PROFILE_BINS:
        displacement = _radial_displacement(
            vertices, scalp, n, masks, frame,
            np.asarray(profile, dtype=np.float64))
        how = "radial, %d directions" % HAIR_PROFILE_BINS
    else:
        displacement = _uniform_displacement(scalp, n, frame, head_w,
                                             width_ratio)
        how = "uniform, width_ratio %.2f" % width_ratio

    # A last guard against a segmentation that mistook a dark background for
    # hair. MAX_HAIR_RADIUS already bounds the profile; this bounds the result
    # in the mesh's own terms. The old cap was 20% of head height and bound at
    # exactly 20.0% on a normal subject - it was setting the shape, not
    # catching a failure - so this one sits well clear of the measured range:
    # the radial shell rises 28% of head height on the subject measured.
    signed = scalp[:, up] * frame.up_sign
    scalp_top = float(signed.max())
    rise = float((signed + displacement[:, up] * frame.up_sign).max()) - scalp_top
    max_rise = head_h * 0.60
    if rise > max_rise > 0:
        displacement *= max_rise / rise
        logger.info("Hair shell scaled %.2fx to cap rise at 60%% of head height",
                    max_rise / rise)

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
        "Built hair shell: %d verts, %d faces (%s, rises %.0f%% of head "
        "height above the scalp)",
        len(verts), len(shell_faces), how, 100.0 * rise / max(head_h, 1e-9),
    )
    return {
        "parts": [{
            "name": "hair",
            "vertices": verts,
            "faces": shell_faces.astype(np.uint32),
            "color": colour,
            "roughness": 0.9,
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
    # Photographs are sRGB; glTF baseColorFactor is linear. Treating these
    # encoded values as linear brightened dark hair into a grey/brown cap.
    # Do not impose a brightness floor: that would lighten black hair again.
    linear = np.where(med <= 0.04045, med / 12.92,
                      ((med + 0.055) / 1.055) ** 2.4)
    return tuple(float(c) for c in np.clip(linear[:3], 0.0, 1.0))
