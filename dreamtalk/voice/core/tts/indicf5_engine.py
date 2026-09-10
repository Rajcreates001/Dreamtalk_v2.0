# dreamtalk - IndicF5 TTS Engine Adapter
import os

# Windows OpenMP DLL conflict fix: espeak-ng (Kokoro) loads libomp.dll while
# torch loads libiomp5md.dll. Setting this env var BEFORE any torch import
# allows both to coexist without crashing.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import pathlib
import logging
from typing import Optional

logger = logging.getLogger("dreamtalk.voice.tts.indicf5")

# ── Fix jieba vs setuptools incompatibility ────────────────────────────
# jieba/_compat.py uses pkg_resources.resource_stream() which was removed
# from setuptools >= 69.0. The project has setuptools 80.9.0, so any
# call to jieba.initialize() crashes with AttributeError.
#
# jieba has TWO code paths that import get_module_res locally via
# `from ._compat import get_module_res` — get_abs_path_dict() AND
# get_dict_file(). Both need patching since the local import in
# jieba.__init__ is a separate copy from jieba._compat.get_module_res.
# -----------------------------------------------------------------------
try:
    import jieba
    import jieba._compat as _jiebac
    _jieba_dir = os.path.dirname(os.path.abspath(jieba.__file__))
    _DICT_NAME = "dict.txt"

    def _patched_get_module_res(*res):
        """Reads jieba resources from filesystem instead of pkg_resources."""
        return open(os.path.normpath(os.path.join(_jieba_dir, *res)), "rb")

    # Patch 1: the module-level reference (covers direct jieba._compat usage)
    _jiebac.get_module_res = _patched_get_module_res

    # Patch 2: jieba.__init__'s local import `from ._compat import get_module_res`
    # The `from-import` creates `jieba.get_module_res` in jieba's module namespace.
    if hasattr(jieba, "get_module_res"):
        jieba.get_module_res = _patched_get_module_res

    # Patch 3: get_abs_path_dict() also uses the locally-imported get_module_res
    def _patched_get_abs_path_dict():
        from jieba._compat import default_encoding
        import pkgutil
        try:
            data = pkgutil.get_data("jieba", _DICT_NAME)
            if data is not None:
                return [(_DICT_NAME, data.decode(default_encoding).splitlines())]
        except Exception:
            pass
        dict_path = os.path.normpath(os.path.join(_jieba_dir, _DICT_NAME))
        with open(dict_path, encoding="utf-8") as f:
            return [(_DICT_NAME, f.read().splitlines())]

    if hasattr(jieba, "get_abs_path_dict"):
        jieba.get_abs_path_dict = _patched_get_abs_path_dict

    # Patch 4: get_dict_file() is called by initialize() after get_abs_path_dict()
    def _patched_get_dict_file():
        return open(os.path.normpath(os.path.join(_jieba_dir, _DICT_NAME)), "rb")

    if hasattr(jieba, "get_dict_file"):
        jieba.get_dict_file = _patched_get_dict_file

    logger.debug("Patched jieba to bypass removed pkg_resources API")
except Exception as _p:
    logger.debug("jieba patching not needed or failed: %s", _p)
# ────────────────────────────────────────────────────────────────────────

# ── Project root & weight path detection ──────────────────────────
# voice/core/tts/indicf5_engine.py -> 4 levels up to dreamtalk/
_INDIC_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
_INDIC_WEIGHTS_DIR = _INDIC_ROOT / "weights" / "voice" / "indic_tts" / "IndicF5"
_INDIC_MODEL_PATH = str(_INDIC_WEIGHTS_DIR / "model.safetensors")
_INDIC_VOCAB_PATH = str(_INDIC_WEIGHTS_DIR / "checkpoints" / "vocab.txt")
_INDIC_CONFIG_PATH = str(_INDIC_WEIGHTS_DIR / "config.json")


class IndicF5TTSEngine:
    """Adapter for IndicF5 TTS (CFM-based, 11 Indian languages, voice cloning).

    Uses locally downloaded weights from weights/voice/indic_tts/IndicF5/.
    Raises FileNotFoundError if weights are not present locally.
    """

    SUPPORTED_LANGUAGES = {
        'as': 'Assamese', 'bn': 'Bengali', 'gu': 'Gujarati',
        'hi': 'Hindi', 'kn': 'Kannada', 'ml': 'Malayalam',
        'mr': 'Marathi', 'or': 'Odia', 'pa': 'Punjabi',
        'ta': 'Tamil', 'te': 'Telugu', 'en': 'English',
    }

    REQUIRED_FILES = {
        "model.safetensors": _INDIC_MODEL_PATH,
        "checkpoints/vocab.txt": _INDIC_VOCAB_PATH,
        "config.json": _INDIC_CONFIG_PATH,
    }

    def __init__(self, model_type="F5-TTS", device=None):
        import torch
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        if self.device == "cpu":
            # Default is physical cores only; all logical cores is ~12% faster
            torch.set_num_threads(os.cpu_count() or torch.get_num_threads())
        self._model = None
        self._loaded = False

        # Validate local weights exist — no HuggingFace fallback
        missing = [name for name, path in self.REQUIRED_FILES.items() if not os.path.exists(path)]
        if missing:
            raise FileNotFoundError(
                f"Local IndicF5 weights not found. Missing files in {_INDIC_WEIGHTS_DIR}:\n"
                + "\n".join(f"  - {f}" for f in missing)
                + "\n\nDownload weights with:\n"
                + "  python scripts/download_weights.py"
            )

        logger.info("Using local IndicF5 weights: %s", _INDIC_WEIGHTS_DIR)

        # Initialize model with local paths
        from .indicf5.api import F5TTS
        self._model = F5TTS(
            model_type=model_type,
            ckpt_file=_INDIC_MODEL_PATH,
            vocab_file=_INDIC_VOCAB_PATH,
            device=self.device,
        )
        self._loaded = True
        logger.info("IndicF5 engine initialized on %s with local weights", self.device)

    def synthesize(self, text, ref_audio_path=None, ref_text=None, lang='hi'):
        """Synthesize speech in the voice of ref_audio, speaking the given text."""
        if self._model is None:
            logger.warning("IndicF5 not loaded")
            return None, 0

        if not ref_audio_path:
            logger.warning("No reference audio provided for voice cloning")
            return None, 0

        wav, sr, _ = self._model.infer(
            ref_file=ref_audio_path,
            ref_text=ref_text or "",
            gen_text=text,
        )
        return wav, sr

    def clone_voice(self, audio_path, transcript=None):
        """Prepare voice clone config: returns ref_audio path + ref_text."""
        if not os.path.exists(audio_path):
            logger.warning("Reference audio not found: %s", audio_path)
            return {"ref_audio": None, "ref_text": ""}
        return {"ref_audio": audio_path, "ref_text": transcript or ""}

    @property
    def is_loaded(self) -> bool:
        return self._loaded
