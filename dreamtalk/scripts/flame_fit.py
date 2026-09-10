"""
FLAME 3D Face Fitting Pipeline

Pipeline:
  1. Load FLAME morphable model (5023 vertices, 9976 triangles)
  2. Detect face landmarks from photo using MediaPipe (478 landmarks)
  3. Fit FLAME identity parameters to match detected face shape
  4. Apply expression and pose parameters
  5. Compute smooth vertex normals
  6. Export textured OBJ + MTL

Usage:
    python scripts/flame_fit.py <photo_path> [--output_dir <dir>] [--fit_identity]
"""

import os
import sys
import pickle
import math
import argparse
import warnings
from typing import Optional, Tuple

import numpy as np

warnings.filterwarnings("ignore")


# ── FLAME Model Loader ────────────────────────────────────────────────

class FLAMELoader:
    """Minimal FLAME model loader for mesh generation."""

    def __init__(self, model_path: str):
        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.v_template: np.ndarray = data["v_template"]          # (5023, 3)
        self.shapedirs: np.ndarray = data["shapedirs"]             # (5023, 3, 400)
        self.faces: np.ndarray = data["f"].astype(np.int32)        # (9976, 3)
        self.posedirs: np.ndarray = data["posedirs"]               # (5023, 3, 36)
        self.weights: np.ndarray = data["weights"]                 # (5023, 5)

        # Identity (first 300) and expression (last 100) basis
        self.identity_basis = self.shapedirs[:, :, :300]           # (5023, 3, 300)
        self.expression_basis = self.shapedirs[:, :, 300:400]      # (5023, 3, 100)

        self.num_vertices = self.v_template.shape[0]
        self.num_faces = self.faces.shape[0]

        # Standard FLAME 2020 (5023-vertex) 68-landmark vertex indices
        # From the FLAME paper and DECA project
        self.lmk_inds = np.array([
            # Jaw (0-16)
            1630, 1976, 3658, 3850, 3973, 1632, 3485, 3769,
            3847, 3821, 3817, 810, 1416, 1158, 838, 1649, 1645,
            # Left eyebrow (17-21)
            3545, 3754, 2207, 2185, 2180,
            # Right eyebrow (22-26)
            1275, 1237, 1259, 1273, 1229,
            # Nose bridge (27-30)
            2136, 2144, 2140, 2145,
            # Nose (31-35)
            333, 338, 341, 350, 363,
            # Left eye (36-41)
            3561, 3757, 2638, 2589, 2555, 2780,
            # Right eye (42-47)
            4140, 4134, 4087, 3572, 3493, 3131,
            # Outer mouth (48-59)
            4518, 4417, 4318, 4220, 4122, 4023,
            4019, 4116, 4214, 4312, 4411, 4511,
            # Inner mouth (60-67)
            4584, 4481, 4381, 4282, 4182, 4185, 4288, 4388
        ])
        assert self.lmk_inds.max() < self.num_vertices, (
            f"Landmark index {self.lmk_inds.max()} >= {self.num_vertices}"
        )

    def generate_mesh(
        self,
        identity_coeffs: Optional[np.ndarray] = None,
        expression_coeffs: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Generate deformed mesh vertices.

        Args:
            identity_coeffs: (300,) identity coefficients (zeros = mean face)
            expression_coeffs: (100,) expression coefficients (zeros = neutral)

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
        """Get 68 landmark positions from deformed mesh."""
        return vertices[self.lmk_inds]


# ── MediaPipe Landmark Detection ─────────────────────────────────────

def detect_face_landmarks(image_path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """Detect 478 face landmarks from image using MediaPipe.

    Returns:
        (landmarks_2d, image_width) or (None, None) if no face found
    """
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        import cv2
    except ImportError as e:
        print(f"  MediaPipe import error: {e}")
        return None, None

    img = cv2.imread(image_path)
    if img is None:
        print(f"  ERROR: Cannot read image: {image_path}")
        return None, None

    h, w = img.shape[:2]

    # Look for the face landmarker model
    model_paths = [
        "weights/face/face_landmarker.task",
        "weights/face/face_landmarker_v2_with_blendshapes.task",
        os.path.join(os.path.dirname(__file__), "..", "weights", "face", "face_landmarker.task"),
    ]

    model_path = None
    for mp_path in model_paths:
        if os.path.exists(mp_path):
            model_path = mp_path
            break

    if model_path is None or not os.path.exists(model_path):
        print("  Face landmarker model not found, downloading...")
        import urllib.request
        model_dir = os.path.join(os.path.dirname(__file__), "..", "weights", "face")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "face_landmarker.task")
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        print(f"  Downloading from {url}...")
        urllib.request.urlretrieve(url, model_path)
        print(f"  Downloaded to {model_path}")

    try:
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
        )
        detector = vision.FaceLandmarker.create_from_options(options)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        result = detector.detect(mp_image)

        if not result.face_landmarks:
            print("  No face detected")
            return None, None

        landmarks = np.array([(p.x * w, p.y * h) for p in result.face_landmarks[0]])
        print(f"  Detected {len(landmarks)} face landmarks")
        return landmarks, w

    except Exception as e:
        print(f"  MediaPipe detection failed: {e}")
        return None, None


# ── Head Pose Estimation ─────────────────────────────────────────────

def estimate_head_pose(landmarks_2d: np.ndarray, image_width: int) -> Tuple[float, float, float, float]:
    """Estimate head pose from MediaPipe landmarks.

    Returns:
        (yaw, pitch, roll, scale) in radians
    """
    # Use nose tip and eye centers for pose estimation
    nose_tip = landmarks_2d[1]
    left_eye = landmarks_2d[33]
    right_eye = landmarks_2d[263]
    left_mouth = landmarks_2d[61]
    right_mouth = landmarks_2d[291]

    eye_center = (left_eye + right_eye) / 2
    mouth_center = (left_mouth + right_mouth) / 2

    # Rough head scale based on inter-ocular distance
    inter_ocular = np.linalg.norm(left_eye - right_eye)
    scale = inter_ocular / 0.15 if inter_ocular > 0 else 1.0

    # Yaw from eye-mouth asymmetry
    eye_to_nose = nose_tip - eye_center
    yaw = np.arctan2(eye_to_nose[0], abs(eye_to_nose[1]) + 1e-6)

    # Pitch from nose-to-mouth vertical offset
    nose_to_mouth = mouth_center - nose_tip
    pitch = np.arctan2(nose_to_mouth[1], abs(nose_to_mouth[0]) + 1e-6)

    # Roll from eye angle
    eye_delta = right_eye - left_eye
    roll = np.arctan2(eye_delta[1], eye_delta[0]) - math.pi / 2

    return yaw, pitch, roll, scale


# ── Identity Fitting ─────────────────────────────────────────────────

def fit_identity(
    flame: FLAMELoader,
    landmarks_2d: np.ndarray,
    image_width: int,
    n_components: int = 50,
    n_iters: int = 30,
    reg_strength: float = 10.0,
) -> np.ndarray:
    """Fit FLAME identity coefficients to 2D landmarks.

    Uses scipy optimization to minimize reprojection error.

    Args:
        flame: FLAME model
        landmarks_2d: (478, 2) detected landmarks
        image_width: image width (for focal length estimation)
        n_components: number of identity PCA components to optimize
        n_iters: max optimization iterations
        reg_strength: regularization weight (higher = closer to mean)

    Returns:
        (300,) identity coefficients
    """
    from scipy.optimize import minimize

    # Map MediaPipe 478 landmarks to FLAME 68 landmarks
    # Each maps to the corresponding FLAME 68 landmark in order
    mp_68_indices = np.array([
        # Jaw (0-16)
        162, 237, 39, 0, 87, 328, 231, 357, 138, 309, 350, 152, 149, 176, 400, 379, 377,
        # Left eyebrow (17-21)
        46, 53, 52, 65, 55,
        # Right eyebrow (22-26)
        285, 295, 282, 283, 276,
        # Nose bridge (27-30)
        48, 66, 67, 64,
        # Nose tip (31-35)
        1, 2, 98, 327, 94,
        # Left eye (36-41)
        33, 7, 163, 144, 159, 155,
        # Right eye (42-47)
        362, 382, 381, 380, 385, 387,
        # Outer mouth (48-59)
        61, 185, 40, 37, 0, 17, 267, 269, 270, 409, 291, 375,
        # Inner mouth (60-67)
        78, 191, 80, 81, 82, 13, 312, 311
    ])

    # Filter valid MediaPipe indices
    valid = mp_68_indices < len(landmarks_2d)
    mp_68_indices = mp_68_indices[valid]

    # Get corresponding 2D landmarks
    observed_2d = landmarks_2d[mp_68_indices]

    # Estimate camera parameters (weak perspective)
    focal_length = image_width * 0.8  # rough estimate
    cx, cy = image_width / 2, np.median(observed_2d[:, 1])  # approximate center

    # Get mean FLAME landmarks (3D)
    mean_vertices = flame.generate_mesh()
    mean_lmks_3d = flame.get_landmarks(mean_vertices)
    # Only use valid landmarks
    mean_lmks_3d = mean_lmks_3d[valid]

    # Estimate initial scale and translation from landmark alignment
    mean_2d = mean_lmks_3d[:, :2]  # project to 2D (ignore Z)
    mean_2d -= mean_2d.mean(axis=0)
    observed_2d_c = observed_2d - observed_2d.mean(axis=0)

    # Initial scale
    scale_init = np.std(observed_2d_c) / (np.std(mean_2d) + 1e-6)

    # Reduce identity basis to n_components
    identity_basis = flame.identity_basis  # (5023, 3, 300)
    # Get landmark vertices of basis
    lmk_basis = identity_basis[flame.lmk_inds[valid]]  # (N, 3, 300)
    # Reshape to (N*3, 300)
    lmk_basis_flat = lmk_basis.reshape(-1, 300)

    # Only use first n_components
    lmk_basis_reduced = lmk_basis_flat[:, :n_components]

    # Objective function
    def objective(coeffs):
        # Compute 3D landmark offsets
        offset_flat = lmk_basis_reduced @ coeffs  # (N*3,)
        offset_3d = offset_flat.reshape(-1, 3)

        # Deformed 3D landmarks
        deformed_lmks = mean_lmks_3d + offset_3d

        # Weak perspective projection
        projected = scale_init * deformed_lmks[:, :2] + observed_2d.mean(axis=0)

        # Reprojection error
        error = projected - observed_2d

        # L2 loss
        reproj_loss = np.sum(error ** 2) / len(observed_2d)

        # Regularization (L2 penalty on coefficients)
        reg_loss = reg_strength * np.sum(coeffs ** 2)

        return reproj_loss + reg_loss

    # Initial guess (zero = mean face)
    x0 = np.zeros(n_components)

    # Optimize
    result = minimize(
        objective,
        x0,
        method="L-BFGS-B",
        options={"maxiter": n_iters, "ftol": 1e-6, "gtol": 1e-6},
    )

    # Full 300-dim coefficient vector
    full_coeffs = np.zeros(300)
    full_coeffs[:n_components] = result.x

    print(f"  Identity fitting: {result.nit} iters, loss={result.fun:.4f}")
    return full_coeffs


# ── Normal Computation ────────────────────────────────────────────────

def compute_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Compute smooth vertex normals via angle-weighted face normal averaging."""
    normals = np.zeros_like(vertices)
    weights = np.zeros(len(vertices))

    for face in faces:
        i0, i1, i2 = face
        v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]

        # Face normal
        e1 = v1 - v0
        e2 = v2 - v0
        fn = np.cross(e1, e2)
        fn_len = np.linalg.norm(fn)
        if fn_len < 1e-10:
            continue
        fn = fn / fn_len

        # Angle weights at each vertex
        for tri_idx, (i, i_prev, i_next) in enumerate([
            (i0, i2, i1), (i1, i0, i2), (i2, i1, i0)
        ]):
            v_cur = vertices[i]
            v_prev = vertices[i_prev]
            v_next = vertices[i_next]

            e_a = v_prev - v_cur
            e_b = v_next - v_cur
            len_a = np.linalg.norm(e_a)
            len_b = np.linalg.norm(e_b)

            if len_a < 1e-10 or len_b < 1e-10:
                continue

            cos_angle = np.dot(e_a, e_b) / (len_a * len_b)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle = math.acos(cos_angle)

            normals[i] += fn * angle
            weights[i] += angle

    # Normalize
    for i in range(len(normals)):
        if weights[i] > 0:
            n = normals[i] / weights[i]
            n_len = np.linalg.norm(n)
            if n_len > 0:
                normals[i] = n / n_len
            else:
                normals[i] = np.array([0.0, 1.0, 0.0])
        else:
            # Radial fallback
            v = vertices[i]
            v_len = np.linalg.norm(v)
            if v_len > 0:
                normals[i] = v / v_len
            else:
                normals[i] = np.array([0.0, 1.0, 0.0])

    return normals


# ── OBJ Export ────────────────────────────────────────────────────────

def export_obj(
    vertices: np.ndarray,
    normals: np.ndarray,
    faces: np.ndarray,
    obj_path: str,
    mtl_name: str = "flame_face.mtl",
):
    """Export mesh as Wavefront OBJ with normals and material reference."""
    with open(obj_path, "w") as f:
        f.write(f"# FLAME 3D Face Mesh\n")
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
            idxs = " ".join(f"{i+1}//{i+1}" for i in face)
            f.write(f"f {idxs}\n")


def export_mtl(mtl_path: str):
    """Write skin material file."""
    mtl = """# DreamTalk FLAME Face Mesh Material
newmtl skin_material
Ka 0.85 0.75 0.65
Kd 0.92 0.82 0.72
Ks 0.30 0.25 0.20
Ns 40.0
d 1.0
illum 2
"""
    with open(mtl_path, "w") as f:
        f.write(mtl)


# ── Main Pipeline ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FLAME 3D face fitting from photo")
    parser.add_argument("photo", type=str, help="Path to input photo")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Output directory (default: avatar/static)")
    parser.add_argument("--fit_identity", action="store_true",
                        help="Fit identity parameters to face shape")
    parser.add_argument("--n_components", type=int, default=30,
                        help="Number of identity PCA components (default: 30)")
    parser.add_argument("--reg", type=float, default=5.0,
                        help="Regularization strength (default: 5.0)")
    args = parser.parse_args()

    # Resolve paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    model_path = os.path.join(project_root, "weights", "flame", "FLAME2020_numpy.pkl")
    if not os.path.exists(model_path):
        # Try original path
        model_path = os.path.join(project_root, "weights", "flame", "FLAME2020.pkl")
        if not os.path.exists(model_path):
            print(f"ERROR: FLAME model not found at {model_path}")
            sys.exit(1)

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = os.path.join(project_root, "avatar", "static")
    os.makedirs(output_dir, exist_ok=True)

    photo_path = args.photo
    if not os.path.exists(photo_path):
        # Try relative to project root
        photo_path = os.path.join(project_root, args.photo)
        if not os.path.exists(photo_path):
            print(f"ERROR: Photo not found: {args.photo}")
            sys.exit(1)

    print("=" * 60)
    print("FLAME 3D Face Fitting Pipeline")
    print("=" * 60)
    print(f"\n  Photo: {photo_path}")
    print(f"  Model: {model_path}")
    print(f"  Output: {output_dir}")

    # Step 1: Load FLAME model
    print("\n[1/4] Loading FLAME model...")
    flame = FLAMELoader(model_path)
    print(f"  Loaded: {flame.num_vertices} vertices, {flame.num_faces} faces")

    # Step 2: Detect face landmarks
    print("\n[2/4] Detecting face landmarks...")
    landmarks_2d, image_width = detect_face_landmarks(photo_path)

    # Step 3: Generate FLAME mesh
    print("\n[3/4] Generating FLAME mesh...")

    identity_coeffs = None
    expression_coeffs = None

    if landmarks_2d is not None and args.fit_identity:
        print("  Fitting identity parameters...")
        identity_coeffs = fit_identity(
            flame, landmarks_2d, image_width or 640,
            n_components=min(args.n_components, 50),
            reg_strength=args.reg,
        )
        print(f"  Identity fitted: range=[{identity_coeffs.min():.4f}, {identity_coeffs.max():.4f}]")
    else:
        print("  Using mean FLAME shape (no identity fitting)")
        if landmarks_2d is not None:
            yaw, pitch, roll, scale = estimate_head_pose(landmarks_2d, image_width or 640)
            print(f"  Head pose: yaw={math.degrees(yaw):.1f}°, pitch={math.degrees(pitch):.1f}°, roll={math.degrees(roll):.1f}°")

    vertices = flame.generate_mesh(identity_coeffs, expression_coeffs)
    print(f"  Generated: {vertices.shape[0]} vertices")

    # Step 4: Compute normals and export
    print("\n[4/4] Computing normals and exporting...")
    normals = compute_normals(vertices, flame.faces)

    # Scale mesh to a reasonable size for the 3D viewer
    # FLAME vertices are in normalized space (~[-0.2, 0.14])
    # Scale up for better visibility
    scale_factor = 2.5
    vertices = vertices * scale_factor

    obj_path = os.path.join(output_dir, "generated_head.obj")
    mtl_path = os.path.join(output_dir, "generated_head.mtl")

    export_obj(vertices, normals, flame.faces, obj_path)
    export_mtl(mtl_path)

    print(f"\n  OBJ: {obj_path}")
    print(f"  MTL: {mtl_path}")

    # Stats
    obj_size = os.path.getsize(obj_path)
    mtl_size = os.path.getsize(mtl_path)
    print(f"  OBJ size: {obj_size / 1024:.1f} KB")
    print(f"  MTL size: {mtl_size} bytes")

    print("\nDone! FLAME face mesh generated successfully.")


if __name__ == "__main__":
    main()
