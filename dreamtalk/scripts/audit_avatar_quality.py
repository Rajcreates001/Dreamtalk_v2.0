"""Audit the quality of a generated avatar head.

Measures the things that decide whether it reads as a person:
  - identity      : face-embedding similarity between the source photo and a
                    render of the generated head
  - texture       : how much of the UV atlas is real skin vs unfilled/mean fill
  - geometry      : symmetry, proportion sanity against the fitted landmarks
  - completeness  : which anatomy the mesh actually contains (teeth? ears?)
  - animation     : viseme coverage and amplitude
"""
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, "/app")

OUT = "/app/dreamtalk/e2e_deep"
GLB = os.environ.get("GLB", os.path.join(OUT, "head.glb"))
PHOTO = os.environ.get(
    "PHOTO", "/app/dreamtalk/local_upload_testing/Image_local/Maharaj Profile.jpg")

findings: list[tuple[str, str, str]] = []


def note(level: str, area: str, msg: str) -> None:
    findings.append((level, area, msg))
    print(f"[{level:4s}] {area:14s} {msg}", flush=True)


def load_glb(path):
    b = open(path, "rb").read()
    jl = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    return b, j, 20 + jl + 8


def accessor(b, j, bin_off, idx, comp=3, fmt="f"):
    a = j["accessors"][idx]
    bv = j["bufferViews"][a["bufferView"]]
    off = bin_off + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    size = {"f": 4, "I": 4, "H": 2}[fmt]
    return np.array([struct.unpack_from("<" + fmt * comp, b, off + i * comp * size)
                     for i in range(a["count"])])


def main() -> int:
    if not os.path.exists(GLB):
        print("no GLB at", GLB)
        return 1
    b, j, bin_off = load_glb(GLB)
    prim = j["meshes"][0]["primitives"][0]
    pos = accessor(b, j, bin_off, prim["attributes"]["POSITION"])
    names = j["meshes"][0].get("extras", {}).get("targetNames", [])
    print(f"GLB: {len(pos)} verts, {len(prim.get('targets', []))} morph targets\n")

    # ── geometry ──────────────────────────────────────────────────────
    H = float(pos[:, 1].max() - pos[:, 1].min())
    W = float(pos[:, 0].max() - pos[:, 0].min())
    D = float(pos[:, 2].max() - pos[:, 2].min())
    print(f"bbox  W={W:.3f}  H={H:.3f}  D={D:.3f}   W/H={W/H:.2f}  D/H={D/H:.2f}")
    # A human head is ~0.65-0.80 as wide as tall, ~0.85-1.05 as deep.
    if not (0.55 <= W / H <= 0.95):
        note("GAP", "geometry", f"head width/height {W/H:.2f} outside human range 0.55-0.95")
    else:
        note("ok", "geometry", f"proportions plausible (W/H {W/H:.2f}, D/H {D/H:.2f})")

    # left/right symmetry: mirror x and measure nearest-neighbour error
    mirrored = pos.copy()
    mirrored[:, 0] *= -1
    step = max(1, len(pos) // 1500)
    sub, mir = pos[::step], mirrored[::step]
    d = np.sqrt(((sub[:, None, :] - mir[None, :, :]) ** 2).sum(-1)).min(axis=1)
    asym = float(d.mean() / H)
    if asym > 0.02:
        note("GAP", "geometry", f"left/right asymmetry {asym*100:.1f}% of head height")
    else:
        note("ok", "geometry", f"symmetric to {asym*100:.2f}% of head height")

    # ── completeness ──────────────────────────────────────────────────
    try:
        from dreamtalk.pipeline.face_blendshapes import load_flame_masks
        masks = load_flame_masks("/app/dreamtalk/weights/flame/FLAME_masks.pkl")
        have = {k: len(v) for k, v in masks.items()}
        print("\nFLAME regions present:", ", ".join(sorted(have)))
        for missing, why in (
            ("teeth", "an open mouth shows a void — biggest realism cost"),
            ("tongue", "no tongue behind the teeth"),
            ("hair", "FLAME is a scalp-only model; head reads bald"),
        ):
            if missing not in have:
                note("GAP", "completeness", f"no '{missing}' geometry — {why}")
    except Exception as exc:
        note("warn", "completeness", f"mask check skipped: {exc}")

    # ── texture ───────────────────────────────────────────────────────
    if j.get("images"):
        bv = j["bufferViews"][j["images"][0]["bufferView"]]
        off = bin_off + bv.get("byteOffset", 0)
        tex_path = os.path.join(OUT, "audit_texture.jpg")
        open(tex_path, "wb").write(b[off:off + bv["byteLength"]])
        import cv2
        tex = cv2.imread(tex_path)
        h, w = tex.shape[:2]
        print(f"\ntexture atlas {w}x{h}")
        if w < 1024:
            note("GAP", "texture", f"atlas is only {w}px — soft/blurry skin at close range")
        # skin-tone coverage (broad HSV band)
        hsv = cv2.cvtColor(tex, cv2.COLOR_BGR2HSV)
        skin = ((hsv[:, :, 0] <= 30) & (hsv[:, :, 1] >= 25) & (hsv[:, :, 2] >= 40))
        frac = float(skin.mean())
        note("ok" if frac > 0.35 else "GAP", "texture",
             f"skin-tone pixels {frac*100:.0f}% of atlas")
        # sharpness
        lap = cv2.Laplacian(cv2.cvtColor(tex, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        note("ok" if lap > 100 else "GAP", "texture",
             f"detail (laplacian var) {lap:.0f}" + ("" if lap > 100 else " — very soft"))

    # ── animation ─────────────────────────────────────────────────────
    print()
    tgt = prim.get("targets", [])
    if not tgt:
        note("GAP", "animation", "no morph targets — head cannot speak")
    else:
        peaks = []
        for i, t in enumerate(tgt):
            d = accessor(b, j, bin_off, t["POSITION"])
            peaks.append((names[i] if i < len(names) else str(i),
                          float(np.abs(d).max()) / H))
        for n, p in peaks:
            if p < 0.005:
                note("GAP", "animation", f"'{n}' displaces only {p*100:.2f}% of head — imperceptible")
        vis = {"aa", "ih", "ou", "ee", "oh"}
        note("ok" if vis.issubset(set(names)) else "GAP", "animation",
             f"visemes {sorted(vis & set(names))} / blink={'blink' in names}")
        note("ok", "animation",
             "peak displacements: " + ", ".join(f"{n} {p*100:.1f}%" for n, p in peaks))

    # ── identity ──────────────────────────────────────────────────────
    print()
    note("info", "identity",
         "render-vs-photo identity similarity needs a headless GL render; "
         "not measured here (see report)")

    gaps = [f for f in findings if f[0] == "GAP"]
    print(f"\n{'='*64}\n{len(gaps)} gap(s) found\n{'='*64}")
    for _l, area, msg in gaps:
        print(f"  - [{area}] {msg}")
    json.dump([{"level": l, "area": a, "msg": m} for l, a, m in findings],
              open(os.path.join(OUT, "quality_audit.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
