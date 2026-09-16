"""Does the synthesised speech actually sound like the enrolled speaker?

`verify_22_languages.py` answers a narrower question: the strict-clone route
was taken, the engine was Indic-Mio rather than an edge-tts stand-in, and the
audio decodes to something non-silent and unclipped. Every one of those can be
true while the voice belongs to somebody else - which is exactly the reported
complaint, "the voice its replying is not cloned voice".

So score it with a model that was trained for this and nothing else:
WavLM-base-plus-sv, a speaker-verification head over WavLM (MIT). Its authors
publish a cosine threshold of 0.86 for the same-speaker decision. That number
is calibrated on English conversational speech, so treat it as a reference
line rather than a verdict on Santali or Manipuri; the useful signal is the
spread across languages and the gap to the unrelated-speaker control.

The control matters. A similarity of 0.9 means nothing on its own unless an
unrelated voice scores meaningfully lower through the same pipeline, because
these encoders drift upward when channel and codec are shared. Every run
therefore scores an impostor as well, and reports the margin between them.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

RUNTIME = "/app/dreamtalk/media/avatar_runtime"
MODEL = "microsoft/wavlm-base-plus-sv"
SAME_SPEAKER_THRESHOLD = 0.86   # the checkpoint's own published operating point
# Above this, two recordings are the same take rather than the same person.
DUPLICATE_COSINE = 0.99
# Below roughly this duration an x-vector is dominated by whatever phonemes
# happen to be present, and the score stops meaning "speaker".
MIN_RELIABLE_SECONDS = 1.5


def load_16k(path: str) -> np.ndarray:
    audio, rate = sf.read(path, always_2d=True)
    audio = audio.mean(axis=1).astype(np.float32)
    if rate != 16000:
        import librosa
        audio = librosa.resample(audio, orig_sr=rate, target_sr=16000)
    peak = float(np.abs(audio).max())
    return audio / peak if peak > 0 else audio


def ensure_safetensors() -> str:
    """Fetch the checkpoint and convert it to safetensors once.

    The published repo ships only pytorch_model.bin, and transformers refuses
    to torch.load it under torch 2.5 because of CVE-2025-32434 - the loader
    can execute code during unpickling even with weights_only set. Rather than
    disable that check globally, unpickle this one file deliberately, in
    isolation, and write a safetensors copy beside it; every later load then
    goes through the safe path, including any other process on this machine.
    """
    import torch
    from huggingface_hub import hf_hub_download, snapshot_download
    from safetensors.torch import save_file

    local = snapshot_download(MODEL, allow_patterns=[
        "*.json", "*.txt", "preprocessor_config.json"])
    target = os.path.join(local, "model.safetensors")
    if os.path.exists(target):
        return local
    binp = hf_hub_download(MODEL, "pytorch_model.bin")
    state = torch.load(binp, map_location="cpu", weights_only=True)
    # safetensors refuses tensors that share storage; clone breaks the aliasing
    # without changing any value.
    state = {k: v.detach().clone().contiguous() for k, v in state.items()
             if isinstance(v, torch.Tensor)}
    save_file(state, target, metadata={"format": "pt"})
    print("converted %s -> %s" % (os.path.basename(binp), target))
    return local


class Encoder:
    def __init__(self, device: str = "cpu"):
        from transformers import AutoFeatureExtractor, WavLMForXVector
        local = ensure_safetensors()
        self.fx = AutoFeatureExtractor.from_pretrained(local)
        self.model = WavLMForXVector.from_pretrained(local).to(device).eval()
        self.device = device

    @torch.no_grad()
    def embed(self, audio: np.ndarray) -> torch.Tensor:
        # 30s is plenty and keeps a long reference from dominating runtime.
        audio = audio[: 16000 * 30]
        inputs = self.fx(audio, sampling_rate=16000, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        return self.model(**inputs).embeddings[0]


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(torch.nn.functional.cosine_similarity(a, b, dim=-1))


def pick_impostor(profile: str, reference: str):
    """Find an enrolled voice that is genuinely a different speaker.

    The obvious implementation - take the first reference.wav belonging to
    another profile - reported a control cosine of exactly 1.0000. Not a
    coincidence and not a bug in the encoder: the same recording had been
    enrolled under several profile ids, so the "impostor" was the subject.
    A control that scores 1.0 silently converts the whole measurement into
    nothing, and it does it while looking like a strong result.

    So reject by content hash first, and then by similarity: anything at or
    above DUPLICATE_COSINE is the same recording however it was named. Among
    what survives, take the least similar, because the tightest bound on
    "these are different people" comes from the furthest voice.
    """
    import hashlib

    own = hashlib.md5(open(reference, "rb").read()).hexdigest()
    seen, candidates = {own}, []
    for path in sorted(glob.glob(os.path.join(RUNTIME, "*", "voice", "reference.wav"))):
        if profile in path:
            continue
        digest = hashlib.md5(open(path, "rb").read()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        candidates.append(path)
    if not candidates:
        return None, 0
    enc = Encoder("cpu")
    ref_emb = enc.embed(load_16k(reference))
    scored = sorted(((cosine(ref_emb, enc.embed(load_16k(p))), p) for p in candidates))
    distinct = [(c, p) for c, p in scored if c < DUPLICATE_COSINE]
    rejected = len(scored) - len(distinct)
    if not distinct:
        return None, rejected
    return distinct[0][1], rejected


def f0_stats(audio: np.ndarray) -> dict:
    """Median voiced pitch, as a second opinion that uses no learned model."""
    import librosa
    f0, voiced, _ = librosa.pyin(audio, sr=16000, fmin=60, fmax=400,
                                 frame_length=1024)
    voiced_f0 = f0[np.isfinite(f0)]
    if voiced_f0.size == 0:
        return {"f0_median_hz": None, "voiced_fraction": 0.0}
    return {"f0_median_hz": round(float(np.median(voiced_f0)), 1),
            "voiced_fraction": round(float(np.mean(np.isfinite(f0))), 3)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--audio-dir", default=None,
                    help="directory of per-language wavs (default: the "
                         "language_checks output for this profile)")
    ap.add_argument("--impostor", default=None,
                    help="reference.wav of a DIFFERENT profile, used as the "
                         "control; auto-selected if omitted")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    audio_dir = Path(args.audio_dir) if args.audio_dir else (
        root / "e2e_deep" / "language_checks" / args.profile)
    reference = Path(RUNTIME) / args.profile / "voice" / "reference.wav"
    if not reference.exists():
        print(f"no enrolment audio at {reference}", file=sys.stderr)
        return 2

    impostor, rejected = args.impostor, 0
    if impostor is None:
        impostor, rejected = pick_impostor(args.profile, str(reference))

    enc = Encoder(args.device)
    ref_audio = load_16k(str(reference))
    ref_emb = enc.embed(ref_audio)
    ref_f0 = f0_stats(ref_audio)
    print(f"reference: {reference}  {ref_f0}")

    control = None
    if impostor:
        imp_audio = load_16k(impostor)
        control = round(cosine(ref_emb, enc.embed(imp_audio)), 4)
        print(f"impostor control: {impostor}")
        print(f"  cosine {control:.4f}, f0 {f0_stats(imp_audio)['f0_median_hz']} Hz"
              f" against the reference's {ref_f0['f0_median_hz']} Hz"
              f"  ({rejected} candidate(s) rejected as the same recording)")
        if control >= DUPLICATE_COSINE:
            print("  WARNING: the control scores as the same speaker, so it is "
                  "not a control. Every similarity below is uncalibrated.")
    else:
        print("impostor control: UNAVAILABLE - every other enrolled profile "
              "holds the same recording as this one. Absolute similarities "
              "below are uncalibrated and should not be read as a pass.")

    rows = []
    for wav in sorted(audio_dir.glob("*.wav")):
        audio = load_16k(str(wav))
        sim = cosine(ref_emb, enc.embed(audio))
        stats = f0_stats(audio)
        delta = (None if stats["f0_median_hz"] is None or ref_f0["f0_median_hz"] is None
                 else round(stats["f0_median_hz"] - ref_f0["f0_median_hz"], 1))
        seconds = round(len(audio) / 16000, 2)
        rows.append({"language": wav.stem, "cosine": round(sim, 4),
                     "same_speaker": bool(sim >= SAME_SPEAKER_THRESHOLD),
                     "seconds": seconds,
                     # A low score on a 0.6s clip is not evidence about the
                     # clone. Flag it instead of letting it read as a failure.
                     "too_short_to_judge": seconds < MIN_RELIABLE_SECONDS,
                     "f0_median_hz": stats["f0_median_hz"],
                     "f0_delta_hz": delta,
                     "voiced_fraction": stats["voiced_fraction"]})
        print(json.dumps(rows[-1]), flush=True)

    if not rows:
        print(f"no wavs found in {audio_dir}", file=sys.stderr)
        return 2

    sims = np.array([r["cosine"] for r in rows])
    judged = [r for r in rows if not r["too_short_to_judge"]]
    judged_sims = np.array([r["cosine"] for r in judged]) if judged else sims
    summary = {
        "profile_id": args.profile,
        "model": MODEL,
        "same_speaker_threshold": SAME_SPEAKER_THRESHOLD,
        "impostor_cosine": control,
        "languages": len(rows),
        "cosine_min": round(float(sims.min()), 4),
        "cosine_mean": round(float(sims.mean()), 4),
        "cosine_max": round(float(sims.max()), 4),
        "above_threshold": int((sims >= SAME_SPEAKER_THRESHOLD).sum()),
        "judged_languages": len(judged),
        "too_short_to_judge": [r["language"] for r in rows if r["too_short_to_judge"]],
        "judged_cosine_min": round(float(judged_sims.min()), 4),
        "judged_cosine_mean": round(float(judged_sims.mean()), 4),
        "judged_above_threshold": int((judged_sims >= SAME_SPEAKER_THRESHOLD).sum()),
        "margin_over_impostor": (None if control is None
                                 else round(float(judged_sims.mean()) - control, 4)),
        "reference_f0_median_hz": ref_f0["f0_median_hz"],
        "rows": rows,
    }
    out = audio_dir / "speaker_similarity.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"\nwrote {out}")
    worst = min(judged or rows, key=lambda r: r["cosine"])
    print(f"weakest judged: {worst['language']} at {worst['cosine']:.4f} "
          f"({worst['seconds']}s)")
    if summary["too_short_to_judge"]:
        print("not judged (clip under %.1fs, the score would be noise): %s"
              % (MIN_RELIABLE_SECONDS, ", ".join(summary["too_short_to_judge"])))
    return 0 if judged and summary["judged_above_threshold"] == len(judged) else 1


if __name__ == "__main__":
    raise SystemExit(main())
