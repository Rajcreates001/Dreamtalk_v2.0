"""Render neutral/closed-eye crops before enabling portrait animation.

Runs on CPU by default so it does not contend with a running lip-sync job.
Outputs are diagnostic crops, not a completed talking-avatar video.
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
import torch

from dreamtalk.face.core.animation.liveportrait.config.crop_config import CropConfig
from dreamtalk.face.core.animation.liveportrait.config.inference_config import InferenceConfig
from dreamtalk.face.core.animation.liveportrait.live_portrait_wrapper import LivePortraitWrapper
from dreamtalk.face.core.animation.liveportrait.utils.cropper import Cropper


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    torch.set_num_threads(2)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    source = cv2.imread(args.source)
    if source is None:
        raise ValueError("Cannot decode source portrait")
    crop_cfg = CropConfig(flag_force_cpu=True)
    crop = Cropper(crop_cfg).crop_source_image(
        cv2.cvtColor(source, cv2.COLOR_BGR2RGB), crop_cfg
    )
    if crop is None:
        raise ValueError("No face detected in source portrait")
    model = LivePortraitWrapper(InferenceConfig(
        flag_force_cpu=True, flag_use_half_precision=False
    ))
    with torch.inference_mode():
        image = model.prepare_source(crop["img_crop_256x256"])
        info = model.get_kp_info(image)
        kp = model.transform_keypoint(info)
        features = model.extract_feature_3d(image)
        for name, target in (("neutral", None), ("closed_eyes", 0.0)):
            driving = kp.clone()
            if target is not None:
                ratios = model.calc_combined_eye_ratio(
                    np.array([[target]], np.float32), crop["lmk_crop"]
                )
                driving += model.retarget_eye(kp, ratios)
            result = model.parse_output(model.warp_decode(features, kp, driving)["out"])[0]
            cv2.imwrite(str(output / f"{name}.png"), cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(output / "source_crop.png"), cv2.cvtColor(crop["img_crop"], cv2.COLOR_RGB2BGR))
    print("Neutral and closed-eye diagnostic crops written", flush=True)


if __name__ == "__main__":
    main()
