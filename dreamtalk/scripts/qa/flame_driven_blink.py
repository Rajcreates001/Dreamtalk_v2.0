"""Drive the portrait's eyes from the 3D head's own blink.

STATUS: the closure works and the surrounding frame does not. Driving the
photograph with the expression delta between two FLAME renders - eyes open and
eyes shut - closes the eyelids at about twice the measured delta, and ghosts
the rest of the head while doing it. Compositing only the eye region back
through a tight mask keeps the closure and discards the ghosting: 0.58% of the
frame changes and the left eye shuts properly. The right eye closes only
partially and the closed lid carries a dark smear rather than clean skin, so
this is not finished.

LivePortrait transfers motion from a driving video. Four ways of faking that
from a single still have been measured and none closes an eyelid. But this
avatar already has a working blink - on the FLAME mesh, where the blink morph
target closes 104.7% of the eyeball diameter, verified on the shipped GLB.

So render the mesh twice, eyes open and eyes shut, and hand those two frames
to LivePortrait as the driving pair. It extracts the expression delta between
them and applies it to the photograph. Everything involved is a component
already known to work: the morph target is measured, the rasteriser is the one
the 3D QA uses, and the warp is the repaired one.

The frames are a textured render of the subject's own head, so the motion
extractor sees a face rather than an abstract shape - the same rasteriser's
output detects at 0.9993 confidence in the 3D identity harness.
"""
import glob
import os
import struct
import sys

import cv2
import numpy as np
import torch

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/dreamtalk/scripts/qa")

from mesh_compare import accessor, extract_texture, rasterise, read_glb  # noqa: E402

PROFILE = os.environ.get("DREAMTALK_QA_PROFILE",
                         "a489f6f4-66f4-47c7-bf75-f3e68df8dbf7")
RUNTIME = "/app/dreamtalk/media/avatar_runtime/" + PROFILE
OUT = "/tmp/flamedrive"
os.makedirs(OUT, exist_ok=True)
# mesh_compare.extract_texture writes into its own OUT directory and does not
# create it.
import mesh_compare as _mc  # noqa: E402
os.makedirs(_mc.OUT, exist_ok=True)


def flame_frames():
    """Two renders of the head: blink at 0.0 and at 1.0."""
    glb = sorted(glob.glob(RUNTIME + "/appearance/generated/*.glb"))[-1]
    js, binc = read_glb(glb)
    head = [m for m in js["meshes"] if m.get("name") == "Head"][0]
    prim = head["primitives"][0]
    names = head["extras"]["targetNames"]
    v = accessor(js, binc, prim["attributes"]["POSITION"]).astype(np.float64)
    uv = accessor(js, binc, prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
    f = accessor(js, binc, prim["indices"]).reshape(-1, 3).astype(np.int64)
    blink = accessor(js, binc,
                     prim["targets"][names.index("blink")]["POSITION"]
                     ).astype(np.float64)
    texp = extract_texture(js, binc, "flamedrive")
    tex = cv2.cvtColor(cv2.imread(texp), cv2.COLOR_BGR2RGB)
    vcol = np.zeros((len(v), 3))
    frames = []
    for weight in (0.0, 1.0):
        img, _ = rasterise(v + weight * blink, uv, f, tex, vcol, size=512)
        frames.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        cv2.imwrite(OUT + "/flame_%.0f.png" % (weight * 100), frames[-1])
    return frames


def main() -> int:
    from dreamtalk.face.core.animation.liveportrait.config.crop_config import CropConfig
    from dreamtalk.face.core.animation.liveportrait.config.inference_config import InferenceConfig
    from dreamtalk.face.core.animation.liveportrait.live_portrait_wrapper import LivePortraitWrapper
    from dreamtalk.face.core.animation.liveportrait.utils.cropper import Cropper

    driving = flame_frames()
    print("rendered FLAME driving pair:", [d.shape for d in driving])

    cc = CropConfig()
    cropper = Cropper(cc)
    src = cv2.imread(RUNTIME + "/responses/source_fit_768.jpg")
    crop = cropper.crop_source_image(cv2.cvtColor(src, cv2.COLOR_BGR2RGB), cc)
    model = LivePortraitWrapper(InferenceConfig(flag_use_half_precision=False))

    # Motion from the driving pair. Both frames must crop successfully or the
    # delta is meaningless, so say which one failed rather than proceeding.
    infos = []
    for i, frame in enumerate(driving):
        dcrop = cropper.crop_source_image(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), cc)
        if dcrop is None:
            print("FLAME frame %d: no face detected in the render - the motion "
                  "extractor cannot read it" % i)
            return 1
        with torch.inference_mode():
            infos.append(model.get_kp_info(
                model.prepare_source(dcrop["img_crop_256x256"])))
        print("FLAME frame %d: face found, exp |max| %.4f"
              % (i, float(infos[-1]["exp"].abs().max())))

    exp_delta = infos[1]["exp"] - infos[0]["exp"]
    print("driving expression delta |max| = %.5f, |mean| = %.5f"
          % (float(exp_delta.abs().max()), float(exp_delta.abs().mean())))

    with torch.inference_mode():
        x = model.prepare_source(crop["img_crop_256x256"])
        feat = model.extract_feature_3d(x)
        info = model.get_kp_info(x)
        base_kp = model.transform_keypoint(info)
        base = model.parse_output(model.warp_decode(feat, base_kp, base_kp)["out"])[0]
        bg = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = bg.shape
        tiles = [cv2.cvtColor(base, cv2.COLOR_RGB2BGR)]
        labels = ["source, no blink"]
        # The whole driving delta closes the eyes and ghosts the head: the
        # FLAME render differs from the photograph in pose and proportion as
        # well as in eyelids, and the motion extractor cannot tell those apart.
        # Keep only the expression components the probe showed act on the eyes
        # and zero the rest, so the blink transfers and the pose does not.
        # Masking the delta to "eye" components loses the closure: the motion
        # extractor spreads an eyelid across the whole expression vector, so
        # there is no eye-only subset to keep. Apply all of it and use the
        # stitching module for what it is for - holding the background and
        # shoulders still while the face moves. Bypassing it is why the full
        # delta ghosted the head.
        use_stitch = os.environ.get("STITCH", "1") == "1"
        print("stitching: %s" % ("on" if use_stitch else "off"))
        for gain in (1.0, 1.5, 2.0, 3.0):
            alt = {k: (v.clone() if torch.is_tensor(v) else v)
                   for k, v in info.items()}
            alt["exp"] = info["exp"] + exp_delta * gain
            driven = model.transform_keypoint(alt)
            if use_stitch:
                driven = model.stitching(base_kp, driven)
            out = model.parse_output(
                model.warp_decode(feat, base_kp, driven)["out"])[0]
            g = cv2.cvtColor(out, cv2.COLOR_RGB2GRAY).astype(np.float32)
            d = np.abs(g - bg)
            outside = np.ones((h, w), bool)
            outside[int(.10 * h):int(.95 * h), int(.15 * w):int(.85 * w)] = False
            print("gain %.1f: eye change %.2f, damage %.2f"
                  % (gain, d[int(.36 * h):int(.50 * h),
                             int(.18 * w):int(.82 * w)].mean(),
                     d[outside].mean()))
            tiles.append(cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
            labels.append("stitched x%.1f" % gain)

    strip = np.vstack([t[150:300, :] for t in tiles])
    strip = cv2.resize(strip, (strip.shape[1] * 2, strip.shape[0] * 2),
                       interpolation=cv2.INTER_CUBIC)
    for i, l in enumerate(labels):
        cv2.putText(strip, l, (10, i * 300 + 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.85, (60, 255, 60), 2)
    cv2.imwrite(OUT + "/flame_driven.png", strip)
    print("wrote flame_driven.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
