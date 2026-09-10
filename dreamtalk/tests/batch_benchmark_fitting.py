"""
Batch Benchmark: Old vs New FLAME Identity Fitting
===================================================
Compares the two fitting strategies across available test photos:

  **Old approach**: hardcoded _MP_68_INDICES map, fixed camera (scale+trans), basic MSE
  **New approach**: model-derived mapping, joint camera+identity optimization, confidence-weighted reprojection

Metrics compared per photo:
  - Final reprojection loss (lower is better)
  - Camera parameters (scale, tx, ty, angle)
  - Identity coefficient range
  - Number of valid landmarks used
  - Optimizer iterations
"""

import os
import sys
import math
import pickle
import logging
import time
from typing import Optional, Tuple
import numpy as np

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("batch_benchmark")

# Add project root to path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))  # parent of dreamtalk/

# ── Find test photos ─────────────────────────────────────────────────

TEST_PHOTOS = []

# Primary test photo
sample1 = os.path.join(_PROJECT_ROOT, "local_upload_testing", "Image_local", "sample1.jpeg")
if os.path.exists(sample1):
    TEST_PHOTOS.append(("sample1 (frontal)", sample1))

# Check media database for any additional uploads
media_dir = os.path.join(
    _PROJECT_ROOT, "dreamtalk", "media", "personal",
    "48acf794-7423-4379-9f20-c2c852d64a01", "appearance"
)
if os.path.isdir(media_dir):
    for fname in os.listdir(media_dir):
        if fname.endswith((".jpg", ".jpeg", ".png")):
            fpath = os.path.join(media_dir, fname)
            if os.path.isfile(fpath):
                TEST_PHOTOS.append((fname, fpath))

# Also check for any images in avatar/static
avatar_static = os.path.join(_PROJECT_ROOT, "avatar", "static")
for fname in os.listdir(avatar_static):
    if fname.endswith((".jpg", ".jpeg", ".png")) and "texture" not in fname:
        fpath = os.path.join(avatar_static, fname)
        if os.path.isfile(fpath) and fname not in [p[0] for p in TEST_PHOTOS]:
            TEST_PHOTOS.append((fname, fpath))

print(f"Found {len(TEST_PHOTOS)} test photos")
print("=" * 70)

# ── Import the new approach ──────────────────────────────────────────

from dreamtalk.pipeline.flame_fitter import (
    FLAMELoader, FlameFitter, detect_landmarks,
    derive_mp68_mapping, compute_landmark_weights,
    compute_normals,
)
from dreamtalk.pipeline.flame_fitter import _LANDMARK_REGION_WEIGHTS

# ── OLD APPROACH: Replicate the previous fitting ────────────────────
# This replicates the exact logic of the old fit_identity_from_landmarks

_MP_68_INDICES_OLD = np.array([
    162, 237, 39, 0, 87, 328, 231, 357, 138, 309, 350, 152, 149, 176, 400, 379, 377,
    46, 53, 52, 65, 55,
    285, 295, 282, 283, 276,
    48, 66, 67, 64,
    1, 2, 98, 327, 94,
    33, 7, 163, 144, 159, 155,
    362, 382, 381, 380, 385, 387,
    61, 185, 40, 37, 0, 17, 267, 269, 270, 409, 291, 375,
    78, 191, 80, 81, 82, 13, 312, 311,
], dtype=np.int32)


def fit_identity_old(
    flame: FLAMELoader,
    landmarks_2d: np.ndarray,
    image_width: int,
    n_components: int = 30,
    reg_strength: float = 5.0,
    n_iters: int = 30,
) -> np.ndarray:
    """Replicate the OLD fitting approach: hardcoded map, fixed camera, unweighted MSE."""
    from scipy.optimize import minimize

    valid_mp = _MP_68_INDICES_OLD < len(landmarks_2d)
    mp_indices = _MP_68_INDICES_OLD[valid_mp]
    observed_2d = landmarks_2d[mp_indices]

    mean_verts = flame.generate_mesh()
    mean_lmks_3d = flame.get_landmarks(mean_verts)
    valid_flame = np.zeros(68, dtype=bool)
    valid_flame[:len(valid_mp)] = valid_mp
    mean_lmks_3d = mean_lmks_3d[valid_flame]

    n_lmks = len(observed_2d)
    if n_lmks < 10:
        return np.zeros(300)

    # Fixed camera estimate (no Y-flip in old version)
    mean_2d = mean_lmks_3d[:, :2]
    mean_2d_c = mean_2d - mean_2d.mean(axis=0)
    obs_2d_c = observed_2d - observed_2d.mean(axis=0)
    scale_init = np.std(obs_2d_c) / (np.std(mean_2d_c) + 1e-8)
    trans_init = observed_2d.mean(axis=0)

    lmk_basis = flame.identity_basis[flame.lmk_inds[valid_flame]]
    lmk_basis_flat = lmk_basis.reshape(n_lmks * 3, 300)[:, :n_components]
    lmk_basis_flat = lmk_basis_flat / (np.std(lmk_basis_flat) + 1e-8)

    def objective(coeffs):
        offset_flat = lmk_basis_flat @ coeffs
        offset_3d = offset_flat.reshape(-1, 3)
        deformed = mean_lmks_3d + offset_3d
        projected = scale_init * deformed[:, :2] + trans_init
        error = projected - observed_2d
        reproj = np.mean(error ** 2)
        reg = reg_strength * np.sum(coeffs ** 2)
        return reproj + reg

    result = minimize(objective, np.zeros(n_components),
                      method="L-BFGS-B",
                      options={"maxiter": n_iters, "ftol": 1e-6, "gtol": 1e-6})

    full_coeffs = np.zeros(300)
    full_coeffs[:n_components] = result.x
    return full_coeffs, result.fun, result.nit


# ── NEW APPROACH: Current implementation (confidence-weighted) ───────

def fit_identity_new(
    flame: FLAMELoader,
    landmarks_2d: np.ndarray,
    image_width: int,
    image_height: int,
    n_components: int = 30,
    reg_strength: float = 5.0,
    n_iters: int = 30,
) -> Tuple[np.ndarray, float, int, dict]:
    """Run the NEW approach: derived mapping, joint camera, confidence weights."""
    from scipy.optimize import minimize

    n_lmks_total = min(len(landmarks_2d), 478)
    mean_verts = flame.generate_mesh()
    mp_indices, mapping_distances = derive_mp68_mapping(
        flame, mean_verts, landmarks_2d, image_width
    )
    flame_landmark_inds = flame.lmk_inds

    valid_mask = mp_indices < n_lmks_total
    mp_idx_subset = mp_indices[valid_mask]
    flame_idx_subset = flame_landmark_inds[valid_mask]

    observed_2d = landmarks_2d[mp_idx_subset]
    mean_lmks_3d = flame.get_landmarks(mean_verts)[valid_mask]
    n_lmks = len(observed_2d)
    if n_lmks < 10:
        return np.zeros(300), 0.0, 0, {}

    # Confidence weights
    weights = compute_landmark_weights(
        landmarks_2d, image_width, image_height,
        mp_indices, mapping_distances, valid_mask,
    )

    # Initial camera
    flame_xy = np.column_stack([mean_lmks_3d[:, 0], -mean_lmks_3d[:, 1]])
    flame_xy_c = flame_xy - flame_xy.mean(axis=0)
    obs_2d_c = observed_2d - observed_2d.mean(axis=0)
    scale_init = np.std(obs_2d_c) / (np.std(flame_xy_c) + 1e-8)
    tx_init = observed_2d[:, 0].mean()
    ty_init = observed_2d[:, 1].mean()
    log_scale_init = np.log(max(scale_init, 1e-6))
    angle_init = 0.0

    # Basis
    lmk_basis = flame.identity_basis[flame_idx_subset]
    lmk_basis_xy = lmk_basis[:, :2, :n_components]
    lmk_basis_flat = lmk_basis_xy.reshape(n_lmks * 2, n_components)
    basis_std = np.std(lmk_basis_flat, axis=0)
    basis_std = np.where(basis_std > 1e-8, basis_std, 1.0)
    lmk_basis_norm = lmk_basis_flat / basis_std

    def objective(params):
        log_scale = params[0]
        tx = params[1]
        ty = params[2]
        angle = params[3]
        coeffs = params[4:]

        offset_flat = lmk_basis_norm @ coeffs
        offset_xy = offset_flat.reshape(-1, 2)

        deformed_xy = mean_lmks_3d[:, :2] + offset_xy
        deformed_xy = np.column_stack([deformed_xy[:, 0], -deformed_xy[:, 1]])

        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        rotated_x = cos_a * deformed_xy[:, 0] - sin_a * deformed_xy[:, 1]
        rotated_y = sin_a * deformed_xy[:, 0] + cos_a * deformed_xy[:, 1]
        s = np.exp(log_scale)
        projected_x = s * rotated_x + tx
        projected_y = s * rotated_y + ty

        error_x = projected_x - observed_2d[:, 0]
        error_y = projected_y - observed_2d[:, 1]
        reproj = np.sum(weights * (error_x ** 2 + error_y ** 2)) / weights.sum()
        reg = reg_strength * np.sum(coeffs ** 2)
        cam_reg = 0.01 * (log_scale ** 2 + angle ** 2 + tx ** 2 + ty ** 2) / (image_width ** 2)
        return reproj + reg + cam_reg

    x0 = np.concatenate([[log_scale_init, tx_init, ty_init, angle_init], np.zeros(n_components)])
    bounds = [(None, None)] * (4 + n_components)

    result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds,
                      options={"maxiter": n_iters, "ftol": 1e-7, "gtol": 1e-7})

    identity_coeffs = np.zeros(300)
    identity_coeffs[:n_components] = result.x[4:] / basis_std

    cam = {
        "scale": np.exp(result.x[0]),
        "tx": result.x[1],
        "ty": result.x[2],
        "angle_deg": np.degrees(result.x[3]),
    }
    extras = {
        "n_lmks": n_lmks,
        "w_min": float(weights.min()),
        "w_max": float(weights.max()),
        "cam": cam,
    }
    return identity_coeffs, result.fun, result.nit, extras


# ── Unweighted variant of the new approach (for ablation) ────────────

def fit_identity_new_unweighted(
    flame: FLAMELoader,
    landmarks_2d: np.ndarray,
    image_width: int,
    image_height: int,
    n_components: int = 30,
    reg_strength: float = 5.0,
    n_iters: int = 30,
) -> Tuple[np.ndarray, float, int, dict]:
    """NEW approach but with uniform weights (1.0) to isolate the effect of confidence weighting."""
    from scipy.optimize import minimize

    n_lmks_total = min(len(landmarks_2d), 478)
    mean_verts = flame.generate_mesh()
    mp_indices, mapping_distances = derive_mp68_mapping(
        flame, mean_verts, landmarks_2d, image_width
    )
    flame_landmark_inds = flame.lmk_inds

    valid_mask = mp_indices < n_lmks_total
    mp_idx_subset = mp_indices[valid_mask]
    flame_idx_subset = flame_landmark_inds[valid_mask]

    observed_2d = landmarks_2d[mp_idx_subset]
    mean_lmks_3d = flame.get_landmarks(mean_verts)[valid_mask]
    n_lmks = len(observed_2d)
    if n_lmks < 10:
        return np.zeros(300), 0.0, 0, {}

    # Uniform weights (all 1.0)
    weights = np.ones(n_lmks, dtype=np.float32)

    flame_xy = np.column_stack([mean_lmks_3d[:, 0], -mean_lmks_3d[:, 1]])
    flame_xy_c = flame_xy - flame_xy.mean(axis=0)
    obs_2d_c = observed_2d - observed_2d.mean(axis=0)
    scale_init = np.std(obs_2d_c) / (np.std(flame_xy_c) + 1e-8)
    tx_init = observed_2d[:, 0].mean()
    ty_init = observed_2d[:, 1].mean()
    log_scale_init = np.log(max(scale_init, 1e-6))
    angle_init = 0.0

    lmk_basis = flame.identity_basis[flame_idx_subset]
    lmk_basis_xy = lmk_basis[:, :2, :n_components]
    lmk_basis_flat = lmk_basis_xy.reshape(n_lmks * 2, n_components)
    basis_std = np.std(lmk_basis_flat, axis=0)
    basis_std = np.where(basis_std > 1e-8, basis_std, 1.0)
    lmk_basis_norm = lmk_basis_flat / basis_std

    def objective(params):
        log_scale = params[0]
        tx = params[1]
        ty = params[2]
        angle = params[3]
        coeffs = params[4:]

        offset_flat = lmk_basis_norm @ coeffs
        offset_xy = offset_flat.reshape(-1, 2)
        deformed_xy = mean_lmks_3d[:, :2] + offset_xy
        deformed_xy = np.column_stack([deformed_xy[:, 0], -deformed_xy[:, 1]])

        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        rotated_x = cos_a * deformed_xy[:, 0] - sin_a * deformed_xy[:, 1]
        rotated_y = sin_a * deformed_xy[:, 0] + cos_a * deformed_xy[:, 1]
        s = np.exp(log_scale)
        projected_x = s * rotated_x + tx
        projected_y = s * rotated_y + ty

        error_x = projected_x - observed_2d[:, 0]
        error_y = projected_y - observed_2d[:, 1]
        reproj = np.mean(error_x ** 2 + error_y ** 2)  # unweighted
        reg = reg_strength * np.sum(coeffs ** 2)
        cam_reg = 0.01 * (log_scale ** 2 + angle ** 2 + tx ** 2 + ty ** 2) / (image_width ** 2)
        return reproj + reg + cam_reg

    x0 = np.concatenate([[log_scale_init, tx_init, ty_init, angle_init], np.zeros(n_components)])
    bounds = [(None, None)] * (4 + n_components)

    result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds,
                      options={"maxiter": n_iters, "ftol": 1e-7, "gtol": 1e-7})

    identity_coeffs = np.zeros(300)
    identity_coeffs[:n_components] = result.x[4:] / basis_std

    cam = {
        "scale": np.exp(result.x[0]),
        "tx": result.x[1],
        "ty": result.x[2],
        "angle_deg": np.degrees(result.x[3]),
    }
    extras = {"n_lmks": n_lmks, "cam": cam}
    return identity_coeffs, result.fun, result.nit, extras


# ── Run the benchmark ─────────────────────────────────────────────────

def benchmark_photo(name: str, path: str) -> dict:
    """Run all three approaches on a single photo and return results."""
    if not os.path.exists(path):
        return {"name": name, "error": "file not found"}

    result = {"name": name, "path": path}

    # Detect landmarks
    lmks, img_w = detect_landmarks(path)
    if lmks is None:
        return {**result, "error": "no face detected"}

    # Get image height
    import cv2
    img = cv2.imread(path)
    img_h = img.shape[0] if img is not None else img_w

    result["image_dims"] = f"{img_w}×{img_h}"
    result["landmarks_detected"] = len(lmks)

    # Load FLAME model
    model_path = os.path.join(_PROJECT_ROOT, "weights", "flame", "FLAME2020_numpy.pkl")
    flame = FLAMELoader(model_path)

    # ── 1. OLD approach ──
    try:
        t0 = time.time()
        coeffs_old, loss_old, nit_old = fit_identity_old(flame, lmks, img_w)
        t_old = time.time() - t0
        result["old"] = {
            "loss": round(loss_old, 2),
            "n_iters": nit_old,
            "identity_range": f"[{coeffs_old.min():.2f}, {coeffs_old.max():.2f}]",
            "time_s": round(t_old, 2),
        }
    except Exception as e:
        result["old"] = {"error": str(e)}

    # ── 2. NEW approach (confidence-weighted) ──
    try:
        t0 = time.time()
        coeffs_new, loss_new, nit_new, extra_new = fit_identity_new(flame, lmks, img_w, img_h)
        t_new = time.time() - t0
        result["new_weighted"] = {
            "loss": round(loss_new, 2),
            "n_iters": nit_new,
            "identity_range": f"[{coeffs_new.min():.2f}, {coeffs_new.max():.2f}]",
            "time_s": round(t_new, 2),
            "n_lmks": extra_new["n_lmks"],
            "weights": f"[{extra_new['w_min']:.2f}, {extra_new['w_max']:.2f}]",
            "camera": extra_new["cam"],
        }
    except Exception as e:
        result["new_weighted"] = {"error": str(e)}

    # ── 3. NEW approach (unweighted — ablation) ──
    try:
        t0 = time.time()
        coeffs_nw, loss_nw, nit_nw, extra_nw = fit_identity_new_unweighted(flame, lmks, img_w, img_h)
        t_nw = time.time() - t0
        result["new_unweighted"] = {
            "loss": round(loss_nw, 2),
            "n_iters": nit_nw,
            "identity_range": f"[{coeffs_nw.min():.2f}, {coeffs_nw.max():.2f}]",
            "time_s": round(t_nw, 2),
            "n_lmks": extra_nw["n_lmks"],
            "camera": extra_nw["cam"],
        }
    except Exception as e:
        result["new_unweighted"] = {"error": str(e)}

    return result


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"{'Photo':<30} {'Dims':<12} {'Old Loss':<12} {'New (unwt)':<12} {'New (wtd)':<12} {'Weights':<14} {'Improvement'}")
    print(f"{'-'*30} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*14} {'-'*12}")

    all_results = []
    for name, path in TEST_PHOTOS:
        r = benchmark_photo(name, path)
        all_results.append(r)

        if "error" in r:
            print(f"{name:<30} {'ERROR: ' + r['error']}")
            continue

        dims = r.get("image_dims", "?×?")
        old_loss = r.get("old", {}).get("loss", float("nan"))
        new_unwt = r.get("new_unweighted", {}).get("loss", float("nan"))
        new_wtd = r.get("new_weighted", {}).get("loss", float("nan"))
        w_range = r.get("new_weighted", {}).get("weights", "N/A")

        # Improvement percentage (old vs new weighted)
        if not np.isnan(old_loss) and not np.isnan(new_wtd) and old_loss > 0:
            impr = (old_loss - new_wtd) / old_loss * 100
            impr_str = f"{impr:.0f}% better"
        else:
            impr_str = "N/A"

        old_s = f"{old_loss:.1f}" if not np.isnan(old_loss) else "FAIL"
        nw_s = f"{new_unwt:.1f}" if not np.isnan(new_unwt) else "FAIL"
        w_s = f"{new_wtd:.1f}" if not np.isnan(new_wtd) else "FAIL"

        print(f"{name:<30} {dims:<12} {old_s:<12} {nw_s:<12} {w_s:<12} {w_range:<14} {impr_str}")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("DETAILED RESULTS")
    print("=" * 70)

    for r in all_results:
        if "error" in r:
            continue
        print(f"\n--- {r['name']} ({r.get('image_dims', 'N/A')}) ---")

        for variant in ["old", "new_unweighted", "new_weighted"]:
            data = r.get(variant, {})
            if "error" in data:
                print(f"  {variant}: ERROR - {data['error']}")
                continue
            if not data:
                continue
            loss = data.get("loss", "N/A")
            n_iters = data.get("n_iters", "N/A")
            id_range = data.get("identity_range", "N/A")
            t = data.get("time_s", "N/A")
            n_lmks = data.get("n_lmks", "N/A")
            camera = data.get("camera", {})

            label = {"old": "OLD (hardcoded map + fixed cam)",
                     "new_unweighted": "NEW (derived map + joint cam, unweighted)",
                     "new_weighted": "NEW (derived map + joint cam, confidence-weighted)"}[variant]

            print(f"  [{label}]")
            print(f"    Loss: {loss}  |  Iters: {n_iters}  |  Time: {t}s  |  N landmarks: {n_lmks}")
            print(f"    Identity range: {id_range}")
            if camera:
                angle = camera.get('angle_deg', 0.0)
                print(f"    Camera: scale={camera.get('scale', '?'):.1f}, "
                      f"tx={camera.get('tx', '?'):.0f}, ty={camera.get('ty', '?'):.0f}, "
                      f"angle={angle:.1f} deg")
            weights = data.get("weights")
            if weights:
                print(f"    Weight range: {weights}")

    print("\nDone.")
