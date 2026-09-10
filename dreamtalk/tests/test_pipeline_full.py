"""
End-to-End Digital Twin Pipeline Integration Test.

Generates synthetic test data (image + audio + text) and runs the
full PipelineOrchestrator to test all modules end-to-end.

Usage:
    python test_pipeline_full.py              # Full pipeline test
    python test_pipeline_full.py --face-only   # Face pipeline only
    python test_pipeline_full.py --voice-only  # Voice pipeline only
    python test_pipeline_full.py --brain-only  # Brain pipeline only
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_pipeline")


def generate_test_image(path: str, width: int = 640, height: int = 480):
    """Generate a synthetic test image with a face-like ellipse."""
    try:
        import cv2
        img = np.ones((height, width, 3), dtype=np.uint8) * 200

        # Draw an oval "face"
        center = (width // 2, height // 2)
        axes = (width // 4, height // 3)
        cv2.ellipse(img, center, axes, 0, 0, 360, (220, 180, 140), -1)

        # Eyes
        eye_y = center[1] - axes[1] // 3
        cv2.circle(img, (center[0] - axes[0] // 3, eye_y), 12, (50, 50, 50), -1)
        cv2.circle(img, (center[0] + axes[0] // 3, eye_y), 12, (50, 50, 50), -1)
        cv2.circle(img, (center[0] - axes[0] // 3, eye_y), 5, (200, 200, 200), -1)
        cv2.circle(img, (center[0] + axes[0] // 3, eye_y), 5, (200, 200, 200), -1)

        # Nose
        nose_tip = (center[0], center[1] + axes[1] // 6)
        cv2.circle(img, nose_tip, 6, (180, 140, 100), -1)

        # Mouth
        mouth_y = center[1] + axes[1] // 3
        cv2.ellipse(img, (center[0], mouth_y), (axes[0] // 3, axes[1] // 8), 0, 0, 180, (80, 60, 40), 3)

        cv2.imwrite(path, img)
        logger.info(f"Test image generated: {path} ({os.path.getsize(path)} bytes)")
        return True
    except ImportError:
        logger.warning("OpenCV not available for test image generation")
        # Write a minimal JPEG header
        with open(path, "wb") as f:
            # 1x1 pixel JPEG
            f.write(bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
                0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
                0xFF, 0xDB, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06,
                0x05, 0x08, 0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
                0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12, 0x13, 0x0F,
                0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
                0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28,
                0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
                0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32,
                0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00, 0x01, 0x01,
                0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01,
                0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05,
                0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B,
                0xFF, 0xD9,
            ]))
        logger.info(f"Minimal test image generated: {path}")
        return True


def generate_test_audio(path: str, duration: float = 3.0, sr: int = 22050):
    """Generate a synthetic test audio file (sine wave with harmonics)."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * 220 * t)
    audio += 0.15 * np.sin(2 * np.pi * 440 * t)
    audio += 0.07 * np.sin(2 * np.pi * 660 * t)
    audio += 0.03 * np.sin(2 * np.pi * 880 * t)
    fade = np.linspace(0, 1, int(sr * 0.05))
    audio[:len(fade)] *= fade
    audio[-len(fade):] *= fade[::-1]

    try:
        import soundfile as sf
        sf.write(path, audio, sr)
        logger.info(f"Test audio generated: {path} ({os.path.getsize(path)} bytes)")
        return True
    except ImportError:
        pass

    try:
        import scipy.io.wavfile as wavfile
        int_audio = (audio * 32767).astype(np.int16)
        wavfile.write(path, sr, int_audio)
        logger.info(f"Test audio generated (scipy): {path}")
        return True
    except ImportError:
        pass

    # Write minimal WAV header
    try:
        import struct
        num_samples = len(audio)
        data_bytes = (audio * 32767).astype(np.int16).tobytes()
        with open(path, "wb") as f:
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(data_bytes)))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
            f.write(b"data")
            f.write(struct.pack("<I", len(data_bytes)))
            f.write(data_bytes)
        logger.info(f"Test audio generated (raw WAV): {path}")
        return True
    except Exception as e:
        logger.warning(f"Failed to generate test audio: {e}")
        return False


async def test_full_pipeline():
    """Run the full pipeline with synthetic data."""
    logger.info("=" * 60)
    logger.info("DREAMTALK END-TO-END PIPELINE TEST")
    logger.info("=" * 60)

    # Create temp directory for test files
    test_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "pipeline_test_data",
    )
    os.makedirs(test_dir, exist_ok=True)

    # Generate test data
    image_path = os.path.join(test_dir, "test_face.jpg")
    audio_path = os.path.join(test_dir, "test_voice.wav")
    generate_test_image(image_path)
    generate_test_audio(audio_path, duration=2.0)

    test_texts = [
        "Hello! I'm excited to meet my Digital Twin. How are you today?",
        "I've been feeling a bit frustrated with my work lately. Can you help me organize my tasks?",
        "I think I might be coming down with something. I have a headache and feel tired.",
    ]

    test_roles = ["normal_user", "business", "healthcare"]

    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
    from dreamtalk.pipeline.models import PipelineRequest

    orchestrator = PipelineOrchestrator()

    for i, (text, role) in enumerate(zip(test_texts, test_roles)):
        logger.info(f"\n{'─' * 50}")
        logger.info(f"TEST {i+1}: Role={role}")
        logger.info(f"  Text: {text[:60]}...")
        logger.info(f"{'─' * 50}")

        request = PipelineRequest(
            twin_id=f"test_twin_{uuid.uuid4().hex[:8]}",
            user_id="test_user",
            role=role,
            image_paths=[image_path],
            voice_paths=[audio_path],
            text_input=text,
            enable_3d_face=True,
            enable_voice_clone=True,
            enable_emotion=True,
            enable_decision=True,
            enable_object_detection=True,
            model_name="rule_based",
        )

        result = await orchestrator.run_full_pipeline(request)

        # Display results
        logger.info(f"  Pipeline Status: {result.status.value}")
        logger.info(f"  Steps completed: {len([s for s in result.steps if s.status == 'completed'])}/{len(result.steps)}")

        if result.face_result:
            fr = result.face_result
            logger.info(f"  [FACE] Detected={fr.face_detected}, Count={fr.face_count}, Quality={fr.quality_score:.3f}")
            logger.info(f"  [FACE] Mesh={os.path.basename(fr.mesh_3d_path) if fr.mesh_3d_path else 'N/A'}")
            logger.info(f"  [FACE] Emotion={fr.emotion_from_face}")

        if result.voice_result:
            vr = result.voice_result
            logger.info(f"  [VOICE] Detected={vr.voice_detected}, Duration={vr.duration_seconds}s")
            logger.info(f"  [VOICE] Pitch={vr.pitch_mean:.1f}Hz, Rate={vr.speaking_rate}")
            logger.info(f"  [VOICE] Cloned={os.path.basename(vr.cloned_voice_path) if vr.cloned_voice_path else 'N/A'}")
            logger.info(f"  [VOICE] TTS={os.path.basename(vr.tts_sample_path) if vr.tts_sample_path else 'N/A'}")

        if result.emotion_result:
            er = result.emotion_result
            logger.info(f"  [EMOTION] Mood={er.primary_mood.value}, Valence={er.valence:.3f}, Arousal={er.arousal:.3f}")
            logger.info(f"  [EMOTION] Intensity={er.intensity}, Hostile={er.is_hostile}")

        if result.brain_result:
            br = result.brain_result
            logger.info(f"  [BRAIN] Response: {br.response_text[:80]}...")
            logger.info(f"  [BRAIN] Confidence={br.confidence:.3f}, Type={br.decision_type}")
            logger.info(f"  [BRAIN] Time={br.processing_time_ms:.1f}ms")

        if result.object_result:
            or_ = result.object_result
            logger.info(f"  [OBJECTS] Count={or_.object_count}, Labels={or_.labels[:5]}")

        if result.error:
            logger.warning(f"  ⚠ Pipeline errors: {result.error}")

        logger.info(f"  Pipeline ID: {result.pipeline_id}")

    # Cleanup test data
    logger.info(f"\n{'─' * 50}")
    logger.info("Test data preserved at: %s", test_dir)
    logger.info("Pipeline outputs preserved at: pipeline_outputs/")
    logger.info("=" * 60)
    logger.info("ALL TESTS COMPLETE")
    logger.info("=" * 60)

    return True


async def test_face_only():
    """Test only the face pipeline."""
    from dreamtalk.pipeline.face_pipeline import FacePipeline
    import tempfile

    test_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "pipeline_test_data",
    )
    os.makedirs(test_dir, exist_ok=True)
    image_path = os.path.join(test_dir, "test_face.jpg")
    generate_test_image(image_path)

    pipeline = FacePipeline()
    result = await pipeline.run([image_path], output_dir=test_dir)

    logger.info("FACE-ONLY TEST RESULTS:")
    logger.info(f"  Face detected: {result.face_detected}")
    logger.info(f"  Face count: {result.face_count}")
    logger.info(f"  Quality score: {result.quality_score}")
    logger.info(f"  Head pose: {result.head_pose}")
    logger.info(f"  Emotion: {result.emotion_from_face}")
    logger.info(f"  Mesh: {result.mesh_3d_path}")
    logger.info(f"  Texture: {result.texture_path}")

    # Print JSON
    print("\n--- Face Result JSON ---")
    print(json.dumps(result.model_dump(), indent=2, default=str))


async def test_voice_only():
    """Test only the voice pipeline."""
    from dreamtalk.pipeline.voice_pipeline import VoicePipeline

    test_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "pipeline_test_data",
    )
    os.makedirs(test_dir, exist_ok=True)
    audio_path = os.path.join(test_dir, "test_voice.wav")
    generate_test_audio(audio_path, duration=3.0)

    pipeline = VoicePipeline()
    result = await pipeline.run(
        [audio_path],
        text_input="Hello, this is a test of the DreamTalk voice cloning pipeline.",
        output_dir=test_dir,
    )

    logger.info("VOICE-ONLY TEST RESULTS:")
    logger.info(f"  Voice detected: {result.voice_detected}")
    logger.info(f"  Duration: {result.duration_seconds}s")
    logger.info(f"  Sample rate: {result.sample_rate}Hz")
    logger.info(f"  Pitch mean: {result.pitch_mean:.1f}Hz")
    logger.info(f"  Energy: {result.energy_mean:.4f}")
    logger.info(f"  Speaking rate: {result.speaking_rate}")
    logger.info(f"  Clone path: {result.cloned_voice_path}")
    logger.info(f"  TTS path: {result.tts_sample_path}")

    print("\n--- Voice Result JSON ---")
    print(json.dumps(result.model_dump(), indent=2, default=str))


async def test_brain_only():
    """Test only the brain pipeline (emotion + decision)."""
    from dreamtalk.pipeline.brain_pipeline import BrainPipeline

    pipeline = BrainPipeline()
    texts = [
        "I am so happy today! Everything is going great!",
        "I hate this stupid thing, it's so frustrating and annoying!",
        "I have a headache and feel really sick.",
        "Can you help me organize my project deadlines?",
    ]
    roles = ["normal_user", "normal_user", "healthcare", "business"]

    for text, role in zip(texts, roles):
        result = await pipeline.run(
            text_input=text,
            role=role,
            enable_emotion=True,
            enable_decision=True,
        )

        logger.info(f"\n--- Brain Test [{role}] ---")
        logger.info(f"  Text: {text}")
        if "emotion" in result:
            e = result["emotion"]
            logger.info(f"  Mood: {e.primary_mood.value} | Valence={e.valence:.2f} | Hostile={e.is_hostile}")
        if "brain" in result:
            b = result["brain"]
            logger.info(f"  Response: {b.response_text[:100]}...")
            logger.info(f"  Confidence: {b.confidence:.3f} | Time: {b.processing_time_ms:.1f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DreamTalk Pipeline Integration Test")
    parser.add_argument("--face-only", action="store_true", help="Run face pipeline only")
    parser.add_argument("--voice-only", action="store_true", help="Run voice pipeline only")
    parser.add_argument("--brain-only", action="store_true", help="Run brain pipeline only")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep test data")
    args = parser.parse_args()

    if args.face_only:
        asyncio.run(test_face_only())
    elif args.voice_only:
        asyncio.run(test_voice_only())
    elif args.brain_only:
        asyncio.run(test_brain_only())
    else:
        asyncio.run(test_full_pipeline())
