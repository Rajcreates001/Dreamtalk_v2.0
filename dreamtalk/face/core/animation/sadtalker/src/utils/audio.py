# Dreamtalk - Face Engine
# Extracted from SadTalker
import librosa
import numpy as np


def load_wav(path, sr):
    wav, _ = librosa.load(path, sr=sr, mono=True)
    return wav


def melspectrogram(wav):
    mel = librosa.feature.melspectrogram(
        y=wav, sr=16000, n_fft=800, hop_length=200, win_length=800,
        n_mels=80, fmin=55, fmax=7600
    )
    mel = librosa.power_to_db(mel, ref=np.max)
    return mel
