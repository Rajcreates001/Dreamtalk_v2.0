# Dreamtalk - Voice Engine
# Extracted from OpenVoice

import os
import glob
import torch
import hashlib
import base64
import numpy as np
import librosa
from glob import glob


def hash_numpy_array(audio_path):
    array, _ = librosa.load(audio_path, sr=None, mono=True)
    array_bytes = array.tobytes()
    hash_object = hashlib.sha256(array_bytes)
    hash_value = hash_object.digest()
    base64_value = base64.b64encode(hash_value)
    return base64_value.decode("utf-8")[:16].replace("/", "_^")


def get_se(audio_path, vc_model, target_dir="processed", vad=True):
    device = vc_model.device
    version = vc_model.version

    audio_name = f"{os.path.basename(audio_path).rsplit('.', 1)[0]}_{version}_{hash_numpy_array(audio_path)}"
    se_path = os.path.join(target_dir, audio_name, "se.pth")

    if vad:
        wavs_folder = split_audio_vad(audio_path, target_dir=target_dir, audio_name=audio_name)
    else:
        wavs_folder = split_audio_whisper(audio_path, target_dir=target_dir, audio_name=audio_name)

    audio_segs = glob(f"{wavs_folder}/*.wav")
    if len(audio_segs) == 0:
        raise NotImplementedError("No audio segments found!")

    return vc_model.extract_se(audio_segs, se_save_path=se_path), audio_name


def split_audio_vad(audio_path, audio_name, target_dir, split_seconds=10.0):
    from pydub import AudioSegment

    SAMPLE_RATE = 16000

    audio = AudioSegment.from_file(audio_path)
    audio_dur = audio.duration_seconds

    target_folder = os.path.join(target_dir, audio_name)
    wavs_folder = os.path.join(target_folder, "wavs")
    os.makedirs(wavs_folder, exist_ok=True)
    start_time = 0.0
    count = 0
    num_splits = int(np.round(audio_dur / split_seconds))
    assert num_splits > 0, "input audio is too short"
    interval = audio_dur / num_splits

    for i in range(num_splits):
        end_time = min(start_time + interval, audio_dur)
        if i == num_splits - 1:
            end_time = audio_dur
        output_file = f"{wavs_folder}/{audio_name}_seg{count}.wav"
        audio_seg = audio[int(start_time * 1000): int(end_time * 1000)]
        audio_seg.export(output_file, format="wav")
        start_time = end_time
        count += 1
    return wavs_folder


def split_audio_whisper(audio_path, audio_name, target_dir="processed"):
    from pydub import AudioSegment
    from faster_whisper import WhisperModel

    _whisper_dev = "cuda" if torch.cuda.is_available() else "cpu"
    _compute_type = "float16" if torch.cuda.is_available() else "int8"
    model = WhisperModel("medium", device=_whisper_dev, compute_type=_compute_type)
    audio = AudioSegment.from_file(audio_path)
    max_len = len(audio)

    target_folder = os.path.join(target_dir, audio_name)
    segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=True)
    segments = list(segments)

    os.makedirs(target_folder, exist_ok=True)
    wavs_folder = os.path.join(target_folder, "wavs")
    os.makedirs(wavs_folder, exist_ok=True)

    s_ind = 0
    start_time = None

    for k, w in enumerate(segments):
        if k == 0:
            start_time = max(0, w.start)

        end_time = w.end
        text = w.text.replace("...", "")

        audio_seg = audio[int(start_time * 1000): min(max_len, int(end_time * 1000) + 80)]
        fname = f"{audio_name}_seg{s_ind}.wav"

        save = audio_seg.duration_seconds > 1.5 and audio_seg.duration_seconds < 20.0 and len(text) >= 2 and len(text) < 200

        if save:
            output_file = os.path.join(wavs_folder, fname)
            audio_seg.export(output_file, format="wav")

        if k < len(segments) - 1:
            start_time = max(0, segments[k + 1].start - 0.08)

        s_ind = s_ind + 1
    return wavs_folder
