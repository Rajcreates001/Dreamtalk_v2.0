import os
import traceback
import pathlib
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

import torch
import torch.nn as nn
import torch.nn.functional as F
import logging

logger = logging.getLogger("dreamtalk.rvc")

# ── Project root detection ────────────────────────────────────────
# voice/core/vc/rvc/rvc_api.py -> 5 levels up to dreamtalk/
_RVC_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent
_RVC_WEIGHTS_DIR = _RVC_PROJECT_ROOT / "weights" / "voice" / "rvc"
_RVC_HUBERT_PATH = str(_RVC_WEIGHTS_DIR / "hubert_base.pt")
_RVC_RMVPE_PATH = str(_RVC_WEIGHTS_DIR / "rmvpe.pt")
_RVC_PRETRAINED_DIR = str(_RVC_WEIGHTS_DIR / "pretrained_v2")

logger.info("RVC weights dir: %s", _RVC_WEIGHTS_DIR)

try:
    import fairseq
except ImportError:
    fairseq = None

try:
    import faiss
except ImportError:
    faiss = None

try:
    import parselmouth
except ImportError:
    parselmouth = None

try:
    import pyworld
except ImportError:
    pyworld = None

try:
    import scipy.signal as signal
except ImportError:
    signal = None

try:
    from torchaudio.transforms import Resample
except ImportError:
    Resample = None

from .model_inference import (
    SynthesizerTrnMs256NSFsid,
    SynthesizerTrnMs768NSFsid,
    SynthesizerTrnMs256NSFsid_nono,
    SynthesizerTrnMs768NSFsid_nono,
)
from .pitch_extraction import RMVPE


@dataclass
class RVCConfig:
    device: str = "cuda:0"
    is_half: bool = False
    use_jit: bool = False
    f0_method: str = "rmvpe"
    f0_up_key: float = 0.0
    formant_shift: float = 0.0
    index_rate: float = 0.0
    protect: float = 0.33
    block_time: float = 0.5
    crossfade_length: float = 0.05
    threhold: float = 0.05
    use_onnx: bool = False
    use_uvr5: bool = False
    use_noise_reduction: bool = False
    use_streaming: bool = False


MODEL_CLS_MAP = {
    ("v1", True): SynthesizerTrnMs256NSFsid,
    ("v2", True): SynthesizerTrnMs768NSFsid,
    ("v1", False): SynthesizerTrnMs256NSFsid_nono,
    ("v2", False): SynthesizerTrnMs768NSFsid_nono,
}

F0_METHOD_REGISTRY: Dict[str, Callable] = {}


def register_f0(name: str):
    def deco(fn):
        F0_METHOD_REGISTRY[name] = fn
        return fn
    return deco


def load_hubert_model(device, is_half=False):
    if fairseq is None:
        raise ImportError("fairseq is required for HuBERT model")
    
    hubert_path = _RVC_HUBERT_PATH
    if not os.path.exists(hubert_path):
        raise FileNotFoundError(f"HuBERT model not found at {hubert_path}. Download from lj1995/VoiceConversionWebUI on HuggingFace.")
    
    models, _, _ = fairseq.checkpoint_utils.load_model_ensemble_and_task(
        [hubert_path],
        suffix="",
    )
    model = models[0]
    model = model.to(device)
    if is_half:
        model = model.half()
    else:
        model = model.float()
    model.eval()
    return model


def load_synthesizer(pth_path, device, is_half=False):
    ckpt = torch.load(pth_path, map_location="cpu")
    
    # Handle raw pretrained model format vs full RVC checkpoint format
    if "config" in ckpt and "weight" in ckpt:
        # Full RVC checkpoint format (config includes all params EXCEPT spk_embed_dim)
        model_config = list(ckpt["config"])
        state_dict = ckpt["weight"]
        if_f0 = ckpt.get("f0", 1)
        version = ckpt.get("version", "v1")
        spk_dim = state_dict["emb_g.weight"].shape[0]
        logger.info("Full RVC checkpoint: config_len=%d, version=%s, f0=%d, spk_dim=%d",
                    len(model_config), version, if_f0, spk_dim)
    elif "model" in ckpt and "iteration" in ckpt:
        # Raw pretrained format: f0G48k.pth from RVC training
        state_dict = ckpt["model"]
        if_f0 = 1
        version = "v2"
        spk_dim = state_dict["emb_g.weight"].shape[0]
        # RVC v2 48kHz config — does NOT include spk_embed_dim
        # Values inferred from actual weight shapes in f0G48k.pth:
        #   enc_p.emb_phone.weight [192, 768]           → hidden_channels=192, in=768
        #   enc_p.proj.weight [384, 192, 1]              → inter_channels=192
        #   dec.ups.0.weight_v [512, 256, 24]            → kernel=24
        #   dec.ups.1.weight_v [256, 128, 20]            → kernel=20
        #   enc_q.pre.weight [192, 1025, 1]              → spec_channels=1025
        model_config = [
            1025,               # spec_channels (from enc_q.pre weight)
            128,                # segment_size
            192,                # inter_channels (from enc_p.proj weight)
            192,                # hidden_channels (from emb_phone weight)
            768,                # filter_channels (from ffn conv_1 weight)
            2,                  # n_heads (from emb_rel_k shape)
            6,                  # n_layers (attn_layers 0-5)
            3,                  # kernel_size
            0.0,                # p_dropout
            "1",                # resblock type
            [3, 7, 11],         # resblock_kernel_sizes
            [[1, 3, 5], [1, 3, 5], [1, 3, 5]],  # resblock_dilation_sizes
            [10, 10, 2, 2],     # upsample_rates
            512,                # upsample_initial_channel
            [24, 20, 4, 4],     # upsample_kernel_sizes (from dec.ups.*.weight_v)
            256,                # gin_channels
            48000,              # sr / tgt_sr
        ]
        logger.info("Raw pretrained checkpoint (f0G48k): spk_dim=%d", spk_dim)
    else:
        raise KeyError(f"Unknown checkpoint format. Keys: {list(ckpt.keys())}")
    
    tgt_sr = model_config[-1]
    model_cls = MODEL_CLS_MAP[(version, bool(if_f0))]
    
    # Constructor: (spec_channels, segment_size, ..., spk_embed_dim, gin_channels, sr)
    # model_config has 17 values: spec_channels..sr but NOT spk_embed_dim
    # Insert spk_embed_dim at position 15 (after upsample_kernel_sizes, before gin_channels)
    full_args = list(model_config)
    full_args.insert(15, spk_dim)  # insert spk_embed_dim
    model = model_cls(*full_args)
    model.to(device)
    model.load_state_dict(state_dict, strict=False)
    if is_half:
        model = model.half()
    else:
        model = model.float()
    model.eval()
    return model, tgt_sr, if_f0, version


def load_onnx_synthesizer(onnx_path: str, device: str = "cpu") -> Any:
    try:
        import onnxruntime as ort
    except ImportError:
        raise ImportError("onnxruntime is required for ONNX inference")
    providers = ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"]
    available = [p for p in providers if p in ort.get_available_providers()]
    session = ort.InferenceSession(onnx_path, providers=available)
    return session


class OnnxRVC:
    def __init__(self, onnx_path: str, hubert_onnx_path: str, device: str = "cpu"):
        self.ort_session = load_onnx_synthesizer(onnx_path, device)
        self.hubert_session = load_onnx_synthesizer(hubert_onnx_path, device) if hubert_onnx_path else None
        self.device = device

    def infer(self, audio: np.ndarray, sr: int = 16000) -> np.ndarray:
        if self.hubert_session:
            input_name = self.hubert_session.get_inputs()[0].name
            hubert_feat = self.hubert_session.run(None, {input_name: audio.astype(np.float32)})[0]
        else:
            hubert_feat = np.zeros((1, 1, 256), dtype=np.float32)
        input_name = self.ort_session.get_inputs()[0].name
        output = self.ort_session.run(None, {input_name: hubert_feat.astype(np.float32)})[0]
        return output.squeeze()


class UVR5Separator:
    def __init__(self, model_path: str, device: str = "cpu"):
        self.device = device
        self.model = None
        try:
            import onnxruntime as ort
            self.ort_session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            logger.info(f"UVR5 model loaded from {model_path}")
        except Exception as e:
            logger.warning(f"UVR5 load failed: {e}")
            self.ort_session = None

    def separate(self, audio_path: str, out_vocal: str, out_inst: str) -> Dict[str, str]:
        if self.ort_session is None:
            return {"vocal": audio_path, "instrument": audio_path}
        import soundfile as sf
        audio, sr = sf.read(audio_path)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        input_name = self.ort_session.get_inputs()[0].shape
        output = self.ort_session.run(None, {self.ort_session.get_inputs()[0].name: audio.astype(np.float32)[np.newaxis, :]})
        vocal = output[0].squeeze()
        sf.write(out_vocal, vocal, sr)
        sf.write(out_inst, audio - vocal, sr)
        return {"vocal": out_vocal, "instrument": out_inst}


class TorchGateDenoiser:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.noise_profile = None

    def denoise(self, audio: np.ndarray, sr: int = 16000, stationary: bool = True) -> np.ndarray:
        try:
            from scipy import signal as sp_signal
            f, t, Zxx = sp_signal.stft(audio, fs=sr, npers=512, noverlap=256)
            mag = np.abs(Zxx)
            if stationary and self.noise_profile is not None:
                noise_thresh = self.noise_profile
            else:
                noise_thresh = np.median(mag, axis=1, keepdims=True) * 1.5
                if stationary:
                    self.noise_profile = noise_thresh
            mask = (mag > noise_thresh).astype(float)
            Zxx_clean = Zxx * mask
            _, audio_clean = sp_signal.istft(Zxx_clean, fs=sr, npers=512, noverlap=256)
            return audio_clean
        except Exception as e:
            logger.warning(f"Denoising failed: {e}")
            return audio


class StreamingBuffer:
    def __init__(self, buffer_duration: float = 0.5, sr: int = 16000):
        self.buffer_size = int(buffer_duration * sr)
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.sr = sr

    def push(self, chunk: np.ndarray) -> np.ndarray:
        chunk = chunk[-self.buffer_size:]
        self.buffer = np.roll(self.buffer, -len(chunk))
        self.buffer[-len(chunk):] = chunk
        return self.buffer.copy()

    def clear(self):
        self.buffer.fill(0)


class SOLAStitcher:
    def __init__(self, crossfade_duration: float = 0.05, sr: int = 16000):
        self.crossfade_frames = int(crossfade_duration * sr)
        self.sr = sr
        self.buffer = np.zeros(self.crossfade_frames, dtype=np.float32)

    def stitch(self, new_block: np.ndarray) -> np.ndarray:
        if len(self.buffer) == 0:
            self.buffer = new_block[-self.crossfade_frames:]
            return new_block
        overlap = min(self.crossfade_frames, len(new_block), len(self.buffer))
        if overlap <= 0:
            self.buffer = new_block[-self.crossfade_frames:]
            return new_block
        fade_in = np.linspace(0, 1, overlap)
        fade_out = np.linspace(1, 0, overlap)
        new_block[:overlap] = new_block[:overlap] * fade_in + self.buffer[-overlap:] * fade_out
        self.buffer = new_block[-self.crossfade_frames:].copy()
        return new_block


class RVC:
    def __init__(
        self,
        pth_path: str,
        index_path: str = "",
        index_rate: float = 0.0,
        f0_up_key: float = 0.0,
        formant_shift: float = 0.0,
        f0_method: str = "rmvpe",
        device: str = "cuda:0",
        is_half: bool = False,
        hubert_model: Optional[nn.Module] = None,
        rmvpe_model: Optional[RMVPE] = None,
    ):
        self.device = torch.device(device)
        self.is_half = is_half
        self.f0_up_key = f0_up_key
        self.formant_shift = formant_shift
        self.f0_min = 50
        self.f0_max = 1100
        self.f0_mel_min = 1127 * np.log(1 + self.f0_min / 700)
        self.f0_mel_max = 1127 * np.log(1 + self.f0_max / 700)
        self.f0_method = f0_method
        self.resample_kernel = {}
        self.use_fcpe = (f0_method == "fcpe")

        if hubert_model is not None:
            self.model = hubert_model
        else:
            self.model = load_hubert_model(self.device, self.is_half)

        self.net_g, self.tgt_sr, self.if_f0, self.version = load_synthesizer(
            pth_path, self.device, self.is_half
        )

        if self.use_fcpe:
            try:
                import torchfcpe
                self.fcpe_model = torchfcpe.spawn_bundled_infer_model(device=self.device)
                logger.info("FCPE model loaded")
            except Exception as e:
                logger.warning(f"FCPE load failed, falling back to rmvpe: {e}")
                self.use_fcpe = False
                self.f0_method = "rmvpe"

        if rmvpe_model is not None:
            self.model_rmvpe = rmvpe_model
        elif self.f0_method == "rmvpe":
            rmvpe_path = _RVC_RMVPE_PATH
            if not os.path.exists(rmvpe_path):
                logger.warning(f"RMVPE model not found at {rmvpe_path}, pitch extraction may fail")
            self.model_rmvpe = RMVPE(
                rmvpe_path,
                is_half=self.is_half,
                device=self.device,
            )
        else:
            self.model_rmvpe = None

        if index_path and index_rate != 0:
            if faiss is None:
                raise ImportError("faiss is required for index")
            self.index = faiss.read_index(index_path)
            self.big_npy = self.index.reconstruct_n(0, self.index.ntotal)
        else:
            self.index = None
            self.big_npy = None
        self.index_rate = index_rate
        self.index_path = index_path

        self.cache_pitch = torch.zeros(1024, device=self.device, dtype=torch.long)
        self.cache_pitchf = torch.zeros(1024, device=self.device, dtype=torch.float32)

        self.stream_buffer = StreamingBuffer()
        self.sola_stitcher = SOLAStitcher()
        self.denoiser = TorchGateDenoiser(device)
        self.uvr5 = None

    def enable_uvr5(self, model_path: str):
        self.uvr5 = UVR5Separator(model_path, str(self.device))

    def separate_sources(self, audio_path: str, out_vocal: str, out_inst: str) -> Dict[str, str]:
        if self.uvr5 is None:
            return {"vocal": audio_path, "instrument": ""}
        return self.uvr5.separate(audio_path, out_vocal, out_inst)

    def get_f0_post(self, f0):
        if not torch.is_tensor(f0):
            f0 = torch.from_numpy(f0)
        f0 = f0.float().to(self.device).squeeze()
        f0_mel = 1127 * torch.log(1 + f0 / 700)
        f0_mel[f0_mel > 0] = (f0_mel[f0_mel > 0] - self.f0_mel_min) * 254 / (
            self.f0_mel_max - self.f0_mel_min
        ) + 1
        f0_mel[f0_mel <= 1] = 1
        f0_mel[f0_mel > 255] = 255
        f0_coarse = torch.round(f0_mel).long()
        return f0_coarse, f0

    def get_f0(self, x, f0_up_key, method="harvest"):
        if method == "crepe":
            return self.get_f0_crepe(x, f0_up_key)
        if method == "rmvpe":
            return self.get_f0_rmvpe(x, f0_up_key)
        if method == "fcpe":
            return self.get_f0_fcpe(x, f0_up_key)
        if method == "dio":
            return self.get_f0_dio(x, f0_up_key)
        x = x.cpu().numpy()
        if method == "pm":
            p_len = x.shape[0] // 160 + 1
            f0_min = 65
            l_pad = int(np.ceil(1.5 / f0_min * 16000))
            r_pad = l_pad + 1
            s = parselmouth.Sound(np.pad(x, (l_pad, r_pad)), 16000).to_pitch_ac(
                time_step=0.01,
                voicing_threshold=0.6,
                pitch_floor=f0_min,
                pitch_ceiling=1100,
            )
            assert np.abs(s.t1 - 1.5 / f0_min) < 0.001
            f0 = s.selected_array["frequency"]
            if len(f0) < p_len:
                f0 = np.pad(f0, (0, p_len - len(f0)))
            f0 = f0[:p_len]
            f0 *= pow(2, f0_up_key / 12)
            return self.get_f0_post(f0)
        f0, t = pyworld.harvest(
            x.astype(np.double),
            fs=16000,
            f0_ceil=1100,
            f0_floor=50,
            frame_period=10,
        )
        f0 = signal.medfilt(f0, 3)
        f0 *= pow(2, f0_up_key / 12)
        return self.get_f0_post(f0)

    def get_f0_crepe(self, x, f0_up_key):
        try:
            import torchcrepe
            f0, pd = torchcrepe.predict(
                x.unsqueeze(0).float(),
                16000,
                160,
                self.f0_min,
                self.f0_max,
                "full",
                batch_size=512,
                device=self.device,
                return_periodicity=True,
            )
            pd = torchcrepe.filter.median(pd, 3)
            f0 = torchcrepe.filter.mean(f0, 3)
            f0[pd < 0.1] = 0
            f0 *= pow(2, f0_up_key / 12)
            return self.get_f0_post(f0)
        except ImportError:
            logger.warning("torchcrepe not installed, falling back to rmvpe")
            return self.get_f0_rmvpe(x, f0_up_key)

    def get_f0_rmvpe(self, x, f0_up_key):
        if self.model_rmvpe is None:
            self.model_rmvpe = RMVPE(
                "assets/rmvpe/rmvpe.pt",
                is_half=self.is_half,
                device=self.device,
            )
        f0 = self.model_rmvpe.infer_from_audio(x, thred=0.03)
        f0 *= pow(2, f0_up_key / 12)
        return self.get_f0_post(f0)

    def get_f0_fcpe(self, x, f0_up_key):
        if not self.use_fcpe or not hasattr(self, 'fcpe_model'):
            return self.get_f0_rmvpe(x, f0_up_key)
        f0 = self.fcpe_model(x.unsqueeze(0).float(), sr=16000, decoder_mode="local_argmax")
        f0 = f0.squeeze(0)
        f0[f0 < 0] = 0
        f0 *= pow(2, f0_up_key / 12)
        return self.get_f0_post(f0)

    def get_f0_dio(self, x, f0_up_key):
        x_np = x.cpu().numpy().astype(np.double)
        f0, _, _ = pyworld.dio(x_np, fs=16000, f0_ceil=1100, f0_floor=50, frame_period=10)
        f0 = pyworld.stonemask(x_np, f0, 16000)
        f0 = signal.medfilt(f0, 3)
        f0 *= pow(2, f0_up_key / 12)
        return self.get_f0_post(f0)

    def infer(
        self,
        input_wav: torch.Tensor,
        block_frame_16k: int = 1600,
        skip_head: int = 0,
        return_length: int = 1600,
        f0method: str = "rmvpe",
    ) -> np.ndarray:
        with torch.no_grad():
            if self.is_half:
                feats = input_wav.half().view(1, -1)
            else:
                feats = input_wav.float().view(1, -1)
            padding_mask = torch.BoolTensor(feats.shape).to(self.device).fill_(False)
            inputs = {
                "source": feats,
                "padding_mask": padding_mask,
                "output_layer": 9 if self.version == "v1" else 12,
            }
            logits = self.model.extract_features(**inputs)
            feats = (
                self.model.final_proj(logits[0]) if self.version == "v1" else logits[0]
            )
            feats = torch.cat((feats, feats[:, -1:, :]), 1)

        if self.index is not None and self.index_rate != 0:
            npy = feats[0][skip_head // 2 :].cpu().numpy().astype("float32")
            score, ix = self.index.search(npy, k=8)
            if (ix >= 0).all():
                weight = np.square(1 / score)
                weight /= weight.sum(axis=1, keepdims=True)
                npy = np.sum(
                    self.big_npy[ix] * np.expand_dims(weight, axis=2), axis=1
                )
                if self.is_half:
                    npy = npy.astype("float16")
                feats[0][skip_head // 2 :] = (
                    torch.from_numpy(npy).unsqueeze(0).to(self.device)
                    * self.index_rate
                    + (1 - self.index_rate) * feats[0][skip_head // 2 :]
                )

        p_len = input_wav.shape[0] // 160
        factor = pow(2, self.formant_shift / 12)
        return_length2 = int(np.ceil(return_length * factor))
        if self.if_f0 == 1:
            f0_extractor_frame = block_frame_16k + 800
            if f0method == "rmvpe":
                f0_extractor_frame = 5120 * ((f0_extractor_frame - 1) // 5120 + 1) - 160
            pitch, pitchf = self.get_f0(
                input_wav[-f0_extractor_frame:],
                self.f0_up_key - self.formant_shift,
                f0method,
            )
            shift = block_frame_16k // 160
            self.cache_pitch[:-shift] = self.cache_pitch[shift:].clone()
            self.cache_pitchf[:-shift] = self.cache_pitchf[shift:].clone()
            self.cache_pitch[4 - pitch.shape[0] :] = pitch[3:-1]
            self.cache_pitchf[4 - pitch.shape[0] :] = pitchf[3:-1]
            cache_pitch = self.cache_pitch[None, -p_len:]
            cache_pitchf = (
                self.cache_pitchf[None, -p_len:] * return_length2 / return_length
            )

        feats = F.interpolate(feats.permute(0, 2, 1), scale_factor=2).permute(0, 2, 1)
        feats = feats[:, :p_len, :]
        p_len_t = torch.LongTensor([p_len]).to(self.device)
        sid = torch.LongTensor([0]).to(self.device)
        skip_head_t = torch.LongTensor([skip_head])
        return_length2_t = torch.LongTensor([return_length2])
        return_length_t = torch.LongTensor([return_length])
        with torch.no_grad():
            if self.if_f0 == 1:
                infered_audio, _, _ = self.net_g.infer(
                    feats,
                    p_len_t,
                    cache_pitch,
                    cache_pitchf,
                    sid,
                    skip_head_t,
                    return_length_t,
                    return_length2_t,
                )
            else:
                infered_audio, _, _ = self.net_g.infer(
                    feats,
                    p_len_t,
                    sid,
                    skip_head_t,
                    return_length_t,
                    return_length2_t,
                )
        infered_audio = infered_audio.squeeze(1).float()
        upp_res = int(np.floor(factor * self.tgt_sr // 100))
        if upp_res != self.tgt_sr // 100:
            if upp_res not in self.resample_kernel:
                self.resample_kernel[upp_res] = Resample(
                    orig_freq=upp_res,
                    new_freq=self.tgt_sr // 100,
                    dtype=torch.float32,
                ).to(self.device)
            infered_audio = self.resample_kernel[upp_res](
                infered_audio[:, : return_length * upp_res]
            )
        return infered_audio.squeeze().cpu().numpy()

    def streaming_infer(self, audio_chunk: np.ndarray) -> np.ndarray:
        chunk = self.stream_buffer.push(audio_chunk)
        chunk_denoised = self.denoiser.denoise(chunk)
        chunk_tensor = torch.from_numpy(chunk_denoised).to(self.device)
        result = self.infer(chunk_tensor, f0method=self.f0_method)
        stitched = self.sola_stitcher.stitch(result)
        return stitched

    def change_key(self, new_key):
        self.f0_up_key = new_key

    def change_formant(self, new_formant):
        self.formant_shift = new_formant

    def change_index_rate(self, new_index_rate):
        if new_index_rate != 0 and self.index_rate == 0 and self.index_path:
            if faiss is None:
                raise ImportError("faiss is required for index")
            self.index = faiss.read_index(self.index_path)
            self.big_npy = self.index.reconstruct_n(0, self.index.ntotal)
        self.index_rate = new_index_rate

    def change_f0_method(self, method: str):
        self.f0_method = method
        self.use_fcpe = (method == "fcpe")
