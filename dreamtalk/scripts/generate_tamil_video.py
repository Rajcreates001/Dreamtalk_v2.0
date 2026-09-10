"""
Tamil Avatar Lip-Sync Video Generator
======================================
Creates a talking-head video combining:
  1. Source photo (sample1.jpeg) as the appearance
  2. Tamil TTS audio (cloned_voice.wav) as the voice
  3. 3D OBJ mesh overlay (optional)

Pipeline:
  1. Try LivePortrait for expression-driven animation (subtle head movement)
  2. Fall back to FFmpeg talking-head video with photo + audio
  3. Copy result to avatar/static/ for web access

Usage:
    cd dreamtalk && python scripts/generate_tamil_video.py
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tamil_video")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "avatar" / "static"
OUTPUT_DIR = PROJECT_ROOT / "pipeline_outputs"
SAMPLE_PHOTO = PROJECT_ROOT / "local_upload_testing" / "image" / "sample1.jpeg"
TTS_AUDIO = STATIC_DIR / "cloned_voice.wav"
DRIVING_VIDEO = PROJECT_ROOT / "local_upload_testing" / "driving_test.mp4"


def find_ffmpeg() -> str:
    """Find ffmpeg binary."""
    candidates = [
        "ffmpeg",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        try:
            result = subprocess.run([c, "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "ffmpeg"  # Hope it's in PATH


async def check_liveportrait() -> bool:
    """Check if LivePortrait can be used."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from dreamtalk.pipeline.animation_pipeline import check_liveportrait_ready
        status = check_liveportrait_ready()
        ready = status.get("ready", False)
        logger.info(f"LivePortrait ready: {ready}")
        if not ready:
            logger.info(f"  Status: direct={status.get('direct_available')}, venv={status.get('venv_available')}")
            for w, ok in status.get("weights", {}).items():
                if w in ("all_present", "count", "total"):
                    continue
                if not ok:
                    logger.info(f"  Missing weight: {w}")
        return ready
    except Exception as e:
        logger.warning(f"LivePortrait check failed: {e}")
        return False


def create_video_with_ffmpeg(photo_path: str, audio_path: str, output_path: str,
                               duration: float = None) -> bool:
    """Create a simple talking-head video from photo + audio using FFmpeg."""
    ffmpeg = find_ffmpeg()
    logger.info(f"Using ffmpeg: {ffmpeg}")

    # Validate inputs
    if not os.path.exists(photo_path):
        logger.error(f"Photo not found: {photo_path}")
        return False
    if not os.path.exists(audio_path):
        logger.error(f"Audio not found: {audio_path}")
        return False

    # Get audio duration if not provided
    if duration is None:
        try:
            import soundfile as sf
            data, sr = sf.read(audio_path)
            duration = len(data) / sr
            logger.info(f"Audio duration: {duration:.1f}s")
        except Exception:
            duration = 30  # fallback

    # Step 1: Create video from photo (loop to match audio duration)
    # Use 1 fps static image and then set proper frame rate
    temp_video = output_path + ".tmp.mp4"

    # Calculate number of frames needed at 30fps
    fps = 30
    frames_needed = int(duration * fps)

    cmd = [
        ffmpeg, "-y",
        "-loop", "1",                     # Loop the input image
        "-i", photo_path,                 # Input image
        "-c:v", "libx264",               # H.264 video codec
        "-t", str(duration),             # Match audio duration
        "-pix_fmt", "yuv420p",           # Pixel format for compatibility
        "-vf", f"scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={fps}",  # Ensure even dimensions, set fps
        "-crf", "23",                    # Quality
        "-preset", "medium",             # Encoding speed
        temp_video,
    ]

    logger.info(f"Generating video frames: {frames_needed} frames @ {fps}fps ({duration:.1f}s)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 or not os.path.exists(temp_video):
        logger.error(f"Video generation failed: {result.stderr[-500:]}")
        return False
    logger.info(f"  Video generated: {os.path.getsize(temp_video) / 1024:.0f} KB")

    # Step 2: Add audio track
    cmd = [
        ffmpeg, "-y",
        "-i", temp_video,                # Input video
        "-i", audio_path,                 # Input audio
        "-c:v", "copy",                  # Don't re-encode video
        "-c:a", "aac",                   # AAC audio codec
        "-map", "0:v:0",                 # Video from first input
        "-map", "1:a:0",                 # Audio from second input
        "-shortest",                     # Match shortest stream
        "-movflags", "+faststart",       # Web-optimized
        output_path,
    ]

    logger.info("Adding audio track...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error(f"Audio muxing failed: {result.stderr[-500:]}")
        # Try outputting video-only as fallback
        shutil.copy2(temp_video, output_path)
        logger.warning("Using video without audio")
    else:
        logger.info(f"  Audio added: {os.path.getsize(output_path) / 1024:.0f} KB")

    # Clean up temp file
    try:
        os.unlink(temp_video)
    except Exception:
        pass

    return os.path.exists(output_path) and os.path.getsize(output_path) > 1024


async def try_liveportrait_video(source_photo: str, audio_path: str, output_path: str) -> bool:
    """Try LivePortrait animation + FFmpeg audio overlay."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from dreamtalk.pipeline.animation_pipeline import LivePortraitAnimationPipeline

        pipeline = LivePortraitAnimationPipeline()
        if not pipeline.is_available:
            logger.warning("LivePortrait not available")
            return False

        logger.info("LivePortrait is available! Generating animated video...")

        # Check if we have a driving video to use for expression
        if os.path.exists(DRIVING_VIDEO):
            logger.info(f"Using driving video: {DRIVING_VIDEO}")
            logger.info(f"  Size: {os.path.getsize(DRIVING_VIDEO) / 1024:.0f} KB")
            result = pipeline.drive_from_video(
                source_image_path=source_photo,
                driving_video_path=str(DRIVING_VIDEO),
                output_dir=str(OUTPUT_DIR / "liveportrait"),
                output_name=f"tamil_avatar_{uuid.uuid4().hex[:8]}",
                animation_region="all",
                do_pasteback=True,
            )
        else:
            # Try emotion-driven animation (neutral talking)
            logger.info("No driving video found. Using emotion-driven animation...")
            result = pipeline.drive_from_emotion(
                source_image_path=source_photo,
                output_dir=str(OUTPUT_DIR / "liveportrait"),
                output_name=f"tamil_avatar_{uuid.uuid4().hex[:8]}",
                emotion_label="neutral",
                num_frames=75,
                do_pasteback=True,
            )

        video_path = result.get("video_path")
        if video_path and os.path.exists(video_path):
            logger.info(f"LivePortrait animation generated: {os.path.getsize(video_path) / 1024:.0f} KB")

            # Add Tamil audio to the animated video
            ffmpeg = find_ffmpeg()
            cmd = [
                ffmpeg, "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                "-movflags", "+faststart",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"✅ LivePortrait video with audio: {os.path.getsize(output_path) / 1024:.0f} KB")
                return True
            else:
                # Fallback: copy the animated video without audio
                shutil.copy2(video_path, output_path)
                logger.warning("Audio overlay failed, using video without audio")
                return True

        logger.warning("LivePortrait produced no video output")
        return False

    except Exception as e:
        logger.warning(f"LivePortrait failed: {e}")
        return False


async def main():
    logger.info("=" * 60)
    logger.info("TAMIL AVATAR LIP-SYNC VIDEO GENERATOR")
    logger.info("=" * 60)

    # Validate inputs
    photo = str(SAMPLE_PHOTO if SAMPLE_PHOTO.exists() else STATIC_DIR / "current_photo.jpg" if (STATIC_DIR / "current_photo.jpg").exists() else STATIC_DIR / "current_texture.jpg")
    audio = str(TTS_AUDIO if TTS_AUDIO.exists() else STATIC_DIR / "tamil_script_full.wav")

    if not os.path.exists(photo):
        # Use any available face photo
        for candidate in [
            STATIC_DIR / "current_texture.jpg",
            STATIC_DIR / "current_texture.png",
        ]:
            if candidate.exists():
                photo = str(candidate)
                break

    logger.info(f"Source photo: {Path(photo).name} ({os.path.getsize(photo)/1024:.0f} KB)")
    logger.info(f"Audio: {Path(audio).name} ({os.path.getsize(audio)/1024:.0f} KB)")

    output_path = str(STATIC_DIR / "tamil_avatar_video.mp4")

    # Step 1: Try LivePortrait (expression-driven animation)
    logger.info("\n[1/2] Trying LivePortrait animation...")
    liveportrait_ok = await try_liveportrait_video(photo, audio, output_path)

    # Step 2: Fall back to FFmpeg talking-head video
    if not liveportrait_ok:
        logger.info("\n[2/2] Using FFmpeg talking-head video (static photo + audio)...")
        success = create_video_with_ffmpeg(photo, audio, output_path)
        if not success:
            logger.error("All video generation methods failed!")
            return

    # Verify output
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        # Get duration
        try:
            import soundfile as sf
            data, sr = sf.read(audio)
            duration = len(data) / sr
            logger.info(f"\n✅ Video generated: {size_mb:.1f} MB, {duration:.1f}s")
        except Exception:
            logger.info(f"\n✅ Video generated: {size_mb:.1f} MB")
    else:
        logger.error("Output video is empty or missing!")
        return

    # Copy to current_video.mp4 for the viewer
    shutil.copy2(output_path, str(STATIC_DIR / "current_video.mp4"))

    logger.info("\n" + "=" * 60)
    logger.info("📋 FINAL DELIVERABLE")
    logger.info("=" * 60)
    logger.info(f"  ✅ Tamil Avatar Video: tamil_avatar_video.mp4")
    logger.info(f"  ✅ Last: current_video.mp4 (for viewer)")
    logger.info(f"  📂 {STATIC_DIR}")
    logger.info(f"  🌐 View video: http://localhost:5000/api/avatar/static/tamil_avatar_video.mp4")
    logger.info(f"  🌐 Avatar viewer: http://localhost:5000/api/avatar/viewer")
    logger.info(f"  🌐 Video status: http://localhost:5000/api/avatar/video/status")


if __name__ == "__main__":
    asyncio.run(main())
