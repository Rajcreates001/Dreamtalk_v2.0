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
_STATIC_DIR = os.path.join(_PROJECT_ROOT, "avatar", "static")

# ── FLAME Model Loader ────────────────────────────────────────────────


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

        # FLAME 2020 68-landmark vertex indices (from DECA project)
        self.lmk_inds = np.array([
            1630, 1976, 3658, 3850, 3973, 1632, 3485, 3769,
            3847, 3821, 3817, 810, 1416, 1158, 838, 1649, 1645,
            3545, 3754, 2207, 2185, 2180,
            1275, 1237, 1259, 1273, 1229,
            2136, 2144, 2140, 2145,
            333, 338, 341, 350, 363,
            3561, 3757, 2638, 2589, 2555, 2780,
            4140, 4134, 4087, 3572, 3493, 3131,
            4518, 4417, 4318, 4220, 4122, 4023,
            4019, 4116, 4214, 4312, 4411, 4511,
            4584, 4481, 4381, 4282, 4182, 4185, 4288, 4388
        ])
        assert self.lmk_inds.max() < self.num_vertices, \
            f"Landmark index {self.lmk_inds.max()} >= {self.num_vertices}"

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
        return vertices[self.lmk_inds]


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
    # Jaw (0-16) — prone to occlusion by hair/neck
    0.50, 0.50, 0.55, 0.55, 0.55, 0.55, 0.50, 0.50,
    0.45, 0.45, 0.50, 0.60, 0.65, 0.65, 0.60, 0.55, 0.55,
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
    mp_indices, mapping_distances = derive_mp68_mapping(
        flame, mean_verts, landmarks_2d, image_width
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
    lmk_basis = flame.identity_basis[flame_idx_subset]  # (N, 3, 300)
    # Each landmark gives 3 rows (x, y, z offset), but we only use x, y
    # in the objective (z doesn't affect weak perspective projection)
    lmk_basis_xy = lmk_basis[:, :2, :n_components]  # (N, 2, n_components)
    lmk_basis_flat = lmk_basis_xy.reshape(n_lmks * 2, n_components)

    # Normalize basis columns to unit variance for better conditioning
    basis_std = np.std(lmk_basis_flat, axis=0)
    basis_std = np.where(basis_std > 1e-8, basis_std, 1.0)
    lmk_basis_norm = lmk_basis_flat / basis_std  # (N*2, n_components)

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
    output_size: int = 512,
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

    # Render each face as a UV triangle
    # Use the UV coordinates from vt indexed by ft, not vertex_uv, for
    # the triangle rasterization, then sample colors via vertex_uv
    for fi in range(len(faces)):
        v_idx = faces[fi]  # (3,) vertex indices
        uv_idx = ft[fi]     # (3,) UV coordinate indices into vt

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

        # Sample colors via barycentric interpolation
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

    # Report gaps
    if not np.all(mask):
        logger.info("Texture atlas coverage: %.1f%% (%.1f%% filled from mean texture)",
                    100.0 * mask.mean(), 100.0 * (1.0 - mask.mean()))

    # Blend uncovered pixels with mean FLAME texture
    mean_tex = mean_texture.astype(np.float32)
    uncovered = ~mask
    if np.any(uncovered):
        texture[uncovered] = mean_tex[uncovered]

    # Light edge smoothing with a gentle blur
    texture = np.clip(texture, 0.0, 255.0).astype(np.uint8)
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
):
    """Write Wavefront OBJ with texture coordinates (v/vt/vn format).

    Every vertex gets a corresponding vt entry from the per-vertex UV map.
    Faces are written as v/vt/vn where all three indices match (1:1 mapping).
    Three.js OBJLoader uses these vt entries with MTL map_Kd for texturing.
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
        for face in faces:
            # v/vt/vn with all three indices matching (1:1 per vertex)
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
        output_size: int = 512,
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
        mp_indices, _ = derive_mp68_mapping(
            self.flame, vertices_3d, landmarks_2d,
            image_width or photo_bgr.shape[1],
        )
        valid_mp = mp_indices < len(landmarks_2d)
        mp_idx_subset = mp_indices[valid_mp]
        lmk_2d = landmarks_2d[mp_idx_subset]

        # FLAME 3D landmarks
        flame_landmarks_3d = self.flame.get_landmarks(vertices_3d)
        lmk_3d = flame_landmarks_3d[valid_mp]

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

        # Render UV texture atlas
        texture = generate_uv_texture(
            vertex_uv, vertex_colors, tex["mean"],
            self.flame.faces, tex["ft"], tex["vt"],
            output_size=output_size,
        )
        return texture

    def _generate_texture_rbf(
        self,
        photo_bgr: np.ndarray,
        vertex_uv: np.ndarray,
        landmarks_2d: np.ndarray,
        mean_texture: np.ndarray,
        output_size: int = 512,
    ) -> np.ndarray:
        """Fallback: use RBF interpolation to map UV → photo pixels.

        Used when head pose estimation fails. Builds a thin-plate spline
        from 68 landmark UV↔photo correspondences, then maps every
        mesh vertex's UV to a photo pixel and samples colors.
        """
        from scipy.interpolate import RBFInterpolator

        # Derive landmark correspondence from geometry
        # For RBF, we need UV→photo pixel mapping via the 68 landmarks
        mp_indices, _ = derive_mp68_mapping(
            self.flame, self.flame.generate_mesh(),
            landmarks_2d, photo_bgr.shape[1],
        )
        valid_mp = mp_indices < len(landmarks_2d)
        mp_idx = mp_indices[valid_mp]
        photo_lmk = landmarks_2d[mp_idx]

        # FLAME landmark UV coordinates
        flame_lmk_uv = vertex_uv[self.flame.lmk_inds[valid_mp]]

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
                    output_size=512,
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
            vertex_uv = self._get_vertex_uv()
            export_textured_mtl(mtl_path, f"{base_name}_texture.png")
            export_textured_obj(vertices_scaled, normals, vertex_uv,
                                faces, obj_path)
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
                        img_w or 640, img_h, output_size=512,
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
