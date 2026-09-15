"""DreamTalk end-to-end verification.

Phases are independent so a slow one can be run alone:

  python e2e_avatar.py train      # build an avatar (FLAME fit + voice clone)
  python e2e_avatar.py mesh       # 3D geometry, morph targets, blink closure
  python e2e_avatar.py voice      # cloned speech across languages
  python e2e_avatar.py lipsync    # 2D video + measured facial motion
  python e2e_avatar.py all

Every check reports a measured number, not a boolean, because "a file was
produced" is exactly the assertion that let a still photograph pass as a
talking head for weeks.

Runs inside dreamtalk-backend:
  docker exec -i dreamtalk-backend python - < e2e_avatar.py <phase>
"""
from __future__ import annotations

import glob
import json
import os
import pickle
import struct
import subprocess
import sys
import time
from urllib.parse import unquote, urlparse

import numpy as np

API = "http://localhost:5000/api/v1"
EMAIL = "wiz1789388539@qa.dev"
PASSWORD = "Qa!2345678"
PROFILE = "71d2b3f8-51eb-4435-a4ee-665f60049850"
RUNTIME = "/app/dreamtalk/media/avatar_runtime"
OUT = "/tmp/e2e_out"
os.makedirs(OUT, exist_ok=True)

MASKS = "/app/dreamtalk/weights/flame/FLAME_masks.pkl"


def log(section: str, msg: str) -> None:
    print(f"[{section:8}] {msg}", flush=True)


def token() -> str:
    import httpx
    r = httpx.post(f"{API}/auth/login",
                   json={"email": EMAIL, "password": PASSWORD}, timeout=60)
    r.raise_for_status()
    d = r.json()
    return (d.get("tokens") or d)["access_token"]


# ── glTF helpers ──────────────────────────────────────────────────────
def read_glb(path: str):
    data = open(path, "rb").read()
    off, js, binc = 12, None, None
    while off < len(data):
        ln, ty = struct.unpack_from("<II", data, off)
        off += 8
        if ty == 0x4E4F534A:
            js = json.loads(data[off:off + ln])
        elif ty == 0x004E4942:
            binc = data[off:off + ln]
        off += ln
    return js, binc


def accessor(js, binc, idx):
    a = js["accessors"][idx]
    bv = js["bufferViews"][a["bufferView"]]
    o = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(binc, np.float32, count=a["count"] * 3, offset=o).reshape(-1, 3)


# ── phases ────────────────────────────────────────────────────────────
def phase_mesh() -> dict:
    """3D geometry, morph targets, and whether the blink can shut the eye."""
    res = {}
    g = sorted(glob.glob(f"{RUNTIME}/{PROFILE}/appearance/generated/*.glb"))
    if not g:
        log("mesh", "FAIL no GLB found")
        return {"ok": False}
    js, binc = read_glb(g[0])
    head = [m for m in js["meshes"] if m["name"] == "Head"][0]
    prim = head["primitives"][0]
    names = head["extras"]["targetNames"]
    v = accessor(js, binc, prim["attributes"]["POSITION"]).astype(np.float64)

    ext = v.max(0) - v.min(0)
    order = np.argsort(-ext)
    depth_ratio = float(ext[order[2]] / ext[order[1]])
    res["meshes"] = [m["name"] for m in js["meshes"]]
    res["head_verts"] = len(v)
    res["depth_over_width"] = round(depth_ratio, 3)
    res["morph_targets"] = names
    log("mesh", f"meshes={res['meshes']}")
    log("mesh", f"head verts={len(v)}  depth/width={depth_ratio:.2f} "
                f"(flat plane=0.00, real head~1.0-1.3)")

    masks = pickle.load(open(MASKS, "rb"), encoding="latin1")
    up = int(np.argmax(ext))
    le = np.asarray(masks["left_eye_region"], np.int64)
    lb = np.asarray(masks["left_eyeball"], np.int64)
    span = float(v[lb][:, up].ptp())
    blink = accessor(js, binc, prim["targets"][names.index("blink")]["POSITION"])
    closure = float(np.linalg.norm(blink[le], axis=1).max() / span * 100)
    res["blink_closure_pct"] = round(closure, 1)
    log("mesh", f"blink closes {closure:.1f}% of the eyeball "
                f"({'PASS' if closure >= 95 else 'FAIL - eye cannot shut'})")

    for n in names:
        d = accessor(js, binc, prim["targets"][names.index(n)]["POSITION"])
        moved = int((np.linalg.norm(d, axis=1) > 1e-6).sum())
        if moved == 0:
            log("mesh", f"WARN morph '{n}' moves no vertices")
    res["ok"] = closure >= 95 and depth_ratio > 0.5
    return res


def phase_voice(langs=("hi", "ta", "te", "bn", "en")) -> dict:
    """Cloned speech per language: engine used, clone vs stand-in, latency."""
    import httpx
    tok = token()
    rows = []
    for lang in langs:
        t0 = time.time()
        try:
            r = httpx.post(
                f"{API}/avatar/profiles/{PROFILE}/respond",
                headers={"Authorization": f"Bearer {tok}"},
                json={"message": "Say one short greeting.", "language": lang,
                      "synthesize": True, "strict_clone": False,
                      "render_video": False},
                timeout=1800,
            )
            dt = time.time() - t0
            r.raise_for_status()
            d = r.json()
            a = d.get("audio") or {}
            row = {
                "lang": lang, "ok": True, "latency_s": round(dt, 1),
                "engine": a.get("engine"), "cloned": a.get("cloned"),
                "audio_url": d.get("audio_url"),
                "reply": (d.get("response") or "")[:60],
                "fallback_reason": a.get("fallback_reason"),
            }
        except Exception as exc:
            row = {"lang": lang, "ok": False,
                   "error": f"{type(exc).__name__}: {exc}"[:160],
                   "latency_s": round(time.time() - t0, 1)}
        rows.append(row)
        log("voice", json.dumps(row, ensure_ascii=False))
    return {"rows": rows}


def _frame_motion(video: str) -> dict:
    """Measure where the face actually moves, region by region.

    A talking head must move at the mouth and stay put elsewhere. Reporting
    only "a video exists" is what allowed a completely still render, and a
    render that shook the whole face, to both look like success.
    """
    d = f"{OUT}/frames"
    subprocess.run(["rm", "-rf", d], check=False)
    os.makedirs(d, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=12",
                    f"{d}/%04d.png"], check=True)
    import cv2
    files = sorted(glob.glob(f"{d}/*.png"))
    if len(files) < 3:
        return {"frames": len(files), "error": "too few frames"}
    imgs = [cv2.imread(f, cv2.IMREAD_GRAYSCALE).astype(np.float32) for f in files]
    h, w = imgs[0].shape
    bands = {
        "forehead_eyes": (int(h * 0.15), int(h * 0.45)),
        "mouth":         (int(h * 0.60), int(h * 0.85)),
        "background":    (0, int(h * 0.08)),
    }
    out = {"frames": len(files), "size": [w, h]}
    for name, (y0, y1) in bands.items():
        diffs = [float(np.abs(imgs[i + 1][y0:y1] - imgs[i][y0:y1]).mean())
                 for i in range(len(imgs) - 1)]
        out[name] = round(float(np.mean(diffs)), 3)
    out["mouth_over_eyes"] = (round(out["mouth"] / out["forehead_eyes"], 2)
                              if out["forehead_eyes"] > 1e-6 else None)
    return out


def phase_lipsync() -> dict:
    """Render a 2D talking head and prove the mouth actually moves."""
    import httpx
    tok = token()
    ref = f"{RUNTIME}/{PROFILE}/voice/reference.wav"
    clip = f"{OUT}/clip4s.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", ref, "-t", "4", clip],
                   check=True)
    t0 = time.time()
    with open(clip, "rb") as fh:
        r = httpx.post(
            f"{API}/avatar/profiles/{PROFILE}/render-2d",
            headers={"Authorization": f"Bearer {tok}"},
            files={"audio": ("clip.wav", fh.read(), "audio/wav")},
            data={"engine": "musetalk"},
            timeout=3600,
        )
    dt = time.time() - t0
    log("lipsync", f"render-2d HTTP {r.status_code} in {dt:.1f}s")
    if r.status_code >= 400:
        log("lipsync", f"FAIL {r.text[:300]}")
        return {"ok": False, "status": r.status_code, "body": r.text[:300]}
    d = r.json()
    url = d.get("video_url") or (d.get("video") or {}).get("video_url")
    local = None
    expected_name = os.path.basename(unquote(urlparse(url or "").path))
    for cand in glob.glob(f"{RUNTIME}/{PROFILE}/responses/**/*.mp4", recursive=True):
        if expected_name and os.path.basename(cand) == expected_name:
            local = cand
            break
    res = {"ok": False, "latency_s": round(dt, 1), "video_url": url,
           "engine": d.get("engine"), "local": local}
    if local:
        res["motion"] = _frame_motion(local)
        m = res["motion"]
        log("lipsync", f"motion mouth={m.get('mouth')} eyes={m.get('forehead_eyes')} "
                       f"bg={m.get('background')} ratio={m.get('mouth_over_eyes')}")
        ok = (m.get("mouth", 0) > 0.5 and
              (m.get("mouth_over_eyes") or 0) > 1.5 and
              m.get("background", 9) < 0.5)
        res["verdict"] = ("PASS mouth moves, rest is still" if ok else
                          "FAIL see numbers above")
        res["ok"] = bool(ok)
        log("lipsync", res["verdict"])
    else:
        res["verdict"] = "FAIL response video was not found; refusing to inspect an older render"
        log("lipsync", res["verdict"])
    return res


def phase_train() -> dict:
    """Build a whole avatar: FLAME fit, texture bake, GLB, voice clone."""
    import httpx
    tok = token()
    src_img = f"{RUNTIME}/{PROFILE}/appearance/source/face_1.jpg"
    src_wav = f"{RUNTIME}/{PROFILE}/voice/reference.wav"
    t0 = time.time()
    with open(src_img, "rb") as im, open(src_wav, "rb") as wv:
        r = httpx.post(
            f"{API}/avatar/profiles",
            headers={"Authorization": f"Bearer {tok}"},
            data={"name": "E2E Avatar", "consent_confirmed": "true",
                  "consent_subject_name": "E2E Avatar", "language": "auto"},
            files=[("voice_sample", ("reference.wav", wv.read(), "audio/wav")),
                   ("face_images", ("face.jpg", im.read(), "image/jpeg"))],
            timeout=3600,
        )
    dt = time.time() - t0
    log("train", f"create_profile HTTP {r.status_code} in {dt:.1f}s")
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "body": r.text[:300]}
    p = r.json()
    app, voice = p.get("appearance") or {}, p.get("voice") or {}
    res = {
        "ok": p.get("status") == "ready", "latency_s": round(dt, 1),
        "id": p.get("id"), "status": p.get("status"),
        "glb": bool(app.get("glb_url")), "mesh": bool(app.get("mesh_url")),
        "texture": bool(app.get("texture_url")),
        "blendshapes": len(app.get("blendshape_names") or []),
        "voice_ready": voice.get("ready"),
        "clone_verified": (voice.get("validation") or {}).get("cloned"),
        "validated_language": voice.get("validated_language"),
    }
    log("train", json.dumps(res, ensure_ascii=False))
    return res


PHASES = {"train": phase_train, "mesh": phase_mesh,
          "voice": phase_voice, "lipsync": phase_lipsync}

if __name__ == "__main__":
    want = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(PHASES) if want == "all" else [want]
    report = {}
    for n in names:
        log("run", f"===== {n} =====")
        try:
            report[n] = PHASES[n]()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            report[n] = {"ok": False, "error": str(exc)[:200]}
    with open(f"{OUT}/report.json", "w") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
    log("run", f"wrote {OUT}/report.json")
