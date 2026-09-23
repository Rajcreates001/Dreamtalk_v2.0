"""
FLAME 3D Face Fitter — shared module used by:
  - pipeline/face_pipeline.py  (orchestrator path)
  - identity/appearance.py    (upload API path)

Loads the clean numpy FLAME model, detects face landmarks from a photo,
fits identity parameters, computes normals, and exports OBJ+MTL.
"""

import os
import sys
import math
import pickle
import logging
import uuid
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger("dreamtalk.pipeline.flame_fitter")

# Resolve project root
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DEFAULT_MODEL_PATH = os.path.join(_PROJECT_ROOT, "weights", "flame", "FLAME2020_numpy.pkl")

# Maximum |identity coefficient| in FLAME shape-PCA standard deviations.
# Real faces live within ~3; beyond that the mesh stops being a head.
IDENTITY_SIGMA_LIMIT = float(os.environ.get("FLAME_IDENTITY_SIGMA_LIMIT", "3.0"))

# UV atlas resolution. The shipped FLAME mean texture is 512², but the colour
# that matters is sampled from the user's photo (typically 1500-2000px), so 512
# threw away most of that detail and the skin read soft. 1024 matches a normal
# portrait's usable face resolution without oversampling.
TEXTURE_ATLAS_SIZE = int(os.environ.get("FLAME_TEXTURE_SIZE", "1024"))
_STATIC_DIR = os.path.join(_PROJECT_ROOT, "avatar", "static")

# ── FLAME Model Loader ────────────────────────────────────────────────


# ── FLAME landmark embedding ──────────────────────────────────────────
#
# Where each of the 68 semantic landmarks (iBUG order, the order of
# MP_TO_IBUG68 below) lies on FLAME: a triangle, and a barycentric position in
# it. Derived by scripts/derive_flame_landmarks.py from FLAME's own mean shape
# and mean albedo, rendered through a known camera and read by the same
# MediaPipe detector the pipeline uses - no licensed file, nothing guessed.
#
# It replaced 68 vertex indices, labelled "from DECA", that were not
# landmarks: their lowest point was index 2 rather than the chin at 8, their
# most forward was 9 rather than the nose tip at 30, and the two "jaw ends"
# sat 2 cm apart in the middle of the face. This one puts the chin at 8 and
# the nose tip at 30, spans 27 x 8 mm across an eye, and mirrors left to right
# within 4.4 mm (mean 2.6 mm) - the spread of MediaPipe's own detections.
# Two jaw-contour points (12, 13) sit a few pixels past the rendered
# silhouette and are snapped to the nearest front-facing vertex.
FLAME_MP68_FACES = np.array([
    7726, 7727, 3410, 3307, 8370, 8371, 8372, 8386, 8248, 8144, 8196, 8139,
    3069, 24, 5239, 149, 1467, 8830, 7930, 225, 3779, 7915, 6592, 7326,
    3, 8891, 3194, 6108, 5990, 471, 8800, 7342, 3534, 5936, 830, 1148,
    5066, 2675, 6802, 6866, 6823, 9550, 6409, 3799, 9205, 8004, 4509, 9039,
    7290, 2294, 3567, 393, 5934, 1065, 863, 944, 985, 8804, 3610, 7451,
    2377, 8669, 5555, 8634, 5965, 8634, 5555, 8669,
], dtype=np.int64)
FLAME_MP68_BARY = np.array([
    [0.174822, 0.037928, 0.787250],
    [0.387417, 0.073264, 0.539319],
    [0.301508, 0.037487, 0.661005],
    [0.141862, 0.171575, 0.686563],
    [0.632478, 0.069238, 0.298284],
    [0.536603, 0.396736, 0.066661],
    [0.134303, 0.782427, 0.083270],
    [0.192744, 0.710161, 0.097095],
    [0.068804, 0.622523, 0.308673],
    [0.115050, 0.793297, 0.091653],
    [0.015789, 0.622036, 0.362175],
    [0.257599, 0.587374, 0.155027],
    [0.000000, 1.000000, 0.000000],
    [1.000000, 0.000000, 0.000000],
    [0.234036, 0.086146, 0.679819],
    [0.156859, 0.334612, 0.508529],
    [0.364742, 0.129404, 0.505854],
    [0.044722, 0.698949, 0.256329],
    [0.000074, 0.486409, 0.513517],
    [0.557218, 0.320963, 0.121819],
    [0.489296, 0.082979, 0.427725],
    [0.145191, 0.651472, 0.203336],
    [0.212824, 0.219569, 0.567607],
    [0.530390, 0.274598, 0.195012],
    [0.251759, 0.338281, 0.409960],
    [0.109188, 0.482375, 0.408437],
    [0.314644, 0.582070, 0.103286],
    [0.328200, 0.399266, 0.272534],
    [0.301991, 0.136267, 0.561742],
    [0.241035, 0.283786, 0.475179],
    [0.344657, 0.385600, 0.269743],
    [0.219911, 0.330628, 0.449461],
    [0.275502, 0.673507, 0.050991],
    [0.429108, 0.324915, 0.245977],
    [0.564877, 0.355494, 0.079629],
    [0.304167, 0.233133, 0.462700],
    [0.079555, 0.676558, 0.243887],
    [0.397714, 0.017620, 0.584666],
    [0.490573, 0.366436, 0.142991],
    [0.494953, 0.331911, 0.173136],
    [0.813795, 0.042945, 0.143260],
    [0.875679, 0.101609, 0.022712],
    [0.128142, 0.341336, 0.530522],
    [0.326406, 0.467181, 0.206412],
    [0.498107, 0.255903, 0.245990],
    [0.667814, 0.044375, 0.287811],
    [0.676727, 0.198491, 0.124782],
    [0.143006, 0.627340, 0.229655],
    [0.334632, 0.650013, 0.015355],
    [0.660733, 0.026087, 0.313179],
    [0.456459, 0.010870, 0.532671],
    [0.281155, 0.235598, 0.483247],
    [0.587372, 0.162202, 0.250426],
    [0.487044, 0.159292, 0.353664],
    [0.084807, 0.864666, 0.050527],
    [0.351814, 0.460599, 0.187587],
    [0.193637, 0.679328, 0.127034],
    [0.186112, 0.636424, 0.177464],
    [0.805118, 0.128624, 0.066258],
    [0.624962, 0.359327, 0.015712],
    [0.157769, 0.087194, 0.755038],
    [0.126041, 0.068376, 0.805583],
    [0.227546, 0.589684, 0.182769],
    [0.316880, 0.584616, 0.098505],
    [0.061718, 0.870557, 0.067725],
    [0.332153, 0.525662, 0.142186],
    [0.240259, 0.543977, 0.215763],
    [0.106894, 0.076881, 0.816225],
], dtype=np.float64)


class FLAMELoader:
    """Minimal FLAME model loader (numpy-only, no chumpy dependency)."""

    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"FLAME model not found: {model_path}")
        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.v_template = data["v_template"]                     # (5023, 3)
        self.shapedirs = data["shapedirs"]                        # (5023, 3, 400)
        self.faces = data["f"].astype(np.int32)                   # (9976, 3)
        self.posedirs = data["posedirs"]                          # (5023, 3, 36)
        self.weights = data["weights"]                            # (5023, 5)

        self.identity_basis = self.shapedirs[:, :, :300]          # (5023, 3, 300)
        self.expression_basis = self.shapedirs[:, :, 300:400]     # (5023, 3, 100)

        self.num_vertices = self.v_template.shape[0]
        self.num_faces = self.faces.shape[0]

        # Where the 68 semantic landmarks sit on the mesh, as a triangle and a
        # barycentric position inside it (see FLAME_MP68_FACES). This replaced
        # a list of 68 vertex indices labelled "from DECA" that were not
        # landmarks at all. The nearest vertex of each is kept as lmk_inds for
        # callers that need an index.
        self.lmk_faces = FLAME_MP68_FACES
        self.lmk_bary = FLAME_MP68_BARY
        corners = self.faces[self.lmk_faces]                      # (68, 3)
        self.lmk_inds = corners[np.arange(68), np.argmax(self.lmk_bary, axis=1)]
        assert self.lmk_faces.max() < self.num_faces, \
            f"Landmark face {self.lmk_faces.max()} >= {self.num_faces}"

    def generate_mesh(
        self,
        identity_coeffs: Optional[np.ndarray] = None,
        expression_coeffs: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Generate deformed mesh vertices.

        Args:
            identity_coeffs: (300,) or None for mean face
            expression_coeffs: (100,) or None for neutral

        Returns:
            (5023, 3) vertex positions
        """
        v = self.v_template.copy()
        if identity_coeffs is not None:
            v += np.tensordot(self.identity_basis, identity_coeffs, axes=[2, 0])
        if expression_coeffs is not None:
            v += np.tensordot(self.expression_basis, expression_coeffs, axes=[2, 0])
        return v

    def get_landmarks(self, vertices: np.ndarray) -> np.ndarray:
        """The 68 landmarks on a mesh of this topology, in iBUG order."""
        corners = vertices[self.faces[self.lmk_faces]]            # (68, 3, 3)
        return (corners * self.lmk_bary[:, :, None]).sum(axis=1)

    def landmark_basis(self) -> np.ndarray:
        """The identity basis evaluated at the landmarks: (68, 3, 300)."""
        corners = self.identity_basis[self.faces[self.lmk_faces]]  # (68,3,3,300)
        return (corners * self.lmk_bary[:, :, None, None]).sum(axis=1)

    def landmark_values(self, per_vertex: np.ndarray) -> np.ndarray:
        """Interpolate any per-vertex quantity (UVs, colours) at the landmarks."""
        corners = per_vertex[self.faces[self.lmk_faces]]
        return (corners * self.lmk_bary.reshape(68, 3, *([1] * (corners.ndim - 2)))).sum(axis=1)


# ── Landmark Detection ────────────────────────────────────────────────

def detect_landmarks(image_path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """Detect 478 face landmarks from an image using MediaPipe Tasks API.

    Returns:
        (landmarks_2d, image_width) or (None, None)
    """
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        import cv2
    except ImportError:
        logger.warning("MediaPipe not available for landmark detection")
        return None, None

    img = cv2.imread(image_path)
    if img is None:
        logger.warning("Cannot read image: %s", image_path)
        return None, None

    h, w = img.shape[:2]

    # Locate face landmarker model
    model_path = None
    for candidate in [
        os.path.join(_PROJECT_ROOT, "weights", "face", "face_landmarker.task"),
        os.path.join(_PROJECT_ROOT, "weights", "face", "face_landmarker_v2_with_blendshapes.task"),
        "weights/face/face_landmarker.task",
    ]:
        if os.path.exists(candidate):
            model_path = candidate
            break

    if model_path is None:
        logger.warning("Face landmarker model not found; skipping detection")
        return None, None

    try:
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
        )
        detector = vision.FaceLandmarker.create_from_options(options)

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)

        if not result.face_landmarks:
            logger.info("No face detected in %s", image_path)
            return None, None

        landmarks = np.array([(p.x * w, p.y * h) for p in result.face_landmarks[0]])
        logger.info("Detected %d face landmarks from %s", len(landmarks), image_path)
        return landmarks, w

    except Exception as e:
        logger.warning("MediaPipe landmark detection failed: %s", e)
        return None, None


# ── Semantic MediaPipe -> iBUG-68 correspondence ─────────────────────
#
# MediaPipe's 478-point topology is fixed, so which of its points is "the outer
# corner of the right eye" is a fact about the model, not something to infer
# per photograph. derive_mp68_mapping (below) inferred it anyway - by
# projecting the mean FLAME face through a guessed camera and taking whichever
# MediaPipe point was nearest - and on a real portrait that agreed with this
# table on 0 of 68 points: its "right eye" spread 433 x 220 px and sat 127 px
# from the iris, where these six sit 5 px from it. Every identity fit and every
# texture projection was built on those pairs, which is what put the fitted
# eyes a full eye-height below the real ones.
#
# Each left point is the mirror of its right counterpart in MediaPipe's own
# symmetric topology (127/356, 234/454, 93/323, 132/361, 58/288, 172/397,
# 136/365, 150/379; brows 70/300 ...; eyes 33/263 ...; lips 61/291 ...). The
# first draft of this table had the left jaw shifted by one point, which a
# mirror check on the derived FLAME embedding caught at 38 mm of asymmetry.
MP_TO_IBUG68 = np.array([
    127, 234, 93, 132, 58, 172, 136, 150, 152, 379, 365, 397, 288, 361, 323, 454, 356,
    70, 63, 105, 66, 107,
    336, 296, 334, 293, 300,
    168, 197, 5, 4,
    75, 97, 2, 326, 305,
    33, 160, 158, 133, 153, 144,
    362, 385, 387, 263, 373, 380,
    61, 39, 37, 0, 267, 269, 291, 405, 314, 17, 84, 181,
    78, 82, 13, 312, 308, 317, 14, 87,
], dtype=np.int64)


def semantic_mp68_mapping(landmarks_2d: np.ndarray):
    """The fixed correspondence, when MediaPipe returned its full topology.

    Returns (indices, distances) in the shape derive_mp68_mapping returns, so
    callers can use either; distances are zero because nothing was matched by
    proximity. None when there are too few points to index into.
    """
    if landmarks_2d is None or len(landmarks_2d) < 468:
        return None
    return MP_TO_IBUG68.copy(), np.zeros(68)


# ── Model-Derived Landmark Correspondence ───────────────────────────
# NOTE: Previously used a hardcoded _MP_68_INDICES constant (with duplicate
# index 0 causing bugs). Now the mapping is derived from mesh geometry via
# derive_mp68_mapping(), which projects FLAME 3D landmarks to 2D and finds
# the nearest MediaPipe neighbor, with automatic duplicate collision resolution.

def derive_mp68_mapping(
    flame: FLAMELoader,
    mean_vertices: np.ndarray,
    landmarks_2d: np.ndarray,
    image_width: int,
) -> np.ndarray:
    """Derive MediaPipe 478 → FLAME 68 landmark correspondence from geometry.

    Instead of using a hardcoded mapping, this function:
      1. Takes the mean FLAME mesh and its 68 semantic landmark vertices
      2. Projects each 3D landmark to 2D using an initial camera estimate
      3. For each projected 2D landmark, finds the nearest MediaPipe 478
         landmark by Euclidean distance
      4. Returns the derived MediaPipe indices (one per FLAME landmark)

    The resulting mapping is:
      - Free of duplicate indices (each FLAME landmark maps to a unique MediaPipe point)
      - Geometrically grounded (uses actual 3D→2D projections from the model)
      - Photo-adaptive (slightly different mappings per face shape)

    Args:
        flame: FLAME model
        mean_vertices: (5023, 3) mean mesh vertices
        landmarks_2d: (478, 2) detected MediaPipe landmarks
        image_width: image width in pixels

    Returns:
        (68,) MediaPipe 478 indices for each of the 68 FLAME landmarks.
        Indices are guaranteed to be within len(landmarks_2d) and unique.
    """
    from scipy.spatial import KDTree

    # Get FLAME 68 landmark 3D positions
    flame_lmks_3d = flame.get_landmarks(mean_vertices)  # (68, 3)

    # Initial camera estimate: align mean FLAME 2D → MediaPipe 2D
    # NOTE: FLAME Y points up, MediaPipe Y points down — negate Y
    flame_xy = np.column_stack([
        flame_lmks_3d[:, 0],           # X as-is
        -flame_lmks_3d[:, 1],          # Y flipped (FLAME up → image down)
    ])

    flame_xy_c = flame_xy - flame_xy.mean(axis=0)
    obs_2d_c = landmarks_2d - landmarks_2d.mean(axis=0)
    scale_init = np.std(obs_2d_c) / (np.std(flame_xy_c) + 1e-8)
    trans_init = landmarks_2d.mean(axis=0)

    # Project FLAME landmarks to 2D
    projected = scale_init * flame_xy + trans_init  # (68, 2)

    # Build KD-tree of MediaPipe 478 2D landmarks
    tree = KDTree(landmarks_2d)
    distances, indices = tree.query(projected)

    # Ensure uniqueness: if multiple FLAME landmarks map to the same
    # MediaPipe index, keep only the closest one for each MediaPipe index
    mp_indices = indices.copy()
    seen = {}
    for i in range(68):
        mp_idx = int(mp_indices[i])
        d = float(distances[i])
        if mp_idx in seen:
            prev_i, prev_d = seen[mp_idx]
            if d < prev_d:
                # Current is closer, reassign the previous one
                mp_indices[prev_i] = _find_next_best(
                    landmarks_2d, tree, projected[prev_i], mp_idx, seen
                )
                seen[mp_idx] = (i, d)
            else:
                # Previous is closer, reassign current
                mp_indices[i] = _find_next_best(
                    landmarks_2d, tree, projected[i], mp_idx, seen
                )
        else:
            seen[mp_idx] = (i, d)

    # Also propagate mapping distances (after uniqueness resolution)
    mapping_distances = distances.copy()  # (68,)

    mp_indices = np.clip(mp_indices, 0, len(landmarks_2d) - 1).astype(np.int32)
    logger.info(
        "Derived MP→FLAME mapping: %d unique correspondences"
        " (max dist=%.1f px, mean dist=%.1f px)",
        len(np.unique(mp_indices)), distances.mean(), distances.max(),
    )
    return mp_indices, mapping_distances


# ── Confidence-Weighted Reprojection ─────────────────────────────────

_LANDMARK_REGION_WEIGHTS = np.array([
    # Jaw (0-16) — MediaPipe traces the jaw along the visible outline, which
    # on a bearded face is the beard, not the bone. With the correspondence
    # fixed, letting those 17 points weigh half as much as an eye corner
    # widened the whole fitted face; at 0.3x the old values the median miss on
    # the 51 inner landmarks fell from 8.2 px to 4.6.
    0.15, 0.15, 0.165, 0.165, 0.165, 0.165, 0.15, 0.15,
    0.135, 0.135, 0.15, 0.18, 0.195, 0.195, 0.18, 0.165, 0.165,
    # Left eyebrow (17-21) — can be obscured by hair/lighting
    0.65, 0.70, 0.70, 0.65, 0.60,
    # Right eyebrow (22-26)
    0.65, 0.70, 0.70, 0.65, 0.60,
    # Nose bridge (27-30) — highly stable
    0.95, 1.00, 1.00, 0.95,
    # Nose (31-35) — most stable, nose tip is gold standard
    1.00, 1.00, 1.00, 1.00, 1.00,
    # Left eye (36-41) — stable, but can be occluded by glasses/hair
    0.90, 0.85, 0.85, 0.85, 0.85, 0.90,
    # Right eye (42-47)
    0.90, 0.85, 0.85, 0.85, 0.85, 0.90,
    # Outer mouth (48-59) — affected by expression, can be occluded
    0.75, 0.75, 0.70, 0.70, 0.70, 0.75,
    0.75, 0.75, 0.70, 0.70, 0.75, 0.75,
    # Inner mouth (60-67) — most affected by expression variation
    0.60, 0.60, 0.65, 0.65, 0.65, 0.65, 0.60, 0.60,
], dtype=np.float32)


def compute_landmark_weights(
    landmarks_2d: np.ndarray,
    image_width: int,
    image_height: int,
    mp_indices: np.ndarray,
    mapping_distances: np.ndarray,
    valid_mask: np.ndarray,
) -> np.ndarray:
    """Compute per-landmark confidence weights from multiple geometric cues.

    Weights combine three signals:
      1. **Semantic region prior** — facial regions weighted by anatomical
         stability (nose=1.0, eyes=0.85, jaw=0.5, inner mouth=0.6, etc.)
      2. **Image-boundary penalty** — landmarks near the photo edge are
         less reliable (likely truncated or distorted)
      3. **Mapping-distance penalty** — if the model-derived FLAME→MediaPipe
         correspondence has a large 2D gap, the mapping is less reliable

    Final weights are normalised so the *mean* weight over valid landmarks
    is 1.0, keeping the reprojection-error scale consistent for regularization.

    Args:
        landmarks_2d: (N, 2) detected MediaPipe landmark positions
        image_width, image_height: photo dimensions
        mp_indices: (68,) MediaPipe indices from derive_mp68_mapping
        mapping_distances: (68,) pixel distances from derive_mp68_mapping
        valid_mask: (68,) boolean mask of valid correspondences

    Returns:
        (N_valid,) float32 weights in roughly [0.2, 1.5], mean ≈ 1.0
    """
    n_total = len(mp_indices)

    # 1. Semantic region prior
    region_w = _LANDMARK_REGION_WEIGHTS.copy()  # (68,)

    # 2. Image-boundary penalty
    # For each landmark, compute the distance (in normalized coords) to
    # the nearest image edge. Use the MediaPipe 2D positions.
    mp_x = landmarks_2d[mp_indices, 0]
    mp_y = landmarks_2d[mp_indices, 1]

    # Normalized distance to nearest edge [0, 0.5]
    edge_dist_x = np.minimum(mp_x, image_width - 1.0 - mp_x) / image_width
    edge_dist_y = np.minimum(mp_y, image_height - 1.0 - mp_y) / image_height
    edge_dist = np.minimum(edge_dist_x, edge_dist_y)  # (68,)

    # Sigmoid-like penalty: w=1.0 when distance > 0.15, drops to 0.2 at edge
    edge_penalty = 0.2 + 0.8 / (1.0 + np.exp(-20.0 * (edge_dist - 0.10)))

    # 3. Mapping-distance penalty
    # Normalise distances by a fraction of image width
    norm_dist = mapping_distances / (0.15 * max(image_width, image_height))
    # Sigmoid: w=1.0 when distance small, drops as distance grows
    dist_penalty = 1.0 / (1.0 + 0.5 * norm_dist ** 2)

    # Combine: geometric mean of all three factors
    combined = (region_w * edge_penalty * dist_penalty) ** (1.0 / 3.0)

    # Apply valid mask and normalise so mean(valid_weights) = 1.0
    valid_weights = combined[valid_mask]
    mean_w = valid_weights.mean()
    if mean_w > 1e-6:
        valid_weights = valid_weights / mean_w

    logger.info(
        "Landmark weights: range=[%.2f, %.2f], mean=%.2f, "
        "edge_penalty=%.2f, dist_penalty=%.2f",
        valid_weights.min(), valid_weights.max(), valid_weights.mean(),
        edge_penalty[valid_mask].mean(), dist_penalty[valid_mask].mean(),
    )
    return valid_weights.astype(np.float32)


def _find_next_best(
    all_points: np.ndarray,
    tree: "KDTree",
    target: np.ndarray,
    exclude_idx: int,
    seen: dict,
) -> int:
    """Find the next closest MediaPipe point to `target` that doesn't
    collide with an already-assigned index, among the 5 nearest neighbors."""
    distances, indices = tree.query(target.reshape(1, -1), k=10)
    for idx in indices[0]:
        if int(idx) != exclude_idx and int(idx) not in seen:
            return int(idx)
    # Fallback: use the second closest
    for idx in indices[0]:
        if int(idx) != exclude_idx:
            return int(idx)
    return int(indices[0, 0])


# ── Joint Camera + Identity Fitting ─────────────────────────────────

def fit_identity_from_landmarks(
    flame: FLAMELoader,
    landmarks_2d: np.ndarray,
    image_width: int,
    image_height: Optional[int] = None,
    n_components: int = 30,
    reg_strength: float = 5.0,
    n_iters: int = 30,
    unseen_reg: Optional[float] = None,
) -> np.ndarray:
    """Fit FLAME identity coefficients with joint camera optimization.

    Improvements over the basic weak-perspective fitting:
      1. **Model-derived correspondences**: The MediaPipe 478→FLAME 68
         landmark mapping is derived from mesh geometry rather than
         hardcoded, avoiding duplicate indices and mismatches.
      2. **Joint camera + identity optimization**: Camera parameters
         (log-scale, translation, in-plane rotation) are optimized
         simultaneously with identity coefficients, allowing the
         optimizer to find the best-fitting camera and shape jointly.
      3. **Confidence-weighted reprojection**: Each landmark contributes
         to the loss weighted by a combination of semantic region prior,
         image-boundary proximity, and mapping-distance reliability.

    The camera model uses a full 2D similarity transform:
      projected = exp(log_scale) * R(angle) * flipY(xyz[:,:2]) + [tx, ty]

    Args:
        flame: FLAME model
        landmarks_2d: (478, 2) MediaPipe landmarks
        image_width: image width in pixels
        image_height: image height in pixels (optional, for edge penalty)
        n_components: number of PCA components to optimize
        reg_strength: regularization weight (higher = closer to mean)
        n_iters: max optimization iterations

    Returns:
        (300,) identity coefficients (zero = mean face)
    """
    from scipy.optimize import minimize

    n_lmks_total = min(len(landmarks_2d), 478)

    # Step 1: Derive landmark correspondence from mesh geometry
    mean_verts = flame.generate_mesh()
    mp_indices, mapping_distances = (
        semantic_mp68_mapping(landmarks_2d)
        or derive_mp68_mapping(flame, mean_verts, landmarks_2d, image_width)
    )  # (68,), (68,)

    # Also get the valid FLAME landmark indices (all 68 from the model)
    flame_landmark_inds = flame.lmk_inds  # all 68 indices are valid

    # Filter to only valid MediaPipe indices
    valid_mask = mp_indices < n_lmks_total
    mp_idx_subset = mp_indices[valid_mask]
    flame_idx_subset = flame_landmark_inds[valid_mask]

    # 2D observations
    observed_2d = landmarks_2d[mp_idx_subset]  # (N, 2)

    # FLAME 3D landmarks (mean face)
    mean_lmks_3d = flame.get_landmarks(mean_verts)[valid_mask]  # (N, 3)

    n_lmks = len(observed_2d)
    if n_lmks < 10:
        logger.warning("Too few landmarks (%d) for identity fitting", n_lmks)
        return np.zeros(300)

    # ── Compute confidence weights ──
    if image_height is None:
        image_height = max(image_width, int(image_width * 1.2))
    weights = compute_landmark_weights(
        landmarks_2d, image_width, image_height,
        mp_indices, mapping_distances, valid_mask,
    )  # (N,) normalised so mean ≈ 1.0

    # ── Initial camera estimate ──
    # FLAME Y points up, MediaPipe Y points down: negate FLAME Y
    flame_xy = np.column_stack([
        mean_lmks_3d[:, 0],
        -mean_lmks_3d[:, 1],
    ])
    flame_xy_c = flame_xy - flame_xy.mean(axis=0)
    obs_2d_c = observed_2d - observed_2d.mean(axis=0)

    scale_init = np.std(obs_2d_c) / (np.std(flame_xy_c) + 1e-8)
    tx_init = observed_2d[:, 0].mean()
    ty_init = observed_2d[:, 1].mean()
    log_scale_init = np.log(max(scale_init, 1e-6))
    angle_init = 0.0

    # ── Build landmark basis for identity deformation ──
    lmk_basis = flame.landmark_basis()[valid_mask]  # (N, 3, 300)
    # Each landmark gives 3 rows (x, y, z offset), but we only use x, y
    # in the objective (z doesn't affect weak perspective projection)
    lmk_basis_xy = lmk_basis[:, :2, :n_components]  # (N, 2, n_components)
    lmk_basis_flat = lmk_basis_xy.reshape(n_lmks * 2, n_components)

    # Normalize basis columns to unit variance for better conditioning
    basis_std = np.std(lmk_basis_flat, axis=0)
    basis_std = np.where(basis_std > 1e-8, basis_std, 1.0)
    lmk_basis_norm = lmk_basis_flat / basis_std  # (N*2, n_components)

    # What a frontal photograph cannot see, it cannot fit - but FLAME's identity
    # components are global, so the coefficients bought to match the face also
    # move the neck. Unconstrained, that went both ways: with the old scrambled
    # landmarks the neck came out 20 mm long against the mean's 80, and with the
    # correct ones it came out 141 mm - a small face on a stretched throat. So
    # penalise how far the unseen vertices move, in pixels at the fitted scale,
    # the same units the landmark error is in.
    if unseen_reg is None:
        unseen_reg = UNSEEN_REGULARISATION
    unseen_basis = None
    if unseen_reg > 0 and UNSEEN_VERTICES is not None:
        ub = flame.identity_basis[UNSEEN_VERTICES][:, :, :n_components]
        unseen_basis = ub.reshape(-1, n_components) / basis_std   # (U*3, n)

    # ── Joint objective: camera(4) + identity(n_components) ──
    def objective(params):
        # Unpack
        log_scale = params[0]
        tx = params[1]
        ty = params[2]
        angle = params[3]
        coeffs = params[4:]  # (n_components,)

        # Identity deformation (in normalized basis space)
        offset_flat = lmk_basis_norm @ coeffs  # (N*2,)
        offset_xy = offset_flat.reshape(-1, 2)  # (N, 2)

        # Deformed 2D landmark positions (FLAME coords: Y up)
        deformed_xy = mean_lmks_3d[:, :2] + offset_xy  # Add offset in FLAME coords
        # NOW flip Y to image coords (FLAME Y up → image Y down)
        deformed_xy = np.column_stack([deformed_xy[:, 0], -deformed_xy[:, 1]])

        # Apply in-plane rotation
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        rotated_x = cos_a * deformed_xy[:, 0] - sin_a * deformed_xy[:, 1]
        rotated_y = sin_a * deformed_xy[:, 0] + cos_a * deformed_xy[:, 1]

        # Scale and translate
        s = np.exp(log_scale)
        projected_x = s * rotated_x + tx
        projected_y = s * rotated_y + ty

        # ── Confidence-weighted reprojection error ──
        error_x = projected_x - observed_2d[:, 0]
        error_y = projected_y - observed_2d[:, 1]
        # Each landmark contributes error^2 * weight, then weighted average
        reproj = np.sum(weights * (error_x ** 2 + error_y ** 2)) / weights.sum()

        # Regularization: identity coefficients (pulled toward mean face).
        # Penalise in FLAME sigma units, not normalised-basis units. `coeffs`
        # are divided by `basis_std` on the way out, so a component with little
        # landmark influence is amplified; penalising the raw normalised value
        # left those effectively unconstrained.
        reg = reg_strength * np.sum((coeffs / basis_std) ** 2) / max(1, n_components)
        if unseen_basis is not None:
            moved = np.exp(log_scale) * (unseen_basis @ coeffs)
            reg += unseen_reg * np.mean(moved ** 2) * 3.0

        # Mild regularization on camera to prevent extreme values
        cam_reg = 0.01 * (log_scale ** 2 + angle ** 2 + tx ** 2 + ty ** 2) / (image_width ** 2)

        return reproj + reg + cam_reg

    # ── Initial guess ──
    x0 = np.concatenate([
        [log_scale_init, tx_init, ty_init, angle_init],
        np.zeros(n_components),
    ])

    # ── Bounds: camera unbounded, identity clamped to a plausible face ──
    # FLAME identity coefficients are standard deviations of the shape PCA; a
    # real human sits within ~3. Leaving them unbounded let the optimiser buy a
    # few pixels of landmark accuracy with absurd deformation — fits were
    # reaching 36 sigma and displacing vertices by ~98% of head height, which
    # both mangled the mesh and made the texture projection sample hair and
    # background instead of skin.
    # The bound is expressed in normalised-basis units so that after the
    # `/ basis_std` un-normalisation below it means +/-IDENTITY_SIGMA_LIMIT.
    ident_bounds = [
        (-IDENTITY_SIGMA_LIMIT * s, IDENTITY_SIGMA_LIMIT * s) for s in basis_std
    ]
    bounds = [(None, None)] * 4 + ident_bounds

    result = minimize(
        objective,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": n_iters, "ftol": 1e-7, "gtol": 1e-7},
    )

    # ── Extract results ──
    log_scale_opt = result.x[0]
    tx_opt = result.x[1]
    ty_opt = result.x[2]
    angle_opt = result.x[3]
    opt_coeffs = result.x[4:]

    # Un-normalize coefficients (undo the basis normalization), then clamp as a
    # belt-and-braces guarantee: the bounds above should already hold, but this
    # keeps a diverged solve from ever reaching the mesh.
    identity_coeffs = np.zeros(300)
    identity_coeffs[:n_components] = np.clip(
        opt_coeffs / basis_std, -IDENTITY_SIGMA_LIMIT, IDENTITY_SIGMA_LIMIT,
    )

    logger.info(
        "Identity fit: %d iters, loss=%.2f, cam=(s=%.1f, tx=%.0f, ty=%.0f, θ=%.1f°), "
        "identity range=[%.3f, %.3f] (weights=[%.2f, %.2f])",
        result.nit, result.fun,
        np.exp(log_scale_opt), tx_opt, ty_opt, np.degrees(angle_opt),
        identity_coeffs.min(), identity_coeffs.max(),
        weights.min(), weights.max(),
    )
    return identity_coeffs


# ── Normal Computation ────────────────────────────────────────────────

def compute_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Compute smooth vertex normals via angle-weighted face normal averaging."""
    normals = np.zeros_like(vertices)
    weights = np.zeros(len(vertices))

    for face in faces:
        i0, i1, i2 = int(face[0]), int(face[1]), int(face[2])
        v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]

        e1 = v1 - v0
        e2 = v2 - v0
        fn = np.cross(e1, e2)
        fn_len = np.linalg.norm(fn)
        if fn_len < 1e-10:
            continue
        fn = fn / fn_len

        for i_cur, i_prev, i_next in [(i0, i2, i1), (i1, i0, i2), (i2, i1, i0)]:
            v_cur, v_prev, v_next = vertices[i_cur], vertices[i_prev], vertices[i_next]
            e_a = v_prev - v_cur
            e_b = v_next - v_cur
            len_a = np.linalg.norm(e_a)
            len_b = np.linalg.norm(e_b)
            if len_a < 1e-10 or len_b < 1e-10:
                continue
            cos_angle = max(-1.0, min(1.0, np.dot(e_a, e_b) / (len_a * len_b)))
            angle = math.acos(cos_angle)
            normals[i_cur] += fn * angle
            weights[i_cur] += angle

    for i in range(len(normals)):
        if weights[i] > 0:
            n = normals[i] / weights[i]
            n_len = np.linalg.norm(n)
            normals[i] = n / n_len if n_len > 0 else np.array([0.0, 1.0, 0.0])
        else:
            v = vertices[i]
            v_len = np.linalg.norm(v)
            normals[i] = v / v_len if v_len > 0 else np.array([0.0, 1.0, 0.0])

    return normals


# ═══════════════════════════════════════════════════════════════════
# TEXTURE PROJECTION — Project photo onto FLAME UV atlas
# ═══════════════════════════════════════════════════════════════════

_TEXTURE_ATLAS_PATH = os.path.join(
    _PROJECT_ROOT, "weights", "flame", "FLAME_texture.npz"
)


def load_texture_atlas() -> dict:
    """Load FLAME texture atlas data (UV coordinates + mean texture)."""
    if not os.path.exists(_TEXTURE_ATLAS_PATH):
        raise FileNotFoundError(f"FLAME texture atlas not found: {_TEXTURE_ATLAS_PATH}")
    tex = np.load(_TEXTURE_ATLAS_PATH)
    return {
        "vt": tex["vt"].astype(np.float32),     # (5118, 2)
        "ft": tex["ft"].astype(np.int32),        # (9976, 3)
        "mean": tex["mean"].astype(np.uint8),    # (512, 512, 3)
        "tex_dir": tex["tex_dir"],               # (512, 512, 3, 200)
    }


def build_vertex_uv_map(
    faces: np.ndarray,
    ft: np.ndarray,
    vt: np.ndarray,
    num_vertices: int,
) -> np.ndarray:
    """Build per-vertex UV coordinates from face-UV correspondence.

    Both `faces` and `ft` have shape (9976, 3) and correspond 1:1.
    Face i uses vertices faces[i] and UV indices ft[i].
    For each mesh vertex we average the UVs of all faces that use it.

    Returns: (num_vertices, 2) UV coordinates in [0, 1] range.
    """
    uv_sum = np.zeros((num_vertices, 2), dtype=np.float64)
    uv_count = np.zeros(num_vertices, dtype=np.int32)

    for fi in range(len(faces)):
        v_idx = faces[fi]
        uv_idx = ft[fi]
        for j in range(3):
            vi = v_idx[j]
            if vi < num_vertices:
                uvi = uv_idx[j]
                uv_sum[vi] += vt[uvi]
                uv_count[vi] += 1

    vertex_uv = np.zeros((num_vertices, 2), dtype=np.float32)
    mask = uv_count > 0
    vertex_uv[mask] = (uv_sum[mask] / uv_count[mask, None]).astype(np.float32)

    # For any vertex without a UV (e.g. neck, ears), use nearest neighbor
    if not np.all(mask):
        from scipy.spatial import cKDTree
        masked_pts = vertex_uv[mask]
        if len(masked_pts) > 0:
            tree = cKDTree(masked_pts)
            query_pts = vertex_uv[~mask]
            # Use (0.5, 0.5) as fallback if no nearest found
            fallback_uv = np.array([0.5, 0.5], dtype=np.float32)
            if len(query_pts) > 0:
                _, idx = tree.query(query_pts)
                vertex_uv[~mask] = masked_pts[idx]
            else:
                vertex_uv[~mask] = fallback_uv

    return vertex_uv


def estimate_head_pose(
    landmarks_3d: np.ndarray,
    landmarks_2d: np.ndarray,
    image_width: int,
    image_height: int,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """Estimate head pose (rotation + translation) via PnP.

    Args:
        landmarks_3d: (N, 3) 3D FLAME landmark positions
        landmarks_2d: (N, 2) corresponding 2D image positions
        image_width, image_height: image dimensions

    Returns:
        (rvec, tvec, camera_matrix) or (None, None, None) on failure
    """
    import cv2

    focal_length = max(image_width, image_height)
    cx, cy = image_width / 2.0, image_height / 2.0
    camera_matrix = np.array([
        [focal_length, 0.0, cx],
        [0.0, focal_length, cy],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    try:
        success, rvec, tvec = cv2.solvePnP(
            landmarks_3d.astype(np.float64),
            landmarks_2d.astype(np.float64),
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if success:
            return rvec, tvec, camera_matrix
    except Exception as e:
        logger.warning("Head pose estimation failed: %s", e)

    return None, None, None


def project_vertices_to_photo(
    vertices_3d: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
    camera_matrix: np.ndarray,
) -> np.ndarray:
    """Project 3D mesh vertices to 2D photo coordinates.

    Returns: (N, 2) pixel coordinates.
    """
    import cv2
    points_2d, _ = cv2.projectPoints(
        vertices_3d.astype(np.float64),
        rvec, tvec, camera_matrix, None,
    )
    return points_2d.reshape(-1, 2).astype(np.float32)


# Weight of the prior that keeps unseen anatomy near the mean shape. Swept on
# the reference portrait, where the mean neck is 80 mm:
#
#     weight    neck    head height   brow-chin/eyes   inner-landmark miss
#       0       145 mm     387 mm         1.53              4.6 px
#       0.1      98        329            1.48              -
#       0.5      90        325            1.49              3.4
#       2.0      85        325            1.53              3.0
#
# (photograph: brow-chin/eyes 1.50). 0.5 brings the neck within ~12% of the
# mean while the face's own proportions stay on the photograph's.
UNSEEN_REGULARISATION = 0.5


def _load_unseen_vertices() -> Optional[np.ndarray]:
    """The neck and the ring along its base: never in a portrait's view."""
    try:
        path = os.path.join(os.path.dirname(_DEFAULT_MODEL_PATH), "FLAME_masks.pkl")
        with open(path, "rb") as f:
            masks = pickle.load(f, encoding="latin1")
        idx = np.unique(np.concatenate([np.asarray(masks["neck"], np.int64),
                                        np.asarray(masks["boundary"], np.int64)]))
        return idx[:: max(1, len(idx) // 400)]
    except Exception as exc:
        logger.info("FLAME masks unavailable (%s); no prior on unseen anatomy", exc)
        return None


UNSEEN_VERTICES = _load_unseen_vertices()

# Landmarks the texture camera is solved from: everything but the jaw.
POSE_LANDMARKS = np.arange(17, 68)

# Parser classes that belong to the subject's head (CelebAMask-HQ order). The
# texture must not sample background, clothing, a hat or jewellery onto the
# head: with no mask at all, the ears came out white where they sampled the
# studio backdrop and the throat carried the shirt collar.
_HEAD_PARSE_CLASSES = (1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 17)


def head_parse_mask(photo_bgr: np.ndarray):
    """Pixels of the photograph that are the subject's head, and their skin tone.

    Returns (mask, skin_rgb). The skin tone is the median of the parser's SKIN
    class, for filling what the camera never saw. It used to be the median of
    every covered texel, which once the scalp was allowed to sample hair came
    out as a muddy brown - a colour no part of the subject actually is.

    (None, None) if the parser is unavailable, which leaves sampling exactly
    as it was rather than failing the texture.
    """
    try:
        import cv2
        from PIL import Image

        from dreamtalk.face.core.lipsync.musetalk.utils.face_parsing.model import (
            FaceParsing,
        )

        parsed = np.asarray(FaceParsing()(
            Image.fromarray(cv2.cvtColor(photo_bgr, cv2.COLOR_BGR2RGB)), mode="all"))
        h, w = photo_bgr.shape[:2]
        if parsed.shape[:2] != (h, w):
            parsed = cv2.resize(parsed, (w, h), interpolation=cv2.INTER_NEAREST)
        mask = np.isin(parsed, _HEAD_PARSE_CLASSES).astype(np.uint8)
        skin = parsed == 1
        # Keep only the part of the mask joined to the face. The parser is
        # wrong in small places far from the head - on the reference portrait
        # it labelled 8% of the TIE as eyeglasses, an allowed class, and the
        # knot came out on the throat in navy. Anything the collar separates
        # from the skin is not the head, whatever it was labelled.
        count, comp = cv2.connectedComponents(mask)
        if count > 2 and skin.any():
            overlap = np.bincount(comp[skin], minlength=count)
            overlap[0] = 0
            mask = (comp == int(np.argmax(overlap))).astype(np.uint8)
        skin_rgb = (np.median(photo_bgr[skin], axis=0)[::-1].astype(np.float32)
                    if int(skin.sum()) > 500 else None)
        # A thin erosion keeps a vertex on the silhouette from straddling the
        # backdrop by a pixel.
        return cv2.erode(mask, np.ones((5, 5), np.uint8)), skin_rgb
    except Exception as exc:
        logger.info("Head parse mask unavailable (%s); sampling unmasked", exc)
        return None, None


def vertex_occlusion(vertices_3d: np.ndarray, faces: np.ndarray,
                     pixels_2d: np.ndarray, rvec: np.ndarray, tvec: np.ndarray,
                     image_size: Tuple[int, int], tolerance: float = 0.004,
                     downscale: int = 2) -> np.ndarray:
    """Which vertices the camera actually saw, not merely faced.

    Facing the camera is not the same as being seen. The underside of the jaw
    and the front of the neck face the lens and sit behind the chin; the
    visibility test used to be the normal alone, so those surfaces sampled the
    beard and collar in front of them, and because a triangle is written only
    when all three of its corners pass, the boundary came out in whole-triangle
    blocks - the tiger stripes down the neck.

    Rasterises the mesh's camera-space depth into a buffer at the photo's
    resolution (halved - a vertex is a few pixels across), and keeps a vertex
    only if nothing nearer covers its pixel.
    """
    import cv2

    h, w = image_size[1] // downscale, image_size[0] // downscale
    R, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64))
    cam = vertices_3d @ R.T + np.asarray(tvec, dtype=np.float64).reshape(1, 3)
    z = cam[:, 2]
    px = pixels_2d / float(downscale)
    depth = np.full((h, w), np.inf)
    for a, b, c in faces:
        tri = px[[a, b, c]]
        lo = np.floor(tri.min(0)).astype(int)
        hi = np.ceil(tri.max(0)).astype(int)
        x0, y0 = max(lo[0], 0), max(lo[1], 0)
        x1, y1 = min(hi[0], w - 1), min(hi[1], h - 1)
        if x0 > x1 or y0 > y1:
            continue
        (xa, ya), (xb, yb), (xc, yc) = tri
        den = (yb - yc) * (xa - xc) + (xc - xb) * (ya - yc)
        if abs(den) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        l1 = ((yb - yc) * (gx - xc) + (xc - xb) * (gy - yc)) / den
        l2 = ((yc - ya) * (gx - xc) + (xa - xc) * (gy - yc)) / den
        l3 = 1.0 - l1 - l2
        ins = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not ins.any():
            continue
        zz = l1 * z[a] + l2 * z[b] + l3 * z[c]
        cur = depth[gy[ins], gx[ins]]
        depth[gy[ins], gx[ins]] = np.minimum(cur, zz[ins])
    xi = np.clip(np.round(px[:, 0]).astype(int), 0, w - 1)
    yi = np.clip(np.round(px[:, 1]).astype(int), 0, h - 1)
    return z <= depth[yi, xi] + tolerance


def sample_colors_from_photo(
    photo_img: np.ndarray,
    pixels_2d: np.ndarray,
) -> np.ndarray:
    """Bilinearly sample RGB colors from a photo at given pixel positions.

    Args:
        photo_img: (H, W, 3) BGR image (OpenCV format)
        pixels_2d: (N, 2) pixel coordinates

    Returns:
        (N, 3) RGB float32 colors in [0, 255] range
    """
    h, w = photo_img.shape[:2]
    x = np.clip(pixels_2d[:, 0], 0.0, w - 1.0)
    y = np.clip(pixels_2d[:, 1], 0.0, h - 1.0)

    x0 = np.floor(x).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y0 = np.floor(y).astype(np.int32)
    y1 = np.minimum(y0 + 1, h - 1)

    wx = x - x0.astype(np.float32)
    wy = y - y0.astype(np.float32)

    # Photo is BGR, convert to RGB
    photo_rgb = photo_img[:, :, ::-1].astype(np.float32)

    colors = (
        (1.0 - wx)[:, None] * (1.0 - wy)[:, None] * photo_rgb[y0, x0]
        + wx[:, None] * (1.0 - wy)[:, None] * photo_rgb[y0, x1]
        + (1.0 - wx)[:, None] * wy[:, None] * photo_rgb[y1, x0]
        + wx[:, None] * wy[:, None] * photo_rgb[y1, x1]
    )
    return np.clip(colors, 0.0, 255.0)


def generate_uv_texture(
    vertex_uv: np.ndarray,
    vertex_colors: np.ndarray,
    mean_texture: np.ndarray,
    faces: np.ndarray,
    ft: np.ndarray,
    vt: np.ndarray,
    output_size: int = TEXTURE_ATLAS_SIZE,
    *,
    photo_img: Optional[np.ndarray] = None,
    vertex_px: Optional[np.ndarray] = None,
    head_mask: Optional[np.ndarray] = None,
    vertex_visible: Optional[np.ndarray] = None,
    fill_rgb: Optional[np.ndarray] = None,
    vertex_confidence: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Generate a UV texture atlas from per-vertex colors.

    Strategy:
      1. Split UV space into an output_size×output_size grid.
      2. For each face, render its UV triangle into the atlas, filling
         with barycentrically-interpolated vertex colors.
      3. Blend with mean FLAME texture for regions unseen in the photo.

    Args:
        vertex_uv: (N, 2) per-vertex UV coordinates in [0, 1]
        vertex_colors: (N, 3) per-vertex RGB colors from photo in [0, 255]
        mean_texture: (512, 512, 3) uint8 mean FLAME texture
        faces: (F, 3) vertex face indices
        ft: (F, 3) UV index face indices
        vt: (M, 2) UV coordinates
        output_size: output texture resolution

    Returns:
        (output_size, output_size, 3) uint8 texture image
    """
    texture = np.zeros((output_size, output_size, 3), dtype=np.float32)
    weight = np.zeros((output_size, output_size), dtype=np.float32)

    # Which vertices actually saw the subject?
    #
    # sample_colors_from_photo CLIPS projected coordinates into the image, so
    # a vertex on the back of the skull - which the camera never saw - does
    # not fail. It silently samples whatever sits at the nearest image edge:
    # backdrop, suit shoulder, hair. Those colours are then "covered" as far
    # as the weight buffer is concerned, so the gap fill never touches them,
    # and the atlas keeps a dark smear where the back of the head should be.
    # Measured on a rebuilt avatar: 10.9% of the atlas still black even with
    # the gap fill running, because those texels were never gaps.
    #
    # A face is only written if all three of its vertices projected strictly
    # inside the frame, and inside the head silhouette when one is supplied.
    # Everything else is left uncovered so the skin fill below owns it.
    vertex_valid = None
    if vertex_px is not None and photo_img is not None:
        ph, pw = photo_img.shape[:2]
        inside = (
            (vertex_px[:, 0] >= 0) & (vertex_px[:, 0] <= pw - 1)
            & (vertex_px[:, 1] >= 0) & (vertex_px[:, 1] <= ph - 1)
        )
        if head_mask is not None:
            xi = np.clip(vertex_px[:, 0].astype(np.int32), 0, pw - 1)
            yi = np.clip(vertex_px[:, 1].astype(np.int32), 0, ph - 1)
            inside &= head_mask[yi, xi] > 0
        # The decisive test. A frontal photo shows one side of a closed
        # surface, and the far side projects back INSIDE the frame, over the
        # face - so a bounds check cannot catch it. Only the surface normal
        # can: a vertex whose normal points away from the camera was never
        # photographed, whatever pixel it happens to land on.
        if vertex_visible is not None:
            inside &= vertex_visible
        vertex_valid = inside
        logger.info("Texture sampling: %.1f%% of vertices projected onto the subject",
                    100.0 * float(inside.mean()))

    # How much to trust the photograph at each vertex, 0..1, rather than a
    # yes/no. A triangle used to be written only when all three corners
    # passed, so wherever visibility changed - the silhouette, the back of the
    # neck, the edge of the jaw - the atlas flipped between photograph and fill
    # colour in whole-triangle blocks: the tiger stripes down the neck. With a
    # confidence per vertex, interpolated per texel, the photograph fades into
    # the fill instead of switching, and grazing-angle samples - stretched and
    # usually shadow - count for little.
    vertex_conf = None
    if vertex_valid is not None:
        vertex_conf = vertex_valid.astype(np.float32)
        if vertex_confidence is not None:
            vertex_conf = vertex_conf * np.clip(
                np.asarray(vertex_confidence, dtype=np.float32), 0.0, 1.0)

    # Render each face as a UV triangle
    # Use the UV coordinates from vt indexed by ft, not vertex_uv, for
    # the triangle rasterization, then sample colors via vertex_uv
    for fi in range(len(faces)):
        v_idx = faces[fi]  # (3,) vertex indices
        uv_idx = ft[fi]     # (3,) UV coordinate indices into vt

        if vertex_conf is not None and not vertex_conf[v_idx].any():
            continue

        # UV triangle in pixel space
        uv_px = np.zeros((3, 2), dtype=np.float32)
        for j in range(3):
            uv_px[j] = vt[uv_idx[j]] * (output_size - 1)

        # Vertex colors
        tri_colors = np.array([
            vertex_colors[v_idx[0]],
            vertex_colors[v_idx[1]],
            vertex_colors[v_idx[2]],
        ], dtype=np.float32)

        # Rasterize UV triangle
        min_x = max(0, int(np.floor(uv_px[:, 0].min())))
        max_x = min(output_size - 1, int(np.ceil(uv_px[:, 0].max())))
        min_y = max(0, int(np.floor(uv_px[:, 1].min())))
        max_y = min(output_size - 1, int(np.ceil(uv_px[:, 1].max())))

        if min_x >= max_x or min_y >= max_y:
            continue

        # Vectorised barycentric check for the bounding box
        xs = np.arange(min_x, max_x + 1, dtype=np.float32)
        ys = np.arange(min_y, max_y + 1, dtype=np.float32)
        xx, yy = np.meshgrid(xs, ys)
        px = np.stack([xx, yy], axis=-1)  # (H, W, 2)

        # Compute barycentric coordinates
        v0 = uv_px[1] - uv_px[0]
        v1 = uv_px[2] - uv_px[0]
        v2 = px - uv_px[0]

        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = v2[..., 0] * v0[0] + v2[..., 1] * v0[1]
        d21 = v2[..., 0] * v1[0] + v2[..., 1] * v1[1]

        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-12:
            continue

        b = (d11 * d20 - d01 * d21) / denom
        g = (d00 * d21 - d01 * d20) / denom
        a = 1.0 - b - g

        # Inside triangle mask
        inside = (a >= -1e-6) & (b >= -1e-6) & (g >= -1e-6)

        if not np.any(inside):
            continue

        if vertex_px is not None:
            # Per-texel photo sampling ("texture baking"). Interpolating
            # per-vertex colours caps detail at one sample per vertex (5023 for
            # FLAME), so a larger atlas only smooths — it cannot add skin
            # detail. Sampling the photo once per texel does.
            #
            # We interpolate the already-projected 2D positions rather than
            # interpolating 3D and re-projecting: the latter needs a
            # projectPoints call per triangle (~10k calls, ~6 min) for a
            # perspective correction that is negligible across a single
            # face-sized triangle.
            tri_px = vertex_px[v_idx]                          # (3,2)
            uvpos = (a[..., None] * tri_px[0]
                     + b[..., None] * tri_px[1]
                     + g[..., None] * tri_px[2])               # (H,W,2)
            if vertex_conf is not None:
                cv = vertex_conf[v_idx]
                conf = a * cv[0] + b * cv[1] + g * cv[2]
            else:
                conf = np.ones_like(a)
            if head_mask is not None:
                # Per texel, not per vertex: a triangle whose corners all sit
                # on the neck can still span the knot of a tie in between.
                mh, mw = head_mask.shape[:2]
                mx = np.clip(uvpos[..., 0].astype(np.int32), 0, mw - 1)
                my = np.clip(uvpos[..., 1].astype(np.int32), 0, mh - 1)
                conf = conf * (head_mask[my, mx] > 0)
            use = inside & (conf > 1e-3)
            sel = uvpos[use]
            if sel.size:
                cols = sample_colors_from_photo(photo_img, sel)  # (M,3) RGB
                wsel = conf[use]
                for c in range(3):
                    tex_slice = texture[min_y:max_y + 1, min_x:max_x + 1, c]
                    tex_slice[use] += cols[:, c] * wsel
                w_slice = weight[min_y:max_y + 1, min_x:max_x + 1]
                w_slice[use] += wsel
                weight[min_y:max_y + 1, min_x:max_x + 1] = w_slice
            continue
        else:
            # Sample colors via barycentric interpolation of vertex colours
            for c in range(3):
                tex_slice = texture[min_y:max_y + 1, min_x:max_x + 1, c]
                color_vals = (
                    a * tri_colors[0, c] + b * tri_colors[1, c] + g * tri_colors[2, c]
                )
                tex_slice[inside] += color_vals[inside]

        w_slice = weight[min_y:max_y + 1, min_x:max_x + 1]
        w_slice[inside] += 1.0
        weight[min_y:max_y + 1, min_x:max_x + 1] = w_slice

    # Average overlapping triangles
    mask = weight > 0
    for c in range(3):
        texture[..., c] = np.divide(texture[..., c], weight, where=mask)
    # How much of each texel is photograph; the rest is filled below. The
    # weight is a sum of confidences, 1 wherever a single well-seen triangle
    # covers the texel.
    confidence = np.clip(weight, 0.0, 1.0)
    photo_part = np.clip(texture, 0.0, 255.0)
    # Only confidently-seen texels seed the fill; weak ones are blended over it.
    mask = confidence > 0.5

    # Report gaps
    if not np.all(mask):
        logger.info("Texture atlas coverage: %.1f%% (%.1f%% filled from mean texture)",
                    100.0 * mask.mean(), 100.0 * (1.0 - mask.mean()))

    # ── Fill what the photograph could not see ────────────────────────
    #
    # A single frontal photo covers the front of the head and nothing else,
    # so a substantial part of the atlas is never written: measured on a real
    # fitted head, 14.7% of the 1024² atlas was still black and a further 8.8%
    # was flat grey. Those are the sides, the back of the scalp and the
    # underside of the jaw, and they are why the rendered head reads as a
    # photograph pasted on a mask rather than as a person.
    #
    # The grey came from filling gaps with the shipped mean FLAME atlas: that
    # is a different, averaged face, so it lands as an obviously foreign skin
    # tone next to the subject's own. Seeding with the subject's OWN median
    # skin colour and letting cv2 inpaint propagate surrounding texture into
    # the hole keeps one person's complexion across the whole head.
    uncovered = ~mask
    texture = np.clip(texture, 0.0, 255.0).astype(np.uint8)
    if np.any(uncovered) and np.any(mask):
        try:
            import cv2
            skin = (np.asarray(fill_rgb, dtype=np.float32).clip(0, 255).astype(np.uint8)
                    if fill_rgb is not None
                    else np.median(texture[mask], axis=0).astype(np.uint8))
            texture[uncovered] = skin
            # Inpaint only the boundary band: Telea smears over very large
            # voids, but across the seam it blends the real texture outward,
            # which is what removes the hard edge.
            holes = uncovered.astype(np.uint8)
            band = cv2.dilate(holes, np.ones((9, 9), np.uint8)) - cv2.erode(
                holes, np.ones((9, 9), np.uint8))
            texture = cv2.inpaint(texture, band, 6, cv2.INPAINT_TELEA)
        except Exception as exc:
            logger.warning("Skin-tone gap fill unavailable (%s); "
                           "falling back to the mean FLAME atlas", exc)
            mean_tex = mean_texture.astype(np.float32)
            if mean_tex.shape[:2] != texture.shape[:2]:
                try:
                    import cv2
                    mean_tex = cv2.resize(
                        mean_tex, (texture.shape[1], texture.shape[0]),
                        interpolation=cv2.INTER_LINEAR)
                except Exception:
                    mean_tex = None
            if mean_tex is not None:
                texture[uncovered] = mean_tex[uncovered].astype(np.uint8)

    # Fade the photograph into the fill by its confidence, so there is no
    # boundary left to see.
    if vertex_px is not None:
        k = confidence[..., None]
        texture = (k * photo_part + (1.0 - k) * texture.astype(np.float32))
        texture = np.clip(texture, 0.0, 255.0).astype(np.uint8)

    # Light edge smoothing with a gentle blur
    try:
        import cv2
        # Smooth seams
        texture = cv2.medianBlur(texture, 3)
    except Exception:
        pass

    return texture


# ── Untextured OBJ / MTL Export (fallback) ───────────────────────────────

def export_obj(vertices: np.ndarray, normals: np.ndarray, faces: np.ndarray,
               obj_path: str, mtl_name: str = "generated_head.mtl"):
    """Write untextured Wavefront OBJ with v//vn face format."""
    with open(obj_path, "w") as f:
        f.write(f"# DreamTalk FLAME 3D Face Mesh\n")
        f.write(f"# {len(vertices)} vertices, {len(faces)} faces\n")
        f.write(f"mtllib {mtl_name}\n")
        f.write(f"usemtl skin_material\n\n")
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        f.write("\n")
        for n in normals:
            f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
        f.write("\n")
        for face in faces:
            idxs = " ".join(f"{int(i)+1}//{int(i)+1}" for i in face)
            f.write(f"f {idxs}\n")


def export_mtl(mtl_path: str):
    """Write untextured skin material MTL."""
    with open(mtl_path, "w") as f:
        f.write("""# DreamTalk FLAME Face Mesh Material
newmtl skin_material
Ka 0.85 0.75 0.65
Kd 0.92 0.82 0.72
Ks 0.30 0.25 0.20
Ns 40.0
d 1.0
illum 2
""")


# ── Textured OBJ / MTL Export ─────────────────────────────────────────

def export_textured_obj(
    vertices: np.ndarray,
    normals: np.ndarray,
    texcoords: np.ndarray,
    faces: np.ndarray,
    obj_path: str,
    mtl_name: str = "generated_head.mtl",
    face_uv: Optional[np.ndarray] = None,
):
    """Write Wavefront OBJ with texture coordinates (v/vt/vn format).

    With `face_uv` - FLAME's own per-corner UV indices (`ft`) into `texcoords`
    (`vt`) - each face corner names its own vt, which is what a UV SEAM needs:
    FLAME has 5118 UVs for 5023 vertices, because 95 vertices sit on a seam
    and need a different UV on each side of it. Without `face_uv`, every
    vertex gets exactly one UV and a triangle straddling a seam takes the
    wrong one for some corner, so it stretches across a third of the atlas.
    Measured on a shipped head: 136 such triangles, each spanning a median
    35% of the atlas, running down the back of the head and neck as a
    smeared stripe.
    """
    with open(obj_path, "w") as f:
        f.write(f"# DreamTalk FLAME 3D Face Mesh (textured)\n")
        f.write(f"# {len(vertices)} vertices, {len(faces)} faces\n")
        f.write(f"mtllib {mtl_name}\n")
        f.write(f"usemtl face_texture\n\n")

        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        f.write("\n")
        for vt in texcoords:
            f.write(f"vt {vt[0]:.6f} {vt[1]:.6f}\n")

        f.write("\n")
        for n in normals:
            f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")

        f.write("\n")
        for fi, face in enumerate(faces):
            if face_uv is not None:
                idxs = " ".join(
                    f"{int(i)+1}/{int(t)+1}/{int(i)+1}"
                    for i, t in zip(face, face_uv[fi])
                )
            else:
                idxs = " ".join(
                    f"{int(i)+1}/{int(i)+1}/{int(i)+1}" for i in face
                )
            f.write(f"f {idxs}\n")


def export_textured_mtl(mtl_path: str, texture_name: str = "face_texture.png"):
    """Write MTL file referencing the texture map.

    Uses moderate specular for natural skin appearance with photo texture.
    """
    with open(mtl_path, "w") as f:
        f.write(f"""# DreamTalk FLAME Face Mesh Textured Material
newmtl face_texture
Ka 1.0 1.0 1.0
Kd 1.0 1.0 1.0
Ks 0.15 0.12 0.10
Ns 30.0
d 1.0
illum 2
map_Kd {texture_name}
""")


# ── High-Level API ───────────────────────────────────────────────────

class FlameFitter:
    """High-level FLAME fitting service for pipeline integration.

    Usage:
        fitter = FlameFitter()
        result = fitter.fit_from_photo("path/to/photo.jpg")
        # result.obj_path, result.mtl_path, result.vertex_count, etc.
    """

    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self._flame: Optional[FLAMELoader] = None

    @property
    def flame(self) -> FLAMELoader:
        if self._flame is None:
            self._flame = FLAMELoader(self.model_path)
        return self._flame

    # ── Texture atlas state ────────────────────────────────────────────────

    def _load_texture(self):
        """Lazy-load texture atlas data."""
        if not hasattr(self, "_texture_data"):
            self._texture_data = load_texture_atlas()
        return self._texture_data

    def _get_vertex_uv(self):
        """Lazy-build per-vertex UV map."""
        if not hasattr(self, "_vertex_uv"):
            tex = self._load_texture()
            self._vertex_uv = build_vertex_uv_map(
                self.flame.faces, tex["ft"], tex["vt"], self.flame.num_vertices
            )
        return self._vertex_uv

    # ── Photo-to-texture pipeline ───────────────────────────────────────────

    def _generate_texture_from_photo(
        self,
        photo_path: str,
        vertices_3d: np.ndarray,
        landmarks_2d: np.ndarray,
        image_width: int,
        image_height: int,
        output_size: int = TEXTURE_ATLAS_SIZE,
    ) -> np.ndarray:
        """Generate a UV texture atlas by projecting the photo onto FLAME UV space.

        Steps:
          1. Build per-vertex UV mapping
          2. Estimate head pose (3D landmarks ↔ 2D landmarks)
          3. Project mesh vertices to photo plane
          4. Sample photo colors for each visible vertex
          5. Render UV texture atlas

        Returns:
            (output_size, output_size, 3) uint8 texture image
        """
        import cv2

        # Load the photo
        photo_bgr = cv2.imread(photo_path)
        if photo_bgr is None:
            logger.warning("Cannot read photo for texturing: %s", photo_path)
            return None

        # Build vertex UV map
        vertex_uv = self._get_vertex_uv()
        tex = self._load_texture()

        # Derive landmark correspondence from geometry
        mp_indices, _ = (
            semantic_mp68_mapping(landmarks_2d)
            or derive_mp68_mapping(
                self.flame,
                vertices_3d,
                landmarks_2d,
                image_width or photo_bgr.shape[1],
            )
        )
        valid_mp = mp_indices < len(landmarks_2d)
        mp_idx_subset = mp_indices[valid_mp]
        lmk_2d = landmarks_2d[mp_idx_subset]

        # FLAME 3D landmarks
        flame_landmarks_3d = self.flame.get_landmarks(vertices_3d)
        lmk_3d = flame_landmarks_3d[valid_mp]

        # Solve the texture camera from the inner 51 landmarks. The jaw is
        # traced along the visible outline - the beard, on a bearded face - and
        # giving those points an equal vote in the pose widened the projection
        # of the whole face. Measured on the reference portrait: median miss on
        # the inner landmarks 8.2 px with the jaw in, 4.6 without.
        inner = np.isin(np.nonzero(valid_mp)[0], POSE_LANDMARKS)
        if inner.sum() >= 10:
            lmk_2d, lmk_3d = lmk_2d[inner], lmk_3d[inner]

        if len(lmk_2d) < 10:
            logger.warning("Too few landmarks (%d) for texture projection", len(lmk_2d))
            return None

        # Estimate head pose
        rvec, tvec, camera_matrix = estimate_head_pose(
            lmk_3d, lmk_2d, image_width or photo_bgr.shape[1],
            image_height or photo_bgr.shape[0]
        )
        if rvec is None:
            logger.warning("Head pose estimation failed; using RBF fallback")
            return self._generate_texture_rbf(
                photo_bgr, vertex_uv, landmarks_2d,
                tex["mean"], output_size
            )

        # Project all vertices to photo plane
        pixels_2d = project_vertices_to_photo(vertices_3d, rvec, tvec, camera_matrix)

        # Sample photo colors
        vertex_colors = sample_colors_from_photo(photo_bgr, pixels_2d)

        # Render UV texture atlas. Passing the projection lets the rasteriser
        # sample the photo per texel rather than interpolating 5023 per-vertex
        # colours, which is what actually puts skin detail in the atlas.
        # Which vertices faced the camera when the photo was taken.
        visible = None
        confidence = None
        try:
            import cv2 as _cv2

            faces_i = self.flame.faces.astype(np.int64)
            vn = np.zeros_like(vertices_3d, dtype=np.float64)
            tri = vertices_3d[faces_i]
            fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            for k in range(3):
                np.add.at(vn, faces_i[:, k], fn)
            vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)
            R, _ = _cv2.Rodrigues(np.asarray(rvec, dtype=np.float64))
            # Camera looks down +Z in OpenCV convention; a surface is seen
            # when its normal has a component back toward the camera.
            n_cam = vn @ R.T
            visible = n_cam[:, 2] < -0.05
            seen = vertex_occlusion(
                vertices_3d, faces_i, pixels_2d, rvec, tvec,
                (photo_bgr.shape[1], photo_bgr.shape[0]))
            logger.info("Texture visibility: %.1f%% face the camera, %.1f%% of "
                        "those are not hidden behind nearer surfaces",
                        100.0 * visible.mean(),
                        100.0 * (visible & seen).sum() / max(int(visible.sum()), 1))
            visible &= seen
            # Facing strength: 1 looking straight at the lens, 0 at grazing.
            # A smoothstep so the photograph fades out before the silhouette,
            # where the samples are stretched and mostly shadow.
            facing = np.clip((-n_cam[:, 2] - 0.10) / (0.45 - 0.10), 0.0, 1.0)
            confidence = facing * facing * (3.0 - 2.0 * facing) * seen
        except Exception as exc:
            logger.info("Vertex visibility unavailable (%s); "
                        "texture will keep unseen-surface samples", exc)

        head_mask, skin_rgb = head_parse_mask(photo_bgr)
        texture = generate_uv_texture(
            vertex_uv, vertex_colors, tex["mean"],
            self.flame.faces, tex["ft"], tex["vt"],
            output_size=output_size,
            photo_img=photo_bgr,
            vertex_px=pixels_2d,
            head_mask=head_mask,
            vertex_visible=visible,
            fill_rgb=skin_rgb,
            vertex_confidence=confidence,
        )
        return texture

    def _generate_texture_rbf(
        self,
        photo_bgr: np.ndarray,
        vertex_uv: np.ndarray,
        landmarks_2d: np.ndarray,
        mean_texture: np.ndarray,
        output_size: int = TEXTURE_ATLAS_SIZE,
    ) -> np.ndarray:
        """Fallback: use RBF interpolation to map UV → photo pixels.

        Used when head pose estimation fails. Builds a thin-plate spline
        from 68 landmark UV↔photo correspondences, then maps every
        mesh vertex's UV to a photo pixel and samples colors.
        """
        from scipy.interpolate import RBFInterpolator

        # Derive landmark correspondence from geometry
        # For RBF, we need UV→photo pixel mapping via the 68 landmarks
        mp_indices, _ = (
            semantic_mp68_mapping(landmarks_2d)
            or derive_mp68_mapping(
                self.flame,
                self.flame.generate_mesh(),
                landmarks_2d,
                photo_bgr.shape[1],
            )
        )
        valid_mp = mp_indices < len(landmarks_2d)
        mp_idx = mp_indices[valid_mp]
        photo_lmk = landmarks_2d[mp_idx]

        # FLAME landmark UV coordinates
        flame_lmk_uv = self.flame.landmark_values(vertex_uv)[valid_mp]

        n = min(len(photo_lmk), len(flame_lmk_uv))
        if n < 10:
            logger.warning("Too few UV correspondences (%d) for RBF texture", n)
            return None

        src_uv = flame_lmk_uv[:n]
        tgt_photo = photo_lmk[:n]

        try:
            rbf = RBFInterpolator(src_uv, tgt_photo, kernel="thin_plate_spline",
                                  epsilon=0.05)
        except Exception as e:
            logger.warning("RBF interpolation failed: %s", e)
            return None

        # For each mesh vertex, map UV → photo pixel
        vertex_photo_pixels = rbf(vertex_uv)  # (5023, 2)

        # Sample photo and render UV texture
        vertex_colors = sample_colors_from_photo(photo_bgr, vertex_photo_pixels)
        tex = self._load_texture()
        return generate_uv_texture(
            vertex_uv, vertex_colors, mean_texture,
            self.flame.faces, tex["ft"], tex["vt"],
            output_size=output_size,
        )

    # ── Main pipeline ───────────────────────────────────────────────────────

    def fit_from_photo(
        self,
        photo_path: str,
        output_dir: Optional[str] = None,
        fit_identity: bool = True,
        generate_texture: bool = True,
        n_components: int = 30,
        reg_strength: float = 5.0,
        scale_factor: float = 2.5,
    ) -> Optional[dict]:
        """Run full FLAME fitting pipeline on a photo, with textured output.

        Args:
            photo_path: path to input photo
            output_dir: where to save OBJ/MTL/PNG (default: avatar/static/)
            fit_identity: whether to optimize identity parameters
            generate_texture: whether to project photo onto UV texture atlas
            n_components: PCA components for identity fitting
            reg_strength: regularization strength
            scale_factor: mesh scale for the viewer

        Returns:
            dict with keys: obj_path, mtl_path, texture_path, vertex_count,
                            face_count, identity_fitted, texture_generated
            or None on failure
        """
        if not os.path.exists(photo_path):
            logger.error("Photo not found: %s", photo_path)
            return None

        if output_dir is None:
            output_dir = _STATIC_DIR
        os.makedirs(output_dir, exist_ok=True)

        result = {
            "obj_path": None,
            "mtl_path": None,
            "texture_path": None,
            "vertex_count": 0,
            "face_count": 0,
            "identity_fitted": False,
            "landmarks_detected": False,
            "texture_generated": False,
        }

        # Step 1: Detect landmarks
        landmarks_2d, image_width = detect_landmarks(photo_path)
        if landmarks_2d is not None:
            result["landmarks_detected"] = True

        # Step 2: Fit identity
        identity_coeffs = None
        if landmarks_2d is not None and fit_identity:
            try:
                # Get image height for accurate edge penalty
                import cv2 as _cv2_h
                _tmp = _cv2_h.imread(photo_path)
                img_h = _tmp.shape[0] if _tmp is not None else None
                identity_coeffs = fit_identity_from_landmarks(
                    self.flame, landmarks_2d, image_width or 640,
                    image_height=img_h,
                    n_components=n_components, reg_strength=reg_strength,
                )
                result["identity_fitted"] = True
            except Exception as e:
                logger.warning("Identity fitting failed, using mean face: %s", e)

        # Step 3: Generate mesh
        vertices = self.flame.generate_mesh(identity_coeffs)
        faces = self.flame.faces
        result["vertex_count"] = len(vertices)
        result["face_count"] = len(faces)

        # Step 4: Compute normals
        normals = compute_normals(vertices, faces)

        # Step 5: Generate texture from photo
        texture_img = None
        if generate_texture and landmarks_2d is not None:
            try:
                import cv2 as _cv2_for_texture
                h_img = _cv2_for_texture.imread(photo_path)
                img_h = h_img.shape[0] if h_img is not None else 480
                texture_img = self._generate_texture_from_photo(
                    photo_path, vertices, landmarks_2d,
                    image_width or 640, img_h,
                    output_size=TEXTURE_ATLAS_SIZE,
                )
                if texture_img is not None:
                    result["texture_generated"] = True
                    logger.info("Texture generated from photo: %dx%d",
                                texture_img.shape[1], texture_img.shape[0])
            except Exception as e:
                logger.warning("Texture generation failed: %s", e)
                import traceback
                traceback.print_exc()

        # Step 6: Scale for viewer
        vertices_scaled = vertices * scale_factor

        # Step 7: Export
        base_name = "generated_head"
        obj_path = os.path.join(output_dir, f"{base_name}.obj")
        mtl_path = os.path.join(output_dir, f"{base_name}.mtl")
        texture_path = os.path.join(output_dir, f"{base_name}_texture.png")

        if texture_img is not None:
            # Export textured OBJ + MTL + texture PNG
            import cv2 as _cv2_export
            _cv2_export.imwrite(texture_path, texture_img[:, :, ::-1])  # RGB→BGR
            tex = self._load_texture()
            export_textured_mtl(mtl_path, f"{base_name}_texture.png")
            # FLAME's own vt/ft, so the seams survive into the OBJ. The
            # atlas above was already rasterised from vt/ft; exporting a
            # collapsed one-UV-per-vertex map threw that away at the last step.
            export_textured_obj(vertices_scaled, normals, tex["vt"],
                                faces, obj_path, face_uv=tex["ft"])
            result["texture_path"] = texture_path
        else:
            # Fall back to untextured export
            export_obj(vertices_scaled, normals, faces, obj_path)
            export_mtl(mtl_path)

        result["obj_path"] = obj_path
        result["mtl_path"] = mtl_path

        logger.info(
            "FLAME mesh generated: %d verts, %d faces -> %s (identity=%s, texture=%s)",
            len(vertices), len(faces), obj_path,
            result["identity_fitted"], result["texture_generated"],
        )
        return result

    def generate_mean_mesh(self, output_dir: Optional[str] = None,
                           scale_factor: float = 2.5,
                           generate_texture: bool = False,
                           photo_path: Optional[str] = None) -> dict:
        """Generate mean FLAME mesh (no identity fitting)."""
        vertices = self.flame.generate_mesh()
        normals = compute_normals(vertices, self.flame.faces)
        vertices = vertices * scale_factor

        if output_dir is None:
            output_dir = _STATIC_DIR
        os.makedirs(output_dir, exist_ok=True)

        base_name = "generated_head"
        obj_path = os.path.join(output_dir, f"{base_name}.obj")
        mtl_path = os.path.join(output_dir, f"{base_name}.mtl")

        # Try texture generation if photo provided
        texture_img = None
        if generate_texture and photo_path and os.path.exists(photo_path):
            try:
                landmarks_2d, img_w = detect_landmarks(photo_path)
                if landmarks_2d is not None:
                    import cv2 as _cv2_m
                    photo_bgr = _cv2_m.imread(photo_path)
                    img_h = photo_bgr.shape[0] if photo_bgr is not None else 480
                    texture_img = self._generate_texture_from_photo(
                        photo_path, self.flame.generate_mesh(), landmarks_2d,
                        img_w or 640, img_h, output_size=TEXTURE_ATLAS_SIZE,
                    )
            except Exception as e:
                logger.warning("Texture gen in mean mesh skipped: %s", e)

        if texture_img is not None:
            texture_path = os.path.join(output_dir, f"{base_name}_texture.png")
            import cv2 as _cv2_export
            _cv2_export.imwrite(texture_path, texture_img[:, :, ::-1])
            export_textured_mtl(mtl_path, f"{base_name}_texture.png")
            vertex_uv = self._get_vertex_uv()
            export_textured_obj(vertices, normals, vertex_uv,
                                self.flame.faces, obj_path)
        else:
            export_obj(vertices, normals, self.flame.faces, obj_path)
            export_mtl(mtl_path)

        return {
            "obj_path": obj_path,
            "mtl_path": mtl_path,
            "vertex_count": len(vertices),
            "face_count": len(self.flame.faces),
            "identity_fitted": False,
            "texture_generated": texture_img is not None,
        }


# ── CLI Entry Point ──────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="FLAME 3D face fitting")
    parser.add_argument("photo", type=str, help="Input photo path")
    parser.add_argument("--no-fit", action="store_true", help="Skip identity fitting")
    parser.add_argument("--n_components", type=int, default=30)
    parser.add_argument("--reg", type=float, default=5.0)
    args = parser.parse_args()

    fitter = FlameFitter()
    result = fitter.fit_from_photo(
        args.photo,
        fit_identity=not args.no_fit,
        n_components=args.n_components,
        reg_strength=args.reg,
    )
    if result:
        print(f"OBJ: {result['obj_path']}")
        print(f"MTL: {result['mtl_path']}")
        print(f"Verts: {result['vertex_count']}, Faces: {result['face_count']}")
        print(f"Identity fitted: {result['identity_fitted']}")
    else:
        print("Failed")
        sys.exit(1)
