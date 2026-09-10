"""
TTS Script Writer — GPT-OSS-powered expressive line rewriting.

Transforms raw chat text into speech-optimized scripts with emotion
metadata (mood, speed, emphasis) that Kokoro/IndicF5 synthesis engines
can use for more natural, emotionally expressive output.

Design:
  - LLM rewrites raw text into natural spoken language
  - Returns structured {rewritten_text, emotion, speed} JSON
  - Graceful fallback to original text on LLM failure
  - Supports all 12+ languages in the DreamTalk stack

Run:
    Called automatically by _generate_tts in avatar.py.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger("dreamtalk.tts.script_writer")


@dataclass
class ScriptResult:
    """Structured output from the TTS script writer."""
    rewritten_text: str
    emotion: str = "neutral"
    speed: float = 1.0
    language: str = "en"
    is_original: bool = False  # True when LLM rewrite was skipped/failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rewritten_text": self.rewritten_text,
            "emotion": self.emotion,
            "speed": self.speed,
            "language": self.language,
            "is_original": self.is_original,
        }


# ── LLM prompt templates ──────────────────────────────────────────────

_SCRIPT_WRITER_SYSTEM_PROMPT = """\
You are a TTS script writer for a Digital Twin avatar. Your job is to \
rewrite text into natural, expressive spoken language optimized for \
text-to-speech synthesis.

Rules:
1. Rewrite ONLY for speech — remove markdown, URLs, code, formatting.
2. Keep the meaning and emotional tone intact.
3. Use natural pauses with "..." for dramatic effect or sentence breaks.
4. Keep it concise — most lines should be 1-3 sentences.
5. Match the language: if the input is in Tamil, write Tamil. Hindi → Hindi. \
Kannada → Kannada. English → English. Never switch languages.
6. For emotional content, use expressive punctuation (!, ...) and natural \
speech patterns (contractions, conversational tone).
7. Output ONLY a JSON object, no explanation.

Output format:
{"rewritten_text": "...", "emotion": "<mood>", "speed": <0.7-1.3>}

emotion must be one of: neutral, happy, sad, excited, calm, angry, surprised, loving
speed: 0.7 = slow/gentle, 1.0 = normal, 1.3 = fast/excited
"""

# Shorter prompt for simple/short texts where rewriting adds latency
_SIMPLE_REWRITE_PROMPT = """\
Rewrite this for TTS speech output. Return ONLY JSON:
{"rewritten_text": "...", "emotion": "<mood>", "speed": <0.7-1.3>}

Emotions: neutral, happy, sad, excited, calm, angry, surprised, loving
Speed: 0.7=slow/gentle, 1.0=normal, 1.3=fast/excited
Language: match the input language exactly.
"""


class TTSScriptWriter:
    """GPT-OSS-powered script writer for TTS lines.

    Reads the LLM endpoint from the same env vars as the brain pipeline:
      - GPU_SERVER_BASE_URL  (e.g. http://144.79.62.242:8002/v1)
      - LLM_MODEL_NAME       (e.g. gpt-oss-120b-coding)
      - GPU_SERVER_API_KEY   (optional)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url or os.environ.get(
            "GPU_SERVER_BASE_URL", "http://localhost:11434/v1"
        )
        self.model = model or os.environ.get("LLM_MODEL_NAME", "deepseek-r1:7b")
        self.api_key = api_key or os.environ.get("GPU_SERVER_API_KEY", "")
        self._available: Optional[bool] = None  # lazy async check

    async def rewrite(
        self,
        text: str,
        language: str = "en",
        emotion_context: Optional[Dict] = None,
    ) -> ScriptResult:
        """Rewrite raw text into a TTS-optimized script line.

        Args:
            text: Raw chat text from the brain pipeline.
            language: ISO 639-1 language code (en, hi, ta, kn, etc.).
            emotion_context: Optional dict with primary_mood, valence, etc.

        Returns:
            ScriptResult with rewritten text and TTS metadata.
        """
        if not text or not text.strip():
            return ScriptResult(
                rewritten_text=text, language=language, is_original=True
            )

        # Very short texts don't benefit from rewriting
        if len(text.strip()) < 10:
            return ScriptResult(
                rewritten_text=text.strip(),
                language=language,
                is_original=True,
            )

        try:
            result = await self._call_llm(text, language, emotion_context)
            if result and result.rewritten_text:
                logger.debug(
                    f"Script rewrite [{language}]: {len(text)}→{len(result.rewritten_text)} chars, "
                    f"emotion={result.emotion}, speed={result.speed}"
                )
                return result
        except Exception as e:
            logger.warning(f"Script writer LLM call failed: {e}")

        # Fallback: return original text
        return ScriptResult(
            rewritten_text=text.strip(),
            language=language,
            is_original=True,
        )

    async def _call_llm(
        self,
        text: str,
        language: str,
        emotion_context: Optional[Dict],
    ) -> Optional[ScriptResult]:
        """Call GPT-OSS to rewrite the text for TTS."""
        # Build system prompt with emotion context
        system = _SCRIPT_WRITER_SYSTEM_PROMPT
        if emotion_context:
            mood = emotion_context.get("primary_mood", "neutral")
            valence = emotion_context.get("valence", 0.0)
            arousal = emotion_context.get("arousal", 0.0)
            system += (
                f"\nContext: The speaker is feeling '{mood}' "
                f"(valence={valence:.2f}, arousal={arousal:.2f}). "
                f"Adjust the tone and pacing accordingly."
            )

        # Use simpler prompt for short texts
        user_prompt = text.strip()
        if len(user_prompt) < 80:
            system = _SIMPLE_REWRITE_PROMPT + (
                f"\nContext: emotion={emotion_context.get('primary_mood', 'neutral') if emotion_context else 'neutral'}"
            )

        # Call GPT-OSS
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 300,
            "temperature": 0.3,  # Low temp for consistent JSON output
        }

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

        if not content:
            return None

        # Parse JSON response (handle markdown code blocks)
        parsed = self._parse_json_response(content)
        if not parsed:
            return None

        rewritten = parsed.get("rewritten_text", "").strip()
        if not rewritten:
            return None

        # Validate and clamp speed
        speed = float(parsed.get("speed", 1.0))
        speed = max(0.5, min(2.0, speed))

        # Validate emotion
        valid_emotions = {
            "neutral", "happy", "sad", "excited", "calm",
            "angry", "surprised", "loving", "fearful",
        }
        emotion = parsed.get("emotion", "neutral").lower()
        if emotion not in valid_emotions:
            emotion = "neutral"

        return ScriptResult(
            rewritten_text=rewritten,
            emotion=emotion,
            speed=speed,
            language=language,
            is_original=False,
        )

    @staticmethod
    def _parse_json_response(content: str) -> Optional[Dict]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        import re
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding a JSON object in the text
        match = re.search(r"\{[^{}]*\}", content)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    async def is_available(self) -> bool:
        """Check if the LLM endpoint is reachable (async-safe)."""
        if self._available is not None:
            return self._available
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                resp = await client.get(f"{self.base_url}/models", headers=headers)
                self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available


# ── Singleton ──────────────────────────────────────────────────────────

_writer: Optional[TTSScriptWriter] = None


def get_script_writer() -> TTSScriptWriter:
    """Get or create the default TTS script writer singleton."""
    global _writer
    if _writer is None:
        _writer = TTSScriptWriter()
    return _writer
