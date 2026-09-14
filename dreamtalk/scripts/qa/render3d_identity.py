"""Render the generated head offscreen and score it against the source photo.

Why a hand-written rasteriser: the container has no pyrender, moderngl or
PyOpenGL, and the browser's WebGL context is created without
preserveDrawingBuffer, so canvas read-back returns a blank image. Screenshots
of the page are neither deterministic nor croppable to the canvas reliably.
A few dozen lines of numpy give a repeatable front-on render instead, which
is what makes "is the 3D head the same person as the photo?" answerable with
a number rather than an opinion.

Scoring uses the same Facenet512 embedding the enrolment gate already uses,
so a pass here means the same model that verified the photo also recognises
the render.

  docker exec -i dreamtalk-backend python - < render3d.py [profile_id]
"""
from __future__ import annotations

import glob
import json
import os
import struct
import sys

import numpy as np

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "71d2b3f8-51eb-4435-a4ee-665f60049850"
RUNTIME = "/app/dreamtalk/media/avatar_runtime"
OUT = "/tmp/render3d"
os.makedirs(OUT, exist_ok=True)
SIZE = 512


def read_glb(path):
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


def acc(js, binc, idx, dim, dtype=np.float32):
    a = js["accessors"][idx]
    bv = js["bufferViews"][a["bufferView"]]
    o = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(binc, dtype, count=a["count"] * dim, offset=o).reshape(-1, dim)



def extract_glb_texture(glb_path: str) -> str:
    """Write the GLB's embedded baseColor image to disk and return its path."""
    js, binc = read_glb(glb_path)
    img = js["images"][0]
    bv = js["bufferViews"][img["bufferView"]]
    o = bv.get("byteOffset", 0)
    blob = binc[o:o + bv["byteLength"]]
    ext = "png" if blob[1:4] == b"PNG" else "jpg"
    path = f"{OUT}/glb_texture.{ext}"
    with open(path, "wb") as fh:
        fh.write(blob)
    return path


def load_head(glb_path):
    js, binc = read_glb(glb_path)
    mesh = [m for m in js["meshes"] if m["name"] == "Head"][0]
    prim = mesh["primitives"][0]
    v = acc(js, binc, prim["attributes"]["POSITION"], 3).astype(np.float64)
    uv = acc(js, binc, prim["attributes"]["TEXCOORD_0"], 2).astype(np.float64)
    ia = js["accessors"][prim["indices"]]
    bv = js["bufferViews"][ia["bufferView"]]
    o = bv.get("byteOffset", 0) + ia.get("byteOffset", 0)
    dt = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}[ia["componentType"]]
    f = np.frombuffer(binc, dt, count=ia["count"], offset=o).reshape(-1, 3).astype(np.int64)
    return v, uv, f


def rasterise(v, uv, faces, tex, size=SIZE):
    """Orthographic front view with a z-buffer and per-pixel UV sampling."""
    # Fit the head to the frame, preserving aspect. FLAME's +Y is up, +Z fwd.
    lo, hi = v.min(0), v.max(0)
    centre = (lo + hi) / 2
    scale = (size * 0.92) / max(hi[0] - lo[0], hi[1] - lo[1])
    x = (v[:, 0] - centre[0]) * scale + size / 2
    y = size / 2 - (v[:, 1] - centre[1]) * scale      # screen Y is down
    z = v[:, 2]

    img = np.zeros((size, size, 3), np.uint8)
    zbuf = np.full((size, size), -np.inf)
    th, tw = tex.shape[:2]

    # Back-face cull on screen-space winding, then painter's order by depth.
    order = np.argsort(z[faces].mean(axis=1))
    for fi in order:
        a, b, c = faces[fi]
        x0, y0, x1, y1, x2, y2 = x[a], y[a], x[b], y[b], x[c], y[c]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if area >= 0:                       # cull triangles facing away
            continue
        minx, maxx = int(max(0, min(x0, x1, x2))), int(min(size - 1, max(x0, x1, x2)))
        miny, maxy = int(max(0, min(y0, y1, y2))), int(min(size - 1, max(y0, y1, y2)))
        if minx > maxx or miny > maxy:
            continue
        px, py = np.meshgrid(np.arange(minx, maxx + 1), np.arange(miny, maxy + 1))
        w0 = ((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)) / area
        w1 = ((x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        # Barycentric order for (a,b,c) is (w1, w2, w0) with the edges above.
        zz = w1 * z[a] + w2 * z[b] + w0 * z[c]
        sel = inside & (zz > zbuf[py, px])
        if not sel.any():
            continue
        u = w1 * uv[a, 0] + w2 * uv[b, 0] + w0 * uv[c, 0]
        vv = w1 * uv[a, 1] + w2 * uv[b, 1] + w0 * uv[c, 1]
        tx = np.clip((u * (tw - 1)).astype(int), 0, tw - 1)
        # glTF UV origin is TOP-left and v grows downward, so there is no
        # flip here. Applying the OpenGL bottom-left convention mirrored
        # the atlas vertically and put the mouth above the eyes.
        ty = np.clip((vv * (th - 1)).astype(int), 0, th - 1)
        img[py[sel], px[sel]] = tex[ty[sel], tx[sel]]
        zbuf[py[sel], px[sel]] = zz[sel]
    return img


def main():
    import cv2
    gen = f"{RUNTIME}/{PROFILE}/appearance/generated"
    glb = sorted(glob.glob(f"{gen}/*.glb"))[0]
    # Use the texture the GLB itself references, extracted from its binary
    # chunk. Picking a same-named file off disk is a guess: the generated
    # directory holds several atlases and the wrong one renders a face whose
    # features land in the wrong places.
    texp = extract_glb_texture(glb)
    src = glob.glob(f"{RUNTIME}/{PROFILE}/appearance/source/*.jpg")[0]

    tex = cv2.cvtColor(cv2.imread(texp), cv2.COLOR_BGR2RGB)
    v, uv, f = load_head(glb)
    print(f"mesh {len(v)} verts / {len(f)} faces, texture {tex.shape[1]}x{tex.shape[0]}")

    img = rasterise(v, uv, f, tex)
    out = f"{OUT}/render_front.png"
    cv2.imwrite(out, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    covered = (img.sum(axis=2) > 12).mean() * 100
    print(f"wrote {out}  (head covers {covered:.1f}% of frame)")

    from deepface import DeepFace
    res = DeepFace.verify(src, out, model_name="Facenet512",
                          detector_backend="retinaface", enforce_detection=False)
    print(json.dumps({k: res[k] for k in ("verified", "distance", "threshold", "model")},
                     default=str))
    d, t = res["distance"], res["threshold"]
    print(f"\nFacenet512 distance {d:.4f} vs threshold {t:.4f} -> "
          f"{'SAME PERSON' if res['verified'] else 'NOT RECOGNISED as the same person'}")
    print(f"margin: {t - d:+.4f}  (positive = recognised, larger is better)")


if __name__ == "__main__":
    main()
