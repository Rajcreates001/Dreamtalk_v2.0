"""Full integration test for all expanded v2 pipeline modules."""
import asyncio
import logging
import os
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_v2")

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline_test_data")
os.makedirs(TEST_DIR, exist_ok=True)

IMG_PATH = os.path.join(TEST_DIR, "test_face.jpg")
WAV_PATH = os.path.join(TEST_DIR, "test_voice.wav")


def generate_test_data():
    try:
        import cv2
        img = np.ones((480, 640, 3), dtype=np.uint8) * 200
        cv2.ellipse(img, (320, 240), (160, 200), 0, 0, 360, (220, 180, 140), -1)
        cv2.circle(img, (260, 200), 15, (50, 50, 50), -1)
        cv2.circle(img, (380, 200), 15, (50, 50, 50), -1)
        cv2.ellipse(img, (320, 300), (80, 25), 0, 0, 180, (80, 60, 40), 3)
        cv2.imwrite(IMG_PATH, img)
        logger.info("Test image generated (OpenCV)")
    except Exception:
        logger.warning("No OpenCV, using small JPEG")
        with open(IMG_PATH, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c\x80$.\' \"\" ,#\x1c\x1c(7) ,012444\x1f\'9=82<.34\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9")

    sr = 22050
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * 220 * t) + 0.15 * np.sin(2 * np.pi * 440 * t)
    fade = np.linspace(0, 1, int(sr * 0.05))
    audio[:len(fade)] *= fade
    audio[-len(fade):] *= fade[::-1]
    try:
        import soundfile as sf
        sf.write(WAV_PATH, audio, sr)
    except Exception:
        try:
            import scipy.io.wavfile as wavfile
            wavfile.write(WAV_PATH, sr, (audio * 32767).astype(np.int16))
        except Exception as e:
            logger.warning(f"Audio gen failed: {e}")
    logger.info("Test data ready")


async def test_face():
    from dreamtalk.pipeline.face_pipeline import FacePipeline

    fp = FacePipeline(assets_dir=TEST_DIR)
    result = await fp.run([IMG_PATH], output_dir=TEST_DIR, enable_sr=True)

    logger.info("=== FACE V2 ===")
    logger.info(f"  Face detected: {result.face_detected}")
    logger.info(f"  Detection backend: {result.detection_backend}")
    logger.info(f"  Quality: {result.original_image_quality} score={result.quality_score:.3f}")
    logger.info(f"  Super-resolution: {result.super_resolution_applied}")
    logger.info(f"  Landmarks: {result.landmark_count} ({result.landmark_backend})")
    logger.info(f"  Blendshapes: {result.blendshape_count}")
    logger.info(f"  Head pose: {result.head_pose}")
    logger.info(f"  Emotion from face: {result.emotion_from_face} (conf={result.emotion_confidence:.3f})")
    logger.info(f"  Mesh: {'OK' if result.mesh_3d_path else 'N/A'} ({result.mesh_vertex_count} verts)")
    logger.info(f"  Texture: {'OK' if result.texture_path else 'N/A'}")
    logger.info(f"  Embedding dim: {result.embedding_dim}")
    if result.quality_factors:
        logger.info(f"  Quality factors: blur={result.quality_factors.get('blur_score', 0):.3f}, "
                    f"bright={result.quality_factors.get('brightness_score', 0):.3f}")
    return result


async def test_voice():
    from dreamtalk.pipeline.voice_pipeline import VoicePipeline

    vp = VoicePipeline(assets_dir=TEST_DIR)
    result = await vp.run([WAV_PATH], text_input="Hello from DreamTalk!", output_dir=TEST_DIR, enable_enhancement=True)

    logger.info("=== VOICE V2 ===")
    logger.info(f"  Voice detected: {result.voice_detected}")
    logger.info(f"  Duration: {result.duration_seconds}s, SR: {result.sample_rate}Hz")
    logger.info(f"  Enhancement: {result.enhancement_applied}, SNR: {result.snr_estimate:.1f}dB")
    logger.info(f"  Pitch: mean={result.pitch_mean:.1f}Hz, std={result.pitch_std:.1f}, median={result.pitch_median:.1f}")
    logger.info(f"  Vibrato: rate={result.vibrato_rate:.2f}Hz, extent={result.vibrato_extent:.2f}%")
    logger.info(f"  Energy: mean={result.energy_mean:.6f}, std={result.energy_std:.6f}")
    logger.info(f"  Spectral: centroid={result.spectral_centroid_mean:.0f}Hz, BW={result.spectral_bandwidth:.0f}Hz")
    logger.info(f"  Formants: {result.formant_frequencies}")
    logger.info(f"  Quality: jitter={result.jitter_local:.3f}%, shimmer={result.shimmer_local:.3f}%, HNR={result.harmonicity_hnr:.1f}dB")
    logger.info(f"  Prosody: rate={result.speaking_rate}, WPM={result.words_per_minute}, pauses={result.pause_count}")
    logger.info(f"  Gender: {result.gender_prediction}, Age: {result.age_prediction}")
    logger.info(f"  Embedding dim: {result.embedding_dim}")
    logger.info(f"  Clone: {result.clone_method} -> {os.path.basename(result.cloned_voice_path) if result.cloned_voice_path else 'N/A'}")
    logger.info(f"  TTS: {result.tts_method} -> {os.path.basename(result.tts_sample_path) if result.tts_sample_path else 'N/A'}")
    return result


async def test_brain():
    from dreamtalk.pipeline.brain_pipeline import BrainPipeline

    bp = BrainPipeline()

    tests = [
        ("I am so happy and grateful today!", "normal_user"),
        ("I hate this stupid thing!", "normal_user"),
        ("I have a terrible headache.", "healthcare"),
        ("Can you analyze Q3 revenue projections?", "business"),
    ]

    for text, role in tests:
        r = await bp.run(text_input=text, role=role, enable_emotion=True, enable_decision=True,
                         model_name="rule_based")
        e = r.get("emotion")
        b = r.get("brain")
        logger.info(f"=== BRAIN [{role}] \"{text[:40]}...\" ===")
        logger.info(f"  Mood: {e.primary_mood.value} | V={e.valence:.2f} A={e.arousal:.2f} | Hostile={e.is_hostile}")
        logger.info(f"  Appraisal: {e.cognitive_appraisal} | Action: {e.action_tendency}")
        logger.info(f"  Response: {b.response_text[:80]}...")
        logger.info(f"  BG Action: {b.basal_ganglia_action} | dACC Conflict: {b.dacc_conflict_score:.3f}")
        logger.info(f"  Brain areas: {[a.area + '=' + str(round(a.firing_rate_hz, 1)) + 'Hz' for a in (b.brain_region_activations or [])]}")


async def test_e2e_pipeline():
    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
    from dreamtalk.pipeline.models import PipelineRequest
    import uuid

    orch = PipelineOrchestrator()
    req = PipelineRequest(
        twin_id=f"e2e_{uuid.uuid4().hex[:8]}",
        role="normal_user",
        image_paths=[IMG_PATH],
        voice_paths=[WAV_PATH],
        text_input="Hello! I'm excited to test the full pipeline!",
        enable_3d_face=True, enable_voice_clone=True,
        enable_emotion=True, enable_decision=True,
        enable_object_detection=True, enable_super_resolution=True,
        enable_audio_enhancement=True,
        model_name="rule_based",
    )
    result = await orch.run_full_pipeline(req)
    logger.info("=== E2E PIPELINE V2 ===")
    logger.info(f"  Status: {result.status.value}")
    for s in result.steps:
        logger.info(f"  Step {s.step}: {s.name} = {s.status}")
    if result.face_result:
        logger.info(f"  FACE: detected={result.face_result.face_detected}, quality={result.face_result.quality_score:.3f}")
    if result.voice_result:
        logger.info(f"  VOICE: detected={result.voice_result.voice_detected}, clone={result.voice_result.clone_method}")
    if result.emotion_result:
        logger.info(f"  EMOTION: mood={result.emotion_result.primary_mood.value}, PAD={result.emotion_result.pad_activation}")
    if result.brain_result:
        logger.info(f"  BRAIN: {result.brain_result.response_text[:60]}...")
    if result.object_result:
        logger.info(f"  OBJECTS: count={result.object_result.object_count}")
    logger.info(f"  Errors: {result.error}")
    return result


async def main():
    generate_test_data()

    passed = 0
    failed = 0

    try:
        await test_face()
        passed += 1
    except Exception as e:
        logger.error(f"FACE FAILED: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    try:
        await test_voice()
        passed += 1
    except Exception as e:
        logger.error(f"VOICE FAILED: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    try:
        await test_brain()
        passed += 1
    except Exception as e:
        logger.error(f"BRAIN FAILED: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    try:
        await test_e2e_pipeline()
        passed += 1
    except Exception as e:
        logger.error(f"E2E FAILED: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    logger.info(f"\n{'='*50}")
    logger.info(f"RESULTS: {passed} passed, {failed} failed")
    logger.info(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
