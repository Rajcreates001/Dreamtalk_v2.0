"""Does this synthesised clip sound like the enrolled speaker?

The clone engine samples. Synthesising one Kashmiri sentence five times from a
single profile produced speaker similarities of 0.8895, 0.8112, 0.8778, 0.7019
and 0.8432 — a spread of 0.19 from identical input, and the low take sits
below the 0.7447 that a completely unrelated speaker scores through the same
pipeline. Averaged over a report that reads as "22 of 22 languages cloned";
heard one utterance at a time it reads as "the voice its replying is not
cloned voice", which is the complaint that has been open for weeks.

Trimming the sampler barely helped: top_p 1.0 -> 0.9 moved the worst Kashmiri
take from 0.6731 to 0.7019 and left the spread at 0.19. Lowering temperature
far enough to remove the tail would flatten the prosody everywhere to fix a
minority of takes.

So measure the output instead of hoping about the input. WavLM-base-plus-sv is
a speaker-verification head trained for exactly this question, and it is
already in this image because the QA harness uses it. A take that scores below
the floor is resynthesised; the best of the attempts is returned either way,
with the score attached so the caller can see what it got rather than trusting
that it got something.

Cost is proportional to how often it fires. Most takes pass first time, so the
expected overhead is a fraction of one extra synthesis, not a multiple.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger("dreamtalk.avatar.speaker_verify")

MODEL = "microsoft/wavlm-base-plus-sv"
# Below this, resynthesise. Chosen from measurement rather than from the
# checkpoint's published 0.86 same-speaker line: real takes for the harder
# languages average 0.82-0.85, so a 0.86 floor would retry almost every
# request and often still fail. 0.80 clears the 0.7447 an unrelated speaker
# scores by a wide margin while leaving normal variation alone.
DEFAULT_FLOOR = 0.80
DEFAULT_MAX_ATTEMPTS = 3
# Under about this much speech an x-vector measures phonetic content more
# than speaker, so a low score would not be evidence of anything.
MIN_SECONDS = 1.0

_model = None
_extractor = None
_lock = threading.Lock()


def enabled() -> bool:
    return os.environ.get("CLONE_VERIFY_ENABLED", "true").lower() not in {
        "0", "false", "no", "off",
    }


def floor() -> float:
    try:
        return float(os.environ.get("CLONE_SIMILARITY_FLOOR", DEFAULT_FLOOR))
    except (TypeError, ValueError):
        return DEFAULT_FLOOR


def max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("CLONE_MAX_ATTEMPTS",
                                         DEFAULT_MAX_ATTEMPTS)))
    except (TypeError, ValueError):
        return DEFAULT_MAX_ATTEMPTS


def _ensure_safetensors() -> Optional[str]:
    """Fetch the checkpoint, converting it to safetensors the first time.

    The published repo ships only pytorch_model.bin, and transformers refuses
    to torch.load it under torch 2.5 because of CVE-2025-32434. Rather than
    disable that check, unpickle this one file deliberately and write a
    safetensors copy beside it, so every later load takes the safe path.
    """
    import torch
    from huggingface_hub import hf_hub_download, snapshot_download
    from safetensors.torch import save_file

    local = snapshot_download(MODEL, allow_patterns=["*.json", "*.txt"])
    target = os.path.join(local, "model.safetensors")
    if not os.path.exists(target):
        binary = hf_hub_download(MODEL, "pytorch_model.bin")
        state = torch.load(binary, map_location="cpu", weights_only=True)
        # safetensors rejects tensors that share storage; cloning breaks the
        # aliasing without changing a value.
        state = {k: v.detach().clone().contiguous()
                 for k, v in state.items() if isinstance(v, torch.Tensor)}
        save_file(state, target, metadata={"format": "pt"})
        logger.info("converted the speaker-verification checkpoint to "
                    "safetensors at %s", target)
    return local


def _load():
    """Load once, on CPU. Never raises — verification is an improvement."""
    global _model, _extractor
    if _model is not None:
        return _model, _extractor
    with _lock:
        if _model is not None:
            return _model, _extractor
        try:
            import torch
            from transformers import AutoFeatureExtractor, WavLMForXVector

            local = _ensure_safetensors()
            extractor = AutoFeatureExtractor.from_pretrained(local)
            model = WavLMForXVector.from_pretrained(local).to("cpu").eval()
            torch.set_grad_enabled(False)
            _model, _extractor = model, extractor
            logger.info("speaker verification ready (%s, cpu)", MODEL)
        except Exception as exc:
            logger.warning("speaker verification unavailable (%s); clone "
                           "output will not be checked", exc)
            _model, _extractor = False, False
    return _model, _extractor


def _load_16k(path: str):
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(path, always_2d=True)
    audio = audio.mean(axis=1).astype("float32")
    if rate != 16000:
        import librosa
        audio = librosa.resample(audio, orig_sr=rate, target_sr=16000)
    peak = float(abs(audio).max()) if audio.size else 0.0
    if peak > 0:
        audio = audio / peak
    return audio[: 16000 * 30]


def _embed(audio):
    model, extractor = _load()
    if not model:
        return None
    import torch

    inputs = extractor(audio, sampling_rate=16000, return_tensors="pt",
                       padding=True)
    with torch.no_grad():
        return model(**inputs).embeddings[0]


def similarity(candidate_path: str, reference_path: str) -> Optional[float]:
    """Cosine similarity of the two clips' speaker embeddings, or None.

    None means "not measured" and never "failed": too short to judge, model
    unavailable, unreadable audio. The caller must treat None as no opinion
    rather than as a low score, or a missing model silently turns every
    synthesis into three.
    """
    if not enabled():
        return None
    try:
        candidate = _load_16k(candidate_path)
        if len(candidate) < int(16000 * MIN_SECONDS):
            return None
        reference = _load_16k(reference_path)
        a, b = _embed(candidate), _embed(reference)
        if a is None or b is None:
            return None
        import torch
        return round(float(torch.nn.functional.cosine_similarity(a, b, dim=-1)), 4)
    except Exception as exc:
        logger.info("speaker similarity not measured (%s)", exc)
        return None
