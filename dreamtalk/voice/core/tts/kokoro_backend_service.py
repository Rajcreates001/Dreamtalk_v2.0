# Dreamtalk — Kokoro TTS backend service
# Uses local RTX 4060 for inference. Falls back to CPU if GPU unavailable.

import os
import uuid
import numpy as np
from pathlib import Path
from typing import Optional


class KokoroVoiceService:
    """Wraps KokoroTTSEngine with file output and device detection.

    Initialization is deferred so that import of this module does not
    trigger the full voice pipeline (torchaudio, etc.).
    """

    def __init__(self, device: Optional[str] = None):
        self.device = device or self._detect_device()
        self._engine = None
        self.output_dir = Path("voice_module/assets/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def engine(self):
        if self._engine is None:
            from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
            self._engine = KokoroTTSEngine(device=self.device)
        return self._engine

    @staticmethod
    def _detect_device() -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def synthesize(
        self,
        text: str,
        voice: str = "am_adam",
        lang_code: str = "a",
        speed: float = 1.0,
    ) -> str:
        audio_chunks = self.engine.synthesize(
            text=text, voice=voice, lang_code=lang_code, speed=speed
        )
        combined = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
        filename = f"kokoro_{uuid.uuid4().hex}.wav"
        filepath = self.output_dir / filename
        self._save_wav(combined, filepath)
        return str(filepath)

    @staticmethod
    def _save_wav(audio: np.ndarray, path: Path):
        import soundfile as sf
        sf.write(str(path), audio, samplerate=24000)

    def list_voices(self) -> dict:
        return self.engine.list_voices()
