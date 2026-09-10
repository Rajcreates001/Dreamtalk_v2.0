r"""
LivePortrait Venv Runner - Standalone entry point for the dedicated venv.

This script is designed to be run using the Python interpreter from a
dedicated venv (e.g. D:\venvs\liveportrait\Scripts\python.exe). It
accepts command-line arguments describing the animation job, runs
LivePortrait, and writes the output video to the specified path.

The venv isolates torch and its DLLs from the main process, avoiding
the Windows OpenMP DLL conflict (libomp.dll vs libiomp5md.dll /
fbgemm.dll).

Usage (from the venv):
    python liveportrait_venv_runner.py \
        --source /path/to/source.jpg \
        --driving /path/to/driving.mp4 \
        --output /path/to/output.mp4 \
        [--region all] \
        [--pasteback]

Or via subprocess from the main app:
    subprocess.run([
        "D:/venvs/liveportrait/Scripts/python.exe",
        "face/core/animation/liveportrait/liveportrait_venv_runner.py",
        "--source", img_path,
        "--driving", video_path,
        "--output", out_path,
    ], cwd=project_root)
"""

import argparse
import os
import sys

# ---------------------------------------------------------------------------
# Fix OpenMP before any other imports
# ---------------------------------------------------------------------------
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# Ensure project root is on sys.path
_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

import logging
import tempfile
import uuid
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dreamtalk.liveportrait.venv")


def main():
    parser = argparse.ArgumentParser(description="LivePortrait Venv Runner")
    parser.add_argument("--source", required=True, help="Source face image path")
    parser.add_argument("--driving", required=True, help="Driving video or image path")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--mode", default="video", choices=["video", "image"],
                        help="Driving mode: video or image")
    parser.add_argument("--region", default="all",
                        choices=["all", "exp", "pose", "lip", "eyes"],
                        help="Animation region")
    parser.add_argument("--no-pasteback", action="store_true",
                        help="Disable paste-back onto source")
    parser.add_argument("--output-name", default="", help="Output name (without ext)")
    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.source):
        logger.error(f"Source image not found: {args.source}")
        print(f"RESULT:error Source image not found: {args.source}")
        return 1

    if not os.path.exists(args.driving):
        logger.error(f"Driving file not found: {args.driving}")
        print(f"RESULT:error Driving file not found: {args.driving}")
        return 1

    out_dir = os.path.dirname(args.output)
    os.makedirs(out_dir, exist_ok=True)

    try:
        # Lazy-import LivePortrait inside the isolated venv
        from dreamtalk.face.core.animation.liveportrait import LivePortraitAPI, LivePortraitPipeline, InferenceConfig, CropConfig, ArgumentConfig

        logger.info("LivePortrait modules imported successfully")

        # Configure inference
        inf_cfg = InferenceConfig()
        inf_cfg.flag_force_cpu = True  # Venv has CPU-only torch
        inf_cfg.device_id = 0
        inf_cfg.flag_use_half_precision = False
        inf_cfg.flag_do_crop = True
        inf_cfg.flag_pasteback = not args.no_pasteback
        inf_cfg.flag_stitching = True
        inf_cfg.flag_relative_motion = True
        inf_cfg.animation_region = args.region
        inf_cfg.flag_normalize_lip = True

        crop_cfg = CropConfig()
        crop_cfg.flag_force_cpu = True

        pipeline = LivePortraitPipeline(inference_cfg=inf_cfg, crop_cfg=crop_cfg)

        arg_config = ArgumentConfig(
            source=args.source,
            driving=args.driving,
            output_dir=out_dir,
            flag_pasteback=not args.no_pasteback,
            flag_do_crop=True,
            flag_stitching=True,
            flag_relative_motion=True,
            animation_region=args.region,
            flag_normalize_lip=True,
        )

        logger.info(f"Animating: source={args.source}, driving={args.driving}")
        wfp, wfp_concat = pipeline.execute(arg_config)

        # Copy to the requested output path
        if wfp and os.path.exists(wfp):
            import shutil
            shutil.copy2(wfp, args.output)
            logger.info(f"Output written to: {args.output}")
            print(f"RESULT:ok {args.output}")
            return 0
        else:
            logger.error("LivePortrait produced no output")
            print("RESULT:error No output produced")
            return 1

    except Exception as e:
        logger.exception(f"LivePortrait venv runner failed: {e}")
        print(f"RESULT:error {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
