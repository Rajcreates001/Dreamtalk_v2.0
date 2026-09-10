# Adapted from IndicF5 (AI4Bharat/IndicF5) - MIT License
import os
import sys

os.environ["PYTOCH_ENABLE_MPS_FALLBACK"] = "1"
sys.path.append(f"../../{os.path.dirname(os.path.abspath(__file__))}/third_party/BigVGAN/")

import hashlib
import re
import tempfile
from importlib.resources import files

import matplotlib

matplotlib.use("Agg")

import matplotlib.pylab as plt
import numpy as np
import soundfile as sf
import torch
import torchaudio
import tqdm
from huggingface_hub import snapshot_download, hf_hub_download
from pydub import AudioSegment, silence
from vocos import Vocos

from ..model import CFM
from ..model.utils import (
    get_tokenizer,
    convert_char_to_pinyin,
)

_ref_audio_cache = {}

device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

target_sample_rate = 24000
n_mel_channels = 100
hop_length = 256
win_length = 1024
n_fft = 1024
mel_spec_type = "vocos"
target_rms = 0.1
cross_fade_duration = 0.15
ode_method = "euler"
nfe_step = 32
cfg_strength = 2.0
sway_sampling_coef = -1.0
speed = 1.0
fix_duration = None


def chunk_text(text, max_chars=135):
    chunks = []
    current_chunk = ""
    sentences = re.split(r"(?<=[;:,.!?])\s+|(?<=[；：，。！？])", text)

    for sentence in sentences:
        if len(current_chunk.encode("utf-8")) + len(sentence.encode("utf-8")) <= max_chars:
            current_chunk += sentence + " " if sentence and len(sentence[-1].encode("utf-8")) == 1 else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " " if sentence and len(sentence[-1].encode("utf-8")) == 1 else sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def load_vocoder(vocoder_name="vocos", is_local=False, local_path="", device=device, hf_cache_dir=None):
    if vocoder_name == "vocos":
        if is_local:
            print(f"Load vocos from local path {local_path}")
            config_path = f"{local_path}/config.yaml"
            model_path = f"{local_path}/pytorch_model.bin"
        else:
            print("Download Vocos from huggingface charactr/vocos-mel-24khz")
            repo_id = "charactr/vocos-mel-24khz"
            config_path = hf_hub_download(repo_id=repo_id, cache_dir=hf_cache_dir, filename="config.yaml")
            model_path = hf_hub_download(repo_id=repo_id, cache_dir=hf_cache_dir, filename="pytorch_model.bin")
        vocoder = Vocos.from_hparams(config_path)
        state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
        from vocos.feature_extractors import EncodecFeatures

        if isinstance(vocoder.feature_extractor, EncodecFeatures):
            encodec_parameters = {
                "feature_extractor.encodec." + key: value
                for key, value in vocoder.feature_extractor.encodec.state_dict().items()
            }
            state_dict.update(encodec_parameters)
        vocoder.load_state_dict(state_dict)
        vocoder = vocoder.eval().to(device)
    elif vocoder_name == "bigvgan":
        try:
            from third_party.BigVGAN import bigvgan
        except ImportError:
            print("You need to follow the README to init submodule and change the BigVGAN source code.")
        if is_local:
            vocoder = bigvgan.BigVGAN.from_pretrained(local_path, use_cuda_kernel=False)
        else:
            local_path = snapshot_download(repo_id="nvidia/bigvgan_v2_24khz_100band_256x", cache_dir=hf_cache_dir)
            vocoder = bigvgan.BigVGAN.from_pretrained(local_path, use_cuda_kernel=False)

        vocoder.remove_weight_norm()
        vocoder = vocoder.eval().to(device)
    return vocoder


asr_pipe = None


def initialize_asr_pipeline(device: str = device, dtype=None):
    # Lazy import to avoid Windows fbgemm.dll dependency crash at module level
    from transformers import pipeline
    if dtype is None:
        dtype = (
            torch.float16
            if "cuda" in device
            and torch.cuda.get_device_properties(device).major >= 6
            and not torch.cuda.get_device_name().endswith("[ZLUDA]")
            else torch.float32
        )
    global asr_pipe
    asr_pipe = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-large-v3-turbo",
        torch_dtype=dtype,
        device=device,
    )


def transcribe(ref_audio, language=None):
    global asr_pipe
    if asr_pipe is None:
        initialize_asr_pipeline(device=device)
    return asr_pipe(
        ref_audio,
        chunk_length_s=30,
        batch_size=128,
        generate_kwargs={"task": "transcribe", "language": language} if language else {"task": "transcribe"},
        return_timestamps=False,
    )["text"].strip()


def load_checkpoint(model, ckpt_path, device: str, dtype=None, use_ema=True):
    if dtype is None:
        dtype = torch.float32
    model = model.to(dtype)

    ckpt_type = ckpt_path.split(".")[-1]
    if ckpt_type == "safetensors":
        from safetensors.torch import load_file

        checkpoint = load_file(ckpt_path, device=device)
    else:
        checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)

    if use_ema:
        if ckpt_type == "safetensors":
            checkpoint = {"ema_model_state_dict": checkpoint}
        checkpoint["model_state_dict"] = {
            k.replace("ema_model.", "").replace("_orig_mod.", ""): v
            for k, v in checkpoint["ema_model_state_dict"].items()
            if k not in ["initted", "step"]
        }

        for key in ["mel_spec.mel_stft.mel_scale.fb", "mel_spec.mel_stft.spectrogram.window"]:
            if key in checkpoint["model_state_dict"]:
                del checkpoint["model_state_dict"][key]

        # Handle _orig_mod. prefix (torch.compile) and vocoder keys
        clean_state = {}
        for k, v in checkpoint["model_state_dict"].items():
            k = k.replace("_orig_mod.", "")
            # Skip vocoder keys (they're loaded separately)
            if k.startswith("vocoder."):
                continue
            clean_state[k] = v

        model.load_state_dict(clean_state, strict=False)
    else:
        if ckpt_type == "safetensors":
            checkpoint = {"model_state_dict": checkpoint}
        model.load_state_dict(checkpoint["model_state_dict"])

    del checkpoint
    torch.cuda.empty_cache()

    return model.to(device)


def load_model(
    model_cls,
    model_cfg,
    mel_spec_type=mel_spec_type,
    vocab_file="",
    ode_method=ode_method,
    use_ema=True,
    device=device,
):
    if vocab_file == "":
        vocab_file = str(files("f5_tts").joinpath("infer/examples/vocab.txt"))
    tokenizer = "custom"

    print("\nvocab : ", vocab_file)
    print("token : ", tokenizer)

    vocab_char_map, vocab_size = get_tokenizer(vocab_file, tokenizer)
    model = CFM(
        transformer=model_cls(**model_cfg, text_num_embeds=vocab_size, mel_dim=n_mel_channels),
        mel_spec_kwargs=dict(
            n_fft=n_fft,
            hop_length=hop_length,
            win_length=win_length,
            n_mel_channels=n_mel_channels,
            target_sample_rate=target_sample_rate,
            mel_spec_type=mel_spec_type,
        ),
        odeint_kwargs=dict(
            method=ode_method,
        ),
        vocab_char_map=vocab_char_map,
    ).to(device)

    dtype = torch.float32 if mel_spec_type == "bigvgan" else None

    return model


def _frame_dbfs(wav, sr, frame_ms=10):
    """Peak dBFS per ~frame_ms window (numpy stand-in for pydub's per-ms dBFS scan)."""
    frame_len = max(1, int(sr * frame_ms / 1000))
    n_frames = len(wav) // frame_len
    if n_frames == 0:
        return np.zeros(0), frame_len
    frames = wav[: n_frames * frame_len].reshape(n_frames, frame_len)
    peak = np.max(np.abs(frames), axis=1)
    return 20.0 * np.log10(np.maximum(peak, 1e-10)), frame_len


def _load_audio_any(path):
    """Load an audio file as float32 mono + sample rate without shelling out to ffprobe."""
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception:
        audio_t, sr = torchaudio.load(str(path))
        data = audio_t.numpy().T
    return np.asarray(data.mean(axis=1), dtype=np.float32), int(sr)


def _split_on_silence_np(wav, sr, min_silence_ms, silence_thresh_dbfs, keep_silence_ms):
    """Speech chunks as (start, end) sample ranges; mirrors pydub.silence.split_on_silence."""
    dbfs, frame_len = _frame_dbfs(wav, sr)
    if dbfs.size == 0:
        return []
    silent = dbfs < silence_thresh_dbfs
    min_run = max(1, int(round(min_silence_ms / 10)))  # frames are 10 ms wide

    bounds = []  # (start_frame, end_frame) per speech run
    start_frame = None
    i, n_frames = 0, silent.size
    while i < n_frames:
        if silent[i]:
            j = i
            while j < n_frames and silent[j]:
                j += 1
            if j - i >= min_run and start_frame is not None:
                bounds.append((start_frame, i))
                start_frame = None
            # silences shorter than min_silence_ms stay inside the current chunk
            i = j
        else:
            if start_frame is None:
                start_frame = i
            i += 1
    if start_frame is not None and n_frames > start_frame:
        bounds.append((start_frame, n_frames))

    keep = max(0, int(sr * keep_silence_ms / 1000))
    return [
        (max(0, s * frame_len - keep), min(len(wav), e * frame_len + keep))
        for s, e in bounds
    ]


def _clip_reference_short(wav, sr, show_info):
    """Accumulate speech chunks up to ~15 s (two detection passes, then hard clip)."""
    clipped = wav[:0]
    for pass_num, min_silence_ms, thresh_dbfs in ((1, 1000, -50), (2, 100, -40)):
        parts = []
        total_ms = 0.0
        for start, end in _split_on_silence_np(wav, sr, min_silence_ms, thresh_dbfs, keep_silence_ms=1000):
            seg_ms = (end - start) / sr * 1000.0
            if total_ms > 6000 and total_ms + seg_ms > 15000:
                show_info(f"Audio is over 15s, clipping short. ({pass_num})")
                break
            parts.append(wav[start:end])
            total_ms += seg_ms
        clipped = np.concatenate(parts) if parts else wav[:0]
        if clipped.shape[0] * 1000.0 / sr <= 15000:
            return clipped

    max_samples = int(15.0 * sr)
    if clipped.shape[0] > max_samples:
        show_info("Audio is over 15s, clipping short. (3)")
        clipped = clipped[:max_samples]
    return clipped


def remove_silence_edges(wav, sr, silence_threshold=-42):
    """Trim leading/trailing near-silence from a float32 waveform."""
    dbfs, frame_len = _frame_dbfs(wav, sr)
    loud = np.nonzero(dbfs >= silence_threshold)[0]
    if loud.size == 0:
        return wav
    start = int(loud[0]) * frame_len
    end = min(len(wav), (int(loud[-1]) + 1) * frame_len)
    return wav[start:end]


def preprocess_ref_audio_text(ref_audio_orig, ref_text, clip_short=True, show_info=print, device=device):
    # numpy/soundfile port of the pydub pipeline: AudioSegment.from_file() shells out to
    # ffprobe, which is absent on this machine (WinError 2 -> HTTP 500 on /synthesize).
    wav, sr = _load_audio_any(ref_audio_orig)

    if clip_short:
        wav = _clip_reference_short(wav, sr, show_info)

    wav = remove_silence_edges(wav, sr)
    if wav.shape[0] == 0:
        wav = np.zeros(int(0.5 * sr), dtype=np.float32)  # degenerate all-silence reference
    wav = np.concatenate([wav.astype(np.float32), np.zeros(max(1, int(0.05 * sr)), dtype=np.float32)])

    fd, ref_audio = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    sf.write(ref_audio, wav, sr, subtype="PCM_16")

    with open(ref_audio, "rb") as audio_file:
        audio_data = audio_file.read()
        audio_hash = hashlib.md5(audio_data).hexdigest()

    if not ref_text.strip():
        global _ref_audio_cache
        if audio_hash in _ref_audio_cache:
            show_info("Using cached reference text...")
            ref_text = _ref_audio_cache[audio_hash]
        else:
            show_info("No reference text provided, transcribing reference audio...")
            ref_text = transcribe(ref_audio)
            _ref_audio_cache[audio_hash] = ref_text
    else:
        pass

    if not ref_text.endswith(". ") and not ref_text.endswith("。"):
        if ref_text.endswith("."):
            ref_text += " "
        else:
            ref_text += ". "

    return ref_audio, ref_text


def infer_process(
    ref_audio,
    ref_text,
    gen_text,
    model_obj,
    vocoder,
    mel_spec_type=mel_spec_type,
    show_info=print,
    progress=tqdm,
    target_rms=target_rms,
    cross_fade_duration=cross_fade_duration,
    nfe_step=nfe_step,
    cfg_strength=cfg_strength,
    sway_sampling_coef=sway_sampling_coef,
    speed=speed,
    fix_duration=fix_duration,
    device=device,
):
    # soundfile instead of torchaudio.load: this venv's torchaudio requires the
    # missing torchcodec module, so loading here would crash after preprocessing.
    data, sr = sf.read(ref_audio, dtype="float32", always_2d=True)
    audio = torch.from_numpy(data.T)  # (channels, time), same shape torchaudio.load returned
    max_chars = int(len(ref_text.encode("utf-8")) / (audio.shape[-1] / sr) * (25 - audio.shape[-1] / sr))
    gen_text_batches = chunk_text(gen_text, max_chars=max_chars)

    return infer_batch_process(
        (audio, sr),
        ref_text,
        gen_text_batches,
        model_obj,
        vocoder,
        mel_spec_type=mel_spec_type,
        progress=progress,
        target_rms=target_rms,
        cross_fade_duration=cross_fade_duration,
        nfe_step=nfe_step,
        cfg_strength=cfg_strength,
        sway_sampling_coef=sway_sampling_coef,
        speed=speed,
        fix_duration=fix_duration,
        device=device,
    )


def infer_batch_process(
    ref_audio,
    ref_text,
    gen_text_batches,
    model_obj,
    vocoder,
    mel_spec_type="vocos",
    progress=tqdm,
    target_rms=0.1,
    cross_fade_duration=0.15,
    nfe_step=32,
    cfg_strength=2.0,
    sway_sampling_coef=-1,
    speed=1,
    fix_duration=None,
    device=None,
):
    audio, sr = ref_audio
    if audio.shape[0] > 1:
        audio = torch.mean(audio, dim=0, keepdim=True)

    rms = torch.sqrt(torch.mean(torch.square(audio)))
    if rms < target_rms:
        audio = audio * target_rms / rms
    if sr != target_sample_rate:
        resampler = torchaudio.transforms.Resample(sr, target_sample_rate)
        audio = resampler(audio)
    audio = audio.to(device)

    generated_waves = []
    spectrograms = []

    if len(ref_text[-1].encode("utf-8")) == 1:
        ref_text = ref_text + " "
    for i, gen_text in enumerate(gen_text_batches):
        text_list = [ref_text + gen_text]
        final_text_list = convert_char_to_pinyin(text_list)

        ref_audio_len = audio.shape[-1] // hop_length
        if fix_duration is not None:
            duration = int(fix_duration * target_sample_rate / hop_length)
        else:
            ref_text_len = len(ref_text.encode("utf-8"))
            gen_text_len = len(gen_text.encode("utf-8"))
            duration = ref_audio_len + int(ref_audio_len / ref_text_len * gen_text_len / speed)
        with torch.inference_mode():
            generated, _ = model_obj.sample(
                cond=audio,
                text=final_text_list,
                duration=duration,
                steps=nfe_step,
                cfg_strength=cfg_strength,
                sway_sampling_coef=sway_sampling_coef,
            )

            generated = generated.to(torch.float32)
            generated = generated[:, ref_audio_len:, :]
            generated_mel_spec = generated.permute(0, 2, 1)
            if mel_spec_type == "vocos":
                generated_wave = vocoder.decode(generated_mel_spec)
            elif mel_spec_type == "bigvgan":
                generated_wave = vocoder(generated_mel_spec)
            if rms < target_rms:
                generated_wave = generated_wave * rms / target_rms

            generated_wave = generated_wave.squeeze().cpu().numpy()

            generated_waves.append(generated_wave)
            spectrograms.append(generated_mel_spec[0].cpu().numpy())

    if cross_fade_duration <= 0:
        final_wave = np.concatenate(generated_waves)
    else:
        final_wave = generated_waves[0]
        for i in range(1, len(generated_waves)):
            prev_wave = final_wave
            next_wave = generated_waves[i]

            cross_fade_samples = int(cross_fade_duration * target_sample_rate)
            cross_fade_samples = min(cross_fade_samples, len(prev_wave), len(next_wave))

            if cross_fade_samples <= 0:
                final_wave = np.concatenate([prev_wave, next_wave])
                continue

            prev_overlap = prev_wave[-cross_fade_samples:]
            next_overlap = next_wave[:cross_fade_samples]

            fade_out = np.linspace(1, 0, cross_fade_samples)
            fade_in = np.linspace(0, 1, cross_fade_samples)

            cross_faded_overlap = prev_overlap * fade_out + next_overlap * fade_in

            new_wave = np.concatenate(
                [prev_wave[:-cross_fade_samples], cross_faded_overlap, next_wave[cross_fade_samples:]]
            )

            final_wave = new_wave

    combined_spectrogram = np.concatenate(spectrograms, axis=1)

    return final_wave, target_sample_rate, combined_spectrogram


def remove_silence_for_generated_wav(filename):
    aseg = AudioSegment.from_file(filename)
    non_silent_segs = silence.split_on_silence(
        aseg, min_silence_len=1000, silence_thresh=-50, keep_silence=500, seek_step=10
    )
    non_silent_wave = AudioSegment.silent(duration=0)
    for non_silent_seg in non_silent_segs:
        non_silent_wave += non_silent_seg
    aseg = non_silent_wave
    aseg.export(filename, format="wav")


def save_spectrogram(spectrogram, path):
    plt.figure(figsize=(12, 4))
    plt.imshow(spectrogram, origin="lower", aspect="auto")
    plt.colorbar()
    plt.savefig(path)
    plt.close()
