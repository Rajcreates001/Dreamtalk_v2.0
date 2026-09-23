"""Derive where MediaPipe's 68 semantic landmarks sit on the FLAME mesh.

flame_fitter carried a hardcoded list of 68 FLAME vertex indices, labelled as
coming from DECA, that were not landmarks: the lowest of them was index 2
rather than 8 (the chin), the most forward was 9 rather than 30 (the nose
tip), and the two "jaw ends" sat 2 cm apart in the middle of the face. DECA
uses a barycentric embedding, not vertex indices, and none ships with this
project; the official FLAME embedding is licence-restricted.

The correspondence can be derived from the model instead. This takes a render
of FLAME's MEAN shape drawn with FLAME's MEAN albedo through a written-down
orthographic camera (scripts/qa or the scratch renderer produce it), runs the
same MediaPipe FaceLandmarker the pipeline uses, and for each semantic point
records the front-most triangle underneath it and the barycentric position
inside that triangle. A barycentric point, not a nearest vertex: FLAME's face
vertices are a few millimetres apart, which is most of an eyelid.

Usage (inside dreamtalk-backend, which has MediaPipe):
    python derive_flame_landmarks.py <render.png> <camera.json>

Prints the embedding as literals for flame_fitter.FLAME_MP68_EMBEDDING and the
checks it has to pass before it is worth pasting.
"""
import json
import pickle
import sys

import cv2
import numpy as np

sys.path.insert(0, "/app")
from dreamtalk.pipeline import flame_fitter as ff  # noqa: E402

RENDER, CAMERA = sys.argv[1], sys.argv[2]
UP, SIDE, DEPTH = 1, 0, 2

with open("/app/dreamtalk/weights/flame/FLAME2020_numpy.pkl", "rb") as f:
    model = pickle.load(f, encoding="latin1")
V = np.asarray(model["v_template"], np.float64)
F = np.asarray(model["f"], np.int64)
cam = json.load(open(CAMERA))
ctr, scale, size = np.asarray(cam["ctr"]), cam["scale"], cam["size"]
PX = np.column_stack([(V[:, SIDE] - ctr[SIDE]) * scale + size / 2,
                      size / 2 - (V[:, UP] - ctr[UP]) * scale])

lm, _ = ff.detect_landmarks(RENDER)
if lm is None or len(lm) < 468:
    raise SystemExit("MediaPipe found no face on the render")
MP = ff.MP_TO_IBUG68
pts = lm[MP]

tri2 = PX[F]                                        # (F,3,2)
triz = V[F][:, :, DEPTH]


def locate(p):
    """Front-most triangle containing p, and p's barycentric coordinates."""
    a, b, c = tri2[:, 0], tri2[:, 1], tri2[:, 2]
    v0, v1, v2 = b - a, c - a, p[None, :] - a
    d00 = (v0 * v0).sum(1)
    d01 = (v0 * v1).sum(1)
    d11 = (v1 * v1).sum(1)
    d20 = (v2 * v0).sum(1)
    d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-12
    bb = np.where(ok, (d11 * d20 - d01 * d21) / np.where(ok, den, 1), -1)
    gg = np.where(ok, (d00 * d21 - d01 * d20) / np.where(ok, den, 1), -1)
    aa = 1.0 - bb - gg
    inside = ok & (aa >= -1e-6) & (bb >= -1e-6) & (gg >= -1e-6)
    if not inside.any():
        return None
    cand = np.nonzero(inside)[0]
    depth = aa[cand] * triz[cand, 0] + bb[cand] * triz[cand, 1] + gg[cand] * triz[cand, 2]
    k = cand[int(np.argmax(depth))]
    return k, np.array([aa[k], bb[k], gg[k]])


# Vertices facing the camera, for the contour points that land just outside
# the silhouette: MediaPipe's jaw line can sit a pixel or two past the mesh
# edge. Those snap to the nearest front-facing vertex and are reported, so a
# large snap cannot hide in the output.
n = np.zeros_like(V)
tri3 = V[F]
fn = np.cross(tri3[:, 1] - tri3[:, 0], tri3[:, 2] - tri3[:, 0])
for k in range(3):
    np.add.at(n, F[:, k], fn)
front = n[:, DEPTH] > 0

face_idx = np.zeros(68, np.int64)
bary = np.zeros((68, 3))
snapped = []
for i, p in enumerate(pts):
    hit = locate(p)
    if hit is None:
        cand = np.nonzero(front)[0]
        vi = cand[int(np.argmin(np.linalg.norm(PX[cand] - p, axis=1)))]
        fi = int(np.nonzero((F == vi).any(1))[0][0])
        b = (F[fi] == vi).astype(float)
        hit = (fi, b)
        snapped.append((i, float(np.linalg.norm(PX[vi] - p))))
    face_idx[i], bary[i] = hit
print("snapped to the silhouette: %s" % (", ".join("%d (%.1f px)" % s for s in snapped) or "none"))

L = (V[F[face_idx]] * bary[:, :, None]).sum(1)      # (68,3) on the mean shape
back = np.column_stack([(L[:, SIDE] - ctr[SIDE]) * scale + size / 2,
                        size / 2 - (L[:, UP] - ctr[UP]) * scale])
print("reprojection of the embedding onto the detections: max %.2f px"
      % np.linalg.norm(back - pts, axis=1).max())

# Anatomy the old index list failed.
print("lowest landmark: %d (the chin is 8)" % int(np.argmin(L[:, UP])))
print("most forward landmark: %d (the nose tip is 30; 27-35 is the nose)"
      % int(np.argmax(L[:, DEPTH])))
MIRROR = [(0, 16), (1, 15), (2, 14), (3, 13), (4, 12), (5, 11), (6, 10), (7, 9),
          (17, 26), (18, 25), (19, 24), (20, 23), (21, 22),
          (31, 35), (32, 34), (36, 45), (37, 44), (38, 43), (39, 42), (40, 47),
          (41, 46), (48, 54), (49, 53), (50, 52), (55, 59), (56, 58),
          (60, 64), (61, 63), (65, 67)]
asym = [abs(L[a, SIDE] + L[b, SIDE]) + abs(L[a, UP] - L[b, UP]) for a, b in MIRROR]
print("left/right mirror pairs: worst asymmetry %.2f mm, mean %.2f mm"
      % (1000 * max(asym), 1000 * np.mean(asym)))
print("eye 36..41 span: %.1f x %.1f mm"
      % (1000 * np.ptp(L[36:42, SIDE]), 1000 * np.ptp(L[36:42, UP])))

np.set_printoptions(precision=6, suppress=True, linewidth=100)
print("\nFLAME_MP68_FACES = np.array(%s)" % face_idx.tolist())
print("FLAME_MP68_BARY = np.array(%s)" % np.round(bary, 6).tolist())
