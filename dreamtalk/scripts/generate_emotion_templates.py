"""
Generate LivePortrait Emotion Motion Templates.

This script creates .pkl motion template files for each supported emotion
(happy, sad, angry, surprised, fearful, disgusted, neutral) by:

  1. Generating a synthetic driving video where an OpenCV face animates
     with the target expression (mouth shapes, eyebrow positions, etc.)
  2. Processing that video through LivePortrait's motion_extractor to
     extract expression coefficients (exp), keypoints, and eye/lip ratios
  3. Saving the result as a .pkl motion template

Templates are saved to weights/liveportrait/templates/<emotion>.pkl

Usage (from the LivePortrait venv):
    D:/venvs/liveportrait/Scripts/python.exe scripts/generate_emotion_templates.py

Or reusing indicf5 venv:
    D:/venvs/indicf5/Scripts/python.exe scripts/generate_emotion_templates.py

The templates can then be loaded by drive_from_emotion() to produce
real expression-driven facial animation instead of a self-loop.
"""

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is on path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("generate_templates")


def create_driving_video(emotion: str, output_path: str, num_frames: int = 90,
                          face_size: int = 512) -> str:
    """Create a synthetic driving video with the target expression.

    Generates frames using OpenCV drawing primitives (oval face, line
    mouth, circle eyes) with positions adjusted for each emotion.

    Args:
        emotion: Target emotion label.
        output_path: Full path for the output MP4 video.
        num_frames: Number of frames to generate (~3s at 30fps).
        face_size: Size of the square face image.

    Returns:
        Path to the generated video.
    """
    import cv2
    import numpy as np

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 30
    writer = cv2.VideoWriter(output_path, fourcc, fps, (face_size, face_size))

    cx, cy = face_size // 2, face_size // 2
    face_w, face_h = face_size // 3, face_size // 2
    mouth_base_y = cy + face_h // 3

    # ── Emotion-specific expression parameters ───────────────────────────
    # Each emotion defines: mouth_curve, brow_height, eye_open, jaw_drop
    # All values are normalized 0-1 ranges mapped to pixel offsets

    params = {
        "neutral": {
            "mouth_curve_range": (0.0, 0.0),
            "mouth_open_range": (0.0, 0.0),
            "brow_height_offset": 0.0,
            "eye_squint": 0.0,
        },
        "happy": {
            "mouth_curve_range": (0.4, 0.8),  # smile curves upward
            "mouth_open_range": (0.0, 0.2),
            "brow_height_offset": 0.0,
            "eye_squint": 0.15,
        },
        "sad": {
            "mouth_curve_range": (-0.5, -0.2),  # frown curves downward
            "mouth_open_range": (0.0, 0.1),
            "brow_height_offset": 0.12,  # inner brows up
            "eye_squint": 0.1,
        },
        "angry": {
            "mouth_curve_range": (-0.3, -0.1),
            "mouth_open_range": (0.0, 0.3),
            "brow_height_offset": -0.15,  # brows lowered
            "eye_squint": 0.3,
        },
        "surprised": {
            "mouth_curve_range": (0.0, 0.0),
            "mouth_open_range": (0.6, 0.9),
            "brow_height_offset": 0.2,  # brows raised
            "eye_squint": -0.2,  # eyes widened (negative = more open)
        },
        "fearful": {
            "mouth_curve_range": (-0.2, 0.1),
            "mouth_open_range": (0.3, 0.5),
            "brow_height_offset": 0.15,
            "eye_squint": -0.15,
        },
        "disgusted": {
            "mouth_curve_range": (-0.4, -0.1),
            "mouth_open_range": (0.1, 0.3),
            "brow_height_offset": -0.1,
            "eye_squint": 0.2,
        },
    }

    p = params.get(emotion, params["neutral"])
    period = max(num_frames, 2)

    for i in range(num_frames):
        # Create a clean background
        frame = np.ones((face_size, face_size, 3), dtype=np.uint8) * 200

        # Progress through the animation (sine wave for natural movement)
        t = i / period
        phase = np.sin(2 * np.pi * t)

        # Compute emotion-driven shape parameters
        mouth_open = p["mouth_open_range"][0] + (p["mouth_open_range"][1] - p["mouth_open_range"][0]) * (0.5 + 0.5 * phase)
        mouth_curve = p["mouth_curve_range"][0] + (p["mouth_curve_range"][1] - p["mouth_curve_range"][0]) * (0.5 + 0.5 * phase)
        eye_squint = p["eye_squint"]
        brow_offset = p["brow_height_offset"]

        # ── Face oval ────────────────────────────────────────────────────
        cv2.ellipse(frame, (cx, cy), (face_w, face_h), 0, 0, 360, (230, 190, 150), -1)
        cv2.ellipse(frame, (cx, cy), (face_w, face_h), 0, 0, 360, (180, 140, 100), 2)

        # ── Eyes ─────────────────────────────────────────────────────────
        eye_y = cy - face_h // 4
        eye_spacing = face_w // 3
        eye_w = int(face_w // 5 * (1.0 - max(0, eye_squint * 0.5)))
        eye_h = int(face_h // 7 * (1.0 - max(0, eye_squint)))

        for ex in [cx - eye_spacing, cx + eye_spacing]:
            cv2.ellipse(frame, (ex, eye_y), (max(eye_w, 3), max(eye_h, 2)), 0, 0, 360, (50, 50, 50), -1)
            # Pupil
            cv2.circle(frame, (ex, eye_y), max(eye_w // 3, 1), (200, 200, 200), -1)

        # ── Eyebrows ─────────────────────────────────────────────────────
        brow_y = eye_y - face_h // 6
        brow_len = face_w // 4
        brow_h = int(brow_offset * face_h)
        cv2.line(frame, (cx - brow_len, brow_y + brow_h), (cx - 5, brow_y + brow_h), (50, 50, 50), 3)
        cv2.line(frame, (cx + 5, brow_y + brow_h), (cx + brow_len, brow_y + brow_h), (50, 50, 50), 3)

        # ── Nose ─────────────────────────────────────────────────────────
        nose_top = (cx, cy - face_h // 6)
        nose_bot = (cx, cy + face_h // 8)
        cv2.line(frame, nose_top, (cx - face_w // 6, cy + face_h // 10), (150, 110, 70), 2)
        cv2.line(frame, nose_top, (cx + face_w // 6, cy + face_h // 10), (150, 110, 70), 2)
        cv2.line(frame, nose_top, nose_bot, (150, 110, 70), 2)

        # ── Mouth ────────────────────────────────────────────────────────
        mouth_open_px = int(mouth_open * face_h // 4)
        mouth_w = face_w // 3
        mouth_y = mouth_base_y - mouth_open_px // 2
        curve_amp = int(mouth_curve * face_h // 4)

        # Upper lip (smile/frown curve + opening)
        pts = []
        for mx in range(-mouth_w, mouth_w + 1, 1):
            nx = cx + mx
            ny = mouth_y + int(curve_amp * (1.0 - (mx / mouth_w) ** 2)) - mouth_open_px // 2
            pts.append([nx, ny])
        if len(pts) > 1:
            pts_arr = np.array(pts, dtype=np.int32)
            cv2.polylines(frame, [pts_arr], False, (80, 40, 20), 3)

        # Lower lip (opens downward)
        if mouth_open_px > 2:
            pts2 = []
            for mx in range(-mouth_w, mouth_w + 1, 1):
                nx = cx + mx
                ny = mouth_y + int(curve_amp * (1.0 - (mx / mouth_w) ** 2)) + mouth_open_px
                pts2.append([nx, ny])
            if len(pts2) > 1:
                pts_arr2 = np.array(pts2, dtype=np.int32)
                cv2.polylines(frame, [pts_arr2], False, (80, 40, 20), 3)
                # Fill inside of open mouth
                overlay = frame.copy()
                cv2.ellipse(overlay, (cx, mouth_y + mouth_open_px // 2),
                            (mouth_w, mouth_open_px // 2), 0, 0, 180, (40, 20, 10), -1)
                cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        writer.write(frame)

    writer.release()
    logger.info(f"Driving video created: {output_path} ({num_frames} frames, {emotion})")
    return output_path


def generate_template_from_video(driving_video: str, output_path: str,
                                 device: str = "cpu") -> bool:
    """Process a driving video through LivePortrait to extract a motion template.

    Uses the LivePortraitPipeline's make_motion_template to extract
    motion data from the driving video and save it as a .pkl template.

    Args:
        driving_video: Path to the driving video.
        output_path: Path for the output .pkl file.
        device: Device to use ('cpu' or 'cuda').

    Returns:
        True if successful, False otherwise.
    """
    try:
        import torch
        from dreamtalk.face.core.animation.liveportrait import (
            LivePortraitPipeline,
            InferenceConfig,
            CropConfig,
            ArgumentConfig,
        )
        from dreamtalk.face.core.animation.liveportrait.utils.io import dump
        from dreamtalk.face.core.animation.liveportrait.utils.video import load_video
    except ImportError as e:
        logger.error(f"LivePortrait import failed: {e}")
        return False

    try:
        # Configure LivePortrait
        inf_cfg = InferenceConfig()
        inf_cfg.flag_use_half_precision = False
        inf_cfg.flag_crop_driving_video = True
        inf_cfg.flag_do_crop = True

        crop_cfg = CropConfig()
        crop_cfg.flag_force_cpu = (device == "cpu")

        pipeline = LivePortraitPipeline(inference_cfg=inf_cfg, crop_cfg=crop_cfg)

        # Set device
        if device == "cpu":
            pipeline.live_portrait_wrapper.device = "cpu"

        # Load the driving video
        frames = load_video(driving_video)
        logger.info(f"Loaded {len(frames)} frames from driving video")

        if len(frames) == 0:
            logger.error("No frames loaded from driving video")
            return False

        # Process through cropper
        from dreamtalk.face.core.animation.liveportrait.utils.cropper import Cropper
        cropper = Cropper(crop_cfg=crop_cfg)

        if inf_cfg.flag_crop_driving_video:
            ret_d = cropper.crop_driving_video(frames)
            if not ret_d or not ret_d.get("frame_crop_lst"):
                logger.warning("Face not detected in driving video frames, using raw frames")
                frames_256 = [cv2.resize(f, (256, 256)) for f in frames]
                crop_frames = frames_256
                lmk_lst = None
            else:
                crop_frames = ret_d["frame_crop_lst"]
                lmk_lst = ret_d.get("lmk_crop_lst")
                crop_frames_256 = [cv2.resize(f, (256, 256)) for f in crop_frames]
                # Compute eye/lip ratios from landmarks
                if lmk_lst:
                    c_d_eyes_lst, c_d_lip_lst = pipeline.live_portrait_wrapper.calc_ratio(lmk_lst)
                else:
                    c_d_eyes_lst = [[[0.0, 0.0, 0.0]]] * len(crop_frames_256)
                    c_d_lip_lst = [[0.0]] * len(crop_frames_256)

                # Prepare video tensors
                I_d_lst = pipeline.live_portrait_wrapper.prepare_videos(crop_frames_256)
                template_dct = pipeline.make_motion_template(
                    I_d_lst, c_d_eyes_lst, c_d_lip_lst, output_fps=15
                )
        else:
            # Fallback: resize frames to 256x256 and process directly
            frames_256 = [cv2.resize(f, (256, 256)) for f in frames]
            crop_frames_256 = frames_256
            lmk_lst = None
            c_d_eyes_lst = [[[0.0, 0.0, 0.0]]] * len(frames_256)
            c_d_lip_lst = [[0.0]] * len(frames_256)
            I_d_lst = pipeline.live_portrait_wrapper.prepare_videos(frames_256)
            template_dct = pipeline.make_motion_template(
                I_d_lst, c_d_eyes_lst, c_d_lip_lst, output_fps=15
            )

        # Save the template
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        dump(output_path, template_dct)
        logger.info(f"Motion template saved: {output_path} "
                    f"({template_dct['n_frames']} frames, "
                    f"{len(template_dct['motion'])} motion entries)")
        return True

    except Exception as e:
        logger.error(f"Template generation failed for {driving_video}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate LivePortrait Emotion Motion Templates")
    parser.add_argument("--emotions", nargs="+",
                        default=["neutral", "happy", "sad", "angry", "surprised", "fearful", "disgusted"],
                        help="Emotions to generate templates for")
    parser.add_argument("--output-dir", default="weights/liveportrait/templates",
                        help="Output directory for .pkl templates")
    parser.add_argument("--num-frames", type=int, default=90,
                        help="Number of frames per template (~3s at 30fps)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                        help="Device for LivePortrait inference")
    parser.add_argument("--force", action="store_true",
                        help="Re-generate existing templates")
    args = parser.parse_args()

    output_dir = Path(_root) / args.output_dir
    os.makedirs(str(output_dir), exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(prefix="lp_templates_"))
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Temp dir: {tmp_dir}")

    generated = []
    skipped = []
    failed = []

    for emotion in args.emotions:
        pkl_path = output_dir / f"{emotion}.pkl"

        if pkl_path.exists() and not args.force:
            logger.info(f"Template exists (skipping): {pkl_path}")
            skipped.append(emotion)
            continue

        logger.info(f"\n{'=' * 50}")
        logger.info(f"Generating template for: {emotion}")
        logger.info(f"{'=' * 50}")

        # Step 1: Generate synthetic driving video
        video_path = tmp_dir / f"{emotion}_driving.mp4"
        try:
            create_driving_video(emotion, str(video_path), num_frames=args.num_frames)
        except Exception as e:
            logger.error(f"Failed to create driving video for {emotion}: {e}")
            failed.append(emotion)
            continue

        # Step 2: Process through LivePortrait to extract motion template
        success = generate_template_from_video(str(video_path), str(pkl_path), device=args.device)

        if success:
            generated.append(emotion)
            size_mb = pkl_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ {emotion}: {pkl_path} ({size_mb:.2f} MB)")
        else:
            # Fallback: create a minimal template with synthetic exp data
            # (This is used when LivePortrait face detection fails on synthetic faces)
            logger.warning(f"LivePortrait extraction failed for {emotion}, "
                          f"creating synthetic template...")
            success = create_synthetic_fallback_template(emotion, str(pkl_path), args.num_frames)
            if success:
                generated.append(emotion)
                size_kb = pkl_path.stat().st_size / 1024
                logger.info(f"✅ {emotion} (synthetic): {pkl_path} ({size_kb:.1f} KB)")
            else:
                failed.append(emotion)

    # Summary
    logger.info(f"\n{'=' * 50}")
    logger.info("GENERATION COMPLETE")
    logger.info(f"{'=' * 50}")
    logger.info(f"  Generated: {len(generated)}: {', '.join(generated)}")
    logger.info(f"  Skipped:   {len(skipped)}: {', '.join(skipped)}")
    logger.info(f"  Failed:    {len(failed)}: {', '.join(failed)}")
    logger.info(f"  Output:    {output_dir}")
    logger.info(f"{'=' * 50}")

    # Cleanup
    import shutil
    shutil.rmtree(str(tmp_dir), ignore_errors=True)

    return 0 if not failed else 1


def create_synthetic_fallback_template(emotion: str, output_path: str,
                                        num_frames: int = 90) -> bool:
    """Create a motion template with synthetic expression coefficients.

    Used as fallback when LivePortrait face detection fails on synthetic
    driving videos. Generates realistic-looking exp coefficient variations
    for each emotion based on known keypoint mappings.

    The 21 keypoints map to facial regions:
      0: nose tip
      1, 2: left/right eyebrow inner
      3, 4, 5: nose bridge/wings
      6, 12, 14, 17, 19, 20: mouth region
      11, 13, 15, 16, 18: eyes
      7, 8, 9, 10: other face regions
    """
    import numpy as np
    import pickle as pkl

    # Scale factor for exp coefficient magnitude
    # Actual values observed in LivePortrait are typically 0-0.5 range
    MAGNITUDE = 0.08

    # Emotion-specific exp modulation for each keypoint (y-axis = dim 1)
    # Positive y = downward movement (most face features), negative = upward
    # Format: {keypoint_idx: (dx_weight, dy_weight, dz_weight)}
    emotion_exp_map = {
        "neutral": {},
        "happy": {
            6:  (0.0, -0.3, 0.0),   # mouth corner - up
            12: (0.0, -0.5, 0.0),   # mouth - up
            14: (0.0, -0.5, 0.0),   # mouth - up
            17: (0.0, -0.3, 0.0),   # mouth corner - up
            19: (0.0, -0.2, 0.0),   # mouth - slight up
            20: (0.0, -0.2, 0.0),   # mouth - slight up
            11: (0.0, 0.1, 0.0),    # eye squint
            13: (0.0, 0.1, 0.0),    # eye squint
        },
        "sad": {
            1:  (0.0, -0.2, 0.0),   # brow inner up
            2:  (0.0, -0.2, 0.0),   # brow inner up
            6:  (0.0, 0.3, 0.0),    # mouth corner down
            12: (0.0, 0.2, 0.0),    # mouth down
            14: (0.0, 0.2, 0.0),    # mouth down
            17: (0.0, 0.3, 0.0),    # mouth corner down
        },
        "angry": {
            1:  (0.0, 0.25, 0.0),   # brow lowered
            2:  (0.0, 0.25, 0.0),   # brow lowered
            6:  (0.0, 0.1, 0.0),    # mouth corner down
            17: (0.0, 0.1, 0.0),    # mouth corner down
            19: (0.0, 0.15, 0.0),   # mouth pressed
            20: (0.0, 0.15, 0.0),   # mouth pressed
            11: (0.0, 0.2, 0.0),    # eye squint
            13: (0.0, 0.2, 0.0),    # eye squint
        },
        "surprised": {
            1:  (0.0, -0.3, 0.0),   # brows raised
            2:  (0.0, -0.3, 0.0),   # brows raised
            6:  (0.0, 0.5, 0.0),    # jaw drop (mouth open)
            12: (0.0, 0.4, 0.0),    # mouth open
            14: (0.0, 0.4, 0.0),    # mouth open
            17: (0.0, 0.3, 0.0),    # mouth corner
            11: (0.0, -0.15, 0.0),  # eyes wide
            13: (0.0, -0.15, 0.0),  # eyes wide
        },
        "fearful": {
            1:  (0.0, -0.2, 0.0),   # brows raised
            2:  (0.0, -0.2, 0.0),   # brows raised
            6:  (0.0, 0.3, 0.0),    # mouth open
            12: (0.0, 0.2, 0.0),    # mouth
            17: (0.0, 0.2, 0.0),    # mouth corner
            11: (0.0, -0.1, 0.0),   # eyes wide
            13: (0.0, -0.1, 0.0),   # eyes wide
        },
        "disgusted": {
            1:  (0.0, 0.15, 0.0),   # brow lowered
            2:  (0.0, 0.15, 0.0),   # brow lowered
            3:  (0.0, 0.1, 0.0),    # nose sneer
            4:  (0.1, 0.0, 0.0),    # nose wrinkle
            6:  (0.0, 0.2, 0.0),    # mouth corner down
            17: (0.0, 0.2, 0.0),    # mouth corner down
            11: (0.0, 0.15, 0.0),   # eye squint
            13: (0.0, 0.15, 0.0),   # eye squint
        },
    }

    exp_mods = emotion_exp_map.get(emotion, emotion_exp_map["neutral"])

    # Build template
    n_frames = num_frames
    motion = []

    for i in range(n_frames):
        # Sinusoidal modulation for natural looping animation
        phase = np.sin(2 * np.pi * i / n_frames)

        # Build exp tensor [1, 21, 3]
        exp = np.zeros((1, 21, 3), dtype=np.float32)
        for kidx, (dx, dy, dz) in exp_mods.items():
            exp[0, kidx, 0] = dx * MAGNITUDE * phase
            exp[0, kidx, 1] = dy * MAGNITUDE * phase
            exp[0, kidx, 2] = dz * MAGNITUDE * phase

        # Rotation matrix (slight head movement for natural feel)
        angle = phase * 0.05  # ±3 degrees
        R = np.eye(3, dtype=np.float32)
        R[0, 0] = np.cos(angle)
        R[0, 2] = np.sin(angle)
        R[2, 0] = -np.sin(angle)
        R[2, 2] = np.cos(angle)
        R = R[np.newaxis, ...]  # [1, 3, 3]

        motion.append({
            "scale": np.ones((1, 1), dtype=np.float32),
            "R": R,
            "exp": exp,
            "t": np.zeros((1, 3), dtype=np.float32),
            "kp": np.zeros((1, 21, 3), dtype=np.float32),
            "x_s": np.zeros((1, 21, 3), dtype=np.float32),
        })

    template_dct = {
        "n_frames": n_frames,
        "output_fps": 15,
        "motion": motion,
        "c_eyes_lst": [[[0.1, 0.1, 0.1]]] * n_frames,
        "c_lip_lst": [[0.1]] * n_frames,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        pkl.dump(template_dct, f)

    return True


if __name__ == "__main__":
    sys.exit(main())
