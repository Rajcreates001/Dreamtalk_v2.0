"""Compare the fitted FLAME identity against the mean face.

FLAME identity coefficients are expressed in standard deviations of the shape
PCA; sane fits sit within roughly +/-3. Anything far outside that is a diverged
fit and produces a deformed head.
"""
import sys
import inspect
import numpy as np

sys.path.insert(0, "/app")
from dreamtalk.pipeline import flame_fitter as ff  # noqa: E402

PHOTO = sys.argv[1] if len(sys.argv) > 1 else \
    "/app/dreamtalk/local_upload_testing/Image_local/Maharaj Profile.jpg"

import cv2  # noqa: E402
img = cv2.imread(PHOTO)
H, W = img.shape[:2]
lm2d, _ = ff.detect_landmarks(PHOTO)
print("landmarks:", lm2d.shape)

print("fit_identity_from_landmarks signature:")
print("   ", inspect.signature(ff.fit_identity_from_landmarks))

fitter = ff.FlameFitter()
flame = fitter.flame

out = ff.fit_identity_from_landmarks(flame, lm2d, W, H)
print("returns:", type(out), len(out) if isinstance(out, tuple) else "")
ident = out[0] if isinstance(out, tuple) else out
ident = np.asarray(ident).ravel()

print(f"\nidentity coeffs: n={ident.size}")
print(f"  range  [{ident.min():.3f}, {ident.max():.3f}]")
print(f"  |max|  {np.abs(ident).max():.3f}   (sane FLAME fits are within ~3 sigma)")
print(f"  mean   {ident.mean():.3f}   std {ident.std():.3f}")
print(f"  #coeffs beyond 3 sigma: {(np.abs(ident) > 3).sum()} / {ident.size}")
print(f"  #coeffs beyond 10 sigma: {(np.abs(ident) > 10).sum()} / {ident.size}")

mean_v = flame.generate_mesh()
fit_v = flame.generate_mesh(identity_coeffs=ident)


def span(v):
    return [round(float(v[:, i].max() - v[:, i].min()), 4) for i in range(3)]


print(f"\nmean  mesh span XYZ = {span(mean_v)}")
print(f"fitted mesh span XYZ = {span(fit_v)}")
d = np.linalg.norm(fit_v - mean_v, axis=1)
head = mean_v[:, 1].max() - mean_v[:, 1].min()
print(f"per-vertex displacement from mean: mean={d.mean()/head*100:.1f}% "
      f"max={d.max()/head*100:.1f}% of head height")
print("VERDICT:", "DIVERGED — mesh is deformed" if np.abs(ident).max() > 6
      else "within sane range")
