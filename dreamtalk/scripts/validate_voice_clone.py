"""
Voice Clone Validation Script
==============================
Compares original voice sample vs clone vs TTS outputs
to determine if voice cloning actually preserved speaker identity.
"""
import numpy as np
import soundfile as sf
import os, sys

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "..", "local_upload_testing", "Voice_local", "sample1.wav")

# Find the clone file
clone_files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("voice_clone_") and f.endswith(".wav")]
clone_path = os.path.join(RESULTS_DIR, sorted(clone_files)[-1]) if clone_files else None

tts_files = {
    "TTS Tamil": os.path.join(RESULTS_DIR, "cloned_voice_tamil.wav"),
    "TTS Hindi": os.path.join(RESULTS_DIR, "cloned_voice_hindi.wav"),
    "TTS Telugu": os.path.join(RESULTS_DIR, "cloned_voice_telugu.wav"),
    "TTS Kannada": os.path.join(RESULTS_DIR, "cloned_voice_kannada.wav"),
    "TTS Malayalam": os.path.join(RESULTS_DIR, "cloned_voice_malayalam.wav"),
}

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 65)
print("  VOICE CLONE VALIDATION REPORT")
print("=" * 65)

# --- Basic stats ---
print("\n== BASIC AUDIO STATS ==")
print("-" * 55)
print(f"{'File':25s} {'Dur':>7s} {'SR':>6s} {'Ch':>3s} {'RMS':>8s}")
print("-" * 55)

orig, sr_o = sf.read(SAMPLE_PATH)
if orig.ndim > 1:
    orig = np.mean(orig, axis=1)
dur_o = len(orig) / sr_o
rms_o = np.sqrt(np.mean(orig ** 2))
print(f"{'ORIGINAL SAMPLE':25s} {dur_o:6.2f}s {sr_o:5d} {1:3d} {rms_o:.4f}")

if clone_path:
    clone, sr_c = sf.read(clone_path)
    if clone.ndim > 1:
        clone = np.mean(clone, axis=1)
    dur_c = len(clone) / sr_c
    rms_c = np.sqrt(np.mean(clone ** 2))
    print(f"{'CLONE (structural)':25s} {dur_c:6.2f}s {sr_c:5d} {1:3d} {rms_c:.4f}")

samples = {"Original": (orig, sr_o)}
if clone_path:
    samples["Clone"] = (clone, sr_c)
for label, path in tts_files.items():
    if os.path.exists(path):
        d, s = sf.read(path)
        if d.ndim > 1:
            d = np.mean(d, axis=1)
        dur = len(d) / s
        rms = np.sqrt(np.mean(d ** 2))
        samples[label] = (d, s)
        print(f"{label:25s} {dur:6.2f}s {s:5d} {1:3d} {rms:.4f}")

# --- Spectral comparison ---
print("\n== SPEAKER SIMILARITY (Spectral Analysis) ==")
print("-" * 55)

def avg_spectrum(audio, sr, nfft=2048):
    n = min(len(audio), sr * 3)
    audio = audio[:n]
    if len(audio) < nfft:
        audio = np.pad(audio, (0, nfft - len(audio)))
    window = np.hanning(nfft)
    seg = audio[:nfft] * window
    spec = np.abs(np.fft.rfft(seg))
    return spec / (np.sum(spec) + 1e-10)

def simple_pitch(audio, sr):
    audio = audio - np.mean(audio)
    n = len(audio)
    min_lag = int(sr / 400)
    max_lag = int(sr / 60)
    if n <= max_lag:
        return 0
    corr = np.correlate(audio, audio, mode="full")
    center = len(corr) // 2
    lags = corr[center + min_lag : center + max_lag + 1]
    if len(lags) == 0:
        return 0
    peak_idx = np.argmax(lags) + min_lag
    return sr / peak_idx

specs = {}
pitches = {}
for name, (d, s) in samples.items():
    specs[name] = avg_spectrum(d, s)
    pitches[name] = simple_pitch(d, s)

# Compare all pairs to the ORIGINAL
print(f"{'Comparison':30s} {'Spectral Sim':>12s} {'Pitch(Hz)':>9s}")
print("-" * 55)
print(f"{'ORIGINAL vs itself':30s} {'1.0000':>12s} {pitches.get('Original',0):8.0f}")

for name in samples:
    if name == "Original":
        continue
    cos = np.dot(specs["Original"], specs[name]) / (
        np.linalg.norm(specs["Original"]) * np.linalg.norm(specs[name]) + 1e-10
    )
    print(f"{'Original vs ' + name:30s} {cos:12.4f} {pitches.get(name,0):8.0f}")

# Show clone vs TTS too
if "Clone" in samples:
    for name in samples:
        if name in ("Original", "Clone"):
            continue
        cos = np.dot(specs["Clone"], specs[name]) / (
            np.linalg.norm(specs["Clone"]) * np.linalg.norm(specs[name]) + 1e-10
        )
        print(f"{'Clone vs ' + name:30s} {cos:12.4f}")

# --- MANIFEST ---
manifest_path = os.path.join(RESULTS_DIR, "manifest.json")
if os.path.exists(manifest_path):
    import json
    with open(manifest_path) as f:
        m = json.load(f)
    print("\n== MANIFEST SUMMARY ==")
    print("-" * 55)
    print(f"  Clone method:  {m.get('clone_method', 'N/A')}")
    print(f"  Source gender: {m.get('source_gender', 'N/A')}")
    print(f"  Source pitch:  {m.get('source_pitch_hz', 'N/A')} Hz")
    print(f"  Languages:")
    for lang, info in m.get("languages", {}).items():
        print(f"    {lang:12s} → {info.get('method', 'N/A')}")

# --- VERDICT ---
print("\n== VERDICT ==")
print("-" * 55)
cos_orig_clone = np.dot(specs["Original"], specs.get("Clone", specs["Original"])) / (
    np.linalg.norm(specs["Original"]) * np.linalg.norm(specs.get("Clone", specs["Original"])) + 1e-10
) if "Clone" in samples else 0
cos_orig_tts = np.dot(specs["Original"], specs.get("TTS Tamil", specs["Original"])) / (
    np.linalg.norm(specs["Original"]) * np.linalg.norm(specs.get("TTS Tamil", specs["Original"])) + 1e-10
) if "TTS Tamil" in samples else 0

print(f"  Original vs Clone spectral similarity: {cos_orig_clone:.4f}")
print(f"  Original vs TTS spectral similarity:   {cos_orig_tts:.4f}")
print()

if cos_orig_clone > 0.5:
    print("  [PASS] CLONE: Voice characteristics appear preserved")
else:
    print("  [FAIL] CLONE: Voice characteristics NOT preserved (structural=fallback = just denoised copy)")

if cos_orig_tts < 0.3:
    print("  [FAIL] TTS: Edge-TTS pre-built voices are COMPLETELY DIFFERENT from the source")
    print("     The output files use Microsoft Azure neural voices")
    print("     (ValluvarNeural, MadhurNeural, etc.) — NOT the cloned voice.")
    print()
    print("  WHY: The script fallback chain is:")
    print("    1. IndicF5 (voice-cloned multi-language TTS) — ❌ Windows DLL conflict")
    print("    2. RVC (voice conversion)")
    print("    3. OpenVoice (tone color cloning)")
    print("    4. Edge-TTS with gender-matched male voice — ✅ FALLBACK USED")
    print()
    print("  FIX: Use Docker (Linux) to run IndicF5 without Windows DLL conflicts")
else:
    print("  [PASS] TTS: Voice identity may be preserved in TTS outputs")

print()
print("=" * 65)
