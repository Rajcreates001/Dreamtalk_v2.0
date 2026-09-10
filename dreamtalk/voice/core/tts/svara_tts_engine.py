# dreamtalk - Svara-TTS Engine Adapter

import base64
from .svara_tts.tts_engine.orchestrator import SvaraTTSOrchestrator


class SvaraTTSEngine:
    """Adapter for Svara-TTS (LLM-based, 19 Indian languages, streaming, zero-shot cloning)."""
    
    SUPPORTED_LANGUAGES = {
        'hi': 'Hindi', 'bn': 'Bengali', 'mr': 'Marathi',
        'te': 'Telugu', 'kn': 'Kannada', 'bh': 'Bhojpuri',
        'mag': 'Magahi', 'hne': 'Chhattisgarhi', 'mai': 'Maithili',
        'as': 'Assamese', 'brx': 'Bodo', 'doi': 'Dogri',
        'gu': 'Gujarati', 'ml': 'Malayalam', 'pa': 'Punjabi',
        'ta': 'Tamil', 'en': 'English (Indian)', 'ne': 'Nepali',
        'sa': 'Sanskrit',
    }
    
    def __init__(self, model_name="kenpath/svara-tts-v1", device=None):
        import os, torch
        self.model_name = model_name
        self.device = device or os.environ.get("DREAMTALK_DEVICE") or ('cuda' if torch.cuda.is_available() else 'cpu')
        self._orchestrator = None
    
    @property
    def orchestrator(self):
        if self._orchestrator is None:
            self._orchestrator = SvaraTTSOrchestrator(model_name=self.model_name)
        return self._orchestrator
    
    def synthesize(self, text, voice='hi_female', lang='hi', stream=False):
        return self.orchestrator.synthesize(text, voice=voice, stream=stream)
    
    def list_voices(self):
        voices = {}
        for lang, name in self.SUPPORTED_LANGUAGES.items():
            voices[f"{lang}_male"] = f"{name} (Male)"
            voices[f"{lang}_female"] = f"{name} (Female)"
        return voices
    
    def clone_voice(self, audio_path, transcript=None):
        with open(audio_path, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        return {"reference_audio": audio_b64, "reference_transcript": transcript}
