"""
Benchmark IndicF5 synthesis latency vs NFE steps and torch thread count.

Loads the model ONCE, then times .infer() across configurations.
Run:  dt_venv/Scripts/python.exe dreamtalk/scripts/bench_indicf5_speed.py [--text "..."] [--full]
"""

import argparse
import os
import pathlib
import sys
import time

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

_SCRIPT = pathlib.Path(__file__).resolve()
_DREAMTALK = _SCRIPT.parent.parent  # dreamtalk/

sys.path.insert(0, str(_DREAMTALK / "voice" / "core" / "tts"))

_REF_AUDIO = _DREAMTALK / "pipeline_outputs" / "tts" / "tts_774dd96c.wav"
_REF_TEXT = "namaste, yeh ek hindi bhasha ka pariksha hai."
_SHORT_TEXT = "Vanakkam, indha oru siriya Tamil test."
_LONG_TEXT = (
    "Vanakkam, indha oru neela Tamil test. "
    "Idhu podhum illa, innum konjam neelamaana vaakyam vendum. "
    "F5 TTS model eppadi work aagudhu nu paakalaam."
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="also benchmark the long text")
    args = parser.parse_args()

    import soundfile as sf  # noqa: F401  (warm import alongside torch)
    import torch

    print(f"torch {torch.__version__} | cuda={torch.cuda.is_available()} | "
          f"cpus={os.cpu_count()} default_threads={torch.get_num_threads()}", flush=True)

    import indicf5.api

    weights = _DREAMTALK / "weights" / "voice" / "indic_tts" / "IndicF5"
    t0 = time.time()
    model = indicf5.api.F5TTS(
        model_type="F5-TTS",
        ckpt_file=str(weights / "model.safetensors"),
        vocab_file=str(weights / "checkpoints" / "vocab.txt"),
        device="cpu",
    )
    print(f"model loaded in {time.time() - t0:.1f}s\n", flush=True)

    def bench(label, text, nfe, threads):
        torch.set_num_threads(threads)
        t0 = time.time()
        wav, sr, _ = model.infer(
            ref_file=str(_REF_AUDIO),
            ref_text=_REF_TEXT,
            gen_text=text,
            show_info=lambda *_: None,   # silence progress prints
            nfe_step=nfe,
        )
        dt = time.time() - t0
        print(f"{label:<28} nfe={nfe:>2} threads={threads:>2}  ->  {dt:6.1f}s  ({len(wav)/sr:.2f}s audio)",
              flush=True)
        return dt

    texts = [("_short_", _SHORT_TEXT)]
    if args.full:
        texts.append(("_long_", _LONG_TEXT))

    for label, text in texts:
        print(f"\n== {label} ({len(text)} chars) ==", flush=True)
        bench(f"{label} warmup", text, 4, 8)       # warm up lazy kernels, ignore
        bench(f"{label} baseline", text, 32, 8)    # current production config
        bench(f"{label} all-cores", text, 32, os.cpu_count() or 16)
        bench(f"{label} half-steps", text, 16, os.cpu_count() or 16)
        bench(f"{label} quarter-steps", text, 8, os.cpu_count() or 16)


if __name__ == "__main__":
    main()
