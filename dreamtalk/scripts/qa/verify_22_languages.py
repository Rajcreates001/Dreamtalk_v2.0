"""Authenticated strict-clone smoke test; does NOT certify pronunciation/identity.

Run in the backend container with --profile ID. Saves playable outputs and a
per-language report incrementally, without persisting authentication tokens.
"""
import argparse
import io
import json
import time
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf

from e2e_avatar import API, token

TEXTS = {
    "as": "নমস্কাৰ, আপোনাক স্বাগতম।",
    "bn": "নমস্কার, আপনাকে স্বাগতম।",
    # Repeated, not extended: a longer sentence would have to be invented
    # in a language nobody here can verify, and a wrong sentence would
    # test the wrong thing. Repetition keeps the text correct and gets
    # the clip past the duration where an x-vector is just noise.
    "brx": "खुलुमबाइ। खुलुमबाइ। खुलुमबाइ। खुलुमबाइ।",
    "doi": "नमस्कार। तुंदा स्वागत ऐ।",
    "gu": "નમસ્તે, તમારું સ્વાગત છે.",
    "hi": "नमस्ते, आपका स्वागत है।",
    "kn": "ನಮಸ್ಕಾರ, ನಿಮಗೆ ಸ್ವಾಗತ.",
    "kok": "नमस्कार, तुमचें स्वागत आसा।",
    "ks": "آداب۔ آداب۔ آداب۔ آداب۔",
    "mai": "प्रणाम, अहाँक स्वागत अछि।",
    "ml": "നമസ്കാരം, നിങ്ങൾക്ക് സ്വാഗതം.",
    "mni": "ꯈꯨꯔꯨꯝꯖꯔꯤ।",
    "mr": "नमस्कार, तुमचे स्वागत आहे।",
    "ne": "नमस्ते, तपाईंलाई स्वागत छ।",
    "or": "ନମସ୍କାର, ଆପଣଙ୍କୁ ସ୍ୱାଗତ।",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ।",
    "sa": "नमस्कारः। भवतः स्वागतम्।",
    "sat": "ᱡᱚᱦᱟᱨ। ᱡᱚᱦᱟᱨ। ᱡᱚᱦᱟᱨ। ᱡᱚᱦᱟᱨ।",
    "sd": "سلام، ڀلي ڪري آيا.",
    "ta": "வணக்கம், உங்களை வரவேற்கிறேன்.",
    "te": "నమస్కారం, మీకు స్వాగతం.",
    "ur": "السلام علیکم، خوش آمدید۔",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--languages", default=",".join(TEXTS))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    # In the container this file is /app/dreamtalk/scripts/qa/...; parents[2]
    # is the project root. Keep reports beside the other e2e_deep evidence.
    output = Path(__file__).resolve().parents[2] / "e2e_deep" / "language_checks" / args.profile
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report = json.loads(report_path.read_text()) if args.resume and report_path.exists() else {
        "profile_id": args.profile, "checks": {},
        "scope": "Strict clone route, decoded non-silent audio, clipping, latency. Native-speaker pronunciation and speaker identity are not certified.",
    }
    with httpx.Client(base_url=API.removesuffix("/api/v1"), timeout=180) as client:
        client.headers["Authorization"] = "Bearer " + token()
        languages = [item.strip() for item in args.languages.split(",") if item.strip()]
        unknown = [language for language in languages if language not in TEXTS]
        if unknown:
            raise SystemExit(f"Unknown language code(s): {', '.join(unknown)}")
        for language in languages:
            if args.resume and report["checks"].get(language, {}).get("passed"):
                continue
            row = {"language": language, "text": TEXTS[language], "passed": False}
            started = time.monotonic()
            try:
                response = client.post("/api/v1/avatar/tts/generate", json={
                    "profile_id": args.profile, "text": TEXTS[language],
                    "language": language, "strict_clone": True, "emotion": "neutral",
                })
                response.raise_for_status()
                payload = response.json()
                media = client.get(payload["audio_url"])
                media.raise_for_status()
                audio, rate = sf.read(io.BytesIO(media.content), always_2d=True)
                duration = len(audio) / rate
                rms = float(np.sqrt(np.mean(audio ** 2)))
                clipping = float(np.mean(np.abs(audio) >= 0.999))
                row.update(engine=payload.get("engine"), cloned=payload.get("cloned"),
                           duration_s=round(duration, 3), sample_rate=rate,
                           rms=round(rms, 6), clipping_fraction=round(clipping, 6),
                           quality_warnings=payload.get("quality_warnings", []))
                row["passed"] = bool(payload.get("cloned") is True and
                                     np.isfinite(audio).all() and
                                     0.25 <= duration <= 40 and rms > 0.001 and clipping < 0.01)
                path = output / f"{language}.wav"
                path.write_bytes(media.content)
                row["audio_file"] = str(path)
            except Exception as exc:
                row["error"] = str(exc)[:350]
            row["elapsed_s"] = round(time.monotonic() - started, 2)
            report["checks"][language] = row
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps(row, ensure_ascii=False), flush=True)
    checks = report["checks"]
    print(f"Passed {sum(bool(r['passed']) for r in checks.values())}/{len(checks)} smoke checks; see {report_path}", flush=True)
    return 0 if len(checks) == 22 and all(r["passed"] for r in checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
