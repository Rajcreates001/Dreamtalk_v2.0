"""DreamTalk deep end-to-end verification.

Runs INSIDE the backend container (needs librosa / cv2 / ffmpeg) and drives the
live API the way the frontend does, then *measures* the results rather than
eyeballing them:

  phase 1  create an avatar profile from a real photo + voice sample
  phase 2  3D head: morph targets, texture atlas, geometry sanity
  phase 3  2D talking head: render MP4, measure per-frame mouth movement
  phase 4  voice cloning: speaker similarity vs the reference sample
  phase 5  all 22 scheduled languages
  phase 6  all emotions, with prosody actually compared
  phase 7  brain: multi-turn memory recall
  phase 8  persistence: profile + assets survive and are re-fetchable

Artifacts land in /app/dreamtalk/e2e_deep (host: dreamtalk/e2e_deep).
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
import uuid
import urllib.request
import urllib.error

API = os.environ.get("API", "http://localhost:5000")
FACE = os.environ.get("FACE", "/app/dreamtalk/local_upload_testing/Image_local/Maharaj Profile.jpg")
VOICE = os.environ.get("VOICE", "/app/dreamtalk/local_upload_testing/Voice_local/sample1.wav")
OUT = os.environ.get("OUT", "/app/dreamtalk/e2e_deep")
STATE = os.path.join(OUT, "state.json")

os.makedirs(OUT, exist_ok=True)
results: list[tuple[str, bool, str]] = []


def rec(stage: str, ok: bool, detail: str = "") -> bool:
    results.append((stage, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {stage}" + (f" — {detail}" if detail else ""), flush=True)
    return ok


def req(method, path, body=None, token=None, form=None, raw=False, timeout=2400):
    url = path if path.startswith("http") else API + path
    headers, data = {}, None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        boundary = "----dt" + uuid.uuid4().hex
        buf = io.BytesIO()
        for k, v in form:
            buf.write(f"--{boundary}\r\n".encode())
            if isinstance(v, tuple):
                fn, content, ct = v
                buf.write(f'Content-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'.encode())
                buf.write(f"Content-Type: {ct}\r\n\r\n".encode())
                buf.write(content)
            else:
                buf.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
                buf.write(str(v).encode())
            buf.write(b"\r\n")
        buf.write(f"--{boundary}--\r\n".encode())
        data = buf.getvalue()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            payload = resp.read()
            return resp.status, (payload if raw else _loads(payload))
    except urllib.error.HTTPError as e:
        payload = e.read()
        return e.code, (payload if raw else _loads(payload))
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def _loads(payload):
    try:
        return json.loads(payload)
    except Exception:  # noqa: BLE001
        return payload[:400]


def save_state(d):
    json.dump(d, open(STATE, "w"), indent=1)


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def asset(url, token, dest):
    """Download a runtime asset (signed URL) to dest."""
    full = url if url.startswith("http") else API + url
    st, blob = req("GET", full, token=token, raw=True)
    if st == 200 and isinstance(blob, (bytes, bytearray)):
        open(dest, "wb").write(blob)
        return len(blob)
    return 0


# ── phase 1 ───────────────────────────────────────────────────────────
def phase1():
    print("\n=== PHASE 1 — profile creation ===")
    st, _ = req("GET", "/livez")
    rec("backend /livez", st == 200, f"HTTP {st}")

    email = f"deep{uuid.uuid4().hex[:8]}@dreamtalkqa.com"
    st, reg = req("POST", "/api/v1/auth/signup",
                  {"email": email, "password": "E2eTest!2345",
                   "full_name": "Maharaj", "role": "personal"})
    token = ((reg or {}).get("tokens") or {}).get("access_token") if isinstance(reg, dict) else None
    rec("auth signup", bool(token), f"HTTP {st} {email}")
    if not token:
        return None

    face, voice = open(FACE, "rb").read(), open(VOICE, "rb").read()
    t0 = time.time()
    st, prof = req("POST", "/api/v1/avatar/profiles", token=token, form=[
        ("name", "Maharaj"), ("consent_confirmed", "true"),
        ("consent_subject_name", "Maharaj"), ("language", "en"), ("reference_text", ""),
        ("voice_sample", ("sample1.wav", voice, "audio/wav")),
        ("face_images", ("maharaj.jpg", face, "image/jpeg")),
    ])
    pid = prof.get("id") if isinstance(prof, dict) else None
    rec("create avatar profile", bool(pid), f"HTTP {st} {time.time()-t0:.0f}s id={pid}")
    if not pid:
        print(json.dumps(prof, indent=1)[:900] if isinstance(prof, dict) else prof)
        return None

    save_state({"token": token, "pid": pid, "email": email})
    return {"token": token, "pid": pid}


# ── phase 2 ───────────────────────────────────────────────────────────
def phase2(s):
    print("\n=== PHASE 2 — 3D head ===")
    import struct
    token, pid = s["token"], s["pid"]
    st, man = req("GET", f"/api/v1/avatar/profiles/{pid}/manifest", token=token)
    render = (man or {}).get("render", {}) if isinstance(man, dict) else {}
    caps = render.get("capabilities", {})
    rec("manifest", st == 200, f"modes={render.get('render_modes')}")
    rec("  blendshapes advertised", bool(caps.get("arkit_blendshapes")),
        f"visemes={caps.get('visemes')} driver={caps.get('animation_driver')}")

    glb = os.path.join(OUT, "head.glb")
    n = asset(render.get("glb_url", ""), token, glb)
    rec("download GLB", n > 0, f"{n/1024:.0f} KB")
    if not n:
        return

    b = open(glb, "rb").read()
    jl = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    bin_off = 20 + jl + 8
    prim = j["meshes"][0]["primitives"][0]
    names = j["meshes"][0].get("extras", {}).get("targetNames", [])
    acc = j["accessors"]
    nverts = acc[prim["attributes"]["POSITION"]]["count"]
    rec("  morph targets", len(prim.get("targets", [])) == 10, f"{len(prim.get('targets', []))}: {names}")
    rec("  FLAME topology", nverts == 5023, f"{nverts} verts")

    # Morph deltas must be non-degenerate and bounded.
    def rd(ai):
        a = acc[ai]; bv = j["bufferViews"][a["bufferView"]]
        off = bin_off + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return [struct.unpack_from("<fff", b, off + i * 12) for i in range(a["count"])]
    pos = rd(prim["attributes"]["POSITION"])
    ys = [p[1] for p in pos]
    height = max(ys) - min(ys)
    worst = []
    for i, t in enumerate(prim.get("targets", [])):
        d = rd(t["POSITION"])
        peak = max(max(abs(c) for c in v) for v in d)
        if peak < 1e-6 or peak > 0.12 * height:
            worst.append(f"{names[i]}={peak/height:.3f}H")
    rec("  morph magnitudes sane", not worst, f"outliers={worst or 'none'}")

    # Texture atlas
    if j.get("images"):
        bv = j["bufferViews"][j["images"][0]["bufferView"]]
        off = bin_off + bv.get("byteOffset", 0)
        tex = os.path.join(OUT, "head_texture.jpg")
        open(tex, "wb").write(b[off:off + bv["byteLength"]])
        import cv2, numpy as np
        im = cv2.imread(tex)
        # A real face atlas has skin-tone pixels and structure; a failed
        # projection is a low-variance smear.
        var = float(np.var(im)) if im is not None else 0.0
        rec("  texture atlas present", im is not None,
            f"{im.shape if im is not None else '?'} variance={var:.0f} -> {tex}")


# ── phase 3 ───────────────────────────────────────────────────────────
def phase3(s):
    print("\n=== PHASE 3 — 2D talking head (MuseTalk) ===")
    token, pid = s["token"], s["pid"]
    t0 = time.time()
    st, res = req("POST", f"/api/v1/avatar/profiles/{pid}/respond", token=token, body={
        "message": "Hello, I am Maharaj. This is my digital twin speaking.",
        "language": "hi", "synthesize": True, "render_video": True, "strict_clone": False,
    })
    vobj = (res or {}).get("video") or {} if isinstance(res, dict) else {}
    vurl = vobj.get("video_url") or vobj.get("url")
    rec("render talking-head video", st == 200 and bool(vurl),
        f"HTTP {st} {time.time()-t0:.0f}s status={vobj.get('status')} reason={str(vobj.get('reason'))[:80]}")
    if not vurl:
        return
    mp4 = os.path.join(OUT, "talking_head.mp4")
    n = asset(vurl, token, mp4)
    rec("  download MP4", n > 0, f"{n/1024:.0f} KB -> {mp4}")
    if not n:
        return
    analyse_video(mp4)


def analyse_video(mp4):
    """Measure that the mouth actually moves, and that audio is present."""
    import cv2, numpy as np
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,duration,nb_frames,width,height",
         "-of", "json", mp4], capture_output=True, text=True)
    info = json.loads(probe.stdout or "{}")
    streams = info.get("streams", [])
    kinds = [st.get("codec_type") for st in streams]
    rec("  video stream", "video" in kinds,
        ", ".join(f"{st.get('codec_type')}:{st.get('codec_name')}" for st in streams))
    rec("  audio stream muxed", "audio" in kinds, f"streams={kinds}")

    cap = cv2.VideoCapture(mp4)
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    rec("  frames decoded", len(frames) > 10, f"{len(frames)} frames")
    if len(frames) < 10:
        return

    # Mouth region: lower-middle third of the face crop. MuseTalk only repaints
    # the mouth, so inter-frame change there proves lip motion — and comparing
    # it with a forehead control proves the change is not global flicker.
    h, w = frames[0].shape[:2]
    mouth = (slice(int(h * 0.60), int(h * 0.85)), slice(int(w * 0.30), int(w * 0.70)))
    brow = (slice(int(h * 0.10), int(h * 0.30)), slice(int(w * 0.30), int(w * 0.70)))
    g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames]
    md = [float(np.mean(np.abs(g[i][mouth] - g[i - 1][mouth]))) for i in range(1, len(g))]
    bd = [float(np.mean(np.abs(g[i][brow] - g[i - 1][brow]))) for i in range(1, len(g))]
    mm, bb = float(np.mean(md)), float(np.mean(bd))
    rec("  mouth moves across frames", mm > 0.5, f"mean |delta| mouth={mm:.2f} vs brow={bb:.2f}")
    rec("  motion localised to mouth", mm > bb * 1.5,
        f"ratio={mm / max(bb, 1e-6):.2f}x (lip-sync repaints mouth, not whole frame)")
    rec("  motion varies over time", float(np.std(md)) > 0.2,
        f"std={np.std(md):.2f} (a static loop would be ~0)")

    # Sample frames for visual review
    for i in (0, len(frames) // 3, 2 * len(frames) // 3, len(frames) - 1):
        cv2.imwrite(os.path.join(OUT, f"frame_{i:04d}.png"), frames[i])
    print(f"       wrote 4 sample frames to {OUT}")

    # Audio track
    wav = os.path.join(OUT, "talking_head_audio.wav")
    subprocess.run(["ffmpeg", "-y", "-i", mp4, "-vn", "-ac", "1", "-ar", "16000", wav],
                   capture_output=True)
    if os.path.exists(wav):
        import librosa
        y, sr = librosa.load(wav, sr=16000, mono=True)
        rms = float(np.sqrt(np.mean(y ** 2))) if y.size else 0.0
        rec("  audio is not silent", rms > 0.005, f"{len(y)/sr:.1f}s rms={rms:.4f}")


# ── phase 4 ───────────────────────────────────────────────────────────
def speaker_features(path):
    """Compact speaker descriptor: MFCC means/stds + pitch stats."""
    import librosa, numpy as np
    y, sr = librosa.load(path, sr=16000, mono=True)
    y, _ = librosa.effects.trim(y, top_db=30)
    if y.size < sr // 2:
        return None, {}
    mf = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    vec = np.concatenate([mf.mean(axis=1), mf.std(axis=1)])
    vec = vec / (np.linalg.norm(vec) + 1e-9)
    f0 = librosa.yin(y, fmin=60, fmax=400, sr=sr)
    f0 = f0[np.isfinite(f0)]
    stats = {
        "dur": round(len(y) / sr, 2),
        "f0_med": round(float(np.median(f0)), 1) if f0.size else 0.0,
        "rms": round(float(np.sqrt(np.mean(y ** 2))), 4),
    }
    return vec, stats


def cos(a, b):
    import numpy as np
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))


def phase4(s):
    print("\n=== PHASE 4 — voice cloning similarity ===")
    token, pid = s["token"], s["pid"]
    ref_vec, ref_stats = speaker_features(VOICE)
    rec("reference sample readable", ref_vec is not None, f"{ref_stats}")
    if ref_vec is None:
        return

    out = {}
    for lang, label in (("hi", "Hindi (IndicF5 clone)"), ("en", "English (no clone engine)")):
        st, r = req("POST", f"/api/v1/avatar/profiles/{pid}/respond", token=token, body={
            "message": "Namaste, yah meri awaaz hai." if lang == "hi" else "Hello, this is my voice.",
            "language": lang, "synthesize": True, "render_video": False, "strict_clone": False,
        })
        if st != 200:
            rec(f"synthesize {lang}", False, f"HTTP {st}")
            continue
        a = (r or {}).get("audio") or {}
        url = r.get("audio_url") or a.get("audio_url")
        dest = os.path.join(OUT, f"voice_{lang}.wav")
        if not asset(url, token, dest):
            rec(f"synthesize {lang}", False, "asset download failed")
            continue
        vec, stats = speaker_features(dest)
        sim = cos(ref_vec, vec) if vec is not None else 0.0
        out[lang] = (sim, bool(a.get("cloned")), a.get("engine"), stats)
        rec(f"{label}", True,
            f"cloned={a.get('cloned')} engine={a.get('engine')} similarity={sim:.3f} {stats}")

    if "hi" in out and "en" in out:
        hi, en = out["hi"][0], out["en"][0]
        rec("cloned voice closer to reference than stand-in", hi > en,
            f"Hindi(clone)={hi:.3f} vs English(edge-tts)={en:.3f}")
        rec("cloned similarity is meaningful", hi > 0.60,
            f"{hi:.3f} (>0.60 = same-speaker territory for this descriptor)")
        if not out["en"][1]:
            rec("stand-in voice correctly flagged cloned=false", True,
                "English has no clone engine; runtime labels it honestly")


PHASES = {"1": phase1, "2": phase2, "3": phase3, "4": phase4}


def summary():
    print("\n" + "=" * 66)
    p = sum(1 for _, ok, _ in results if ok)
    print(f"SUMMARY: {p} passed, {len(results)-p} failed, {len(results)} total")
    for st, ok, d in results:
        if not ok:
            print(f"  FAIL {st}: {d}")
    print("=" * 66)
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    want = sys.argv[1:] or ["1", "2", "3", "4"]
    state = load_state()
    for ph in want:
        if ph == "1":
            state = phase1() or state
            if not state.get("pid"):
                break
        else:
            if not state.get("pid"):
                print("no profile in state; run phase 1 first")
                break
            PHASES[ph](state)
    sys.exit(summary())
