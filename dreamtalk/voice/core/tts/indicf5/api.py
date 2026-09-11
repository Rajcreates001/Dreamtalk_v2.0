# Adapted from IndicF5 (AI4Bharat/IndicF5) - MIT License
import os
import random
import sys
from importlib.resources import files

import soundfile as sf
import tqdm
from cached_path import cached_path

from .infer.utils_infer import (
    hop_length,
    infer_process,
    load_checkpoint,
    load_model,
    load_vocoder,
    preprocess_ref_audio_text,
    remove_silence_for_generated_wav,
    save_spectrogram,
    transcribe,
    target_sample_rate,
)
from .model import DiT, UNetT
from .model.utils import seed_everything


class F5TTS:
    def __init__(
        self,
        model_type="F5-TTS",
        ckpt_file="",
        vocab_file="",
        ode_method="euler",
        use_ema=True,
        vocoder_name="vocos",
        local_path=None,
        device=None,
        hf_cache_dir=None,
    ):
        self.final_wave = None
        self.target_sample_rate = target_sample_rate
        self.hop_length = hop_length
        self.seed = -1
        self.mel_spec_type = vocoder_name

        if device is not None:
            self.device = device
        else:
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

        self.load_vocoder_model(vocoder_name, local_path=local_path, hf_cache_dir=hf_cache_dir)
        self.load_ema_model(
            model_type, ckpt_file, vocoder_name, vocab_file, ode_method, use_ema, hf_cache_dir=hf_cache_dir
        )

    def load_vocoder_model(self, vocoder_name, local_path=None, hf_cache_dir=None):
        self.vocoder = load_vocoder(vocoder_name, local_path is not None, local_path, self.device, hf_cache_dir)

    def load_ema_model(self, model_type, ckpt_file, mel_spec_type, vocab_file, ode_method, use_ema, hf_cache_dir=None):
        if model_type == "F5-TTS":
            if not ckpt_file:
                if mel_spec_type == "vocos":
                    ckpt_file = str(
                        cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors", cache_dir=hf_cache_dir)
                    )
                elif mel_spec_type == "bigvgan":
                    ckpt_file = str(
                        cached_path("hf://SWivid/F5-TTS/F5TTS_Base_bigvgan/model_1250000.pt", cache_dir=hf_cache_dir)
                    )
            model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
            model_cls = DiT
        elif model_type == "E2-TTS":
            if not ckpt_file:
                ckpt_file = str(
                    cached_path("hf://SWivid/E2-TTS/E2TTS_Base/model_1200000.safetensors", cache_dir=hf_cache_dir)
                )
            model_cfg = dict(dim=1024, depth=24, heads=16, ff_mult=4)
            model_cls = UNetT
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        self.ema_model = load_model(
            model_cls, model_cfg, mel_spec_type, vocab_file, ode_method, use_ema, self.device
        )
        if ckpt_file:
            self.ema_model = load_checkpoint(self.ema_model, ckpt_file, self.device, use_ema=use_ema)

    def transcribe(self, ref_audio, language=None):
        return transcribe(ref_audio, language)

    def export_wav(self, wav, file_wave, remove_silence=False):
        sf.write(file_wave, wav, self.target_sample_rate)

        if remove_silence:
            remove_silence_for_generated_wav(file_wave)

    def export_spectrogram(self, spect, file_spect):
        save_spectrogram(spect, file_spect)

    def infer(
        self,
        ref_file,
        ref_text,
        gen_text,
        show_info=print,
        progress=tqdm,
        target_rms=0.1,
        cross_fade_duration=0.15,
        sway_sampling_coef=-1,
        cfg_strength=2,
        nfe_step=None,
        speed=1.0,
        fix_duration=None,
        remove_silence=False,
        file_wave=None,
        file_spect=None,
        seed=-1,
    ):
        # Resolve ODE steps: explicit arg > INDICF5_NFE_STEPS env var > auto.
        # CPU inference for this 1.3B model is otherwise several minutes per
        # sentence. Eight ODE steps balances intelligibility and latency;
        # GPU deployments retain the higher-quality 16/32 step defaults.
        if nfe_step is None:
            env_nfe = os.environ.get("INDICF5_NFE_STEPS", "").strip()
            if env_nfe:
                nfe_step = int(env_nfe)
            elif str(self.device).startswith("cpu"):
                nfe_step = 8
            else:
                nfe_step = 16 if len(gen_text) <= 200 else 32
        nfe_step = max(1, int(nfe_step))

        if seed == -1:
            seed = random.randint(0, sys.maxsize)
        seed_everything(seed)
        self.seed = seed

        ref_file, ref_text = preprocess_ref_audio_text(ref_file, ref_text, device=self.device)

        wav, sr, spect = infer_process(
            ref_file,
            ref_text,
            gen_text,
            self.ema_model,
            self.vocoder,
            self.mel_spec_type,
            show_info=show_info,
            progress=progress,
            target_rms=target_rms,
            cross_fade_duration=cross_fade_duration,
            nfe_step=nfe_step,
            cfg_strength=cfg_strength,
            sway_sampling_coef=sway_sampling_coef,
            speed=speed,
            fix_duration=fix_duration,
            device=self.device,
        )

        if file_wave is not None:
            self.export_wav(wav, file_wave, remove_silence)

        if file_spect is not None:
            self.export_spectrogram(spect, file_spect)

        return wav, sr, spect


if __name__ == "__main__":
    f5tts = F5TTS()

    wav, sr, spect = f5tts.infer(
        ref_file=str(files("f5_tts").joinpath("infer/examples/basic/basic_ref_en.wav")),
        ref_text="some call me nature, others call me mother nature.",
        gen_text="""I don't really care what you call me. I've been a silent spectator, watching species evolve, empires rise and fall. But always remember, I am mighty and enduring. Respect me and I'll nurture you; ignore me and you shall face the consequences.""",
        file_wave=str(files("f5_tts").joinpath("../../tests/api_out.wav")),
        file_spect=str(files("f5_tts").joinpath("../../tests/api_out.png")),
        seed=-1,
    )

    print("seed :", f5tts.seed)
