# dreamtalk - Indic-TTS Engine Adapter

# Heavy imports are lazy-loaded to avoid hangs on Python 3.11 startup


class IndicTTSEngine:
    """Adapter for Indic-TTS (AI4Bharat, FastPitch+HiFi-GAN, 13 Indian languages).
    
    Lazy-loads the underlying TextToSpeechEngine only when actually used,
    so importing this class doesn't trigger heavy dependency chains.
    """
    
    SUPPORTED_LANGUAGES = {
        'as': 'Assamese', 'bn': 'Bengali', 'brx': 'Bodo',
        'gu': 'Gujarati', 'hi': 'Hindi', 'kn': 'Kannada',
        'ml': 'Malayalam', 'mni': 'Manipuri', 'mr': 'Marathi',
        'or': 'Odia', 'raj': 'Rajasthani', 'ta': 'Tamil',
        'te': 'Telugu', 'en': 'English (Indian)', 'hne': 'Hinglish',
    }
    
    def __init__(self, model_dir=None, device=None):
        import os, torch
        self.device = device or os.environ.get("DREAMTALK_DEVICE") or ('cuda' if torch.cuda.is_available() else 'cpu')
        self._engine = None
        self._model_dir = model_dir
        if model_dir:
            self._lazy_init_engine()
    
    def _lazy_init_engine(self):
        """Lazy-init the underlying TextToSpeechEngine to avoid heavy import chains at module level."""
        if self._engine is not None:
            return
        from .indic_tts.inference.src.inference import TextToSpeechEngine
        from .indic_tts.inference.src.models.request import TTSRequest
        self._TTSRequest = TTSRequest
        self._engine = TextToSpeechEngine(model_dir=self._model_dir, device=self.device)
    
    def synthesize(self, text, lang='hi', speaker_id=None):
        self._lazy_init_engine()
        if self._engine is None:
            raise RuntimeError("Indic-TTS engine not initialized - provide model_dir")
        request = self._TTSRequest(text=text, language=lang, speaker_id=speaker_id)
        response = self._engine.synthesize(request)
        return response.audio, response.sample_rate
    
    def is_ready(self):
        return self._engine is not None
