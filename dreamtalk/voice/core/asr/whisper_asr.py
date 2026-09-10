# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: tools/asr/fasterwhisper_asr.py

import os
from faster_whisper import WhisperModel


class WhisperASR:
    def __init__(self, model_size: str = "medium", device: str = "cpu", compute_type: str = "float32"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str, language: str = None):
        segments, info = self.model.transcribe(audio_path, language=language)
        result = {"text": "", "segments": [], "language": info.language}
        full_text = []
        for seg in segments:
            full_text.append(seg.text)
            result["segments"].append({
                "start": seg.start, "end": seg.end, "text": seg.text,
            })
        result["text"] = " ".join(full_text)
        return result

    def transcribe_batch(self, audio_dir: str, output_dir: str = None):
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        results = {}
        import glob
        for audio_path in glob.glob(os.path.join(audio_dir, "*.wav")):
            base = os.path.basename(audio_path)
            result = self.transcribe(audio_path)
            results[base] = result
            if output_dir:
                txt_path = os.path.join(output_dir, base.replace(".wav", ".txt"))
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(result["text"])
        return results
