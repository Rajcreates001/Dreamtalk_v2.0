# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/feature_extractor/cnhubert.py + whisper_enc.py

import torch
import os
import logging
import torch.nn as nn

from transformers import (
    Wav2Vec2FeatureExtractor,
    HubertModel,
    logging as tf_logging,
)

tf_logging.set_verbosity_error()
logging.getLogger("numba").setLevel(logging.WARNING)


class CNHubert(nn.Module):
    def __init__(self, base_path: str = None):
        super().__init__()
        if base_path is None:
            raise ValueError("base_path cannot be None")
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"CNHuBERT path not found: {base_path}")
        self.model = HubertModel.from_pretrained(base_path, local_files_only=True)
        self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(base_path, local_files_only=True)

    def forward(self, x):
        input_values = self.feature_extractor(x, return_tensors="pt", sampling_rate=16000).input_values.to(x.device)
        feats = self.model(input_values)["last_hidden_state"]
        return feats


def get_content(hmodel, wav_16k_tensor):
    with torch.no_grad():
        feats = hmodel(wav_16k_tensor)
    return feats.transpose(1, 2)


class WhisperEncoder:
    @staticmethod
    def get_model():
        import whisper
        _whisper_dev = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("small", device=_whisper_dev)
        return model.encoder

    @staticmethod
    def get_content(model=None, wav_16k_tensor=None):
        from whisper import log_mel_spectrogram, pad_or_trim
        dev = next(model.parameters()).device
        mel = log_mel_spectrogram(wav_16k_tensor).to(dev)[:, :3000]
        feature_len = mel.shape[-1] // 2
        assert mel.shape[-1] < 3000, "Input audio too long, only audio within 30s is allowed"
        with torch.no_grad():
            feature = model(pad_or_trim(mel, 3000).unsqueeze(0))[:1, :feature_len, :].transpose(1, 2)
        return feature
