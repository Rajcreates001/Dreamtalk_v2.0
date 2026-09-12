"""Definitive lip-sync check: true lip aperture per frame vs the audio envelope.

Tracks the inner-lip landmarks on every frame to get a real mouth-opening
signal (robust to beards, unlike pixel-darkness proxies), then correlates it
with the speech envelope, allowing for a small A/V offset.
"""
import os
import subprocess
import sys

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MP4 = sys.argv[1] if len(sys.argv) > 1 else "/app/dreamtalk/e2e_deep/talking_head.mp4"
OUT = os.path.dirname(MP4)

cap = cv2.VideoCapture(MP4)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
cap.release()
print(f"{len(frames)} frames @ {fps:.1f}fps")

# The installed mediapipe exposes only the Tasks API (no mp.solutions), so
# build a FaceLandmarker once and reuse it across frames.
MODEL = None
for c in ("/app/dreamtalk/weights/face/face_landmarker.task",
          "/app/dreamtalk/weights/face/face_landmarker_v2_with_blendshapes.task"):
    if os.path.exists(c):
        MODEL = c
        break
if MODEL is None:
    sys.exit("face_landmarker.task not found")
mesh = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.IMAGE, num_faces=1))

UPPER_INNER, LOWER_INNER = 13, 14      # inner lip centre pair
LEFT_C, RIGHT_C = 78, 308              # mouth corners

aperture, width, ok_frames = [], [], 0
for f in frames:
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                      data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    res = mesh.detect(mp_img)
    if not res.face_landmarks:
        aperture.append(np.nan); width.append(np.nan); continue
    lm = res.face_landmarks[0]
    h, w = f.shape[:2]
    p = lambda i: np.array([lm[i].x * w, lm[i].y * h])  # noqa: E731
    span = np.linalg.norm(p(LEFT_C) - p(RIGHT_C)) + 1e-6
    aperture.append(float(np.linalg.norm(p(UPPER_INNER) - p(LOWER_INNER)) / span))
    width.append(float(span))
    ok_frames += 1
mesh.close()

ap = np.array(aperture, dtype=float)
print(f"landmarks found on {ok_frames}/{len(frames)} frames")
valid = np.isfinite(ap)
if valid.sum() < 20:
    sys.exit("too few tracked frames")
ap = np.interp(np.arange(len(ap)), np.flatnonzero(valid), ap[valid])

print(f"lip aperture (normalised by mouth width):")
print(f"  min {ap.min():.4f}  max {ap.max():.4f}  mean {ap.mean():.4f}  std {ap.std():.4f}")
print(f"  dynamic range (max-min) = {ap.max()-ap.min():.4f}")

wav = os.path.join(OUT, "_audio2.wav")
subprocess.run(["ffmpeg", "-y", "-i", MP4, "-vn", "-ac", "1", "-ar", "16000", wav],
               capture_output=True)
import librosa  # noqa: E402
y, sr = librosa.load(wav, sr=16000, mono=True)
hop = max(1, int(round(sr / fps)))
env = np.array([np.sqrt(np.mean(y[i * hop:(i + 1) * hop] ** 2) + 1e-12)
                for i in range(len(frames))])

n = min(len(env), len(ap))
a = (ap[:n] - ap[:n].mean()) / (ap[:n].std() + 1e-9)
e = (env[:n] - env[:n].mean()) / (env[:n].std() + 1e-9)

best_r, best_lag = -2.0, 0
for lag in range(-8, 9):                       # +/- 320 ms of A/V offset
    if lag < 0:
        r = np.corrcoef(a[-lag:], e[:n + lag])[0, 1]
    elif lag > 0:
        r = np.corrcoef(a[:n - lag], e[lag:])[0, 1]
    else:
        r = np.corrcoef(a, e)[0, 1]
    if np.isfinite(r) and r > best_r:
        best_r, best_lag = float(r), lag
print(f"\ncorrelation aperture vs audio envelope: r={best_r:+.3f} at lag {best_lag} frames "
      f"({best_lag/fps*1000:+.0f} ms)")

# Speech vs silence: the mouth should be more open while there is speech.
thr = np.percentile(env[:n], 60)
loud, quiet = ap[:n][env[:n] >= thr], ap[:n][env[:n] < thr]
print(f"aperture while speaking  {loud.mean():.4f}")
print(f"aperture while quiet     {quiet.mean():.4f}")
print(f"difference               {loud.mean()-quiet.mean():+.4f}")

checks = [
    ("mouth aperture varies", ap.std() > 0.01, f"std={ap.std():.4f}"),
    ("aperture correlates with speech", best_r > 0.20, f"r={best_r:+.3f} @ {best_lag}f"),
    ("mouth more open during speech", loud.mean() > quiet.mean(),
     f"{loud.mean():.4f} vs {quiet.mean():.4f}"),
]
print()
fails = 0
for name, ok, d in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name} — {d}")
    fails += (not ok)
sys.exit(1 if fails else 0)
