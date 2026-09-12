"""Controlled test of emotion prosody.

The earlier end-to-end emotion sweep was confounded: each emotion produced a
*different* LLM reply, so content variation (~48% pitch spread) swamped the
prosody preset (+/-0.8 semitones ~= 4.7%). This synthesizes the SAME sentence
under each emotion, so the only variable is the preset.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, "/app")

TEXT = "Main aaj yahaan aapke saath baat kar raha hoon."
LANG = "hi"
# Reference audio + its transcript come from an enrolled profile: IndicF5
# requires the transcript for reliable cloning.
REGISTRY = "/app/dreamtalk/results/avatar_runtime_profiles.json"


def _reference():
    with open(REGISTRY, encoding="utf-8") as fh:
        raw = json.load(fh)
    profiles = raw.get("profiles", raw)
    for prof in reversed(list(profiles.values())):
        v = prof.get("voice") or {}
        path, text = v.get("reference_audio_path"), (v.get("reference_text") or "").strip()
        if path and text and os.path.exists(path):
            return path, text, v.get("sample_language") or "en"
    raise SystemExit("no enrolled profile with a reference transcript")


REF, REF_TEXT, REF_LANG = _reference()
OUT = "/app/dreamtalk/e2e_deep/prosody"
os.makedirs(OUT, exist_ok=True)


def features(path):
    import librosa
    import numpy as np
    y, sr = librosa.load(path, sr=16000, mono=True)
    y, _ = librosa.effects.trim(y, top_db=30)
    f0 = librosa.yin(y, fmin=60, fmax=400, sr=sr)
    f0 = f0[np.isfinite(f0)]
    return {
        "f0": round(float(np.median(f0)), 1) if f0.size else 0.0,
        "rms": round(float(np.sqrt(np.mean(y ** 2))), 4),
        "dur": round(len(y) / sr, 2),
    }


async def main() -> int:
    from dreamtalk.backend.services.cloned_speech import (
        get_cloned_speech_service, PROSODY_PRESETS,
    )
    svc = get_cloned_speech_service()

    rows = {}
    for emo in ("neutral", "calm", "happy", "excited", "sad", "angry"):
        try:
            res = await svc.synthesize_clone(
                text=TEXT, reference_audio=REF, reference_text=REF_TEXT,
                language=LANG, emotion=emo, reference_language=REF_LANG,
            )
        except Exception as exc:
            print(f"{emo:9s} FAILED: {exc}")
            continue
        dest = os.path.join(OUT, f"{emo}.wav")
        try:
            os.replace(res.path, dest)
        except OSError:
            dest = res.path
        f = features(dest)
        rate, semi, gain = PROSODY_PRESETS[emo]
        rows[emo] = {**f, "preset_rate": rate, "preset_semitones": semi, "preset_gain": gain}
        print(f"{emo:9s} f0={f['f0']:6.1f}Hz rms={f['rms']:.4f} dur={f['dur']:5.2f}s "
              f"| preset rate={rate} semitones={semi:+.1f} gain={gain}")

    if "neutral" not in rows or len(rows) < 3:
        print("\nnot enough samples to compare")
        return 1

    base = rows["neutral"]
    print(f"\n{'emotion':9s} {'dF0 measured':>13s} {'dF0 expected':>13s} {'dRMS':>8s} {'dur ratio':>10s}")
    agree = total = 0
    for emo, r in rows.items():
        if emo == "neutral":
            continue
        # semitones -> ratio: 2**(n/12)
        exp_f0 = base["f0"] * (2 ** (r["preset_semitones"] / 12.0))
        d_meas = r["f0"] - base["f0"]
        d_exp = exp_f0 - base["f0"]
        dur_ratio = base["dur"] / r["dur"] if r["dur"] else 0
        same_dir = (d_meas >= 0) == (d_exp >= 0) or abs(d_exp) < 0.5
        agree += same_dir
        total += 1
        print(f"{emo:9s} {d_meas:+12.1f}  {d_exp:+12.1f}  "
              f"{r['rms']-base['rms']:+8.4f} {dur_ratio:10.2f}  "
              f"{'ok' if same_dir else 'OPPOSITE'}")

    print(f"\npitch direction matches preset in {agree}/{total} emotions")
    json.dump(rows, open(os.path.join(OUT, "prosody.json"), "w"), indent=1)
    return 0 if agree >= total * 0.6 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
