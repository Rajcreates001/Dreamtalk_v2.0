# Dreamtalk - Voice Engine
# Silero VAD integration

import torch
import numpy as np


class SileroVAD:
    def __init__(self, model_path: str = None, device: str = "cpu"):
        self.device = torch.device(device)
        if model_path is None:
            self.model, self.utils = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False)
        else:
            self.model = torch.jit.load(model_path)
            self.utils = None
        self.model.eval()
        self.get_speech_timestamps = None
        if self.utils:
            self.get_speech_timestamps = self.utils[0]

    def get_timestamps(self, audio: np.ndarray, sr: int = 16000):
        audio_tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            timestamps = self.model.get_speech_timestamps(audio_tensor, sampling_rate=sr)
        return timestamps

    def is_speech(self, audio: np.ndarray, sr: int = 16000):
        audio_tensor = torch.tensor(audio, dtype=torch.float32)
        with torch.no_grad():
            prob = self.model(audio_tensor, sr).item()
        return prob > 0.5
