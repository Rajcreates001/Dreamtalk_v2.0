"""Measure lip-sync in a rendered talking-head video.

Locates the mouth with MediaPipe face landmarks (not hardcoded fractions), then
compares per-frame pixel change in the mouth against a forehead control region.
Real lip-sync repaints the mouth and leaves the forehead alone, so the ratio is
the signal. Also correlates mouth motion against the audio envelope.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

MP4 = sys.argv[1] if len(sys.argv) > 1 else "/app/dreamtalk/e2e_deep/talking_head.mp4"
OUT = os.path.dirname(MP4)

cap = cv2.VideoCapture(MP4)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
frames = []
while True:
    ok, fr = cap.read()
    if not ok:
        break
    frames.append(fr)
cap.release()
H, W = frames[0].shape[:2]
print(f"video {W}x{H}  {len(frames)} frames @ {fps:.1f}fps = {len(frames)/fps:.1f}s")

# ── locate the mouth with landmarks ───────────────────────────────────
sys.path.insert(0, "/app")
from dreamtalk.pipeline.flame_fitter import detect_landmarks  # noqa: E402

probe = os.path.join(OUT, "_probe.png")
cv2.imwrite(probe, frames[len(frames) // 2])
lm, _ = detect_landmarks(probe)
if lm is None:
    sys.exit("no face landmarks in the rendered video — cannot locate mouth")

# MediaPipe FaceMesh: outer lip ring, and brow/forehead indices.
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
        185, 40, 39, 37, 0, 267, 269, 270, 409]
BROW = [70, 63, 105, 66, 107, 336, 296, 334, 293, 300, 10, 151]


def box(idx, pad=0.25):
    pts = lm[idx]
    x0, y0 = pts[:, 0].min(), pts[:, 1].min()
    x1, y1 = pts[:, 0].max(), pts[:, 1].max()
    dx, dy = (x1 - x0) * pad, (y1 - y0) * pad
    return (max(0, int(y0 - dy)), min(H, int(y1 + dy)),
            max(0, int(x0 - dx)), min(W, int(x1 + dx)))


my0, my1, mx0, mx1 = box(LIPS)
by0, by1, bx0, bx1 = box(BROW)
print(f"mouth box    y[{my0},{my1}] x[{mx0},{mx1}]")
print(f"forehead box y[{by0},{by1}] x[{bx0},{bx1}]")

g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames]
mouth_d = np.array([np.mean(np.abs(g[i][my0:my1, mx0:mx1] - g[i - 1][my0:my1, mx0:mx1]))
                    for i in range(1, len(g))])
brow_d = np.array([np.mean(np.abs(g[i][by0:by1, bx0:bx1] - g[i - 1][by0:by1, bx0:bx1]))
                   for i in range(1, len(g))])

# Mouth openness proxy: vertical dark-pixel extent inside the mouth box.
open_px = []
for f in frames:
    roi = cv2.cvtColor(f[my0:my1, mx0:mx1], cv2.COLOR_BGR2GRAY)
    thr = roi < max(40, int(np.percentile(roi, 15)))
    open_px.append(float(thr.sum()) / thr.size)
open_px = np.array(open_px)

# ── audio envelope ────────────────────────────────────────────────────
wav = os.path.join(OUT, "_audio.wav")
subprocess.run(["ffmpeg", "-y", "-i", MP4, "-vn", "-ac", "1", "-ar", "16000", wav],
               capture_output=True)
import librosa  # noqa: E402
y, sr = librosa.load(wav, sr=16000, mono=True)
hop = max(1, int(sr / fps))
env = np.array([np.sqrt(np.mean(y[i * hop:(i + 1) * hop] ** 2) + 1e-12)
                for i in range(len(frames))])
env = (env - env.mean()) / (env.std() + 1e-9)
op = (open_px - open_px.mean()) / (open_px.std() + 1e-9)
n = min(len(env), len(op))
corr = float(np.corrcoef(env[:n], op[:n])[0, 1])

print("\n── measurements ──")
print(f"mouth mean |delta|     {mouth_d.mean():.3f}")
print(f"forehead mean |delta|  {brow_d.mean():.3f}   (control)")
print(f"ratio mouth/forehead   {mouth_d.mean()/max(brow_d.mean(),1e-6):.2f}x")
print(f"mouth motion std       {mouth_d.std():.3f}")
print(f"mouth-open vs audio r  {corr:+.3f}")
print(f"audio rms              {np.sqrt(np.mean(y**2)):.4f}  dur {len(y)/sr:.1f}s")

checks = [
    ("mouth region actually changes", mouth_d.mean() > 0.5, f"{mouth_d.mean():.3f}"),
    ("mouth changes more than forehead", mouth_d.mean() > brow_d.mean() * 1.5,
     f"{mouth_d.mean()/max(brow_d.mean(),1e-6):.2f}x"),
    ("motion is time-varying (not a loop)", mouth_d.std() > 0.2, f"std={mouth_d.std():.3f}"),
    ("mouth opening tracks the audio", corr > 0.15, f"r={corr:+.3f}"),
]
print()
fails = 0
for name, ok, d in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name} — {d}")
    fails += (not ok)

# Save the most-open and most-closed frames for visual confirmation.
cv2.imwrite(os.path.join(OUT, "mouth_most_open.png"), frames[int(np.argmax(open_px))])
cv2.imwrite(os.path.join(OUT, "mouth_most_closed.png"), frames[int(np.argmin(open_px))])
crop = lambda f: f[my0:my1, mx0:mx1]  # noqa: E731
cv2.imwrite(os.path.join(OUT, "mouth_crop_open.png"),
            cv2.resize(crop(frames[int(np.argmax(open_px))]), None, fx=3, fy=3))
cv2.imwrite(os.path.join(OUT, "mouth_crop_closed.png"),
            cv2.resize(crop(frames[int(np.argmin(open_px))]), None, fx=3, fy=3))
print(f"\nwrote mouth_most_open/closed.png and 3x mouth crops to {OUT}")
json.dump({"mouth_delta": mouth_d.tolist(), "open": open_px.tolist()},
          open(os.path.join(OUT, "lipsync_series.json"), "w"))
sys.exit(1 if fails else 0)
