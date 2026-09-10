import logging
import os
import pathlib
import numpy as np
from typing import List, Optional, Dict, Tuple

logger = logging.getLogger("dreamtalk.voice.kokoro")

# --- Auto-configure project-local espeak-ng for non-English TTS (Hindi, Spanish, etc.) ---
def _setup_espeak_ng():
    """
    Automatically detect and configure the project-local espeak-ng installation
    so that phonemizer/misaki can use it without manual environment variable setup.
    
    Looks for espeak-ng/ alongside this file (up 4 dirs to project root).
    Respects user-set PHONEMIZER_ESPEAK_LIBRARY if already configured.
    """
    if os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        return  # User has explicit config, don't override
    
    # Find project root: voice/core/tts/kokoro_engine.py -> 4 levels up
    here = pathlib.Path(__file__).resolve().parent
    project_root = here.parent.parent.parent
    
    espeak_dir = project_root / "espeak-ng"
    lib_path = espeak_dir / "libespeak-ng.dll"
    data_path = espeak_dir / "espeak-ng-data"
    
    if lib_path.exists() and data_path.is_dir():
        os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = str(lib_path.resolve())
        os.environ["ESPEAK_DATA_PATH"] = str(data_path.resolve())
        logger.info(
            "Using project-local espeak-ng: %s",
            lib_path.resolve(),
        )

_setup_espeak_ng()
# ---------------------------------------------------------------------------

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from .kokoro import KPipeline

VOICE_METADATA: Dict[str, Dict] = {
    "af_heart": { "display": "Heart", "gender": "female", "lang": "a", "quality": "A", "category": "american_female" },
    "af_alloy": { "display": "Alloy", "gender": "female", "lang": "a", "quality": "C", "category": "american_female" },
    "af_aoede": { "display": "Aoede", "gender": "female", "lang": "a", "quality": "C+", "category": "american_female" },
    "af_bella": { "display": "Bella", "gender": "female", "lang": "a", "quality": "A-", "category": "american_female" },
    "af_jessica": { "display": "Jessica", "gender": "female", "lang": "a", "quality": "D", "category": "american_female" },
    "af_kore": { "display": "Kore", "gender": "female", "lang": "a", "quality": "C+", "category": "american_female" },
    "af_nicole": { "display": "Nicole", "gender": "female", "lang": "a", "quality": "B-", "category": "american_female" },
    "af_nova": { "display": "Nova", "gender": "female", "lang": "a", "quality": "C", "category": "american_female" },
    "af_river": { "display": "River", "gender": "female", "lang": "a", "quality": "D", "category": "american_female" },
    "af_sarah": { "display": "Sarah", "gender": "female", "lang": "a", "quality": "C+", "category": "american_female" },
    "af_sky": { "display": "Sky", "gender": "female", "lang": "a", "quality": "C-", "category": "american_female" },
    "am_adam": { "display": "Adam", "gender": "male", "lang": "a", "quality": "F+", "category": "american_male" },
    "am_echo": { "display": "Echo", "gender": "male", "lang": "a", "quality": "D", "category": "american_male" },
    "am_eric": { "display": "Eric", "gender": "male", "lang": "a", "quality": "D", "category": "american_male" },
    "am_fenrir": { "display": "Fenrir", "gender": "male", "lang": "a", "quality": "C+", "category": "american_male" },
    "am_liam": { "display": "Liam", "gender": "male", "lang": "a", "quality": "D", "category": "american_male" },
    "am_michael": { "display": "Michael", "gender": "male", "lang": "a", "quality": "C+", "category": "american_male" },
    "am_onyx": { "display": "Onyx", "gender": "male", "lang": "a", "quality": "D", "category": "american_male" },
    "am_puck": { "display": "Puck", "gender": "male", "lang": "a", "quality": "C+", "category": "american_male" },
    "am_santa": { "display": "Santa", "gender": "male", "lang": "a", "quality": "D-", "category": "american_male" },
    "bf_alice": { "display": "Alice", "gender": "female", "lang": "b", "quality": "D", "category": "british_female" },
    "bf_emma": { "display": "Emma", "gender": "female", "lang": "b", "quality": "B-", "category": "british_female" },
    "bf_isabella": { "display": "Isabella", "gender": "female", "lang": "b", "quality": "C", "category": "british_female" },
    "bf_lily": { "display": "Lily", "gender": "female", "lang": "b", "quality": "D", "category": "british_female" },
    "bm_daniel": { "display": "Daniel", "gender": "male", "lang": "b", "quality": "D", "category": "british_male" },
    "bm_fable": { "display": "Fable", "gender": "male", "lang": "b", "quality": "C", "category": "british_male" },
    "bm_george": { "display": "George", "gender": "male", "lang": "b", "quality": "C", "category": "british_male" },
    "bm_lewis": { "display": "Lewis", "gender": "male", "lang": "b", "quality": "D+", "category": "british_male" },
    "jf_alpha": { "display": "Alpha", "gender": "female", "lang": "j", "quality": "C+", "category": "japanese_female" },
    "jf_gongitsune": { "display": "Gongitsune", "gender": "female", "lang": "j", "quality": "C", "category": "japanese_female" },
    "jf_nezumi": { "display": "Nezumi", "gender": "female", "lang": "j", "quality": "C-", "category": "japanese_female" },
    "jf_tebukuro": { "display": "Tebukuro", "gender": "female", "lang": "j", "quality": "C", "category": "japanese_female" },
    "jm_kumo": { "display": "Kumo", "gender": "male", "lang": "j", "quality": "C-", "category": "japanese_male" },
    "zf_xiaobei": { "display": "Xiaobei", "gender": "female", "lang": "z", "quality": "D", "category": "chinese_female" },
    "zf_xiaoni": { "display": "Xiaoni", "gender": "female", "lang": "z", "quality": "D", "category": "chinese_female" },
    "zf_xiaoxiao": { "display": "Xiaoxiao", "gender": "female", "lang": "z", "quality": "D", "category": "chinese_female" },
    "zf_xiaoyi": { "display": "Xiaoyi", "gender": "female", "lang": "z", "quality": "D", "category": "chinese_female" },
    "zm_yunjian": { "display": "Yunjian", "gender": "male", "lang": "z", "quality": "D", "category": "chinese_male" },
    "zm_yunxi": { "display": "Yunxi", "gender": "male", "lang": "z", "quality": "D", "category": "chinese_male" },
    "zm_yunxia": { "display": "Yunxia", "gender": "male", "lang": "z", "quality": "D", "category": "chinese_male" },
    "zm_yunyang": { "display": "Yunyang", "gender": "male", "lang": "z", "quality": "D", "category": "chinese_male" },
    "ef_dora": { "display": "Dora", "gender": "female", "lang": "e", "quality": "B", "category": "spanish_female" },
    "em_alex": { "display": "Alex", "gender": "male", "lang": "e", "quality": "B", "category": "spanish_male" },
    "em_santa": { "display": "Santa", "gender": "male", "lang": "e", "quality": "B", "category": "spanish_male" },
    "ff_siwis": { "display": "Siwis", "gender": "female", "lang": "f", "quality": "B-", "category": "french_female" },
    "hf_alpha": { "display": "Alpha", "gender": "female", "lang": "h", "quality": "C", "category": "hindi_female" },
    "hf_beta": { "display": "Beta", "gender": "female", "lang": "h", "quality": "C", "category": "hindi_female" },
    "hm_omega": { "display": "Omega", "gender": "male", "lang": "h", "quality": "C", "category": "hindi_male" },
    "hm_psi": { "display": "Psi", "gender": "male", "lang": "h", "quality": "C", "category": "hindi_male" },
    "if_sara": { "display": "Sara", "gender": "female", "lang": "i", "quality": "C", "category": "italian_female" },
    "im_nicola": { "display": "Nicola", "gender": "male", "lang": "i", "quality": "C", "category": "italian_male" },
    "pf_dora": { "display": "Dora", "gender": "female", "lang": "p", "quality": "B", "category": "portuguese_female" },
    "pm_alex": { "display": "Alex", "gender": "male", "lang": "p", "quality": "B", "category": "portuguese_male" },
    "pm_santa": { "display": "Santa", "gender": "male", "lang": "p", "quality": "B", "category": "portuguese_male" },
}

VOICE_CATEGORIES: Dict[str, List[str]] = {}
for vid, meta in VOICE_METADATA.items():
    cat = meta["category"]
    if cat not in VOICE_CATEGORIES:
        VOICE_CATEGORIES[cat] = []
    VOICE_CATEGORIES[cat].append(vid)

SUPPORTED_LANGUAGES = {
    "a": "American English",
    "b": "British English",
    "e": "Spanish",
    "f": "French",
    "h": "Hindi",
    "i": "Italian",
    "p": "Brazilian Portuguese",
    "j": "Japanese",
    "z": "Mandarin Chinese",
}

EMOTION_VOICE_MAP: Dict[str, str] = {
    "happy": "af_heart",
    "sad": "af_nicole",
    "angry": "am_adam",
    "surprised": "af_bella",
    "fearful": "af_sky",
    "disgusted": "am_michael",
    "neutral": "af_heart",
}

EMOTION_DESCRIPTION_MAP: Dict[str, str] = {
    "happy": "bright, cheerful",
    "sad": "soft, melancholic",
    "angry": "firm, assertive",
    "surprised": "bright, raised pitch",
    "fearful": "soft, breathy",
    "disgusted": "flat, firm",
    "neutral": "balanced, neutral",
}

QUALITY_BEST = ["af_heart", "af_bella", "af_nicole", "bf_emma", "ff_siwis", "ef_dora", "pf_dora", "hf_alpha", "if_sara", "jf_alpha", "bm_george", "am_michael", "am_fenrir"]
QUALITY_FALLBACK = ["af_heart", "af_alloy", "af_sarah", "bf_emma", "bf_isabella", "bm_fable", "am_adam", "am_michael"]

class KokoroTTSEngine:
    SUPPORTED_LANGUAGES = SUPPORTED_LANGUAGES

    def __init__(self, device: Optional[str] = None, weights_dir: Optional[str] = None):
        self.device = device or "cpu"
        self.weights_dir = weights_dir
        self._pipelines: Dict[str, KPipeline] = {}

    def _get_pipeline(self, lang_code: str) -> KPipeline:
        if lang_code not in self._pipelines:
            self._pipelines[lang_code] = KPipeline(
                lang_code=lang_code, weights_dir=self.weights_dir,
            )
        return self._pipelines[lang_code]

    def detect_language(self, text: str) -> str:
        script_ranges = {
            "z": (0x4E00, 0x9FFF),
            "j": (0x3040, 0x30FF),
            "h": (0x0900, 0x097F),
        }
        for code, (start, end) in script_ranges.items():
            if any(start <= ord(c) <= end for c in text):
                return code
        return "a"

    def select_voice_for_emotion(self, emotion: Optional[str] = None, gender: Optional[str] = None) -> str:
        if emotion and emotion.lower() in EMOTION_VOICE_MAP:
            return EMOTION_VOICE_MAP[emotion.lower()]
        if gender and gender.lower() == "male":
            return "am_adam"
        return "af_heart"

    def select_best_voice(self, lang_code: str = "a", gender: Optional[str] = None, quality_hint: str = "best") -> str:
        candidates = []
        for vid, meta in VOICE_METADATA.items():
            if meta["lang"] == lang_code:
                if gender and meta["gender"] == gender:
                    candidates.append(vid)
                elif not gender:
                    candidates.append(vid)
        if not candidates:
            candidates = [vid for vid in QUALITY_BEST if VOICE_METADATA[vid]["lang"] == lang_code]
        if not candidates:
            return "af_heart"
        if quality_hint == "best":
            for vid in QUALITY_BEST:
                if vid in candidates:
                    return vid
        return candidates[0]

    def synthesize(
        self,
        text: str,
        voice: str = "af_heart",
        lang_code: str = "a",
        speed: float = 1.0,
        emotion: Optional[str] = None,
    ) -> List[np.ndarray]:
        if emotion:
            voice = self.select_voice_for_emotion(emotion)
        if lang_code == "auto":
            lang_code = self.detect_language(text)
        pipeline = self._get_pipeline(lang_code)
        audio_chunks: List[np.ndarray] = []
        try:
            for gs, ps, audio in pipeline(text, voice=voice, speed=speed):
                # KModel returns torch tensors; normalize to numpy for callers
                audio_chunks.append(np.asarray(audio))
        except Exception as e:
            logger.warning(f"Kokoro synthesis failed with {voice}/{lang_code}: {e}")
            if lang_code != "a":
                logger.info("Falling back to American English pipeline")
                pipeline = self._get_pipeline("a")
                for gs, ps, audio in pipeline(text, voice=voice, speed=speed):
                    audio_chunks.append(np.asarray(audio))
            else:
                fallback_voices = QUALITY_FALLBACK
                for fv in fallback_voices:
                    if fv == voice:
                        continue
                    try:
                        for gs, ps, audio in pipeline(text, voice=fv, speed=speed):
                            audio_chunks.append(np.asarray(audio))
                        break
                    except Exception:
                        continue
        return audio_chunks

    def synthesize_full(self, text: str, voice: str = "af_heart", lang_code: str = "a", speed: float = 1.0) -> Optional[np.ndarray]:
        chunks = self.synthesize(text, voice=voice, lang_code=lang_code, speed=speed)
        if chunks:
            return np.concatenate(chunks)
        return None

    def voice_mix(self, text: str, voice_a: str, voice_b: str, mix_ratio: float = 0.5, lang_code: str = "a", speed: float = 1.0) -> Optional[np.ndarray]:
        chunks_a = self.synthesize(text, voice=voice_a, lang_code=lang_code, speed=speed)
        chunks_b = self.synthesize(text, voice=voice_b, lang_code=lang_code, speed=speed)
        if not chunks_a or not chunks_b:
            return None
        audio_a = np.concatenate(chunks_a)
        audio_b = np.concatenate(chunks_b)
        min_len = min(len(audio_a), len(audio_b))
        mixed = (audio_a[:min_len] * (1 - mix_ratio) + audio_b[:min_len] * mix_ratio)
        return mixed

    def list_voices_by_category(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        if category and category in VOICE_CATEGORIES:
            return {category: VOICE_CATEGORIES[category]}
        return VOICE_CATEGORIES

    def list_voices(self) -> Dict[str, str]:
        all_voices: Dict[str, str] = {}
        for vid, meta in VOICE_METADATA.items():
            all_voices[vid] = f"{meta['display']} ({meta['category'].replace('_', ' ').title()}, Quality: {meta['quality']})"
        return all_voices

    def get_voice_info(self, voice: str) -> Optional[Dict]:
        return VOICE_METADATA.get(voice)

    def synthesize_from_tokens(self, tokens, voice: str = "af_heart", lang_code: str = "a", speed: float = 1.0) -> Optional[np.ndarray]:
        pipeline = self._get_pipeline(lang_code)
        audio_chunks = []
        try:
            for gs, ps, audio in pipeline(tokens, voice=voice, speed=speed):
                audio_chunks.append(np.asarray(audio))
        except Exception as e:
            logger.warning(f"Token synthesis failed: {e}")
            return None
        if audio_chunks:
            return np.concatenate(audio_chunks)
        return None
