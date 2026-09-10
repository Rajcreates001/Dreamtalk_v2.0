import logging
import os

# Prevent OpenMP DLL conflict before any torch-dependent imports
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

logger = logging.getLogger("dreamtalk.voice")

# Core modules
from .core.tts.inference import DreamtalkTTS
from .core.tts.tts_pipeline import TTS, TTS_Config
from .models.config import Config

# Lazy-load optional TTS engine adapters
def _lazy(name, import_path):
    try:
        mod = __import__(import_path, fromlist=[name])
        obj = getattr(mod, name)
        globals()[name] = obj
        return obj
    except Exception as e:
        logger.debug(f"Optional voice engine '{name}' unavailable: {e}")
        globals()[name] = None
        return None

_lazy("KokoroTTSEngine", "dreamtalk.voice.core.tts.kokoro_engine")
_lazy("IndicF5TTSEngine", "dreamtalk.voice.core.tts.indicf5_engine")
_lazy("SvaraTTSEngine", "dreamtalk.voice.core.tts.svara_tts_engine")
_lazy("IndicTTSEngine", "dreamtalk.voice.core.tts.indic_tts_engine")
_lazy("Fastspeech2HSEngine", "dreamtalk.voice.core.tts.fastspeech2_hs_engine")

__all__ = [
    "DreamtalkTTS", "TTS", "TTS_Config", "Config",
    "KokoroTTSEngine", "IndicF5TTSEngine",
    "SvaraTTSEngine", "IndicTTSEngine", "Fastspeech2HSEngine",
]
