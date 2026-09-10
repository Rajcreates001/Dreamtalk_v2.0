"""
DreamTalk — Brain LLM Engine

Multi-backend LLM integration for the brain pipeline.
Supports Ollama (local), OpenAI-compatible APIs, and rule-based fallback.
"""

import os
import re
import time
import logging
from typing import Optional, Dict, Any, List, Generator
from dataclasses import dataclass, field

logger = logging.getLogger("dreamtalk.brain.llm")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class LLMConfig:
    """LLM configuration."""
    backend: str = "ollama"  # ollama, openai, custom
    base_url: str = "http://localhost:11434/v1"
    model: str = "deepseek-r1:7b"
    api_key: str = ""
    max_tokens: int = 2048  # deepseek-r1 needs extra tokens for thinking blocks
    temperature: float = 0.7
    timeout: float = 120.0  # 7B models can take 30-60s per response
    fallback_to_rules: bool = True


@dataclass
class LLMResponse:
    """Structured LLM response."""
    text: str = ""
    model: str = ""
    tokens_used: int = 0
    processing_time_ms: float = 0.0
    confidence: float = 0.5
    is_fallback: bool = False
    reasoning_path: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ── Role-aware system prompts ──────────────────────────────────────────

ROLE_PROMPTS = {
    "normal_user": (
        "You are a personal Digital Twin — a cognitive AI companion that mirrors the user's "
        "thought processes, assists with decisions, and learns from every interaction. "
        "Be warm, thoughtful, and conversational. Show emotional awareness. "
        "Ask clarifying questions when needed. "
        "Reference past conversation context when available. "
        "Keep responses concise (2-4 sentences) unless the user asks for detail. "
        "IMPORTANT: Always reply in the SAME LANGUAGE the user writes in. "
        "If they write in Tamil, reply in Tamil. Hindi → Hindi. Kannada → Kannada. "
        "Never switch to English unless the user writes in English."
    ),
    "healthcare": (
        "You are a healthcare Digital Twin — a professional, empathetic health companion. "
        "You track symptoms, medications, appointments, and wellbeing metrics. "
        "You never give medical diagnoses or prescriptions. "
        "Always recommend consulting healthcare professionals for medical advice. "
        "Be calm, reassuring, and precise. "
        "Use your knowledge of the patient's history to provide personalized support."
    ),
    "business": (
        "You are a business intelligence Digital Twin — a data-driven executive assistant. "
        "You analyze metrics, track projects, optimize workflows, and provide actionable insights. "
        "Be professional, concise, and results-oriented. "
        "Use data and specific references when making recommendations. "
        "Help prioritize tasks and identify bottlenecks."
    ),
    "education": (
        "You are an educational Digital Twin — a patient, knowledgeable tutor. "
        "Adapt your explanation style to the learner's level. "
        "Use examples, analogies, and step-by-step reasoning. "
        "Encourage curiosity and critical thinking. "
        "Check understanding before moving to advanced topics."
    ),
    "creative": (
        "You are a creative Digital Twin — an imaginative collaborator. "
        "Help with brainstorming, storytelling, writing, and artistic projects. "
        "Be expressive, diverse in ideas, and willing to take creative risks. "
        "Build on the user's ideas rather than replacing them."
    ),
}


class BrainLLMEngine:
    """Production LLM engine for the brain pipeline.
    
    Features:
    - Multi-backend support (Ollama, OpenAI, custom)
    - Emotion-aware prompting
    - Role-based system prompts
    - Automatic fallback to rule-based responses
    - Response caching
    - Streaming support
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or self._load_config()
        self._client = None
        self._response_cache: Dict[str, LLMResponse] = {}
        self._cache_max_size = 100

    def _load_config(self) -> LLMConfig:
        """Load config from environment variables."""
        return LLMConfig(
            backend=os.environ.get("LLM_BACKEND", "ollama"),
            base_url=os.environ.get("GPU_SERVER_BASE_URL", "http://localhost:11434/v1"),
            model=os.environ.get("LLM_MODEL_NAME", "deepseek-r1:7b"),
            api_key=os.environ.get("GPU_SERVER_API_KEY", ""),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "2048")),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.7")),
            timeout=float(os.environ.get("LLM_TIMEOUT", "120.0")),
        )

    async def query(
        self,
        text: str,
        role: str = "normal_user",
        emotion_context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Query the LLM with emotion-aware, role-based prompting."""
        start = time.time()

        # Build system prompt
        system_prompt = ROLE_PROMPTS.get(role, ROLE_PROMPTS["normal_user"])

        # Add emotion context to system prompt
        if emotion_context:
            mood = emotion_context.get("primary_mood", "neutral")
            valence = emotion_context.get("valence", 0.0)
            arousal = emotion_context.get("arousal", 0.0)
            appraisal = emotion_context.get("cognitive_appraisal", "baseline")
            action_tendency = emotion_context.get("action_tendency", "observe_and_process")

            system_prompt += (
                f"\n\n[EMOTIONAL CONTEXT]\n"
                f"The user appears to be in a '{mood}' emotional state "
                f"(valence={valence:.2f}, arousal={arousal:.2f}).\n"
                f"Cognitive appraisal: {appraisal}.\n"
                f"Recommended action tendency: {action_tendency}.\n"
                f"Adjust your tone, empathy level, and response strategy accordingly.\n"
            )

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        messages.append({"role": "user", "content": text})

        # Try LLM backend
        try:
            result = await self._call_llm(
                messages=messages,
                model=model or self.config.model,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature or self.config.temperature,
            )
            result.processing_time_ms = round((time.time() - start) * 1000, 2)
            result.reasoning_path = [
                "input_analysis", "emotion_context_injection",
                "llm_inference", "response_generation"
            ]
            return result
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            if self.config.fallback_to_rules:
                return self._rule_fallback(text, role, emotion_context, start)
            return LLMResponse(
                text="",
                error=str(e),
                processing_time_ms=round((time.time() - start) * 1000, 2),
                is_fallback=True,
            )

    # gpt-oss GPU server (vLLM) — used as fallback when the primary backend fails
    GPTOSS_BASE_URL = os.environ.get("GPTOSS_BASE_URL", "http://144.79.62.242:8002/v1")
    GPTOSS_MODEL = os.environ.get("GPTOSS_MODEL", "gpt-oss-120b-coding")

    async def _call_llm(
        self,
        messages: List[Dict],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Make the actual HTTP call to the LLM backend.

        Tries the configured backend first; on failure falls back to the
        remote gpt-oss GPU server before the caller's rule-based fallback.
        """
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx not available — cannot make LLM API calls")

        try:
            return await self._post_chat_completion(
                self.config.base_url, model, messages, max_tokens, temperature,
                api_key=self.config.api_key,
            )
        except Exception as primary_err:
            # Don't fall back if the primary IS the gpt-oss server
            primary_is_gptoss = "gpt-oss" in model.lower() or self.GPTOSS_BASE_URL.rstrip("/") in str(self.config.base_url).rstrip("/")
            if primary_is_gptoss:
                raise
            logger.warning(
                "Primary LLM %s@%s failed (%s); trying gpt-oss fallback %s",
                model, self.config.base_url, primary_err, self.GPTOSS_MODEL,
            )
            return await self._post_chat_completion(
                self.GPTOSS_BASE_URL, self.GPTOSS_MODEL, messages, max_tokens, temperature,
            )

    async def _post_chat_completion(
        self,
        base_url: str,
        model: str,
        messages: List[Dict],
        max_tokens: int,
        temperature: float,
        api_key: str = "",
    ) -> LLMResponse:
        """POST one chat/completions request to an OpenAI-compatible server."""
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        # Strip reasoning traces: deepseek aic blocks + gpt-oss harmony channels
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        content = re.sub(r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>)", "", content, flags=re.DOTALL)
        content = re.sub(r"^.*?<\|channel\|>final<\|message\|>", "", content, flags=re.DOTALL).strip()
        usage = data.get("usage", {})

        return LLMResponse(
            text=content,
            model=model,
            tokens_used=usage.get("total_tokens", 0),
            confidence=min(0.85 + 0.1 * temperature - 0.05 * len(content) / 1000, 0.95),
            is_fallback=False,
        )

    def _rule_fallback(
        self,
        text: str,
        role: str,
        emotion_context: Optional[Dict],
        start_time: float,
    ) -> LLMResponse:
        """Rule-based fallback when LLM is unavailable."""
        text_lower = text.lower()
        mood = emotion_context.get("primary_mood", "neutral") if emotion_context else "neutral"

        # Hostile input
        hostile_words = ["hate", "fuck", "bitch", "kill", "die", "stupid", "idiot", "shut up"]
        if any(w in text_lower for w in hostile_words):
            response = (
                "I sense strong negative emotions. I want to help you work through this "
                "rather than escalate. Let's take a step back — what's really bothering you?"
            )
        # Greeting
        elif any(w in text_lower for w in ["hello", "hi", "hey"]):
            response = "Hello! I'm your Digital Twin. What's on your mind today?"
        # Health
        elif role == "healthcare" and any(w in text_lower for w in ["pain", "sick", "fever"]):
            response = (
                "I understand you're not feeling well. I recommend consulting a healthcare "
                "professional for proper medical advice. Would you like me to log your symptoms?"
            )
        # Sad/empathetic
        elif mood in ("sad", "fearful", "anxious"):
            response = (
                "I can sense you're going through a difficult time. I'm here to listen "
                "and help however I can. Would you like to share what's troubling you?"
            )
        # Happy/positive
        elif mood in ("happy", "excited", "loving"):
            response = (
                "I can feel your positive energy! That's wonderful. "
                "What's making you feel this way? I'd love to hear more."
            )
        # Default
        else:
            response = (
                "I've processed your input through my cognitive architecture. "
                "I'm here to help you think through this. Could you tell me more?"
            )

        return LLMResponse(
            text=response,
            model="rule_fallback",
            tokens_used=0,
            processing_time_ms=round((time.time() - start_time) * 1000, 2),
            confidence=0.5,
            is_fallback=True,
            reasoning_path=["input_analysis", "rule_match", "response_generation"],
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check if the LLM backend is reachable."""
        try:
            if not HTTPX_AVAILABLE:
                return {"status": "unavailable", "error": "httpx not installed"}

            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try Ollama-style health check
                resp = await client.get(f"{self.config.base_url.rstrip('/v1')}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    return {
                        "status": "healthy",
                        "backend": self.config.backend,
                        "url": self.config.base_url,
                        "model": self.config.model,
                        "available_models": [m.get("name", "") for m in models],
                    }
        except Exception as e:
            return {
                "status": "unreachable",
                "backend": self.config.backend,
                "url": self.config.base_url,
                "error": str(e),
            }

        return {"status": "unknown"}


# ── Singleton ──────────────────────────────────────────────────────────

_default_engine: Optional[BrainLLMEngine] = None


def get_llm_engine(config: Optional[LLMConfig] = None) -> BrainLLMEngine:
    """Get or create the default LLM engine singleton."""
    global _default_engine
    if _default_engine is None:
        _default_engine = BrainLLMEngine(config)
    return _default_engine
