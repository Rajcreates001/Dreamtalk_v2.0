"""Diagnose the FLAME UV texture projection on a real photo.

Reports whether solvePnP produces a pose that actually lands the mesh on the
face, and writes an overlay of the projected vertices on the photo.
"""
import os
import sys
import numpy as np
import cv2

sys.path.insert(0, "/app")
from dreamtalk.pipeline.flame_fitter import (  # noqa: E402
    FlameFitter, detect_landmarks, derive_mp68_mapping,
    estimate_head_pose, project_vertices_to_photo, fit_identity_from_landmarks,
)

PHOTO = sys.argv[1] if len(sys.argv) > 1 else \
    "/app/dreamtalk/local_upload_testing/Image_local/Maharaj Profile.jpg"
OUT = "/app/dreamtalk/e2e_deep"
os.makedirs(OUT, exist_ok=True)

img = cv2.imread(PHOTO)
H, W = img.shape[:2]
print(f"photo {W}x{H}")

lm2d, _n = detect_landmarks(PHOTO)
print("landmarks_2d:", None if lm2d is None else lm2d.shape)
if lm2d is None:
    sys.exit("no landmarks")
print(f"  landmark bbox x[{lm2d[:,0].min():.0f},{lm2d[:,0].max():.0f}] "
      f"y[{lm2d[:,1].min():.0f},{lm2d[:,1].max():.0f}]")

fitter = FlameFitter()
flame = fitter.flame

# Fit identity the same way fit_from_photo does.
try:
    ident, cam = fit_identity_from_landmarks(flame, lm2d, W, H, n_components=30, reg_strength=5.0)
    print("identity fitted; cam =", cam)
except Exception as e:
    print("identity fit failed:", e)
    ident, cam = None, None

verts = flame.generate_mesh(identity_coeffs=ident)
print("verts", verts.shape, "bbox",
      [(round(float(verts[:, i].min()), 3), round(float(verts[:, i].max()), 3)) for i in range(3)])

mp_idx, _ = derive_mp68_mapping(flame, verts, lm2d, W)
valid = mp_idx < len(lm2d)
lmk2 = lm2d[mp_idx[valid]]
lmk3 = flame.get_landmarks(verts)[valid]
print(f"correspondences: {len(lmk2)}")

rvec, tvec, K = estimate_head_pose(lmk3, lmk2, W, H)
print("solvePnP ->", "OK" if rvec is not None else "FAILED")
if rvec is None:
    sys.exit("pose failed -> RBF fallback path is what produced the smear")

print("  rvec", np.round(rvec.ravel(), 3), " tvec", np.round(tvec.ravel(), 3))
px = project_vertices_to_photo(verts, rvec, tvec, K)
print(f"projected px bbox x[{px[:,0].min():.0f},{px[:,0].max():.0f}] "
      f"y[{px[:,1].min():.0f},{px[:,1].max():.0f}]  (image is {W}x{H})")

inside = ((px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < H)).mean()
print(f"fraction of vertices inside image: {inside*100:.1f}%")

# How well do projected landmarks match the detected 2D landmarks?
plmk = project_vertices_to_photo(lmk3, rvec, tvec, K)
err = np.linalg.norm(plmk - lmk2, axis=1)
face_w = lm2d[:, 0].max() - lm2d[:, 0].min()
print(f"landmark reprojection error: mean={err.mean():.1f}px median={np.median(err):.1f}px "
      f"({err.mean()/face_w*100:.1f}% of face width)")

ov = img.copy()
for p in px[::5]:
    x, y = int(p[0]), int(p[1])
    if 0 <= x < W and 0 <= y < H:
        cv2.circle(ov, (x, y), 1, (0, 255, 0), -1)
for p in lm2d:
    cv2.circle(ov, (int(p[0]), int(p[1])), 3, (0, 0, 255), -1)
cv2.imwrite(os.path.join(OUT, "projection_overlay.jpg"), ov)
print("wrote projection_overlay.jpg (green = projected mesh, red = detected landmarks)")
