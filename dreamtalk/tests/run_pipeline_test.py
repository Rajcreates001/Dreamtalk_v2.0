"""Quick pipeline smoke test — runs orchestrator with synthetic data."""
import asyncio
import logging
import os
import sys
import json
import uuid

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("smoke_test")

# Generate test data
test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline_test_data")
os.makedirs(test_dir, exist_ok=True)

img_path = os.path.join(test_dir, "test_face.jpg")
wav_path = os.path.join(test_dir, "test_voice.wav")

try:
    import cv2
    img = np.ones((480, 640, 3), dtype=np.uint8) * 200
    cv2.ellipse(img, (320, 240), (160, 200), 0, 0, 360, (220, 180, 140), -1)
    cv2.circle(img, (260, 200), 15, (50, 50, 50), -1)
    cv2.circle(img, (380, 200), 15, (50, 50, 50), -1)
    cv2.ellipse(img, (320, 300), (80, 25), 0, 0, 180, (80, 60, 40), 3)
    cv2.imwrite(img_path, img)
    logger.info("Test image generated")
except Exception as e:
    logger.warning(f"Could not generate test image: {e}")
    # Write placeholder
    with open(img_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c\x80$.\' \"\" ,#\x1c\x1c(7) ,012444\x1f\'9=82<.34\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9")

# Generate test audio
sr = 22050
duration = 2.0
t = np.linspace(0, duration, int(sr * duration), endpoint=False)
audio = 0.3 * np.sin(2 * np.pi * 220 * t) + 0.15 * np.sin(2 * np.pi * 440 * t)
try:
    import soundfile as sf
    sf.write(wav_path, audio, sr)
except Exception:
    try:
        import scipy.io.wavfile as wavfile
        wavfile.write(wav_path, sr, (audio * 32767).astype(np.int16))
    except Exception as e:
        logger.warning(f"Could not generate test audio: {e}")

logger.info("Test data ready")


async def main():
    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
    from dreamtalk.pipeline.models import PipelineRequest

    orch = PipelineOrchestrator()

    # ── Test 1: Full pipeline ────────────────────────────────────
    logger.info("\n=== TEST 1: Full Pipeline (normal_user) ===")
    req1 = PipelineRequest(
        twin_id=f"test_{uuid.uuid4().hex[:8]}",
        role="normal_user",
        image_paths=[img_path],
        voice_paths=[wav_path],
        text_input="Hello! I am so happy to meet my Digital Twin today!",
        enable_3d_face=True, enable_voice_clone=True,
        enable_emotion=True, enable_decision=True,
        enable_object_detection=True, model_name="rule_based",
    )
    r1 = await orch.run_full_pipeline(req1)
    logger.info(f"Status: {r1.status.value}")
    for s in r1.steps:
        logger.info(f"  Step {s.step}: {s.name} = {s.status}")
    if r1.face_result:
        logger.info(f"  FACE: detected={r1.face_result.face_detected}, mesh={r1.face_result.mesh_3d_path is not None}")
    if r1.voice_result:
        logger.info(f"  VOICE: detected={r1.voice_result.voice_detected}, clone={r1.voice_result.cloned_voice_path is not None}")
    if r1.emotion_result:
        logger.info(f"  EMOTION: mood={r1.emotion_result.primary_mood.value}, valence={r1.emotion_result.valence:.2f}")
    if r1.brain_result:
        logger.info(f"  BRAIN: {r1.brain_result.response_text[:60]}...")
    if r1.object_result:
        logger.info(f"  OBJECTS: count={r1.object_result.object_count}")
    if r1.error:
        logger.info(f"  Errors: {r1.error}")

    # ── Test 2: Healthcare role ──────────────────────────────────
    logger.info("\n=== TEST 2: Role-aware (healthcare) ===")
    req2 = PipelineRequest(
        twin_id=f"test_{uuid.uuid4().hex[:8]}",
        role="healthcare",
        image_paths=[img_path],
        text_input="I have a terrible headache and feel really sick.",
        enable_3d_face=True, enable_emotion=True, enable_decision=True,
        model_name="rule_based",
    )
    r2 = await orch.run_full_pipeline(req2)
    logger.info(f"Status: {r2.status.value}")
    if r2.emotion_result:
        logger.info(f"  EMOTION: mood={r2.emotion_result.primary_mood.value}, intensity={r2.emotion_result.intensity}")
    if r2.brain_result:
        logger.info(f"  BRAIN: {r2.brain_result.response_text[:80]}")

    # ── Test 3: Business role ────────────────────────────────────
    logger.info("\n=== TEST 3: Role-aware (business) ===")
    req3 = PipelineRequest(
        twin_id=f"test_{uuid.uuid4().hex[:8]}",
        role="business",
        image_paths=[img_path],
        voice_paths=[wav_path],
        text_input="Can you help me organize my project deadlines and team meetings?",
        enable_3d_face=True, enable_voice_clone=True,
        enable_emotion=True, enable_decision=True,
        model_name="rule_based",
    )
    r3 = await orch.run_full_pipeline(req3)
    logger.info(f"Status: {r3.status.value}")
    if r3.brain_result:
        logger.info(f"  BRAIN: {r3.brain_result.response_text[:80]}")

    # ── Summary ──────────────────────────────────────────────────
    logger.info("\n" + "=" * 50)
    logger.info("PIPELINE SMOKE TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"  Face pipeline:  {'PASS' if r1.face_result else 'FAIL'}")
    logger.info(f"  Voice pipeline: {'PASS' if r1.voice_result else 'FAIL'}")
    logger.info(f"  Emotion det:    {'PASS' if r1.emotion_result else 'FAIL'}")
    logger.info(f"  Brain decision: {'PASS' if r1.brain_result else 'FAIL'}")
    logger.info(f"  Object detect:  {'PASS' if r1.object_result else 'FAIL'}")
    logger.info(f"  Healthcare role:{'PASS' if r2.brain_result else 'FAIL'}")
    logger.info(f"  Business role:  {'PASS' if r3.brain_result else 'FAIL'}")
    logger.info("=" * 50)
    logger.info("ALL TESTS COMPLETE")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
