# Dreamtalk - Voice Engine
# Extracted from Fish Speech (TTSInferenceEngine)

import queue
from dataclasses import dataclass
from typing import Generator, Optional, Tuple

import numpy as np
import torch
import torchaudio

from .vqgan import DAC
from .llm import BaseTransformer, DualARTransformer
from .inference import generate_with_codes


@dataclass
class InferenceResult:
    code: str
    audio: Optional[Tuple[int, np.ndarray]]
    error: Optional[Exception]


def wav_chunk_header(sample_rate=44100, bit_depth=16, channels=1) -> bytes:
    import io
    import wave
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(bit_depth // 8)
        wav_file.setframerate(sample_rate)
    wav_header_bytes = buffer.getvalue()
    buffer.close()
    return wav_header_bytes


def set_seed(seed: int):
    torch.manual_seed(seed)
    np.random.seed(seed)


def autocast_exclude_mps(device_type, dtype):
    if device_type == "mps":
        return torch.no_grad()
    return torch.autocast(device_type=device_type, dtype=dtype)


class TTSInferenceEngine:
    def __init__(
        self,
        llama_model: BaseTransformer,
        decoder_model: DAC,
        tokenizer=None,
        precision: torch.dtype = torch.float16,
        compile: bool = False,
    ):
        self.llama_model = llama_model
        self.decoder_model = decoder_model
        self.tokenizer = tokenizer
        self.precision = precision
        self.compile = compile

    @torch.inference_mode()
    def inference(
        self,
        text: str,
        max_new_tokens: int = 2048,
        temperature_text: float = 0.7,
        top_p_text: float = 0.9,
        top_k_text: int = 50,
        temperature_codes: float = 0.3,
        top_p_codes: float = 0.9,
        top_k_codes: int = 50,
        seed: Optional[int] = None,
        reference_audio: Optional[torch.Tensor] = None,
        reference_text: Optional[str] = None,
        streaming: bool = False,
    ) -> Generator[InferenceResult, None, None]:
        if seed is not None:
            set_seed(seed)

        sample_rate = getattr(self.decoder_model, "sample_rate", 44100)

        if streaming:
            yield InferenceResult(
                code="header",
                audio=(sample_rate, np.array(wav_chunk_header(sample_rate=sample_rate))),
                error=None,
            )

        segments = []

        try:
            result = self._generate(
                text=text,
                max_new_tokens=max_new_tokens,
                temperature_text=temperature_text,
                top_p_text=top_p_text,
                top_k_text=top_k_text,
                temperature_codes=temperature_codes,
                top_p_codes=top_p_codes,
                top_k_codes=top_k_codes,
            )

            if streaming:
                yield InferenceResult(
                    code="segment",
                    audio=(sample_rate, result),
                    error=None,
                )
            segments.append(result)

        except Exception as e:
            yield InferenceResult(code="error", audio=None, error=e)
            return

        if len(segments) == 0:
            yield InferenceResult(
                code="error",
                audio=None,
                error=RuntimeError("No audio generated."),
            )
        else:
            audio = np.concatenate(segments, axis=0)
            yield InferenceResult(
                code="final",
                audio=(sample_rate, audio),
                error=None,
            )

    @torch.inference_mode()
    def _generate(self, text, max_new_tokens, temperature_text, top_p_text, top_k_text,
                  temperature_codes, top_p_codes, top_k_codes) -> np.ndarray:
        if self.tokenizer is not None:
            input_ids = torch.tensor(
                self.tokenizer.encode(text, add_special_tokens=False),
                dtype=torch.long, device=self.llama_model.embeddings.weight.device,
            ).unsqueeze(0)
        else:
            raise ValueError("Tokenizer required for text encoding")

        if isinstance(self.llama_model, DualARTransformer):
            _, codes = generate_with_codes(
                self.llama_model,
                input_ids,
                max_new_tokens=max_new_tokens,
                temperature_text=temperature_text,
                top_p_text=top_p_text,
                top_k_text=top_k_text,
                temperature_codes=temperature_codes,
                top_p_codes=top_p_codes,
                top_k_codes=top_k_codes,
            )
        else:
            raise ValueError("Model must be DualARTransformer for codec generation")

        audio = self.decode_vq_tokens(codes)
        return audio.float().cpu().numpy()

    def decode_vq_tokens(self, codes: torch.Tensor) -> torch.Tensor:
        if isinstance(self.decoder_model, DAC):
            return self.decoder_model.from_indices(codes[None])[0].squeeze()
        raise ValueError(f"Unknown model type: {type(self.decoder_model)}")

    @torch.inference_mode()
    def encode_reference(self, audio: torch.Tensor, sample_rate: int):
        if audio.dim() == 1:
            audio = audio.unsqueeze(0).unsqueeze(0)
        elif audio.dim() == 2:
            audio = audio.unsqueeze(0)

        if sample_rate != self.decoder_model.sample_rate:
            resampler = torchaudio.transforms.Resample(sample_rate, self.decoder_model.sample_rate)
            audio = resampler(audio)

        audio = audio.to(self.decoder_model.encoder.first.conv.weight.device)
        audio_lengths = torch.tensor([audio.shape[2]], device=audio.device, dtype=torch.long)

        if isinstance(self.decoder_model, DAC):
            prompt_tokens = self.decoder_model.encode(audio, audio_lengths)[0][0]
            return prompt_tokens

        raise ValueError(f"Unknown model type: {type(self.decoder_model)}")
