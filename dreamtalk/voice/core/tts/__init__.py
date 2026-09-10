import logging
import os

# Prevent OpenMP DLL conflict before any torch-dependent module imports
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

logger = logging.getLogger("dreamtalk.tts")

# Core modules (should always work)
from .tts_pipeline import TTS, TTS_Config
from .inference import DreamtalkTTS
from .ar_model import Text2SemanticDecoder
from .sovits_model import SynthesizerTrn, SynthesizerTrnV3, Generator
from .bigvgan import BigVGAN
from .feature_extract import CNHubert
from .text_frontend import TextFrontend

# Lazy-load optional TTS engines to avoid deep dependency chains
def _lazy_import(name, path, attr):
    try:
        mod = __import__(path, fromlist=[attr])
        obj = getattr(mod, attr)
        globals()[name] = obj
        return obj
    except Exception as e:
        logger.debug(f"Optional TTS engine '{name}' unavailable: {e}")
        return None

class LazyModule:
    def __init__(self, name, path, attr):
        self._name = name
        self._path = path
        self._attr = attr
        self._obj = None

    def __getattr__(self, attr):
        if self._obj is None:
            try:
                mod = __import__(self._path, fromlist=[self._attr])
                self._obj = mod
            except Exception as e:
                logger.debug(f"Optional engine '{self._name}' unavailable: {e}")
                raise AttributeError(attr)
        return getattr(self._obj, attr)

# Kokoro (82M param StyleTTS 2-based)
try:
    from .kokoro import KModel, KPipeline
except Exception as e:
    logger.debug(f"Kokoro unavailable: {e}")
    KModel = None
    KPipeline = None

try:
    from .kokoro_engine import KokoroTTSEngine
except Exception as e:
    logger.debug(f"KokoroTTSEngine unavailable: {e}")
    KokoroTTSEngine = None

# IndicF5
try:
    from .indicf5.api import F5TTS as IndicF5TTS
except Exception as e:
    logger.debug(f"IndicF5 unavailable: {e}")
    IndicF5TTS = None

try:
    from .indicf5_engine import IndicF5TTSEngine
except Exception as e:
    logger.debug(f"IndicF5TTSEngine unavailable: {e}")
    IndicF5TTSEngine = None

# Svara TTS
try:
    from .svara_tts_engine import SvaraTTSEngine
except Exception as e:
    logger.debug(f"SvaraTTSEngine unavailable: {e}")
    SvaraTTSEngine = None

# Indic TTS
try:
    from .indic_tts_engine import IndicTTSEngine
except Exception as e:
    logger.debug(f"IndicTTSEngine unavailable: {e}")
    IndicTTSEngine = None

# Fastspeech2 HS
try:
    from .fastspeech2_hs_engine import Fastspeech2HSEngine
except Exception as e:
    logger.debug(f"Fastspeech2HSEngine unavailable: {e}")
    Fastspeech2HSEngine = None

__all__ = [
    "TTS", "TTS_Config", "DreamtalkTTS",
    "Text2SemanticDecoder",
    "SynthesizerTrn", "SynthesizerTrnV3", "Generator",
    "BigVGAN", "CNHubert", "TextFrontend",
    "KModel", "KPipeline", "KokoroTTSEngine",
    "IndicF5TTS", "IndicF5TTSEngine",
    "SvaraTTSEngine", "IndicTTSEngine",
    "Fastspeech2HSEngine",
]
