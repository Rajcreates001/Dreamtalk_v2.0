# dreamtalk - Fastspeech2_HS Engine Adapter

class Fastspeech2HSEngine:
    """Adapter for Fastspeech2_HS (FastSpeech 2, 16 Indian languages)."""
    
    SUPPORTED_LANGUAGES = {
        'as': 'Assamese', 'bn': 'Bengali', 'gu': 'Gujarati',
        'hi': 'Hindi', 'kn': 'Kannada', 'ml': 'Malayalam',
        'mr': 'Marathi', 'or': 'Odia', 'pa': 'Punjabi',
        'ta': 'Tamil', 'te': 'Telugu', 'ur': 'Urdu',
        'brx': 'Bodo', 'mai': 'Maithili', 'mni': 'Manipuri',
        'raj': 'Rajasthani',
    }
    
    def __init__(self, model_dir=None, device=None):
        import os, torch
        self.device = device or os.environ.get("DREAMTALK_DEVICE") or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.synthesizer = Synthesizer(model_dir=model_dir, device=self.device) if model_dir else None
    
    def synthesize(self, text, lang='hi', speed=1.0):
        if self.synthesizer is None:
            raise RuntimeError("Fastspeech2_HS not initialized - provide model_dir")
        return self.synthesizer.synthesize(text, lang=lang, speed=speed)
    
    def is_ready(self):
        return self.synthesizer is not None
