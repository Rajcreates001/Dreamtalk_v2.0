"""Verify the two test fixes: PAD inertia numpy import + LearningOrchestrator import."""
import os, sys, pathlib
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
_proj = str(pathlib.Path(__file__).resolve().parent.parent)
if _proj not in sys.path:
    sys.path.insert(0, _proj)

print("=== TEST 1: PAD Inertia (fixed numpy import) ===")
from dreamtalk.emotion.core.pad_model import PADEmotionEngine
import numpy as np
engine = PADEmotionEngine(inertia=0.85)
engine.update((-0.9, 1.0, 0.8))
state1 = engine.get_current_emotion()
engine.update((0.9, 0.9, 0.8))
state2 = engine.get_current_emotion()
p1 = np.array(state1["pad"])
p2 = np.array(state2["pad"])
has_inertia = state2["pad"][0] < 0.5
print(f"  After rage: {state1['name']} PAD=({state1['pad'][0]:+.2f},{state1['pad'][1]:+.2f},{state1['pad'][2]:+.2f})")
print(f"  After ecstasy: {state2['name']} PAD=({state2['pad'][0]:+.2f},{state2['pad'][1]:+.2f},{state2['pad'][2]:+.2f})")
print(f"  Distance: {np.linalg.norm(p1-p2):.3f}")
print(f"  PASS: {has_inertia}")
assert has_inertia, "PAD inertia test failed!"
print()

print("=== TEST 2: Learning Signals (fixed import) ===")
from dreamtalk.digital_twin.learning_orchestrator import LearningOrchestrator as LO
print("  LearningOrchestrator imported: OK")
conversations = [
    ("Fact extraction", "My name is John and I work as a software engineer."),
    ("Preference extraction", "I love Italian food. I prefer dark mode."),
    ("Correction detection", "Actually, that is not right. I think you meant the other one."),
    ("Emotion signals", "I am feeling really stressed about work."),
]
for label, text in conversations:
    facts = LO._extract_facts(text)
    prefs = LO._extract_preferences(text)
    corrs = LO._extract_corrections(text)
    emot = LO._extract_emotional_signals(text)
    print(f"  {label:22s}: {len(facts)} facts, {len(prefs)} prefs, {len(corrs)} corrs, {len(emot)} emotions")
print()
print("ALL TESTS PASSED")
