"""
End-to-End "Wired" Pipeline Test — Voice + Brain (Emotion + Decision)
using a real audio sample file.

Runs the PipelineOrchestrator with:
  - Real audio: local_upload_testing/Voice_local/sample1.wav (48kHz, stereo, 11.4s)
  - Real text for emotion detection + brain decision
  - Verifies voice feature extraction, cloning, TTS, and brain response

Usage:
    python tests/test_wired_pipeline_e2e.py
"""

import asyncio
import json
import logging
import os
import sys
import uuid

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)
logger = logging.getLogger("test_wired_e2e")

# ── Real audio sample ───────────────────────────────────────────────────
REAL_AUDIO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "local_upload_testing", "Voice_local", "sample1.wav",
)

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "pipeline_outputs", "wired_e2e_test",
)

TEST_TEXTS = [
    "Hello! I'm so happy to be talking with you today. This is a great day!",
    "I'm feeling really frustrated with this problem. It keeps failing and I don't know why.",
    "I have a terrible headache and feel really sick. Can you help me feel better?",
]

TEST_ROLES = ["normal_user", "business", "healthcare"]

# ── Test tracking ───────────────────────────────────────────────────────
passed = 0
failed = 0
results = []


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        logger.info(f"  ✅ {name}")
    else:
        failed += 1
        logger.error(f"  ❌ {name} — {detail}")


def section(title: str):
    logger.info(f"\n{'=' * 60}")
    logger.info(f"  {title}")
    logger.info(f"{'=' * 60}")


async def main():
    global passed, failed

    # ── Phase 1: Verify real audio file ──────────────────────────────────
    section("PHASE 1: Verify Real Audio Sample")
    check("Audio file exists", os.path.exists(REAL_AUDIO_PATH),
          f"Not found at {REAL_AUDIO_PATH}")

    if os.path.exists(REAL_AUDIO_PATH):
        import soundfile as sf
        data, sr = sf.read(REAL_AUDIO_PATH)
        check(f"Sample rate = {sr}Hz (expect 48000)", sr == 48000,
              f"Got {sr}Hz")
        check(f"Channels = {data.ndim if data.ndim > 1 else 1}",
              data.ndim > 1 or (data.ndim == 1 and len(data) > 0))
        check(f"Duration = {len(data)/sr:.2f}s (>= 5s)", len(data) / sr >= 5.0,
              f"Only {len(data)/sr:.2f}s")
        check("Audio has energy (RMS > 0.01)", np.sqrt((data**2).mean()) > 0.01,
              "Audio appears silent")
        logger.info(f"  Audio file size: {os.path.getsize(REAL_AUDIO_PATH)} bytes")

    # ── Phase 2: Import the wired orchestrator ──────────────────────────
    section("PHASE 2: Import Orchestrator")
    try:
        from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
        from dreamtalk.pipeline.models import PipelineRequest
        check("PipelineOrchestrator import", True)
        check("PipelineRequest import", True)
    except Exception as e:
        check(f"Import failed: {e}", False)
        failed += 1
        return

    # ── Phase 3: Initialize orchestrator ─────────────────────────────────
    section("PHASE 3: Initialize Orchestrator")
    try:
        orchestrator = PipelineOrchestrator()
        check("Orchestrator instantiated", True)
        check("Face pipeline loaded", orchestrator.face_pipeline is not None)
        check("Voice pipeline loaded", orchestrator.voice_pipeline is not None)
        check("Brain pipeline loaded", orchestrator.brain_pipeline is not None)
    except Exception as e:
        check(f"Orchestrator init failed: {e}", False)
        failed += 1
        return

    # ── Phase 4: Run voice analysis only through orchestrator ────────────
    section("PHASE 4: Voice Pipeline through Orchestrator (Real Audio)")
    try:
        voice_result = await orchestrator.run_voice_only(
            PipelineRequest(
                twin_id=f"test_wired_{uuid.uuid4().hex[:8]}",
                voice_paths=[REAL_AUDIO_PATH],
                text_input=TEST_TEXTS[0],
            )
        )
        check("Voice pipeline completed without error",
              voice_result.error is None,
              f"Error: {voice_result.error}")

        if voice_result.error is None:
            check("Voice detected", voice_result.voice_detected,
                  f"VAD ratio: {voice_result.voice_activity_ratio:.3f}")
            check(f"Duration = {voice_result.duration_seconds:.2f}s (> 5s)",
                  voice_result.duration_seconds > 5.0,
                  f"Only {voice_result.duration_seconds:.2f}s")
            check(f"Sample rate = {voice_result.sample_rate}", 
                  voice_result.sample_rate > 0)
            check(f"Pitch mean = {voice_result.pitch_mean:.1f}Hz",
                  voice_result.pitch_mean > 50,
                  f"Suspiciously low pitch: {voice_result.pitch_mean:.1f}")
            check(f"Pitch std = {voice_result.pitch_std:.1f}Hz",
                  voice_result.pitch_std > 0)
            check(f"Energy mean = {voice_result.energy_mean:.6f}",
                  voice_result.energy_mean > 0)
            check(f"Spectral centroid = {voice_result.spectral_centroid_mean:.1f}Hz",
                  voice_result.spectral_centroid_mean > 100)
            check(f"MFCCs mean computed ({len(voice_result.mfccs_mean) if voice_result.mfccs_mean else 0} dims)",
                  voice_result.mfccs_mean is not None and len(voice_result.mfccs_mean) > 0)
            check(f"Speaking rate = {voice_result.speaking_rate:.2f}",
                  voice_result.speaking_rate > 0)
            check(f"Voice embedding ({voice_result.embedding_dim} dims)",
                  len(voice_result.voice_embedding) == 256,
                  f"Got {len(voice_result.voice_embedding)} dims")

            # Optional: clone and TTS
            if voice_result.cloned_voice_path:
                check(f"Voice cloned via {voice_result.clone_method}",
                      os.path.exists(voice_result.cloned_voice_path),
                      f"Clone file missing: {voice_result.cloned_voice_path}")
                check(f"Clone confidence = {voice_result.clone_confidence:.2f}",
                      voice_result.clone_confidence > 0)
            else:
                logger.info("  ⚠ Voice cloning skipped (no method available)")

            if voice_result.tts_sample_path:
                check(f"TTS generated via {voice_result.tts_method}",
                      os.path.exists(voice_result.tts_sample_path),
                      f"TTS file missing: {voice_result.tts_sample_path}")
                check(f"TTS duration = {voice_result.tts_duration_seconds:.2f}s",
                      voice_result.tts_duration_seconds > 0.5)
            else:
                logger.info("  ⚠ TTS skipped (no TTS engine available)")

            # Print key voice metrics
            logger.info(f"\n  ── Key Voice Metrics ──")
            logger.info(f"  Gender: {voice_result.gender_prediction}")
            logger.info(f"  Age est: {voice_result.age_prediction}")
            logger.info(f"  Pitch: mean={voice_result.pitch_mean:.0f}Hz "
                        f"median={voice_result.pitch_median:.0f}Hz "
                        f"std={voice_result.pitch_std:.0f}Hz")
            logger.info(f"  Formants: {voice_result.formant_frequencies}")
            logger.info(f"  Jitter: {voice_result.jitter_local:.3f}%")
            logger.info(f"  Shimmer: {voice_result.shimmer_local:.3f}%")
            logger.info(f"  HNR: {voice_result.harmonicity_hnr:.1f}dB")
            logger.info(f"  Words/min: {voice_result.words_per_minute}")
            logger.info(f"  SNR: {voice_result.snr_estimate:.1f}dB")

    except Exception as e:
        check(f"Voice pipeline crashed: {e}", False)
        failed += 1

    # ── Phase 5: Brain emotion + decision pipeline ───────────────────────
    section("PHASE 5: Brain Pipeline (Emotion + Decision)")
    try:
        brain_result = await orchestrator.run_decision_only(
            PipelineRequest(
                text_input=TEST_TEXTS[0],
                role="normal_user",
                enable_emotion=True,
                enable_decision=True,
                model_name="rule_based",
            )
        )
        check("Brain pipeline completed without crash", brain_result is not None)

        if brain_result:
            emotion = brain_result.get("emotion")
            decision = brain_result.get("brain")
            if emotion:
                logger.info(f"  Primary mood: {emotion.primary_mood.value}")
                check(f"Valence = {emotion.valence:.3f}",
                      -1.0 <= emotion.valence <= 1.0)
                check(f"Arousal = {emotion.arousal:.3f}",
                      0.0 <= emotion.arousal <= 1.0)
                check(f"Intensity = {emotion.intensity}",
                      emotion.intensity in ("low", "medium", "high"))
                check(f"Confidence = {emotion.confidence:.3f}",
                      emotion.confidence > 0)
                check(f"Scores set",
                      emotion.mood_confidences is not None)
                logger.info(f"  Mood confidences: {emotion.mood_confidences}")

            if decision:
                check(f"Response text generated (len={len(decision.response_text)})",
                      len(decision.response_text) > 0)
                check(f"Confidence = {decision.confidence:.3f}",
                      decision.confidence > 0)
                check(f"Decision type = {decision.decision_type}",
                      bool(decision.decision_type))
                check(f"Processing time = {decision.processing_time_ms:.1f}ms",
                      decision.processing_time_ms > 0)
                logger.info(f"  Response: {decision.response_text[:100]}...")
    except Exception as e:
        check(f"Brain pipeline crashed: {e}", False)
        failed += 1

    # ── Phase 6: Multi-text brain analysis with emotion variation ────────
    section("PHASE 6: Brain Emotion Variation Across Texts")
    emotions = []
    for i, (text, role) in enumerate(zip(TEST_TEXTS, TEST_ROLES)):
        try:
            result = await orchestrator.run_decision_only(
                PipelineRequest(
                    text_input=text,
                    role=role,
                    enable_emotion=True,
                    enable_decision=True,
                    model_name="rule_based",
                )
            )
            emotion = result.get("emotion")
            decision = result.get("brain")
            if emotion and decision:
                emotions.append({
                    "text": text[:40],
                    "role": role,
                    "mood": emotion.primary_mood.value,
                    "valence": round(emotion.valence, 3),
                    "arousal": round(emotion.arousal, 3),
                    "intensity": emotion.intensity,
                    "hostile": emotion.is_hostile,
                    "hostility": round(emotion.hostility_score, 3),
                    "response": decision.response_text[:60],
                })
                logger.info(f"  [{i+1}] role={role}, mood={emotion.primary_mood.value}, "
                            f"V={emotion.valence:.2f}, A={emotion.arousal:.2f}, "
                            f"I={emotion.intensity}, hostile={emotion.is_hostile}")
        except Exception as e:
            logger.warning(f"  [{i+1}] Failed: {e}")

    check(f"All {len(TEST_TEXTS)} texts analyzed",
          len(emotions) == len(TEST_TEXTS),
          f"Only {len(emotions)}/{len(TEST_TEXTS)} completed")

    # Verify emotion differentiation
    if len(emotions) >= 2:
        valences = [e["valence"] for e in emotions]
        moods = [e["mood"] for e in emotions]
        unique_moods = len(set(moods))
        valence_range = max(valences) - min(valences)
        check(f"Emotion differentiation: {unique_moods} unique moods, "
              f"valence range={valence_range:.2f}",
              unique_moods > 1 or valence_range > 0.1,
              "All texts produced same emotion — model may not be differentiating")
        # Happy text should have higher valence than frustrated/sick
        check("Happy text valence > frustrated valence",
              emotions[0]["valence"] > emotions[1]["valence"],
              f"Happy={emotions[0]['valence']:.3f} <= Frustrated={emotions[1]['valence']:.3f}")

    # ── Phase 7: Full pipeline end-to-end ────────────────────────────────
    section("PHASE 7: End-to-End Wired Pipeline (Voice + Brain)")
    try:
        full_result = await orchestrator.run_full_pipeline(
            PipelineRequest(
                twin_id=f"test_wired_full_{uuid.uuid4().hex[:8]}",
                voice_paths=[REAL_AUDIO_PATH],
                text_input=TEST_TEXTS[0],
                role="normal_user",
                enable_3d_face=False,       # skip face (no image)
                enable_voice_clone=True,
                enable_emotion=True,
                enable_decision=True,
                enable_object_detection=False,
                model_name="rule_based",
            )
        )
        check("Full pipeline completed", full_result.status.value in ("completed", "partial"),
              f"Status: {full_result.status.value} — Error: {full_result.error}")
        check(f"Steps: {len(full_result.steps)} total, "
              f"{len([s for s in full_result.steps if s.status == 'completed'])} completed",
              len(full_result.steps) > 0)

        # Summarize all steps
        logger.info(f"\n  ── Pipeline Step Summary ──")
        for step in full_result.steps:
            status_icon = "✅" if step.status == "completed" else "❌"
            logger.info(f"  {status_icon} Step {step.step}: {step.name} — {step.status}")
            if step.data:
                for k, v in step.data.items():
                    logger.info(f"      {k}: {v}")
            if step.error:
                logger.info(f"      Error: {step.error}")

        # Check specific results
        if full_result.voice_result:
            check("Voice result present", True)
        if full_result.emotion_result:
            check("Emotion result present", True)
        if full_result.brain_result:
            check("Brain result present", True)

        logger.info(f"\n  Pipeline ID: {full_result.pipeline_id}")

    except Exception as e:
        check(f"Full pipeline crashed: {e}", False)
        failed += 1

    # ── Summary ──────────────────────────────────────────────────────────
    section("SUMMARY")
    total = passed + failed
    logger.info(f"  Total checks: {total}")
    logger.info(f"  ✅ Passed: {passed}")
    logger.info(f"  ❌ Failed: {failed}")

    if failed == 0:
        logger.info("\n  🎉 ALL END-TO-END PIPELINE TESTS PASSED!")
    else:
        logger.info(f"\n  ⚠ {failed}/{total} checks failed")

    # Save results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result_summary = {
        "passed": passed,
        "failed": failed,
        "total": total,
        "audio_file": REAL_AUDIO_PATH,
        "test_texts": TEST_TEXTS,
    }
    summary_path = os.path.join(OUTPUT_DIR, "wired_e2e_results.json")
    with open(summary_path, "w") as f:
        json.dump(result_summary, f, indent=2)
    logger.info(f"\nResults saved to: {summary_path}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
