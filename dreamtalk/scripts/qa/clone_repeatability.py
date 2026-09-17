"""Synthesize the same sentence several times and score every take.

Two avatars built from the same recording scored differently on the same
languages - Kashmiri came back at 0.9054 on one and 0.7271 on the other - and
there are two candidate explanations that lead to opposite conclusions:

  the enrolment transcript differs between them, and a prompt that matches its
  audio clones better

  or Indic-Mio samples, and one take is not a measurement

A single number cannot tell those apart. Repeating the synthesis can: if the
spread within one profile covers the gap between the profiles, the gap was
never evidence of anything.

  docker exec -i dreamtalk-backend python - < clone_repeatability.py \
      --profiles <id> <id> --languages ks sat hi --repeats 3
"""
from __future__ import annotations

import argparse
import io
import json
import statistics
import sys
import time

import httpx
import numpy as np
import torch

sys.path.insert(0, "/app/dreamtalk/scripts/qa")
from speaker_similarity import (  # noqa: E402
    Encoder, SAME_SPEAKER_THRESHOLD, cosine, load_16k, pick_impostor,
)
from e2e_avatar import API, token  # noqa: E402
from verify_22_languages import TEXTS  # noqa: E402

RUNTIME = "/app/dreamtalk/media/avatar_runtime"


def synthesize(client, profile: str, language: str) -> bytes:
    response = client.post("/api/v1/avatar/tts/generate", json={
        "profile_id": profile, "text": TEXTS[language], "language": language,
        "strict_clone": True, "emotion": "neutral"})
    response.raise_for_status()
    payload = response.json()
    if not payload.get("cloned"):
        raise RuntimeError("not cloned: engine=%s reason=%s"
                           % (payload.get("engine"),
                              payload.get("fallback_reason")))
    media = client.get(payload["audio_url"])
    media.raise_for_status()
    return media.content


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profiles", nargs="+", required=True)
    ap.add_argument("--languages", nargs="+", default=["ks", "sat", "hi"])
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    encoder = Encoder("cpu")
    impostor_path, _ = pick_impostor(args.profiles[0],
                                     "%s/%s/voice/reference.wav"
                                     % (RUNTIME, args.profiles[0]))
    control = None
    if impostor_path:
        first_ref = encoder.embed(load_16k(
            "%s/%s/voice/reference.wav" % (RUNTIME, args.profiles[0])))
        control = cosine(first_ref, encoder.embed(load_16k(impostor_path)))
        print("impostor control: %.4f" % control)
    print("same-speaker threshold: %.2f\n" % SAME_SPEAKER_THRESHOLD)

    results = {}
    with httpx.Client(base_url=API.removesuffix("/api/v1"), timeout=300) as client:
        client.headers["Authorization"] = "Bearer " + token()
        for profile in args.profiles:
            ref = encoder.embed(load_16k("%s/%s/voice/reference.wav"
                                         % (RUNTIME, profile)))
            for language in args.languages:
                takes = []
                for index in range(args.repeats):
                    started = time.monotonic()
                    try:
                        raw = synthesize(client, profile, language)
                    except Exception as exc:
                        print("  %s %s take %d FAILED: %s"
                              % (profile[:8], language, index + 1, str(exc)[:160]))
                        continue
                    import soundfile as sf
                    audio, rate = sf.read(io.BytesIO(raw), always_2d=True)
                    audio = audio.mean(axis=1).astype(np.float32)
                    if rate != 16000:
                        import librosa
                        audio = librosa.resample(audio, orig_sr=rate,
                                                 target_sr=16000)
                    peak = float(np.abs(audio).max())
                    if peak > 0:
                        audio = audio / peak
                    score = cosine(ref, encoder.embed(audio))
                    takes.append(score)
                    print("  %s %-4s take %d: %.4f  (%.1fs audio, %.1fs wall)"
                          % (profile[:8], language, index + 1, score,
                             len(audio) / 16000, time.monotonic() - started),
                          flush=True)
                if takes:
                    results[(profile, language)] = takes

    print("\n" + "=" * 70)
    print("%-10s %-5s %7s %7s %7s %7s  %s"
          % ("profile", "lang", "min", "mean", "max", "spread", "verdict"))
    print("-" * 70)
    for (profile, language), takes in results.items():
        spread = max(takes) - min(takes)
        mean = statistics.fmean(takes)
        verdict = ("all above" if min(takes) >= SAME_SPEAKER_THRESHOLD
                   else "all below" if max(takes) < SAME_SPEAKER_THRESHOLD
                   else "STRADDLES the threshold")
        print("%-10s %-5s %7.4f %7.4f %7.4f %7.4f  %s"
              % (profile[:8], language, min(takes), mean, max(takes),
                 spread, verdict))

    spreads = [max(t) - min(t) for t in results.values()]
    if spreads:
        print("\nlargest within-profile spread across repeats: %.4f" % max(spreads))
        print("If that covers the gap between profiles, the gap is sampling "
              "noise and not a property of either avatar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
