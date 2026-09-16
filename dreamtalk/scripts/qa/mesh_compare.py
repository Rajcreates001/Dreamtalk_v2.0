"""Compare a generated mesh against the FLAME fit on the same photograph.

Two numbers decide this, and they are deliberately different in kind:

  identity   Facenet512 distance between the source photo and a front render.
             FLAME scores 0.1445 against a 0.300 threshold, so it is already
             recognisably the right person. Texture projection is why.

  silhouette IoU of the rendered head outline against the BiSeNet head mask
             taken from the photo. This is the number that captures the actual
             complaint. FLAME's outline is a bare cranium whatever texture is
             painted on it, so hair with volume can only show up here.

A model can win one and lose the other, and that outcome is informative rather
than a problem: it is the argument for keeping FLAME geometry and spending the
effort elsewhere, or for the blendshape transfer in Phase 3.

Orientation is chosen by RetinaFace *detection confidence* over the candidate
rotations, never by the identity score. Picking the pose that scores best on
the metric you are about to report is how a harness talks itself into a
result; detection only asks "is a face pointing at me here", which is a
different question from "is it him".

  docker exec -i dreamtalk-backend python - < mesh_compare.py --generated-glb ...
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import struct
import sys

import numpy as np

OUT = "/tmp/mesh_compare"
SIZE = 512
# CelebAMask-HQ label order as loaded by the vendored parser. "Head" for the
# silhouette means everything belonging to the person's head: skin, all the
# features, ears and earrings, and crucially hair. Neck and cloth are left out
# because no candidate mesh reconstructs a torso comparably.
HEAD_LABELS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17, 18}


# -- GLB reading ------------------------------------------------------
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


_DT = {5120: np.int8, 5121: np.uint8, 5122: np.int16,
       5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def accessor(js, binc, idx):
    a = js["accessors"][idx]
    dim = _NCOMP[a["type"]]
    bv = js["bufferViews"][a["bufferView"]]
    o = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(binc, _DT[a["componentType"]],
                         count=a["count"] * dim, offset=o).reshape(-1, dim)


def load_mesh(path, mesh_name=None):
    """Every primitive of every mesh, concatenated.

    Generated meshes carry a single unnamed primitive, so selecting by the
    name "Head" only works for the FLAME export.
    """
    js, binc = read_glb(path)
    V, UV, F, C = [], [], [], []
    base = 0
    has_uv = has_col = False
    for m in js["meshes"]:
        if mesh_name and m.get("name") != mesh_name:
            continue
        for prim in m["primitives"]:
            at = prim["attributes"]
            v = accessor(js, binc, at["POSITION"]).astype(np.float64)
            if "TEXCOORD_0" in at:
                uv = accessor(js, binc, at["TEXCOORD_0"]).astype(np.float64)
                has_uv = True
            else:
                uv = np.zeros((len(v), 2))
            if "COLOR_0" in at:
                c = accessor(js, binc, at["COLOR_0"]).astype(np.float64)
                if c.max() > 1.5:
                    c = c / 255.0
                c = c[:, :3]
                has_col = True
            else:
                c = np.full((len(v), 3), 0.6)
            f = accessor(js, binc, prim["indices"]).reshape(-1, 3).astype(np.int64)
            V.append(v)
            UV.append(uv)
            C.append(c)
            F.append(f + base)
            base += len(v)
    if not V:
        raise SystemExit("no primitives in %s%s" % (
            path, (" named " + mesh_name) if mesh_name else ""))
    return (np.concatenate(V), np.concatenate(UV), np.concatenate(F),
            np.concatenate(C), has_uv, has_col, js, binc)


def extract_texture(js, binc, tag):
    if not js.get("images"):
        return None
    img = js["images"][0]
    if "bufferView" in img:
        bv = js["bufferViews"][img["bufferView"]]
        o = bv.get("byteOffset", 0)
        blob = binc[o:o + bv["byteLength"]]
    elif str(img.get("uri", "")).startswith("data:"):
        blob = base64.b64decode(img["uri"].split(",", 1)[1])
    else:
        return None
    ext = "png" if blob[1:4] == b"PNG" else "jpg"
    path = os.path.join(OUT, "%s_texture.%s" % (tag, ext))
    with open(path, "wb") as fh:
        fh.write(blob)
    return path


# -- rasteriser -------------------------------------------------------
def rasterise(v, uv, faces, tex, vcol, size=SIZE, use_vertex_colour=False):
    """Orthographic front view with a z-buffer. Returns (rgb, coverage)."""
    lo, hi = v.min(0), v.max(0)
    centre = (lo + hi) / 2
    scale = (size * 0.92) / max(hi[0] - lo[0], hi[1] - lo[1])
    x = (v[:, 0] - centre[0]) * scale + size / 2
    y = size / 2 - (v[:, 1] - centre[1]) * scale
    z = v[:, 2]

    img = np.zeros((size, size, 3), np.uint8)
    cov = np.zeros((size, size), bool)
    zbuf = np.full((size, size), -np.inf)
    th, tw = (tex.shape[:2] if tex is not None else (1, 1))

    for fi in np.argsort(z[faces].mean(axis=1)):
        a, b, c = faces[fi]
        x0, y0, x1, y1, x2, y2 = x[a], y[a], x[b], y[b], x[c], y[c]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if area >= 0:
            continue
        minx = int(max(0, min(x0, x1, x2)))
        maxx = int(min(size - 1, max(x0, x1, x2)))
        miny = int(max(0, min(y0, y1, y2)))
        maxy = int(min(size - 1, max(y0, y1, y2)))
        if minx > maxx or miny > maxy:
            continue
        px, py = np.meshgrid(np.arange(minx, maxx + 1), np.arange(miny, maxy + 1))
        w0 = ((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)) / area
        w1 = ((x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        zz = w1 * z[a] + w2 * z[b] + w0 * z[c]
        sel = inside & (zz > zbuf[py, px])
        if not sel.any():
            continue
        if use_vertex_colour or tex is None:
            col = (w1[..., None] * vcol[a] + w2[..., None] * vcol[b]
                   + w0[..., None] * vcol[c])
            img[py[sel], px[sel]] = np.clip(col[sel] * 255, 0, 255).astype(np.uint8)
        else:
            u = w1 * uv[a, 0] + w2 * uv[b, 0] + w0 * uv[c, 0]
            vv = w1 * uv[a, 1] + w2 * uv[b, 1] + w0 * uv[c, 1]
            tx = np.clip((u * (tw - 1)).astype(int), 0, tw - 1)
            # glTF UV origin is TOP-left; no flip here. Applying the OpenGL
            # bottom-left convention once mirrored the atlas vertically and
            # put the mouth above the eyes while still scoring plausibly.
            ty = np.clip((vv * (th - 1)).astype(int), 0, th - 1)
            img[py[sel], px[sel]] = tex[ty[sel], tx[sel]]
        cov[py[sel], px[sel]] = True
        zbuf[py[sel], px[sel]] = zz[sel]
    return img, cov


def yaw(v, degrees):
    t = np.radians(degrees)
    r = np.array([[np.cos(t), 0, np.sin(t)], [0, 1, 0], [-np.sin(t), 0, np.cos(t)]])
    return v @ r.T


def pitch(v, degrees):
    t = np.radians(degrees)
    r = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    return v @ r.T


# -- metrics ----------------------------------------------------------
def detect_face(path):
    """Return (box, confidence) or (None, 0.0). RetinaFace reports a score."""
    try:
        from retinaface import RetinaFace
        faces = RetinaFace.detect_faces(path)
        if not isinstance(faces, dict) or not faces:
            return None, 0.0
        best = max(faces.values(), key=lambda f: f.get("score", 0))
        return list(best["facial_area"]), float(best.get("score", 0))
    except Exception as exc:
        print("  (detector unavailable: %s)" % exc)
        return None, 0.0


def head_mask_from_photo(photo):
    """BiSeNet head mask, resized back into the photo's own pixel space."""
    import cv2
    from PIL import Image
    from dreamtalk.face.core.lipsync.musetalk.utils.face_parsing.model import (
        FaceParsing,
    )

    bgr = cv2.imread(photo)
    h, w = bgr.shape[:2]
    pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).resize((512, 512))
    parsing = np.asarray(FaceParsing()(pil, mode="all"))
    mask = np.isin(parsing, list(HEAD_LABELS)).astype(np.uint8) * 255
    return cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST) > 127


def silhouette_iou(render_cov, render_box, photo_mask, photo_box, tag):
    """IoU after aligning the two by their detected face boxes.

    Without that alignment this measures framing, not shape: the render is a
    head floating in a 512 square and the photo is a person in a room.
    Matching the face boxes puts both at the same scale and position, so what
    is left over -- the outline above and around the face -- is the hair and
    skull shape actually in question.
    """
    import cv2
    if render_box is None or photo_box is None:
        return None
    rx1, ry1, rx2, ry2 = render_box
    px1, py1, px2, py2 = photo_box
    rw, rh = max(1, rx2 - rx1), max(1, ry2 - ry1)
    pw, ph = max(1, px2 - px1), max(1, py2 - py1)
    s = ((pw / rw) + (ph / rh)) / 2.0
    h, w = photo_mask.shape
    m = np.array([[s, 0, px1 + pw / 2 - s * (rx1 + rw / 2)],
                  [0, s, py1 + ph / 2 - s * (ry1 + rh / 2)]], np.float32)
    warped = cv2.warpAffine(render_cov.astype(np.uint8) * 255, m, (w, h),
                            flags=cv2.INTER_NEAREST) > 127
    inter = int(np.logical_and(warped, photo_mask).sum())
    union = int(np.logical_or(warped, photo_mask).sum())
    cv2.imwrite(os.path.join(OUT, "%s_silhouette.png" % tag),
                np.dstack([photo_mask.astype(np.uint8) * 255,
                           warped.astype(np.uint8) * 255,
                           np.zeros_like(photo_mask, np.uint8)]))
    return {
        "iou": round(inter / union, 4) if union else 0.0,
        "render_area_px": int(warped.sum()),
        "photo_head_area_px": int(photo_mask.sum()),
        "area_ratio": round(float(warped.sum()) / max(1, int(photo_mask.sum())), 4),
        "recall": round(inter / max(1, int(photo_mask.sum())), 4),
        "precision": round(inter / max(1, int(warped.sum())), 4),
    }


def evaluate(glb, photo, tag, mesh_name=None, vertex_colour=False):
    import cv2
    os.makedirs(OUT, exist_ok=True)
    v, uv, f, vcol, has_uv, has_col, js, binc = load_mesh(glb, mesh_name)
    texp = extract_texture(js, binc, tag)
    tex = cv2.cvtColor(cv2.imread(texp), cv2.COLOR_BGR2RGB) if texp else None
    use_vc = vertex_colour or (tex is None and has_col) or not has_uv
    print("[%s] %d verts / %d faces, texture=%s, vertex_colour=%s" % (
        tag, len(v), len(f),
        ("%dx%d" % (tex.shape[1], tex.shape[0])) if tex is not None else "none",
        use_vc))

    # Yaw is a real search: a generated mesh arrives in whatever frame the
    # reconstructor chose, and nothing says +Z is forward. Pitch is not - the
    # upright pose is the one that matches how the photo was taken, and tilting
    # the head only ever costs identity.
    #
    # Selecting purely on the highest detection confidence got this wrong on
    # the first run: pitch -20 scored 0.9997 against pitch 0's 0.9993, won on
    # four ten-thousandths of detector noise, and dragged the reported identity
    # distance from 0.1445 to 0.3494 - across the threshold, so the harness
    # would have announced that the avatar is not the same person. So pitch is
    # a fallback, tried only where the upright pose finds no face at all.
    candidates = []
    for yd in (0, 90, 180, 270):
        for pd in (0, -20, 20):
            vr = pitch(yaw(v, yd), pd)
            img, cov = rasterise(vr, uv, f, tex, vcol, use_vertex_colour=use_vc)
            path = os.path.join(OUT, "%s_y%d_p%d.png" % (tag, yd, pd))
            cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            box, conf = detect_face(path)
            print("  yaw %4d pitch %4d: detection %.4f%s" % (
                yd, pd, conf, "" if box else "   (no face)"))
            candidates.append({"yaw": yd, "pitch": pd, "conf": conf,
                               "box": box, "path": path, "cov": cov})
            if pd == 0 and conf == 0.0:
                continue
            if pd == 0 and conf > 0:
                break     # upright works at this yaw; no need to tilt
    upright = [c for c in candidates if c["pitch"] == 0 and c["conf"] > 0]
    best = (max(upright, key=lambda c: c["conf"]) if upright
            else max(candidates, key=lambda c: c["conf"]))
    if best["conf"] <= 0:
        print("[%s] no orientation yielded a detectable face" % tag)
    elif best["pitch"] != 0:
        print("[%s] no upright view found a face; falling back to pitch %d"
              % (tag, best["pitch"]))
    render = os.path.join(OUT, "%s_front.png" % tag)
    os.replace(best["path"], render)
    print("[%s] front view: yaw %d pitch %d (detection %.4f) -> %s" % (
        tag, best["yaw"], best["pitch"], best["conf"], render))

    from deepface import DeepFace
    res = DeepFace.verify(photo, render, model_name="Facenet512",
                          detector_backend="retinaface", enforce_detection=False)
    identity = {"distance": round(float(res["distance"]), 4),
                "threshold": round(float(res["threshold"]), 4),
                "verified": bool(res["verified"]),
                "margin": round(float(res["threshold"] - res["distance"]), 4)}

    photo_mask = head_mask_from_photo(photo)
    photo_box, _ = detect_face(photo)
    sil = silhouette_iou(best["cov"], best["box"], photo_mask, photo_box, tag)

    return {"tag": tag, "glb": glb, "vertices": int(len(v)), "faces": int(len(f)),
            "orientation": {"yaw": best["yaw"], "pitch": best["pitch"],
                            "detection_confidence": round(best["conf"], 4)},
            "render": render, "identity": identity, "silhouette": sil,
            "coverage_of_frame_pct": round(float(best["cov"].mean() * 100), 2)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="71d2b3f8-51eb-4435-a4ee-665f60049850")
    ap.add_argument("--flame-glb", default=None)
    ap.add_argument("--generated-glb", default=None)
    ap.add_argument("--photo", default=None)
    ap.add_argument("--skip-flame", action="store_true")
    args = ap.parse_args()

    runtime = "/app/dreamtalk/media/avatar_runtime/%s" % args.profile
    photo = args.photo or sorted(glob.glob(runtime + "/appearance/source/*.jpg"))[0]
    flame = args.flame_glb or sorted(glob.glob(
        runtime + "/appearance/generated/*.glb"))[0]

    results = []
    if not args.skip_flame:
        # Two passes when the export has more than one mesh. Identity is
        # measured on the Head alone so the number stays comparable with the
        # 0.1445 already on record; the silhouette needs every part, because
        # the hair shell is a separate mesh and it is the entire reason the
        # outline could change at all.
        names = [m.get("name") for m in read_glb(flame)[0]["meshes"]]
        if len(names) > 1:
            results.append(evaluate(flame, photo, "flame_head", mesh_name="Head"))
            results.append(evaluate(flame, photo, "flame_full"))
        else:
            results.append(evaluate(flame, photo, "flame", mesh_name="Head"))
    if args.generated_glb:
        results.append(evaluate(args.generated_glb, photo, "generated"))

    print("\n" + "=" * 74)
    hdr = ("%-10s %8s %9s %10s %7s %7s %7s"
           % ("model", "verts", "identity", "verdict", "IoU", "recall", "prec"))
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        s = r["silhouette"] or {}
        print("%-10s %8d %9.4f %10s %7.4f %7.4f %7.4f" % (
            r["tag"], r["vertices"], r["identity"]["distance"],
            "SAME" if r["identity"]["verified"] else "DIFFERENT",
            s.get("iou", float("nan")), s.get("recall", float("nan")),
            s.get("precision", float("nan"))))
    path = os.path.join(OUT, "comparison.json")
    with open(path, "w") as fh:
        fh.write(json.dumps(results, indent=2))
    print("\nwrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
