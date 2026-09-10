"""
DreamTalk — Language Router

Detects input language, translates to target language, and routes
to the appropriate TTS engine. Uses GPT-OSS as translation backend
(no external translation API needed).

Architecture:
  Input text → Detect language → Translate to target → Route to TTS

Supported languages (IndicF5 + Kokoro):
  hi, ta, te, kn, ml, bn, mr, gu, pa, or, as, en

Usage:
    router = get_language_router()
    result = await router.translate("வணக்கம்", target_lang="en")
    print(result.text)  # "Hello"
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

import httpx

logger = logging.getLogger("dreamtalk.translation")


# ── Language definitions ──────────────────────────────────────────────

INDIC_LANGUAGES: Dict[str, Dict] = {
    "hi": {"name": "Hindi", "tts_engine": "indicf5", "kokoro_code": "h", "script_range": (0x0900, 0x097F)},
    "ta": {"name": "Tamil", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0B80, 0x0BFF)},
    "te": {"name": "Telugu", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0C00, 0x0C7F)},
    "kn": {"name": "Kannada", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0C80, 0x0CFF)},
    "ml": {"name": "Malayalam", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0D00, 0x0D7F)},
    "bn": {"name": "Bengali", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0980, 0x09FF)},
    "mr": {"name": "Marathi", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0900, 0x097F)},
    "gu": {"name": "Gujarati", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0A80, 0x0AFF)},
    "pa": {"name": "Punjabi", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0A00, 0x0A7F)},
    "or": {"name": "Odia", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0B00, 0x0B7F)},
    "as": {"name": "Assamese", "tts_engine": "indicf5", "kokoro_code": None, "script_range": (0x0980, 0x09FF)},
    "en": {"name": "English", "tts_engine": "kokoro", "kokoro_code": "a", "script_range": (0x0041, 0x007A)},
}

# Languages that share scripts (Devanagari family)
DEVANAGARI_LANGS = {"hi", "mr", "ne", "sa", "bho"}


@dataclass
class TranslationResult:
    """Result from language routing/translation."""
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    tts_engine: str
    kokoro_code: Optional[str]
    was_translated: bool = False
    confidence: float = 1.0


class LanguageRouter:
    """Detect, translate, and route text to the appropriate TTS engine."""

    def __init__(
        self,
        llm_base_url: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        self.llm_base_url = llm_base_url or os.environ.get(
            "GPU_SERVER_BASE_URL", "http://localhost:11434/v1"
        )
        self.llm_model = llm_model or os.environ.get("LLM_MODEL_NAME", "gpt-oss-120b-coding")
        self.llm_api_key = llm_api_key or os.environ.get("GPU_SERVER_API_KEY", "")
        # gpt-oss models live on the remote vLLM GPU server, not on local Ollama.
        # Keep a (url, model) fallback chain so translation still works offline.
        self._llm_endpoints: List[Tuple[str, str]] = []
        if "gpt-oss" in self.llm_model.lower():
            gpu_url = os.environ.get("GPTOSS_BASE_URL", "http://144.79.62.242:8002/v1")
            self._llm_endpoints.append((gpu_url, self.llm_model))
            self._llm_endpoints.append((
                os.environ.get("GPU_SERVER_BASE_URL", "http://localhost:11434/v1"),
                os.environ.get("LLM_FALLBACK_MODEL", "deepseek-r1:7b"),
            ))
        else:
            self._llm_endpoints.append((self.llm_base_url, self.llm_model))

    def detect_language(self, text: str) -> str:
        """Detect the language of input text using Unicode script analysis.

        Returns ISO 639-1 code (e.g. "hi", "ta", "en").
        """
        if not text or not text.strip():
            return "en"

        script_scores: Dict[str, int] = {}

        for lang_code, lang_info in INDIC_LANGUAGES.items():
            if lang_code == "en":
                continue
            start, end = lang_info["script_range"]
            count = sum(1 for c in text if start <= ord(c) <= end)
            if count > 0:
                script_scores[lang_code] = count

        if not script_scores:
            return "en"

        # Return the script with the most characters
        best = max(script_scores, key=script_scores.get)

        # Disambiguate Devanagari languages (hi vs mr)
        if best in DEVANAGARI_LANGS:
            # Default to Hindi for Devanagari text (most common)
            return "hi"

        return best

    def get_tts_config(self, lang_code: str) -> Dict:
        """Get TTS engine configuration for a language."""
        lang = INDIC_LANGUAGES.get(lang_code, INDIC_LANGUAGES["en"])
        return {
            "engine": lang["tts_engine"],
            "kokoro_code": lang["kokoro_code"],
            "language_name": lang["name"],
            "lang_code": lang_code,
        }

    async def translate(
        self,
        text: str,
        target_lang: str = "en",
        source_lang: Optional[str] = None,
    ) -> TranslationResult:
        """Translate text to target language using GPT-OSS.

        Args:
            text: Input text in any supported language.
            target_lang: Target ISO 639-1 code.
            source_lang: Source language (auto-detected if None).

        Returns:
            TranslationResult with translated text and routing info.
        """
        if not source_lang:
            source_lang = self.detect_language(text)

        tts_config = self.get_tts_config(source_lang)

        # If already in target language, no translation needed
        if source_lang == target_lang:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                tts_engine=tts_config["engine"],
                kokoro_code=tts_config["kokoro_code"],
                was_translated=False,
            )

        # Translate using LLM
        translated = await self._llm_translate(text, source_lang, target_lang)

        if translated and translated != text:
            return TranslationResult(
                original_text=text,
                translated_text=translated,
                source_lang=source_lang,
                target_lang=target_lang,
                tts_engine=tts_config["engine"],
                kokoro_code=tts_config["kokoro_code"],
                was_translated=True,
            )

        # Translation failed — return original
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            tts_engine=tts_config["engine"],
            kokoro_code=tts_config["kokoro_code"],
            was_translated=False,
            confidence=0.5,
        )

    async def route_for_tts(
        self,
        text: str,
        preferred_lang: Optional[str] = None,
        user_lang: Optional[str] = None,
    ) -> TranslationResult:
        """Route text for TTS: detect language, optionally translate to preferred output language.

        This is the main entry point for the voice pipeline:
          1. Detect input language
          2. If user prefers a different output language, translate
          3. Return with TTS engine config

        Args:
            text: Text to speak.
            preferred_lang: If set, translate output to this language.
            user_lang: User's primary language (for TTS engine selection).

        Returns:
            TranslationResult with text ready for TTS.
        """
        detected = self.detect_language(text)
        output_lang = preferred_lang or user_lang or detected

        # If output language differs from detected, translate
        if output_lang != detected:
            return await self.translate(text, target_lang=output_lang, source_lang=detected)

        # Same language — just route
        tts_config = self.get_tts_config(detected)
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_lang=detected,
            target_lang=detected,
            tts_engine=tts_config["engine"],
            kokoro_code=tts_config["kokoro_code"],
        )

    async def _llm_translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """Use GPT-OSS to translate text between languages."""
        source_name = INDIC_LANGUAGES.get(source_lang, {}).get("name", source_lang)
        target_name = INDIC_LANGUAGES.get(target_lang, {}).get("name", target_lang)

        prompt = (
            f"Translate the following {source_name} text to {target_name}. "
            f"Output ONLY the translated text, nothing else.\n\n{text}"
        )

        for ep_url, ep_model in self._llm_endpoints:
            url = f"{ep_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.llm_api_key:
                headers["Authorization"] = f"Bearer {self.llm_api_key}"

            payload = {
                "model": ep_model,
                "messages": [
                    {"role": "system", "content": f"You are a professional {source_name}-to-{target_name} translator. Output only the translation."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
                "temperature": 0.1,  # Low temperature for accurate translation
            }

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if content:
                    # strip <think> blocks from reasoning models (deepseek-r1)
                    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                return content if content else None

            except Exception as e:
                logger.warning(f"LLM translation failed via {ep_model}@{ep_url}: {e}")
                continue
        return None


# ── Singleton ──────────────────────────────────────────────────────────

_router: Optional[LanguageRouter] = None


def get_language_router() -> LanguageRouter:
    """Get or create the default language router singleton."""
    global _router
    if _router is None:
        _router = LanguageRouter()
    return _router
