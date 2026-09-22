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

# Rec. 601 luma, used to compare the shell's brightness with the
# photograph's hair without letting one channel dominate.
_LUMA = np.array([0.299, 0.587, 0.114])

# The parser class the profile and the colour sampling both take
# their origin from. CelebAMask-HQ puts skin at 1.
_SKIN_FOR_ORIGIN = 1

# A vertex counts as being on the silhouette when its normal is within this
# much of perpendicular to the view. Those are the only vertices where a
# photograph measures hair THICKNESS rather than hair colour.
SILHOUETTE_COS = 0.40

# One subdivision takes the shell from 900 faces to 3600 and the mean
# dihedral angle from 8.7 degrees to 4.2, with nothing left folded. A second
# halves the mean again but reintroduces a 124 degree kink, so it is not
# worth the four times the vertices.
SHELL_SUBDIVISIONS = 1


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


def _adjacency(count, faces):
    from collections import defaultdict
    adj = defaultdict(set)
    for a, b, c in faces:
        adj[a].update((b, c))
        adj[b].update((a, c))
        adj[c].update((a, b))
    return [np.fromiter(adj[i], np.int64) if adj[i] else np.array([i], np.int64)
            for i in range(count)]


def _edges(faces):
    seen = set()
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            seen.add((min(e), max(e)))
    return np.asarray(sorted(seen), dtype=np.int64)


def _boundary(faces):
    from collections import defaultdict
    count = defaultdict(int)
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            count[(min(e), max(e))] += 1
    out = set()
    for e, k in count.items():
        if k == 1:
            out.update(e)
    return out


def _diffuse(values, pinned, adj, iters=400):
    """Laplace over the patch, holding the measured vertices fixed."""
    x = values.copy()
    x[~pinned] = float(values[pinned].mean()) if pinned.any() else 0.0
    for _ in range(iters):
        nxt = np.array([x[a].mean() for a in adj])
        nxt[pinned] = values[pinned]
        if np.abs(nxt - x).max() < 1e-7:
            return nxt
        x = nxt
    return x


def _clamp_gradient(need, verts, edges, k=0.8, sweeps=32):
    """Make a fold impossible rather than smoothing until one stops showing.

    If the push distance changes faster between two neighbouring vertices than
    the edge between them is long, the triangle turns inside out. Holding

        |need_i - need_j| <= k * |v_i - v_j|,  k < 1

    rules that out. Measured on the first shell that shipped: 18 edges kinked
    past 150 degrees and 38 past 90, none of them degenerate triangles and
    almost none near the patch boundary - real interior folds. With the clamp,
    nothing exceeds 90 at all.
    """
    need = need.copy()
    lim = k * np.linalg.norm(verts[edges[:, 0]] - verts[edges[:, 1]], axis=1)
    for _ in range(sweeps):
        d = need[edges[:, 0]] - need[edges[:, 1]]
        over = np.abs(d) > lim
        if not over.any():
            break
        hi = np.where(d > 0, edges[:, 0], edges[:, 1])[over]
        lo = np.where(d > 0, edges[:, 1], edges[:, 0])[over]
        np.minimum.at(need, hi, need[lo] + lim[over])
    return need


def _subdivide(verts, faces):
    """Split each triangle on its edge midpoints."""
    mid, out = {}, list(verts)

    def midpoint(a, b):
        key = (min(a, b), max(a, b))
        if key not in mid:
            mid[key] = len(out)
            out.append((verts[a] + verts[b]) / 2.0)
        return mid[key]

    new_faces = []
    for a, b, c in faces:
        ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
        new_faces += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
    return np.asarray(out, dtype=np.float64), np.asarray(new_faces, dtype=np.int64)


def _taubin(verts, faces, iters=4, lam=0.5, mu=-0.53):
    """Smooth without shrinking - a plain Laplacian pass would deflate it."""
    adj = _adjacency(len(verts), faces)
    fixed = np.zeros(len(verts), dtype=bool)
    for i in _boundary(faces):
        fixed[i] = True
    verts = verts.copy()
    for _ in range(iters):
        for w in (lam, mu):
            delta = np.zeros_like(verts)
            for i, a in enumerate(adj):
                delta[i] = verts[a].mean(axis=0) - verts[i]
            delta[fixed] = 0.0
            verts = verts + w * delta
    return verts


def _cap_shell(vertices, scalp_idx, normals, faces_local, masks, frame,
               profile, max_rise=None):
    """Hair as a layer over the skull, thick where the photograph says it is.

    The first version of this pushed every scalp vertex outward in the FRONTAL
    plane until it reached the radius the profile asked for. Head on, that
    scores well - IoU 0.82, recall 0.84. Turn the head thirty degrees and it is
    a disc: the back of the skull was pushed sideways exactly as hard as the
    crown, so the shell stands out past the head as a brim with a hard rim and
    a gap where it leaves the scalp. Every one of those numbers is measured in
    the frontal view, so none of them could see it, and the shape was optimised
    into the blind spot.

    Hair is a layer, so solve for its THICKNESS. A photograph shows thickness
    honestly in one place - the silhouette, where the surface turns away from
    the camera and the outline is the hair's own edge. So read it there, hold
    it at zero along the hairline because that is where hair starts, diffuse
    between the two over the mesh's own connectivity, and offset along the 3D
    normal.

    Measured against the disc, on the same head:

                          outline err   depth past head   side past head   max kink
        disc (shipped)        0.156          14.5%             5.0%          177 deg
        sealed cap            0.166           7.9%             2.3%          105 deg
        + subdivided          0.167           7.7%             2.1%           50 deg

    The frontal outline it was fitted to is kept, the overhang halves, and
    nothing is left folded.
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

    scalp = vertices[scalp_idx]
    n = normals[scalp_idx]
    dx = (scalp[:, side] - ox) / width
    dy = (scalp[:, up] * frame.up_sign - oy) / width
    rad = np.hypot(dx, dy)
    ang = _wrap_deg(np.degrees(np.arctan2(dy, dx)))
    edges = _profile_edges()
    centres = (edges[:-1] + edges[1:]) / 2.0
    target = np.interp(np.clip(ang, centres[0], centres[-1]), centres, profile)
    want = np.maximum(target - rad, 0.0) * width

    on_silhouette = np.abs(n[:, fwd]) < SILHOUETTE_COS
    rim = np.zeros(len(scalp), dtype=bool)
    for i in _boundary(faces_local):
        rim[i] = True
    on_silhouette &= ~rim

    thickness = np.zeros(len(scalp))
    thickness[on_silhouette] = want[on_silhouette]
    thickness = _diffuse(thickness, on_silhouette | rim,
                         _adjacency(len(scalp), faces_local))
    thickness = _clamp_gradient(thickness, scalp, _edges(faces_local))

    # A last guard against a segmentation that mistook a dark background for
    # hair. MAX_HAIR_RADIUS already bounds the profile, so this bounds the
    # result in the mesh's own terms and sits well clear of the measured
    # range - the cap rises 28% of head height on the subject measured. The
    # cap it replaced was 20% and bound at exactly 20.0%, i.e. it was setting
    # the shape rather than catching a failure.
    if max_rise and max_rise > 0:
        signed = scalp[:, up] * frame.up_sign
        top = float(signed.max())
        reach = float((signed + (n[:, up] * frame.up_sign) * thickness).max())
        if reach - top > max_rise:
            thickness *= max_rise / (reach - top)
            logger.info("Hair cap scaled to keep its rise within %.2f", max_rise)

    shell = scalp + n * thickness[:, None]
    shell_faces = faces_local.copy()
    for _ in range(SHELL_SUBDIVISIONS):
        shell, shell_faces = _subdivide(shell, shell_faces)
    if SHELL_SUBDIVISIONS:
        shell = _taubin(shell, shell_faces)
    logger.info("Hair cap: thickness measured at %d silhouette vertices, "
                "%d verts after %d subdivision(s)",
                int(on_silhouette.sum()), len(shell), SHELL_SUBDIVISIONS)
    return shell, shell_faces


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

    # Two constructions. The cap, used when the photo segmentation yielded a
    # per-direction profile, solves for how THICK the hair is over each part
    # of the skull and offsets along the surface normal. The uniform one, used
    # when it did not, offsets along the normals by a single distance sized
    # from width_ratio - the previous behaviour, kept as the fallback so a
    # failed parse still gives the head some volume.
    #
    # Against the subject's segmented hair, in the frontal view:
    #
    #                                  IoU     recall  precision
    #     uniform offset             0.4398   0.4645     0.8918
    #     profile-driven             0.8260   0.8442     0.9745
    #
    # Those are all frontal numbers, and a frontal number cannot see the shape
    # of the thing it is scoring. The first profile-driven shell pushed every
    # vertex outward in the frontal PLANE, which scores 0.82 and, turned
    # thirty degrees, is a disc standing out past the head as a brim. What
    # fixed it was solving for thickness instead; see _cap_shell.
    #
    # The older figures for the uniform shell - IoU 0.2178, then 0.3411 - were
    # measured in a canvas sized to the head, which silently clipped any shell
    # rising above it, so every candidate looked alike above a certain height.
    # 0.4398 is that same shell measured in a canvas large enough to hold it.
    width_ratio = float(np.clip(
        (metrics or {}).get("width_ratio", DEFAULT_WIDTH_RATIO), 1.0, 1.6))
    profile = (metrics or {}).get("profile")

    up, side = frame.up, frame.side
    head_w = float(vertices[:, side].max() - vertices[:, side].min())
    head_h = float(vertices[:, up].max() - vertices[:, up].min())
    max_rise = head_h * 0.60

    normals = _vertex_normals(vertices, faces)
    scalp = vertices[scalp_idx].copy()
    n = normals[scalp_idx]

    # Keep only faces whose three corners are all scalp, then remap to the
    # compact vertex list. Needed before either construction: the cap solves
    # over this patch's own connectivity.
    remap = -np.ones(len(vertices), dtype=np.int64)
    remap[scalp_idx] = np.arange(len(scalp_idx))
    keep = np.all(np.isin(faces, scalp_idx), axis=1)
    faces_local = remap[faces[keep]]
    if len(faces_local) == 0:
        logger.info("Scalp region has no complete faces — skipping hair")
        return None

    if profile is not None and len(profile) == HAIR_PROFILE_BINS:
        shell, shell_faces = _cap_shell(
            vertices, scalp_idx, normals, faces_local, masks, frame,
            np.asarray(profile, dtype=np.float64), max_rise=max_rise)
        how = "cap from %d directions" % HAIR_PROFILE_BINS
    else:
        displacement = _uniform_displacement(scalp, n, frame, head_w,
                                             width_ratio)
        signed = scalp[:, up] * frame.up_sign
        top = float(signed.max())
        rise = float((signed + displacement[:, up] * frame.up_sign).max()) - top
        if rise > max_rise > 0:
            displacement *= max_rise / rise
            logger.info("Hair shell scaled %.2fx to cap its rise",
                        max_rise / rise)
        shell = scalp + displacement
        shell_faces = faces_local.copy()
        how = "uniform, width_ratio %.2f" % width_ratio

    # Wind the shell outward. The scalp's own winding faces out of the skull;
    # the shell sits outside it and must face the same way to be lit and
    # culled correctly.
    verts = shell.astype(np.float32)
    tri = verts[shell_faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    centre = verts.mean(axis=0)
    flipped = (fn * (tri.mean(axis=1) - centre)).sum(axis=1) < 0
    shell_faces[flipped] = shell_faces[flipped][:, ::-1]

    # Ship normals. The shell went out with none at all, leaving every viewer
    # to invent them; three.js recomputes, but nothing guarantees the next one
    # will, and a shell shaded flat looks like the faceted block this stopped
    # being.
    shell_normals = _vertex_normals(verts.astype(np.float64), shell_faces)

    rise = (float((verts[:, up] * frame.up_sign).max())
            - float((scalp[:, up] * frame.up_sign).max()))
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
            "normals": shell_normals.astype(np.float32),
            "color": colour,
            "roughness": 0.9,
            "jaw_follow": 0.0,
        }]
    }


def sample_hair_vertex_colours(
    shell: np.ndarray, vertices: np.ndarray, masks: Dict[str, np.ndarray],
    frame, image: np.ndarray, parsing: np.ndarray, hair_label: int,
) -> Optional[Tuple[np.ndarray, Tuple[float, float, float]]]:
    """A colour per shell vertex, read off the photograph where it projects.

    The shell is one flat value: 489 vertices all carrying the material's
    baseColorFactor. The photograph's hair runs across a wide range of
    luminance with real structure in it, so a single value renders the hair as
    a silhouette with no highlight, no parting and no sense of volume - and
    now that the shell is the right size, that flat mass is bigger and reads
    worse, not better.

    No new geometry is needed for this. The vertices are already spread over
    the hair, and the profile gave a mapping between mesh units and the
    parse's own pixels: both are measured about the middle of the top of the
    face, in face widths. So the same mapping that decides how far to push a
    vertex also decides which pixel it lands on.

    Returns the per-vertex colours and the factor they are relative to. The
    factor is the brightest tone on the shell, not its median, so the
    attribute divides down into 0..1 as glTF requires and a renderer ignoring
    COLOR_0 gets a plausible flat hair colour rather than white.
    """
    if image is None or parsing is None:
        return None
    hair = parsing == hair_label
    skin = parsing == _SKIN_FOR_ORIGIN
    if not hair.any() or not skin.any():
        return None
    if image.shape[:2] != parsing.shape[:2]:
        return None

    sy, sx = np.nonzero(skin)
    sw = float(max(1, sx.max() - sx.min()))
    ox = float((sx.min() + sx.max()) / 2.0)
    oy = float(sy.min())

    up, side = frame.up, frame.side
    face_idx = masks.get("face")
    ref = (vertices[np.asarray(face_idx, dtype=np.int64)]
           if face_idx is not None and len(face_idx) else vertices)
    across = ref[:, side]
    along = ref[:, up] * frame.up_sign
    width = max(float(across.max() - across.min()), 1e-9)
    mx = float((across.max() + across.min()) / 2.0)
    my = float(along.max())

    px = ox + (shell[:, side] - mx) / width * sw
    py = oy - (shell[:, up] * frame.up_sign - my) / width * sw
    h, w = parsing.shape[:2]
    xi = np.clip(px, 0, w - 1).astype(np.int64)
    yi = np.clip(py, 0, h - 1).astype(np.int64)
    inside = ((px >= 0) & (px < w) & (py >= 0) & (py < h)
              & hair[np.clip(py, 0, h - 1).astype(np.int64),
                     np.clip(px, 0, w - 1).astype(np.int64)])
    if int(inside.sum()) < len(shell) // 4:
        logger.info("Only %d of %d hair vertices land on hair in the photo - "
                    "keeping the flat colour", int(inside.sum()), len(shell))
        return None

    # Blur INSIDE the hair only. A plain blur near the silhouette mixes in
    # whatever is behind the head - here a pale studio backdrop - and the
    # vertices around the rim are exactly the ones that then come back far too
    # light. The first attempt did that and rendered black hair as a grey
    # helmet: the tonal spread was right, 93% of the photograph's, and the
    # level was several times too bright. So carry the mask through the blur
    # and divide it out, which keeps every sample made of hair.
    import cv2

    sigma = max(1.5, sw / 180.0)
    m = hair.astype(np.float64)
    num = cv2.GaussianBlur(image[:, :, :3].astype(np.float64) * m[:, :, None],
                           (0, 0), sigmaX=sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigmaX=sigma)
    smooth = num / np.maximum(den, 1e-6)[:, :, None]

    rgb = np.clip(smooth[yi, xi], 0.0, 255.0) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92,
                      ((rgb + 0.055) / 1.055) ** 2.4)
    median = np.median(linear[inside], axis=0)
    linear[~inside] = median

    # Match the level as well as the variation. The spread alone says nothing
    # about how dark the hair is, and hair that is the right shape, the right
    # size and the wrong brightness is still wrong - more visibly so now that
    # the shell is large.
    photo = image[:, :, :3][hair].astype(np.float64) / 255.0
    photo = np.where(photo <= 0.04045, photo / 12.92,
                     ((photo + 0.055) / 1.055) ** 2.4)
    want = float((photo @ _LUMA).mean())
    have = float((linear @ _LUMA).mean())
    if have > 1e-6:
        linear = linear * (want / have)

    # glTF float COLOR_0 has to sit in 0..1, so the material carries the
    # brightest tone and the attribute holds each vertex relative to it. That
    # also means a renderer ignoring COLOR_0 gets a plausible flat hair colour
    # rather than white.
    factor = np.maximum(linear.max(axis=0), 1e-4)
    cols = np.clip(linear / factor, 0.0, 1.0)
    lum = linear @ _LUMA
    logger.info("Hair colour sampled per vertex: %d of %d on hair, luminance "
                "%.4f..%.4f mean %.4f against the photo's %.4f",
                int(inside.sum()), len(shell), float(lum.min()),
                float(lum.max()), float(lum.mean()), want)
    return cols, tuple(float(c) for c in np.clip(factor, 0.0, 1.0))


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
