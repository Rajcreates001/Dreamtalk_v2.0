"""Compare IndicF5 and Indic-Mio on identical input.

Objective numbers only go so far here: neither container ships a speaker
verification model, so "does this sound like KB" is measured with proxies
(pitch distribution, MFCC statistics) and the rendered audio is written out
so a person can listen and decide. The proxies are labelled as proxies.

Run:  docker exec -i dreamtalk-backend python - < tts_compare.py
"""
import json
import os
import sys
import time
import wave
import io

import httpx
import numpy as np

REF = "/app/dreamtalk/media/avatar_runtime/71d2b3f8-51eb-4435-a4ee-665f60049850/voice/reference.wav"
OUT = os.environ.get("TTS_COMPARE_OUT", "/tmp/tts_compare")
os.makedirs(OUT, exist_ok=True)

# One line per language; English is the case IndicF5 cannot do at all.
CASES = [
    ("en", "Hello, my name is KB and I am an engineer from Chennai."),
    ("hi", "नमस्ते, मेरा नाम केबी है और मैं एक इंजीनियर हूँ।"),
    ("ta", "வணக்கம், என் பெயர் கேபி, நான் ஒரு பொறியாளர்."),
]

INDICF5 = os.environ.get("INDICF5_BASE_URL", "http://indicf5:8002")
INDICMIO = os.environ.get("INDICMIO_BASE_URL", "http://indic-mio:8001")
REF_TEXT = ("Hello this is Maharaj and this is the voice which I am giving "
            "for the demo script for the voice cloning. So let's see how it goes.")


def load_wav(data: bytes):
    import soundfile as sf
    y, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
    if getattr(y, "ndim", 1) > 1:
        y = y.mean(axis=1)
    return y, sr


def features(y, sr):
    """Speaker-ish proxies. Not speaker verification - labelled as proxies."""
    import librosa
    if len(y) < sr // 4:
        return None
    f0, voiced, _ = librosa.pyin(
        y, fmin=60, fmax=400, sr=sr,
        frame_length=min(2048, len(y)),
    )
    f0v = f0[~np.isnan(f0)] if f0 is not None else np.array([])
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    return {
        "duration_s": round(len(y) / sr, 2),
        "sample_rate": sr,
        "f0_median_hz": round(float(np.median(f0v)), 1) if f0v.size else None,
        "f0_iqr_hz": round(float(np.subtract(*np.percentile(f0v, [75, 25]))), 1) if f0v.size else None,
        "voiced_frac": round(float(np.mean(~np.isnan(f0))), 3) if f0 is not None else None,
        "mfcc_mean": np.mean(mfcc, axis=1),
        "rms": round(float(np.sqrt(np.mean(y ** 2))), 4),
    }


def cos(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return round(float(a @ b / d), 4) if d else None


def call_indicf5(text, lang):
    """Field names mirror dreamtalk.voice.core.vc.indicf5_microservice."""
    files = {"ref_audio": ("reference.wav", open(REF, "rb").read(), "audio/wav")}
    data = {"gen_text": text, "ref_text": REF_TEXT, "lang": lang}
    t0 = time.time()
    r = httpx.post(f"{INDICF5}/synthesize", files=files, data=data, timeout=900)
    dt = time.time() - t0
    r.raise_for_status()
    return r.content, dt


def call_indicmio(text, lang):
    """Field names mirror backend/services/cloned_speech.py's indic-mio branch.
    Indic-Mio infers the language from the text, so no `lang` field."""
    files = {"reference_audio": ("reference.wav", open(REF, "rb").read(), "audio/wav")}
    data = {"text": text, "output_format": "wav"}
    t0 = time.time()
    r = httpx.post(f"{INDICMIO}/v1/tts/file", files=files, data=data, timeout=900)
    dt = time.time() - t0
    r.raise_for_status()
    return r.content, dt


def main():
    ref_y, ref_sr = load_wav(open(REF, "rb").read())
    ref_f = features(ref_y, ref_sr)
    print("REFERENCE (the real voice):")
    print(f"  duration {ref_f['duration_s']}s  sr {ref_f['sample_rate']}  "
          f"f0_median {ref_f['f0_median_hz']} Hz  f0_iqr {ref_f['f0_iqr_hz']}")
    print()

    results = []
    for engine, fn in (("indicf5", call_indicf5), ("indic-mio", call_indicmio)):
        for lang, text in CASES:
            row = {"engine": engine, "lang": lang}
            try:
                audio, dt = fn(text, lang)
                path = os.path.join(OUT, f"{engine}_{lang}.wav")
                with open(path, "wb") as fh:
                    fh.write(audio)
                y, sr = load_wav(audio)
                f = features(y, sr)
                row.update({
                    "ok": True,
                    "latency_s": round(dt, 1),
                    "path": path,
                    "duration_s": f["duration_s"],
                    "sample_rate": f["sample_rate"],
                    "f0_median_hz": f["f0_median_hz"],
                    "f0_iqr_hz": f["f0_iqr_hz"],
                    "rms": f["rms"],
                    "mfcc_cos_vs_ref": cos(f["mfcc_mean"], ref_f["mfcc_mean"]),
                    "f0_delta_vs_ref": (
                        round(abs(f["f0_median_hz"] - ref_f["f0_median_hz"]), 1)
                        if f["f0_median_hz"] and ref_f["f0_median_hz"] else None
                    ),
                    "rtf": round(dt / f["duration_s"], 2) if f["duration_s"] else None,
                })
            except Exception as exc:
                row.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200]})
            results.append(row)
            print(json.dumps(row, default=str))

    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("\nwrote", os.path.join(OUT, "results.json"))


if __name__ == "__main__":
    main()
