import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import numpy as np

# ── Cloned voice profiles storage ───────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/services/ -> 3 levels up
_CLONED_VOICES_FILE = str(_PROJECT_ROOT / "results" / "cloned_voice_profiles.json")


def _load_cloned_voices() -> Dict:
    """Load cloned voice profiles from JSON file."""
    if os.path.exists(_CLONED_VOICES_FILE):
        try:
            with open(_CLONED_VOICES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cloned_voices(voices: Dict):
    """Save cloned voice profiles to JSON file."""
    os.makedirs(os.path.dirname(_CLONED_VOICES_FILE), exist_ok=True)
    with open(_CLONED_VOICES_FILE, "w") as f:
        json.dump(voices, f, indent=2)


# ── ISO → Kokoro language code mapping ─────────────────────────────
# Kokoro natively supports these language codes:
#   a = American English,  b = British English,  e = Spanish,
#   f = French,            h = Hindi,            i = Italian,
#   p = Brazilian Portuguese,  j = Japanese,    z = Mandarin Chinese
#
# This mapping covers ISO 639-1 codes, BCP-47 tags, and regional variants.
# Languages without native Kokoro support fall back to American English ("a").
_ISO_TO_KOKORO = {
    # ── Native Kokoro languages (exact match) ──────────────────────
    "a": "a",  # Kokoro code passthrough
    "b": "b",
    "e": "e",
    "f": "f",
    "h": "h",
    "i": "i",
    "p": "p",
    "j": "j",
    "z": "z",

    # ── English ────────────────────────────────────────────────────
    "en":    "a",   # English → American English (default)
    "en-us": "a",   # American English
    "en-gb": "b",   # British English
    "en-au": "b",   # Australian → British English
    "en-in": "a",   # Indian English → American English

    # ── Hindi ──────────────────────────────────────────────────────
    "hi":    "h",   # Hindi
    "hi-in": "h",   # Hindi (India)

    # ── Spanish ────────────────────────────────────────────────────
    "es":    "e",   # Spanish (default)
    "es-es": "e",   # Spanish (Spain)
    "es-mx": "e",   # Spanish (Mexico)
    "es-ar": "e",   # Spanish (Argentina)
    "es-co": "e",   # Spanish (Colombia)

    # ── French ─────────────────────────────────────────────────────
    "fr":    "f",   # French (default)
    "fr-fr": "f",   # French (France)
    "fr-ca": "f",   # French (Canada)
    "fr-be": "f",   # French (Belgium)
    "fr-ch": "f",   # French (Switzerland)

    # ── Italian ────────────────────────────────────────────────────
    "it":    "i",   # Italian (default)
    "it-it": "i",   # Italian (Italy)

    # ── Portuguese ─────────────────────────────────────────────────
    "pt":     "p",  # Portuguese (default) → Brazilian Portuguese
    "pt-br":  "p",  # Brazilian Portuguese
    "pt-pt":  "p",  # Portuguese (Portuguese) → Brazilian Portuguese
    "pt-ao":  "p",  # Portuguese (Angola) → Brazilian Portuguese

    # ── Japanese ───────────────────────────────────────────────────
    "ja":    "j",   # Japanese (default)
    "ja-jp": "j",   # Japanese (Japan)

    # ── Mandarin Chinese ───────────────────────────────────────────
    "zh":    "z",   # Chinese (default) → Mandarin
    "zh-cn": "z",   # Mandarin (Simplified)
    "zh-tw": "z",   # Mandarin (Traditional) → Mandarin
    "zh-hk": "z",   # Cantonese → Mandarin (fallback, Kokoro doesn't have Cantonese)

    # ── Indian languages (no native Kokoro support → American English fallback) ──
    "ta": "a",   # Tamil
    "te": "a",   # Telugu
    "ml": "a",   # Malayalam
    "kn": "a",   # Kannada
    "mr": "a",   # Marathi
    "bn": "a",   # Bengali
    "gu": "a",   # Gujarati
    "pa": "a",   # Punjabi
    "or": "a",   # Odia
    "as": "a",   # Assamese
    "ur": "a",   # Urdu

    # ── German (no native Kokoro support) ──────────────────────────
    "de": "a",   # German
    "de-de": "a",

    # ── Russian (no native Kokoro support) ─────────────────────────
    "ru": "a",   # Russian
    "ru-ru": "a",

    # ── Arabic (no native Kokoro support) ──────────────────────────
    "ar": "a",   # Arabic
    "ar-sa": "a",

    # ── Korean (no native Kokoro support) ──────────────────────────
    "ko": "a",   # Korean
    "ko-kr": "a",

    # ── Dutch (no native Kokoro support) ───────────────────────────
    "nl": "a",   # Dutch
    "nl-nl": "a",

    # ── Swedish (no native Kokoro support) ─────────────────────────
    "sv": "a",   # Swedish
    "sv-se": "a",

    # ── Thai (no native Kokoro support) ────────────────────────────
    "th": "a",   # Thai
    "th-th": "a",

    # ── Turkish (no native Kokoro support) ─────────────────────────
    "tr": "a",   # Turkish
    "tr-tr": "a",

    # ── Polish (no native Kokoro support) ──────────────────────────
    "pl": "a",   # Polish
    "pl-pl": "a",

    # ── Vietnamese (no native Kokoro support) ──────────────────────
    "vi": "a",   # Vietnamese
    "vi-vn": "a",
}

# Languages that Kokoro supports natively (for display purposes)
_NATIVE_LANGUAGES = {
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


def _map_iso_to_kokoro(code: str) -> str:
    """Map an ISO language code or Kokoro single-letter code to a valid Kokoro code."""
    # If it's already a valid Kokoro code, return as-is
    if code in _NATIVE_LANGUAGES:
        return code
    # Try the ISO map
    mapped = _ISO_TO_KOKORO.get(code, "a")
    return mapped





class VoiceOrchestrator:
    def __init__(self):
        self._kokoro_engine = None
        self._kokoro_available = self._check_kokoro()
        self._rvc_converter = None
        self._rvc_available = False

    @property
    def kokoro_engine(self):
        if self._kokoro_engine is None:
            from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
            self._kokoro_engine = KokoroTTSEngine()
        return self._kokoro_engine

    @property
    def rvc_converter(self):
        if self._rvc_converter is None:
            try:
                from dreamtalk.voice.core.vc.rvc.rvc_converter import RVCConverter, get_best_pretrained_path, check_weights_available
                weights = check_weights_available()
                if all(weights.values()):
                    model_path = get_best_pretrained_path()
                    if model_path:
                        self._rvc_converter = RVCConverter(model_path=model_path, device="cpu")
                        self._rvc_available = self._rvc_converter.is_loaded
                    else:
                        self._rvc_converter = None
                        self._rvc_available = False
                else:
                    missing = [k for k, v in weights.items() if not v]
                    print(f"RVC weights missing: {missing}")
                    self._rvc_converter = None
                    self._rvc_available = False
            except Exception as e:
                print(f"RVC init failed: {e}")
                self._rvc_converter = None
                self._rvc_available = False
        return self._rvc_converter

    @property
    def rvc_available(self) -> bool:
        if self._rvc_converter is None:
            return self.rvc_converter is not None and self._rvc_available
        return self._rvc_available

    @staticmethod
    def _check_kokoro() -> bool:
        try:
            import soundfile
            import numpy as np
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_indicf5_health() -> bool:
        """Check if the IndicF5 microservice is actually reachable on port 8003.
        This is a synchronous method — call via _check_indicf5_health_async()
        to avoid blocking the event loop.
        """
        try:
            import urllib.request
            import json
            _host = os.environ.get("INDICF5_HOST", "localhost")
            _port = os.environ.get("INDICF5_PORT", "8002")
            req = urllib.request.Request(f"http://{_host}:{_port}/health")
            resp = urllib.request.urlopen(req, timeout=2)
            if resp.status == 200:
                data = json.loads(resp.read())
                return data.get("model_loaded", False)
            return False
        except Exception:
            return False

    async def _check_indicf5_health_async(self) -> bool:
        """Non-blocking health check that runs the sync method in a thread.
        Uses asyncio.to_thread() to avoid blocking the async event loop.
        """
        return await asyncio.to_thread(
            VoiceOrchestrator._check_indicf5_health
        )

    async def generate_speech(
        self,
        text: str,
        voice_id: str,
        emotion: str = "neutral",
        pitch: float = 1.0,
        speed: float = 1.0,
        tone: str = "neutral",
        engine: str = "kokoro",
        language: str = "auto",
    ) -> str:
        # A stored clone must use the reference-conditioned IndicF5 path.
        # Never silently return a generic Kokoro voice as a successful clone.
        cloned_voices = _load_cloned_voices()
        if voice_id in cloned_voices:
            from dreamtalk.backend.services.cloned_speech import get_cloned_speech_service
            from dreamtalk.backend.services.multimodal_language import detect_text_language

            profile = cloned_voices[voice_id]
            target_language = language
            if not target_language or target_language == "auto":
                target_language = detect_text_language(text, profile.get("language")).language
            result = await get_cloned_speech_service().synthesize_clone(
                text=text,
                reference_audio=profile["ref_audio_path"],
                reference_text=profile.get("ref_text", ""),
                language=target_language,
                emotion=emotion,
                reference_language=profile.get("language"),
            )
            return result.path

        if engine in {"indicf5", "rvc", "clone"}:
            raise ValueError("A cloned voice_id is required for cloned speech generation")
        if not self._kokoro_available:
            raise RuntimeError("Kokoro TTS engine is not available")

        # Default: use Kokoro directly
        return await self._kokoro_generate(text, voice_id, speed, emotion, language)

    async def _kokoro_generate(
        self,
        text: str,
        voice_id: str,
        speed: float,
        emotion: str = "neutral",
        language: str = "auto",
    ) -> str:
        output_dir = "voice_module/assets/outputs"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"kokoro_{uuid.uuid4().hex}.wav"
        filepath = os.path.join(output_dir, filename)

        lang_code = _map_iso_to_kokoro(language if language != "auto" else self.kokoro_engine.detect_language(text))
        voice = voice_id if voice_id in self.kokoro_engine.list_voices() else self.kokoro_engine.select_voice_for_emotion(emotion)

        audio = self.kokoro_engine.synthesize_full(text, voice=voice, lang_code=lang_code, speed=speed)
        if audio is not None:
            import soundfile as sf
            sf.write(filepath, audio, 24000)
        return filepath

    async def _kokoro_generate_with_clone(
        self,
        text: str,
        voice_id: str,
        speed: float,
        emotion: str = "neutral",
        language: str = "auto",
        clone_profile: dict = None,
    ) -> str:
        """Generate TTS with Kokoro, then apply RVC voice conversion."""
        output_dir = "voice_module/assets/outputs"
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Generate base audio with Kokoro
        temp_file = os.path.join(output_dir, f"kokoro_{uuid.uuid4().hex}.wav")
        final_file = os.path.join(output_dir, f"cloned_{voice_id[:8]}_{uuid.uuid4().hex}.wav")

        lang_code = _map_iso_to_kokoro(language if language != "auto" else self.kokoro_engine.detect_language(text))
        # Use a matching voice for the base generation
        base_voice = "af_heart"  # Default good quality voice

        audio = self.kokoro_engine.synthesize_full(text, voice=base_voice, lang_code=lang_code, speed=speed)
        if audio is None:
            raise RuntimeError("Kokoro TTS failed for base audio generation")

        import soundfile as sf
        sf.write(temp_file, audio, 24000)

        # Step 2: Apply RVC voice conversion if available
        if self.rvc_available:
            try:
                rvc = self.rvc_converter
                result = rvc.convert(
                    audio_path=temp_file,
                    target_speaker=voice_id,
                    output_path=final_file,
                    pitch_adjust=0,
                )
                if result and os.path.exists(result):
                    # Clean up temp file
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                    return result
            except Exception as e:
                print(f"RVC conversion failed for {voice_id}: {e}")

        # Fallback: return the base Kokoro audio
        try:
            import shutil
            shutil.copy2(temp_file, final_file)
            os.remove(temp_file)
            return final_file  # Return final_file (temp_file was deleted)
        except Exception:
            pass
        return temp_file  # If copy failed, temp_file still exists

    async def clone_voice(
        self,
        name: str,
        description: str,
        audio_files: list,
        language: str = "auto",
        ref_text: str = "",
    ):
        """Create an IndicF5 zero-shot voice profile and store its reference.

        Steps:
        1. Validate audio files
        2. Run RVC conversion to extract voice characteristics
        3. Store the voice profile in cloned_voice_profiles.json
        4. Return the new voice_id
        """
        if not audio_files:
            raise ValueError("No audio files provided")

        audio_path = audio_files[0]
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Generate a voice ID
        voice_id = f"indicf5_{uuid.uuid4().hex[:12]}"
        output_dir = "voice_module/assets/voices"
        os.makedirs(output_dir, exist_ok=True)

        # Store a copy of the reference audio
        ref_filename = f"{voice_id}_ref.wav"
        ref_path = os.path.join(output_dir, ref_filename)

        from dreamtalk.backend.services.cloned_speech import prepare_reference_audio
        from dreamtalk.backend.services.multimodal_language import (
            detect_text_language,
            get_multilingual_asr,
            normalize_language,
        )

        quality = await asyncio.to_thread(prepare_reference_audio, audio_path, ref_path)
        requested_language = None if language == "auto" else normalize_language(language)
        transcription = None
        if not ref_text.strip():
            transcription = await get_multilingual_asr().transcribe(ref_path, requested_language)
            ref_text = transcription.text
            detected_language = transcription.language
        else:
            detected_language = requested_language or detect_text_language(ref_text).language
        if not ref_text.strip():
            raise ValueError("Reference transcript is required and ASR did not detect speech")

        # Build the voice profile
        profile = {
            "voice_id": voice_id,
            "name": name,
            "description": description,
            "ref_audio_path": ref_path,
            "created_at": datetime.utcnow().isoformat(),
            "engine": "indicf5",
            "language": detected_language,
            "ref_text": ref_text.strip(),
            "quality": quality,
            "transcription": transcription.to_dict() if transcription else None,
        }

        from dreamtalk.backend.services.cloned_speech import get_cloned_speech_service
        health = await get_cloned_speech_service().discover()
        profile["ready"] = bool(health.get("available"))
        profile["service"] = health.get("url")

        # Save the profile
        voices = _load_cloned_voices()
        voices[voice_id] = profile
        _save_cloned_voices(voices)

        return voice_id

    async def delete_voice_profile(self, voice_id: str) -> bool:
        """Delete a cloned voice profile by voice_id."""
        voices = _load_cloned_voices()
        if voice_id in voices:
            # Clean up reference audio file if it exists
            ref_path = voices[voice_id].get("ref_audio_path")
            if ref_path and os.path.exists(ref_path):
                try:
                    os.remove(ref_path)
                except Exception:
                    pass
            del voices[voice_id]
            _save_cloned_voices(voices)
            return True
        return False

    async def get_all_voices(self) -> Dict[str, Dict]:
        voices: Dict[str, Dict] = {}
        try:
            voices["kokoro"] = self.kokoro_engine.list_voices()
        except Exception:
            voices["kokoro"] = {}

        # Add cloned voices
        cloned = _load_cloned_voices()
        if cloned:
            voices["cloned"] = {
                vid: {
                    "name": p["name"],
                    "description": p.get("description", ""),
                    "engine": p.get("engine", "indicf5"),
                    "language": p.get("language", "en"),
                    "ready": p.get("ready", False),
                }
                for vid, p in cloned.items()
            }

        return voices

    async def list_engines(self) -> List[dict]:
        engines = [
            {
                "id": "kokoro",
                "name": "Kokoro TTS",
                "available": self._kokoro_available,
                "type": "local",
                "cost": "free",
                "model": "StyleTTS 2 (82M params)",
                "languages": list(self.kokoro_engine.SUPPORTED_LANGUAGES.values()),
                "voices": len(self.kokoro_engine.list_voices()),
            },
        ]

        # Add IndicF5 (F5-TTS — neural, 11 documented Indian languages)
        try:
            from dreamtalk.backend.services.cloned_speech import get_cloned_speech_service
            indicf5_health = await get_cloned_speech_service().discover()
            indicf5_available = bool(indicf5_health.get("available"))
        except Exception:
            indicf5_available = False
        engines.append({
            "id": "indicf5",
            "name": "IndicF5 TTS",
            "available": indicf5_available,
            "type": "microservice",
            "cost": "free",
            "model": "F5-TTS (CFM-based, 1.34B params)",
            "languages": [
                "Assamese", "Bengali", "Gujarati", "Hindi",
                "Kannada", "Malayalam", "Marathi", "Odia", "Punjabi",
                "Tamil", "Telugu",
            ],
            "voices": 11,
            "description": "Zero-shot voice cloning for 11 Indian languages via the dedicated IndicF5 service",
        })

        # Add RVC if available
        if self.rvc_available:
            engines.append({
                "id": "rvc",
                "name": "RVC Voice Cloning",
                "available": True,
                "type": "local",
                "cost": "free",
                "description": "Retrieval-based Voice Conversion - clone any voice from audio samples",
            })

        return engines
