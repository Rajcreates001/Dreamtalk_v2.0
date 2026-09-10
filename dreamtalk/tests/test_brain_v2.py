"""Test the expanded brain pipeline v2."""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def test():
    from dreamtalk.pipeline.brain_pipeline import BrainPipeline

    bp = BrainPipeline()
    r = await bp.run(
        text_input="I am so happy and grateful today! Everything is going wonderfully!",
        role="normal_user",
        enable_emotion=True,
        enable_decision=True,
    )

    e = r.get("emotion")
    b = r.get("brain")

    print("=== EMOTION ===")
    print(f"  Primary: {e.primary_mood.value} | Valence: {e.valence:.3f} | Arousal: {e.arousal:.3f}")
    print(f"  PAD Activation: {e.pad_activation} | Appraisal: {e.cognitive_appraisal}")
    print(f"  Action Tendency: {e.action_tendency}")
    print(f"  EMA Valence: {e.ema_valence:.3f} | Trend: {e.valence_trend}")
    print(f"  Insula: {e.brain_insula_activation:.3f} | Amygdala: {e.brain_amgydala_activation:.3f}")

    print("=== BRAIN DECISION ===")
    print(f"  Response: {b.response_text[:120]}...")
    print(f"  Strategy: {b.response_strategy} | Confidence: {b.confidence:.3f}")
    print(f"  Time: {b.processing_time_ms:.1f}ms")
    print(f"  BG Action: {b.basal_ganglia_action} | Value: {b.basal_ganglia_action_value:.3f}")
    print(f"  Brain Regions:")
    for area in b.brain_region_activations or []:
        print(f"    {area.area}: firing={area.firing_rate_hz}Hz, mem={area.membrane_potential:.3f}, DA={area.dopamine_modulation:.3f}")
    print(f"  Spiking: rate={b.spiking_activity.total_firing_rate_hz}Hz, sync={b.spiking_activity.network_synchrony:.3f}")
    print(f"  Encoding: {b.encoding_method}, timesteps={b.encoding_parameters.get('timesteps')}")
    print(f"  dACC conflict: {b.dacc_conflict_score:.4f}")
    print(f"  Insula valence: {b.insula_emotional_valence:.4f}")

    # Test hostile input
    print("\n=== HOSTILE INPUT TEST ===")
    r2 = await bp.run(
        text_input="I hate this stupid thing! It's so frustrating and awful!",
        role="normal_user",
        enable_emotion=True,
        enable_decision=True,
    )
    e2 = r2.get("emotion")
    b2 = r2.get("brain")
    print(f"  Mood: {e2.primary_mood.value} | Hostile: {e2.is_hostile} | Score: {e2.hostility_score:.3f}")
    print(f"  Triggers: {e2.hostility_triggers}")
    print(f"  Response: {b2.response_text[:100]}...")
    print(f"  Tone: {b2.response_tone}")

    # Test healthcare role
    print("\n=== HEALTHCARE TEST ===")
    r3 = await bp.run(
        text_input="I have a terrible headache and feel really sick.",
        role="healthcare",
        enable_emotion=True,
        enable_decision=True,
    )
    e3 = r3.get("emotion")
    b3 = r3.get("brain")
    print(f"  Mood: {e3.primary_mood.value} | Conf: {e3.confidence:.3f}")
    print(f"  Response: {b3.response_text[:100]}...")

    print("\n=== ALL BRAIN V2 TESTS PASSED ===")


asyncio.run(test())
