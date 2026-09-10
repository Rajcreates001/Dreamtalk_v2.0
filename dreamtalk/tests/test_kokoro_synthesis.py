"""
Test Kokoro TTS Speech Synthesis
=================================
Verifies Kokoro produces actual audible speech audio.
Uses package import with torch DLL workaround.
"""
import os, sys, pathlib

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("KMP_INIT_AT_FORK", "FALSE")

_proj = str(pathlib.Path(".").resolve())
if _proj not in sys.path:
    sys.path.insert(0, _proj)

# Import torch first to isolate the DLL error
try:
    import torch
    _ = torch.tensor([1.0])
    TORCH_OK = True
except Exception:
    TORCH_OK = False

OUTPUT_DIR = os.path.join(_proj, "pipeline_outputs", "kokoro_test")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import time, numpy as np
from dreamtalk.voice.core.tts.kokoro_engine import (
    KokoroTTSEngine, EMOTION_VOICE_MAP, VOICE_METADATA,
    QUALITY_BEST, SUPPORTED_LANGUAGES,
)

passed = 0
failed = 0
results = []

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1; s = "PASS"
    else:
        failed += 1; s = "FAIL"
    msg = f"  [{s}] {name}  {detail}"
    print(msg)
    results.append(msg)

# ── Phase 1: Init ─────────────────────────────────────────────────────
section("PHASE 1: Engine Init")
check("Torch import", TORCH_OK, "CPU mode" if not TORCH_OK else "OK")
engine = KokoroTTSEngine(device="cpu")
check("Engine init", True, "device=cpu")
voices = engine.list_voices()
check("54 voices listed", len(voices) == 54, f"got {len(voices)}")
check("af_heart metadata", bool(engine.get_voice_info("af_heart")))

# ── Phase 2: Basic Synthesis ──────────────────────────────────────────
section("PHASE 2: Text Synthesis (audible content)")
for label, text in [
    ("Short", "Hello world."),
    ("Medium", "The quick brown fox jumps over the lazy dog near the river bank."),
    ("Multi-sentence", "This is a test. Kokoro is working. The audio sounds great."),
]:
    t0 = time.time()
    chunks = engine.synthesize(text, voice="af_heart", lang_code="a", speed=1.0)
    elapsed = time.time() - t0
    ok = bool(chunks) and all(isinstance(c, np.ndarray) and len(c) > 0 for c in chunks)
    dur = sum(len(c) for c in chunks) / 24000 if ok else 0
    check(f"'{label}' output", ok, f"{len(chunks)} chunks, {dur:.2f}s in {elapsed:.1f}s")
    if ok:
        combined = np.concatenate(chunks)
        rms = float(np.sqrt(np.mean(combined ** 2)))
        check(f"  '{label}' audible content", rms > 0.001, f"RMS={rms:.6f}")

# ── Phase 3: Multiple Voices ──────────────────────────────────────────
section("PHASE 3: Multiple Voices")
for vid in ["af_heart","af_bella","af_nicole","am_adam","am_michael","bf_emma","bm_george"]:
    t0 = time.time()
    chunks = engine.synthesize("Voice quality test.", voice=vid, lang_code="a")
    elapsed = time.time() - t0
    ok = bool(chunks) and sum(len(c) for c in chunks) > 0
    dur = sum(len(c) for c in chunks) / 24000 if ok else 0
    check(f"Voice '{vid}'", ok, f"{dur:.2f}s in {elapsed:.1f}s")
    if ok:
        combined = np.concatenate(chunks)
        rms = float(np.sqrt(np.mean(combined ** 2)))
        check(f"  '{vid}' audible", rms > 0.001, f"RMS={rms:.6f}")

# ── Phase 4: Emotion Mapping ──────────────────────────────────────────
section("PHASE 4: Emotion → Voice Map")
for emo, exp in EMOTION_VOICE_MAP.items():
    got = engine.select_voice_for_emotion(emo)
    check(f"Emotion '{emo}'", got == exp, f"→ '{got}'")

# ── Phase 5: Synthesize Full ──────────────────────────────────────────
section("PHASE 5: synthesize_full()")
full = engine.synthesize_full("Full synthesis method test.", voice="af_heart")
check("synthesize_full", full is not None and len(full) > 0,
      f"{len(full)/24000:.2f}s" if full is not None else "None")
if full is not None:
    rms = float(np.sqrt(np.mean(full ** 2)))
    check("  Full audible", rms > 0.001, f"RMS={rms:.6f}")
    check("  dtype", full.dtype in (np.float32, np.float64), str(full.dtype))

# ── Phase 6: Voice Mix ────────────────────────────────────────────────
section("PHASE 6: voice_mix()")
text_mix = "Voice mixing test example."
voice_a_only = engine.synthesize_full(text_mix, voice="af_heart")
voice_b_only = engine.synthesize_full(text_mix, voice="af_bella")
mixed = engine.voice_mix(text_mix, voice_a="af_heart", voice_b="af_bella", mix_ratio=0.3)
check("voice_mix output", mixed is not None and len(mixed) > 0,
      f"{len(mixed)/24000:.2f}s" if mixed is not None else "None")
if mixed is not None and voice_a_only is not None and len(voice_a_only) > 0:
    min_len = min(len(mixed), len(voice_a_only))
    diff_from_a = float(np.abs(mixed[:min_len] - voice_a_only[:min_len]).mean())
    check("  Differs from voice A", diff_from_a > 0.001, f"mean diff={diff_from_a:.6f}")

# ── Phase 7: Language Detection ───────────────────────────────────────
section("PHASE 7: Language Detection")
for lang, text, exp in [
    ("English", "Hello.", "a"), ("Chinese", "你好。", "z"),
    ("Japanese", "こんにちは。", "j"), ("Hindi", "नमस्ते।", "h"),
]:
    got = engine.detect_language(text)
    check(lang, got == exp, f"detected '{got}'")

# ── Phase 8: Best Voice Selection ─────────────────────────────────────
section("PHASE 8: select_best_voice()")
check("Best female US", engine.select_best_voice("a",gender="female") == "af_heart")
check("Best male US", bool(engine.select_best_voice("a",gender="male")))

# ── Phase 9: Fallback ─────────────────────────────────────────────────
section("PHASE 9: Fallback & Speed")
# Invalid voice
chunks = engine.synthesize("Fallback test.", voice="nonexistent_zzz")
ok = bool(chunks) and sum(len(c) for c in chunks) > 0
dur = sum(len(c) for c in chunks) / 24000 if ok else 0
check("Invalid voice fallback", ok, f"{dur:.2f}s")
if ok:
    rms = float(np.sqrt(np.mean(np.concatenate(chunks) ** 2)))
    check("  Fallback audible", rms > 0.001, f"RMS={rms:.6f}")

# Auto language
ca = engine.synthesize("Auto language test.", voice="af_heart", lang_code="auto")
check("Auto lang detection", bool(ca) and sum(len(c) for c in ca) > 0,
      f"{sum(len(c) for c in ca)/24000:.2f}s" if ca else "None")

# Speed
for sl, sv in [("Slow 0.8",0.8), ("Normal 1.0",1.0), ("Fast 1.2",1.2)]:
    t0 = time.time()
    sc = engine.synthesize("Speed test text here.", voice="af_heart", speed=sv)
    ok = bool(sc) and sum(len(c) for c in sc) > 0
    check(f"Speed {sv}", ok, f"{sum(len(c) for c in sc)/24000:.2f}s in {time.time()-t0:.1f}s")

# ── Phase 10: Save WAV files ──────────────────────────────────────────
section("PHASE 10: Save WAV Audio")
try:
    import soundfile as sf
    HAS_SF = True
except ImportError:
    HAS_SF = False
check("soundfile available", HAS_SF)

for mood in ["neutral","happy","sad","angry","calm"]:
    voice = EMOTION_VOICE_MAP.get(mood, "af_heart")
    chunks = engine.synthesize(f"This is a {mood} sounding test.", voice=voice, lang_code="a")
    if chunks and HAS_SF:
        combined = np.concatenate(chunks)
        if combined.dtype == np.float64:
            combined = combined.astype(np.float32)
        out = os.path.join(OUTPUT_DIR, f"kokoro_{mood}.wav")
        sf.write(out, combined, 24000)
        size = os.path.getsize(out)
        rms = float(np.sqrt(np.mean(combined ** 2)))
        check(f"Save '{mood}.wav'", size > 1000 and rms > 0.001,
              f"{size:,} bytes, {len(combined)/24000:.2f}s, RMS={rms:.6f}")
        print(f"    → {out}")

# ── Phase 11: Non-English Synthesis ────────────────────────────────────
section("PHASE 11: Non-English Synthesis")
for lang_code, voice_id, label, text in [
    ("h", "hf_alpha", "Hindi", "Namaste, yeh ek parikshan hai."),
    ("b", "bf_emma", "British", "Hello, this is a British voice test."),
]:
    try:
        c = engine.synthesize(text, voice=voice_id, lang_code=lang_code)
        ok = bool(c) and sum(len(v) for v in c) > 0
        check(f"{label} synthesis", ok, f"{sum(len(v) for v in c)/24000:.2f}s" if ok else "empty")
        if ok:
            rm = float(np.sqrt(np.mean(np.concatenate(c)**2)))
            check(f"  {label} audible", rm > 0.001, f"RMS={rm:.6f}")
    except Exception as e:
        check(f"{label} synthesis", False, str(e)[:80])

# ── Summary ───────────────────────────────────────────────────────────
section("SUMMARY")
total = passed + failed
print(f"\n  Passed: {passed}/{total}   Failed: {failed}/{total}")
status = "✅ KOKORO SYNTHESIZES SPEECH" if failed == 0 else "❌ Some tests FAILED"
print(f"  {status}")
print(f"\n  Audio files: {OUTPUT_DIR}/")
