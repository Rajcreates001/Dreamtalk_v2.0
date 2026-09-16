"""Rebuild an avatar from an existing profile's own source photo and voice.

The point is to re-run the *production* creation path, not a test double, so
that fixes which live inside it are actually exercised. The hair shell is the
current example: it was written, committed, and silently never ran, because
`build_hair` was called with an undefined name and the surrounding try/except
logged the NameError as "hair shell build failed" at warning level. Every GLB
produced afterwards still had exactly one mesh named Head. Only re-running
creation and then reading the GLB back proves otherwise.

Keeps the old profile. The previous build is the "before" half of any
measurement of what changed.

  docker exec -i dreamtalk-backend python - < rebuild_profile.py --from <id>
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import struct
import sys
import time

import httpx

API = "http://localhost:5000/api/v1"
EMAIL = "wiz1789388539@qa.dev"
PASSWORD = "Qa!2345678"
RUNTIME = "/app/dreamtalk/media/avatar_runtime"


def token() -> str:
    r = httpx.post("%s/auth/login" % API,
                   json={"email": EMAIL, "password": PASSWORD}, timeout=60)
    r.raise_for_status()
    d = r.json()
    return (d.get("tokens") or d)["access_token"]


def glb_summary(path: str) -> dict:
    data = open(path, "rb").read()
    off, js = 12, None
    while off < len(data):
        ln, ty = struct.unpack_from("<II", data, off)
        off += 8
        if ty == 0x4E4F534A:
            js = json.loads(data[off:off + ln])
        off += ln
    prim = js["meshes"][0]["primitives"][0]
    return {
        "path": path,
        "size_mb": round(len(data) / 1e6, 2),
        "meshes": [m.get("name") for m in js["meshes"]],
        "has_hair": any(m.get("name") == "hair" for m in js["meshes"]),
        "morph_targets": len(prim.get("targets", []) or []),
        "target_names": js["meshes"][0].get("extras", {}).get("targetNames", []),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="source", required=True,
                    help="profile id to take the photo and voice from")
    ap.add_argument("--name", default=None)
    ap.add_argument("--language", default="hi")
    ap.add_argument("--reference-text", default="")
    ap.add_argument("--timeout", type=float, default=2400)
    args = ap.parse_args()

    src = os.path.join(RUNTIME, args.source)
    photos = sorted(glob.glob(src + "/appearance/source/*.jpg")
                    + glob.glob(src + "/appearance/source/*.png"))
    voice = os.path.join(src, "voice", "reference.wav")
    if not photos or not os.path.exists(voice):
        print("source profile %s is missing photo or voice" % args.source,
              file=sys.stderr)
        return 2

    before = sorted(glob.glob(src + "/appearance/generated/*.glb"))
    if before:
        print("before: %s" % json.dumps(glb_summary(before[-1]), indent=2))

    name = args.name or ("rebuild %s" % time.strftime("%H%M%S"))
    print("\nrebuilding from %s (%d photo(s), voice %s)"
          % (args.source, len(photos), voice))
    started = time.time()
    with httpx.Client(timeout=args.timeout) as client:
        client.headers["Authorization"] = "Bearer " + token()
        files = [("voice_sample", ("reference.wav", open(voice, "rb"), "audio/wav"))]
        for p in photos:
            files.append(("face_images", (os.path.basename(p), open(p, "rb"),
                                          "image/jpeg")))
        data = {
            "name": name,
            "language": args.language,
            "reference_text": args.reference_text,
            "validate_clone": "true",
            "consent_confirmed": "true",
            "consent_subject_name": name,
            "consent_version": "1.0",
        }
        r = client.post("%s/avatar-runtime/profiles" % API, data=data, files=files)
        if r.status_code >= 400:
            print("HTTP %d: %s" % (r.status_code, r.text[:1500]), file=sys.stderr)
            return 1
        payload = r.json()

    elapsed = time.time() - started
    profile = payload.get("profile") or payload
    pid = profile.get("id") or profile.get("profile_id")
    print("\ncreated %s in %.1fs" % (pid, elapsed))
    for key in ("voice", "appearance", "validation", "warnings"):
        if key in profile:
            print("  %s: %s" % (key, json.dumps(profile[key])[:600]))

    after = sorted(glob.glob(os.path.join(RUNTIME, str(pid),
                                          "appearance/generated/*.glb")))
    if not after:
        print("no GLB produced for %s" % pid, file=sys.stderr)
        return 1
    summary = glb_summary(after[-1])
    print("\nafter: %s" % json.dumps(summary, indent=2))
    if not summary["has_hair"]:
        print("\nNO HAIR MESH. The shell still did not run; check the backend "
              "log for 'Hair shell build failed' or 'Hair measurement "
              "unavailable'.")
        return 1
    print("\nhair mesh present")
    print("PROFILE_ID=%s" % pid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
