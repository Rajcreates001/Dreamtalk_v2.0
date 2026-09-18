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
# Credentials come from the environment and are not stored here. An earlier
# revision of this file hardcoded them, so they are already in this
# repository's history and the account needs rotating regardless - but a
# harness is not a place to keep a password, and every new commit that carries
# one makes the eventual cleanup harder.
#
#   docker exec -e DREAMTALK_QA_EMAIL=... -e DREAMTALK_QA_PASSWORD=... #       dreamtalk-backend python /app/dreamtalk/scripts/qa/e2e_avatar.py all
EMAIL = os.environ.get("DREAMTALK_QA_EMAIL", "")
PASSWORD = os.environ.get("DREAMTALK_QA_PASSWORD", "")
# Overridable so a freshly rebuilt avatar can be checked without editing
# the harness - which is how a "verified" number ends up describing the
# previous build.
PROFILE = os.environ.get("DREAMTALK_QA_PROFILE",
                         "71d2b3f8-51eb-4435-a4ee-665f60049850")
RUNTIME = "/app/dreamtalk/media/avatar_runtime"
OUT = "/tmp/e2e_out"
os.makedirs(OUT, exist_ok=True)

MASKS = "/app/dreamtalk/weights/flame/FLAME_masks.pkl"


def log(section: str, msg: str) -> None:
    print(f"[{section:8}] {msg}", flush=True)


def token() -> str:
    import httpx
    if not EMAIL or not PASSWORD:
        raise SystemExit(
            "Set DREAMTALK_QA_EMAIL and DREAMTALK_QA_PASSWORD. They are not "
            "stored in the repository; pass them to docker exec with -e.")
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

    # "the morph moves some vertices" is too weak a test - a viseme that
    # displaced the ears would pass it - so check WHERE the motion lands.
    #
    # Not by mask, though. The first version of this check required 20% of a
    # viseme's displacement to fall inside FLAME's `lips` region and failed
    # `aa` and `ih`. The mesh was fine; the test was wrong. `lips` contains
    # only the lip vertices, and an open-mouth viseme correctly moves mostly
    # jaw, chin and upper neck - `aa` puts 49% of its motion in `neck`, which
    # is what a dropped jaw looks like.
    #
    # The displacement centroid needs no mask to be the right one. Measured on
    # a good head: visemes sit at 16-28% of head height and blink at 63%.
    up = int(np.argmax(ext))
    y = v[:, up]
    lo, hi = float(y.min()), float(y.max())
    visemes = [n for n in ("aa", "ih", "ou", "ee", "oh") if n in names]
    res["morph_detail"] = {}
    deltas = {}
    bad = []
    for n in names:
        d = accessor(js, binc, prim["targets"][names.index(n)]["POSITION"])
        mag = np.linalg.norm(d, axis=1)
        moved = int((mag > 1e-6).sum())
        total = float(mag.sum())
        height = (float(((y - lo) / (hi - lo) * (mag / total)).sum())
                  if total > 0 else 0.0)
        deltas[n] = d.astype(np.float64).ravel()
        res["morph_detail"][n] = {"moved_vertices": moved,
                                  "max_displacement": round(float(mag.max()), 5),
                                  "centroid_height": round(height, 3)}
        if moved == 0:
            log("mesh", f"FAIL morph '{n}' moves no vertices")
            bad.append(n)
        elif n in visemes and height > 0.40:
            log("mesh", f"FAIL viseme '{n}' is centred at {height:.0%} of head "
                        f"height - that is not the mouth")
            bad.append(n)
    for n in visemes:
        info = res["morph_detail"][n]
        log("mesh", f"viseme {n:3} moves {info['moved_vertices']:4} verts, "
                    f"centred at {info['centroid_height']:.0%} of head height, "
                    f"max {info['max_displacement']:.4f}")
    if "blink" in res["morph_detail"]:
        log("mesh", f"blink        centred at "
                    f"{res['morph_detail']['blink']['centroid_height']:.0%} "
                    f"of head height")

    # Five visemes that are the same shape would animate as one. Any pair
    # above this correlation is a duplicate wearing two names.
    pairs = []
    for i, a in enumerate(visemes):
        for b in visemes[i + 1:]:
            u, w = deltas[a], deltas[b]
            denom = float(np.linalg.norm(u) * np.linalg.norm(w))
            sim = float(u @ w / denom) if denom else 0.0
            pairs.append((round(sim, 3), a, b))
            if sim > 0.98:
                log("mesh", f"FAIL visemes '{a}' and '{b}' are the same shape "
                            f"(cosine {sim:.3f})")
                bad.append(f"{a}~{b}")
    res["viseme_pair_similarity"] = sorted(pairs, reverse=True)
    if pairs:
        worst = max(pairs)
        log("mesh", f"most similar viseme pair: {worst[1]}/{worst[2]} at "
                    f"cosine {worst[0]:.3f} (1.000 would mean identical)")
    res["bad_morphs"] = bad
    res["ok"] = closure >= 95 and depth_ratio > 0.5 and not bad
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
    # The source is a portrait with the head in the upper half of a 768px
    # canvas. Fixed full-frame percentages put the old mouth band on the
    # shirt/torso and could report a valid talking render as motionless.
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = detector.detectMultiScale(imgs[0].astype(np.uint8), scaleFactor=1.08,
                                      minNeighbors=5, minSize=(max(40, w // 10), max(40, h // 10)))
    if len(faces):
        fx, fy, fw, fh = max(faces, key=lambda box: int(box[2]) * int(box[3]))
        regions = {
            "forehead_eyes": (max(0, fy + int(fh * 0.08)), min(h, fy + int(fh * 0.48)),
                               max(0, fx + int(fw * 0.10)), min(w, fx + int(fw * 0.90))),
            "mouth": (max(0, fy + int(fh * 0.52)), min(h, fy + int(fh * 0.92)),
                      max(0, fx + int(fw * 0.10)), min(w, fx + int(fw * 0.90))),
            "background": (0, max(1, int(h * 0.08)), 0, w),
        }
        out_face = [int(fx), int(fy), int(fw), int(fh)]
    else:
        regions = {
            "forehead_eyes": (int(h * 0.15), int(h * 0.45), 0, w),
            "mouth": (int(h * 0.60), int(h * 0.85), 0, w),
            "background": (0, int(h * 0.08), 0, w),
        }
        out_face = None
    out = {"frames": len(files), "size": [w, h], "face_box": out_face}
    for name, (y0, y1, x0, x1) in regions.items():
        diffs = [float(np.abs(imgs[i + 1][y0:y1, x0:x1] - imgs[i][y0:y1, x0:x1]).mean())
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
    video = d.get("video") or d
    url = video.get("video_url") or video.get("url")
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
        eyes = float(m.get("forehead_eyes") or 0.0)
        mouth_ratio_ok = eyes <= 0.15 or (m.get("mouth_over_eyes") or 0) > 1.5
        ok = (m.get("mouth", 0) > 0.5 and mouth_ratio_ok and
              m.get("background", 9) < 0.5)

        # "rest is still" was the verdict this check printed, and it was the
        # wrong thing to want. It was written to catch a renderer that shook
        # the whole face, and it ended up certifying the opposite failure: a
        # photograph with a moving mouth, eyes at exactly 0.000, no blink in
        # four seconds, no head movement at all. Every run passed. The face
        # was dead and the harness called it correct.
        #
        # Isolation is still worth checking, so it stays - but it is now
        # reported as isolation, and the absence of life is reported beside
        # it instead of being the pass condition.
        alive = eyes > 0.02
        res["mouth_isolated"] = bool(ok)
        res["shows_life"] = bool(alive)
        res["verdict"] = (
            ("mouth isolated" if ok else "FAIL mouth not isolated")
            + ("; face shows secondary motion" if alive else
               "; STILL FACE - no blink, no head motion, only the mouth moves")
        )
        # A still face is not a pass. It is the defect that reads as unreal.
        res["ok"] = bool(ok and alive)
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
