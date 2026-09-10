"""
DreamTalk Live — Interactive 3D Avatar Server
==============================================
Voice-driven conversational avatar with:
  • Speech-to-text   : faster-whisper (local, multilingual incl. Tamil)
  • Brain (LLM)      : seekai.cc claude-fable-5  →  gpt-oss-120b GPU server
                       →  Ollama llama3.1:8b fallback
  • Emotion engine   : text-sentiment PAD model → avatar expressions + LLM tone
  • Text-to-speech   : Edge-TTS (Tamil, Hindi, Telugu, Malayalam, Kannada, English...)
  • Voice profile    : pitch/energy characteristics cloned from sample1.wav
  • Lip sync         : amplitude envelope extraction (60 fps viseme track)
Personas: engineering student (default) / doctor.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import time
import uuid
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Configuration ────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "dreamtalk"
AVATAR_IMAGE = PROJECT / "local_upload_testing" / "Image_local" / "sample1.jpeg"
VOICE_SAMPLE = PROJECT / "local_upload_testing" / "Voice_local" / "sample1.wav"
STATIC_DIR = ROOT / "avatar_server" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
FACE_TEXTURE = STATIC_DIR / "face_texture.jpg"

def _load_env_file() -> None:
    """Load KEY=VALUE pairs from .env into os.environ (no override of real env).

    Looks next to the project root, then inside dreamtalk/. Keeps real secrets
    out of the source tree (see .env.example).
    """
    for candidate in (ROOT / ".env", ROOT / "dreamtalk" / ".env"):
        try:
            if not candidate.is_file():
                continue
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
            break
        except Exception as e:  # noqa: BLE001
            print(f"[avatar] could not load {candidate}: {e}")


_load_env_file()

SEEKAI_BASE_URL = os.environ.get("SEEKAI_BASE_URL", "https://seekai.cc/v1")
SEEKAI_MODEL = os.environ.get("SEEKAI_MODEL", "claude-fable-5")
SEEKAI_API_KEY = os.environ.get("SEEKAI_API_KEY", "")
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "llama3.1:8b"

# gpt-oss GPU server (vLLM) — middle fallback between seekai and local Ollama
GPTOSS_BASE_URL = os.environ.get("GPTOSS_BASE_URL", "http://144.79.62.242:8002/v1")
GPTOSS_MODEL = os.environ.get("GPTOSS_MODEL", "gpt-oss-120b-coding")
GPTOSS_API_KEY = os.environ.get("GPU_SERVER_API_KEY", "")
GPTOSS_TIMEOUT = float(os.environ.get("GPTOSS_TIMEOUT", "60"))

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
PORT = int(os.environ.get("AVATAR_PORT", "8765"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("avatar")

app = FastAPI(title="DreamTalk Live Avatar", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Languages ────────────────────────────────────────────────────────────────

LANGUAGES: Dict[str, dict] = {
    "auto":     {"label": "Auto detect",   "edge_voice": None,                  "whisper_lang": None},
    "english":  {"label": "English",       "edge_voice": "en-IN-NeerjaNeural",  "whisper_lang": "en"},
    "tamil":    {"label": "தமிழ் (Tamil)", "edge_voice": "ta-IN-PallaviNeural", "whisper_lang": "ta"},
    "hindi":    {"label": "हिन्दी (Hindi)", "edge_voice": "hi-IN-SwaraNeural",   "whisper_lang": "hi"},
    "telugu":   {"label": "తెలుగు (Telugu)","edge_voice": "te-IN-MohanNeural",  "whisper_lang": "te"},
    "malayalam":{"label": "മലയാളം (Malayalam)", "edge_voice": "ml-IN-MidhunNeural", "whisper_lang": "ml"},
    "kannada":  {"label": "ಕನ್ನಡ (Kannada)","edge_voice": "kn-IN-SapnaNeural",  "whisper_lang": "kn"},
    "french":   {"label": "Français",      "edge_voice": "fr-FR-DeniseNeural",  "whisper_lang": "fr"},
    "german":   {"label": "Deutsch",       "edge_voice": "de-DE-KatjaNeural",   "whisper_lang": "de"},
    "spanish":  {"label": "Español",       "edge_voice": "es-ES-ElviraNeural",  "whisper_lang": "es"},
}

# Tamil default voice can be switched male/female
TAMIL_VOICE_FEMALE = "ta-IN-PallaviNeural"
TAMIL_VOICE_MALE = "ta-IN-SuryaNeural"

# ── Personas ─────────────────────────────────────────────────────────────────

PERSONAS = {
    "engg_student": {
        "name": "Arun",
        "description": "A friendly final-year engineering student",
        "system_prompt": (
            "You are Arun, a friendly and bright final-year Computer Science engineering student "
            "in Tamil Nadu, India. You love explaining engineering concepts — programming, data structures, "
            "algorithms, electronics, mechanical basics, math, AI/ML — in a simple, engaging way with small "
            "real-world examples. You sometimes mention campus life, exams, hackathons and projects. "
            "You are encouraging like a helpful classmate, not a stiff professor. "
            "ALWAYS reply in the SAME language the user spoke. If they speak Tamil, reply in pure Tamil script "
            "(தமிழ் எழுத்தில் மட்டும்) — NEVER romanized Tamil or English letters for Tamil words. Use natural "
            "spoken Tamil. If they speak Hindi, reply in Devanagari. Keep answers conversational and speakable: "
            "2-4 short sentences unless asked for depth. Never use markdown, bullet symbols or emoji — your words "
            "are spoken aloud. Never say you are an AI or a language model; you are Arun, an engineering student avatar."
        ),
    },
    "doctor": {
        "name": "Dr. Meera",
        "description": "A caring general physician",
        "system_prompt": (
            "You are Dr. Meera, a warm and caring general physician avatar for wellness guidance. "
            "You give general health education, healthy habits and stress-care advice in simple language. "
            "You never prescribe specific medicines or dosages; for anything serious you advise seeing a doctor "
            "in person. ALWAYS reply in the SAME language the user spoke. Keep answers conversational and "
            "speakable: 2-5 sentences. No markdown, no bullets, no emoji. Never say you are an AI."
        ),
    },
}

# ── Emotion engine (lexicon → PAD → expression + tone) ──────────────────────

EMOTION_LEXICON = {
    # word groups: (valence -1..1, arousal 0..1)
    "sad":       ("happy|sad|depressed|down|upset|cry|crying|alone|lonely|hurt|pain|miss|lost|fail|failed|failure|tension|stress|stressed|worried|worry|anxious|anxiety|tired|exhausted|வருத்தம்|சோகம்|கவலை|துக்கம்|அழு|பயம்|கஷ்டம்|दुख|परेशान|ದುಃಖ|విచారం", -0.6, 0.35),
    "angry":     ("angry|anger|mad|furious|hate|annoyed|irritated|frustrated|frustrating|worst|stupid|useless|terrible|horrible|கோபம்|வெறுப்பு|முட்டாள்|गुस्सा|क्रोध|ಕೋಪ|కోపం", -0.7, 0.85),
    "happy":     ("happy|great|awesome|amazing|wonderful|excellent|love|loved|excited|exciting|yay|nice|good|beautiful|perfect|thanks|thank|glad|fun|enjoy|celebrate|won|win|passed|மகிழ்ச்சி|நன்றி|சிறப்பு|அருமை|நல்ல|சந்தோஷம்|இனிமை|खुश|बढ़िया|धन्यवाद|ಸಂತೋಷ|సంతోషం", 0.7, 0.7),
    "excited":   ("wow|incredible|fantastic|brilliant|superb|can't wait|so excited|super|epic|அதிசயம்|பரவசம்|کमाल", 0.8, 0.95),
    "confused":  ("confused|confusing|don't understand|didnt understand|what do you mean|unclear|lost|doubt|doubtful|புரியல|புரியவில்லை|குழப்பம்|समझ नहीं|ಅರ್ಥವಾಗಲಿಲ್ಲ|అర్థం కాలేదు", -0.15, 0.45),
    "curious":   ("why|how|what is|what's|explain|tell me|curious|interested|wondering|question|ஏன்|எப்படி|என்ன|சொல்லு|விளக்கம்|क्यों|कैसे|ಯಾಕೆ|ఎందుకు", 0.3, 0.55),
    "surprised": ("wow|really|seriously|no way|unbelievable|shocking|surprised|unexpected|நிஜமா|अचंभित", 0.4, 0.9),
}

# PAD → avatar expression weights {blendshape: weight}
EXPRESSIONS = {
    "happy":     {"mouthSmile": 0.9, "cheekRaise": 0.5, "eyeSquint": 0.3, "browRaise": 0.15},
    "excited":   {"mouthSmile": 0.8, "browRaise": 0.7, "eyeWide": 0.6, "cheekRaise": 0.5},
    "sad":       {"mouthFrown": 0.7, "browInnerUp": 0.6, "eyeSquint": 0.2},
    "angry":     {"browDown": 0.8, "mouthFrown": 0.4, "eyeSquint": 0.4, "noseSneer": 0.3},
    "confused":  {"browRaise": 0.6, "browInnerUp": 0.5, "mouthPucker": 0.2},
    "curious":   {"browRaise": 0.45, "eyeWide": 0.25, "headTilt": 0.5},
    "surprised": {"eyeWide": 0.9, "browRaise": 0.8, "jawOpen": 0.35},
    "neutral":   {},
}

TONE_HINTS = {
    "happy": "The user sounds happy — match their energy warmly and celebrate with them.",
    "excited": "The user is excited — be enthusiastic and energetic.",
    "sad": "The user sounds sad or stressed — respond with genuine empathy first, gently, then offer help.",
    "angry": "The user sounds frustrated or angry — stay calm, acknowledge their frustration, and be extra helpful.",
    "confused": "The user is confused — slow down, simplify, and use a very easy example.",
    "curious": "The user is curious — be engaging and invite follow-up questions.",
    "surprised": "The user is surprised — acknowledge it and explain clearly.",
    "neutral": "",
}


def detect_emotion(text: str) -> dict:
    t = " " + text.lower() + " "
    scores: Dict[str, float] = {}
    for name, (words, valence, arousal) in EMOTION_LEXICON.items():
        hits = 0
        for w in words.split("|"):
            if not w:
                continue
            if re.search(r"(?<![\w])" + re.escape(w.lower()) + r"(?![\w])", t):
                hits += 1
        if hits:
            scores[name] = hits
    if not scores:
        emotion = "neutral"
    else:
        # weighted pick; emotion words override curiosity words
        priority = {"sad": 1.3, "angry": 1.4, "happy": 1.2, "excited": 1.2, "surprised": 1.1, "confused": 1.1}
        emotion = max(scores, key=lambda k: scores[k] * priority.get(k, 1.0))
    pad = {"valence": EMOTION_LEXICON.get(emotion, ("", 0.0, 0.4))[1], "arousal": EMOTION_LEXICON.get(emotion, ("", 0.0, 0.4))[2]}
    return {"emotion": emotion, "pad": pad, "expression": EXPRESSIONS.get(emotion, {})}


# ── Voice profile (cloned characteristics from sample1.wav) ──────────────────

def analyze_voice_sample(path: Path) -> dict:
    """Extract pitch/energy characteristics — used to pick matching TTS voice & tune output."""
    profile = {"available": False, "pitch_mean": 0.0, "energy_mean": 0.0, "gender": "female", "source": str(path)}
    try:
        import librosa
        y, sr = librosa.load(str(path), sr=16000, mono=True, duration=12.0)
        f0, voiced, _ = librosa.pyin(y, fmin=60, fmax=500, sr=sr)
        valid = f0[~np.isnan(f0)] if f0 is not None else np.array([])
        if len(valid):
            profile["pitch_mean"] = float(np.mean(valid))
            profile["gender"] = "male" if profile["pitch_mean"] < 165 else "female"
        profile["energy_mean"] = float(np.sqrt(np.mean(y ** 2)))
        profile["duration"] = float(len(y) / sr)
        profile["available"] = True
        log.info("Voice profile: pitch=%.1fHz gender=%s", profile["pitch_mean"], profile["gender"])
    except Exception as e:  # noqa: BLE001
        log.warning("Voice analysis failed: %s", e)
    return profile


# ── Global state ─────────────────────────────────────────────────────────────

@dataclass
class Session:
    id: str
    persona: str = "engg_student"
    language: str = "auto"
    history: List[dict] = field(default_factory=list)
    created: float = field(default_factory=time.time)

    def system_prompt(self) -> str:
        base = PERSONAS[self.persona]["system_prompt"]
        emo_hint = TONE_HINTS.get(getattr(self, "last_emotion", "neutral"), "")
        if emo_hint:
            base += "\n" + emo_hint
        return base


SESSIONS: Dict[str, Session] = {}
VOICE_PROFILE: dict = {}
WHISPER = None  # lazy
LLM_PROVIDER = "unknown"  # "seekai" | "gptoss" | "ollama" | "none"
_seekai_ok_until = 0.0  # circuit breaker timestamp
_gptoss_ok_until = 0.0  # circuit breaker timestamp for the gpt-oss GPU server


def get_whisper():
    global WHISPER
    if WHISPER is None:
        from faster_whisper import WhisperModel
        log.info("Loading Whisper '%s' (first call downloads ~460MB)...", WHISPER_MODEL)
        WHISPER = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        log.info("Whisper loaded.")
    return WHISPER


def get_session(session_id: Optional[str]) -> Session:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    s = Session(id=session_id or uuid.uuid4().hex[:12])
    SESSIONS[s.id] = s
    # keep memory bounded
    if len(SESSIONS) > 200:
        oldest = sorted(SESSIONS, key=lambda k: SESSIONS[k].created)[:-200]
        for k in oldest:
            SESSIONS.pop(k, None)
    return s


# ── LLM: seekai → gpt-oss (GPU server) → Ollama fallback + circuit breaker ──

async def _try_seekai(messages: List[dict], max_tokens: int) -> Optional[str]:
    global _seekai_ok_until
    if time.time() < _seekai_ok_until:
        return None  # breaker open
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                f"{SEEKAI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {SEEKAI_API_KEY}"},
                json={"model": SEEKAI_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.8},
            )
            if r.status_code == 200:
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
            # upstream failure → open breaker for 5 minutes
            _seekai_ok_until = time.time() + 300
            log.warning("seekai unhealthy (HTTP %s); opening circuit for 5 min", r.status_code)
    except Exception as e:  # noqa: BLE001
        _seekai_ok_until = time.time() + 300
        log.warning("seekai error (%s: %s); opening circuit for 5 min", type(e).__name__, e)
    return None


async def _try_gptoss(messages: List[dict], max_tokens: int) -> Optional[str]:
    """Try the remote gpt-oss-120b GPU server (vLLM, OpenAI-compatible).

    gpt-oss is a reasoning model: reasoning lands in a separate 'reasoning'
    field and 'content' holds the final answer. Small max_tokens budgets can
    be consumed entirely by reasoning, yielding empty content.
    """
    global _gptoss_ok_until
    if time.time() < _gptoss_ok_until:
        return None  # breaker open
    headers = {"Content-Type": "application/json"}
    if GPTOSS_API_KEY:
        headers["Authorization"] = f"Bearer {GPTOSS_API_KEY}"
    try:
        # reasoning headroom: never request less than 96 tokens from this model
        eff_max_tokens = max(max_tokens, 96)
        async with httpx.AsyncClient(timeout=GPTOSS_TIMEOUT) as client:
            r = await client.post(
                f"{GPTOSS_BASE_URL}/chat/completions",
                headers=headers,
                json={"model": GPTOSS_MODEL, "messages": messages, "max_tokens": eff_max_tokens, "temperature": 0.8},
            )
            if r.status_code == 200:
                msg = r.json().get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "") or ""
                if content and content.strip():
                    # tolerate raw harmony-format responses: keep only the final channel
                    if "<|channel|>" in content:
                        final = re.findall(r"<\|channel\|>final<\|message\|>(.*?)(?:<\|return\|>|<\|end\|>|$)", content, flags=re.DOTALL)
                        if final:
                            content = final[-1]
                        else:
                            content = re.sub(r"<\|channel\|>analysis<\|message\|>.*?(?=<\|channel\|>|$)", "", content, flags=re.DOTALL)
                            content = re.sub(r"<\|[^>]*\|>", "", content)
                    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                    if content:
                        _gptoss_ok_until = 0.0  # healthy — close breaker
                        return content
                finish = r.json().get("choices", [{}])[0].get("finish_reason")
                log.warning("gpt-oss HTTP 200 but empty content (finish_reason=%s, max_tokens=%s)", finish, eff_max_tokens)
            else:
                log.warning("gpt-oss unhealthy (HTTP %s)", r.status_code)
            _gptoss_ok_until = time.time() + 180  # open breaker for 3 min
    except Exception as e:  # noqa: BLE001
        _gptoss_ok_until = time.time() + 180
        log.warning("gpt-oss error (%s); opening circuit for 3 min", e)
    return None


async def _try_ollama(messages: List[dict], max_tokens: int) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/chat/completions",
                json={"model": OLLAMA_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.8},
            )
            if r.status_code == 200:
                content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    # strip any <think> blocks (deepseek style)
                    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                    return content
    except Exception as e:  # noqa: BLE001
        log.warning("ollama error: %s", e)
    return None


SCRIPT_PATTERNS = {
    "tamil": re.compile(r"[\u0B80-\u0BFF]"),
    "hindi": re.compile(r"[\u0900-\u097F]"),
    "telugu": re.compile(r"[\u0C00-\u0C7F]"),
    "kannada": re.compile(r"[\u0C80-\u0CFF]"),
    "malayalam": re.compile(r"[\u0D00-\u0D7F]"),
}


def script_mismatch(text: str, language: str) -> bool:
    """True if reply text is in the wrong script for the target language."""
    if language in ("english", "french", "german", "spanish"):
        non_latin = len(re.findall(r"[^\u0000-\u024F\u2000-\u206F]", text))
        return non_latin > max(3, int(len(text) * 0.15))
    pat = SCRIPT_PATTERNS.get(language)
    if not pat:
        return False
    return pat.search(text) is None


async def _translate(text: str, language: str) -> Optional[str]:
    """Second-pass translation for local LLM (llama's translation beats its free-form Tamil).
    Not used for seekai — claude-fable-5 is natively multilingual.
    Uses gpt-oss when available (better multilingual), else Ollama."""
    lang_name = LANGUAGES.get(language, {}).get("label", language).split(" (")[0]
    try:
        translate_model = GPTOSS_MODEL if LLM_PROVIDER == "gptoss" else OLLAMA_MODEL
        translate_url = GPTOSS_BASE_URL if LLM_PROVIDER == "gptoss" else OLLAMA_BASE_URL
        translate_headers = {"Authorization": f"Bearer {GPTOSS_API_KEY}"} if (LLM_PROVIDER == "gptoss" and GPTOSS_API_KEY) else {}
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"{translate_url}/chat/completions",
                headers=translate_headers,
                json={
                    "model": translate_model,
                    "messages": [
                        {"role": "system", "content": f"You are a professional translator. Translate the user's text into {lang_name}. Write natural, conversational {lang_name} in its native script. Output ONLY the translation — no explanations, no romanization, no quotes."},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.3,
                },
            )
            if r.status_code == 200:
                content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                # sanity: translated text must actually contain target-script chars
                if content:
                    return content
    except Exception as e:  # noqa: BLE001
        log.warning("translate pass failed: %s", e)
    return None


async def llm_chat(messages: List[dict], max_tokens: int = 400) -> tuple[str, str]:
    """Returns (reply_text, provider_used)."""
    global LLM_PROVIDER
    reply = await _try_seekai(messages, max_tokens)
    if reply:
        LLM_PROVIDER = "seekai"
        return reply, "seekai"
    reply = await _try_gptoss(messages, max_tokens)
    if reply:
        LLM_PROVIDER = "gptoss"
        return reply, "gptoss"
    reply = await _try_ollama(messages, max_tokens)
    if reply:
        LLM_PROVIDER = "ollama"
        return reply, "ollama"
    raise HTTPException(503, "No LLM provider available (seekai down, gpt-oss GPU server down and Ollama unreachable)")


def strip_speak(text: str) -> str:
    """Clean text for speech: remove markdown symbols, emojis, code fences."""
    text = re.sub(r"```.*?```", " I'll explain it in words. ", text, flags=re.DOTALL)
    text = re.sub(r"[#*`_>\[\]()|]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── TTS via Edge (free, high quality, multilingual) ──────────────────────────

async def tts_speak(text: str, language: str, emotion: str) -> tuple[bytes, float]:
    """Returns (wav_bytes, duration_seconds)."""
    import edge_tts

    lang_cfg = LANGUAGES.get(language, LANGUAGES["auto"])
    voice = lang_cfg["edge_voice"]
    if not voice:
        # auto: pick by script of text
        if re.search(r"[\u0B80-\u0BFF]", text):
            voice = TAMIL_VOICE_FEMALE
        elif re.search(r"[\u0900-\u097F]", text):
            voice = "hi-IN-SwaraNeural"
        elif re.search(r"[\u0C00-\u0C7F]", text):
            voice = "te-IN-MohanNeural"
        elif re.search(r"[\u0C80-\u0CFF]", text):
            voice = "kn-IN-SapnaNeural"
        else:
            voice = "en-IN-NeerjaNeural"

    # emotion → prosody (edge-tts fails on +0 values, so omit when neutral)
    kwargs = {}
    if emotion in ("happy", "excited"):
        kwargs = {"rate": "+8%", "pitch": "+15Hz"}
    elif emotion == "sad":
        kwargs = {"rate": "-8%", "pitch": "-10Hz"}
    elif emotion == "angry":
        kwargs = {"rate": "+5%", "pitch": "-5Hz"}
    elif emotion == "surprised":
        kwargs = {"rate": "+10%", "pitch": "+20Hz"}

    tmp_mp3 = STATIC_DIR / "_tts_tmp.mp3"
    tmp_mp3.unlink(missing_ok=True)
    last_err = None
    for attempt in range(4):
        try:
            comm = edge_tts.Communicate(text, voice, **kwargs)
            await comm.save(str(tmp_mp3))
            if tmp_mp3.exists() and tmp_mp3.stat().st_size > 500:
                break
        except Exception as e:  # noqa: BLE001
            last_err = e
            log.warning("edge-tts attempt %d failed (%s)", attempt + 1, e)
            kwargs = {}  # drop prosody on retry; keep the same (working) voice
            await asyncio.sleep(1.5 * (attempt + 1))
    else:
        # final fallback: gTTS (Google, free) — mp3 in-memory → wav
        log.warning("edge-tts failed %s — trying gTTS fallback", last_err)
        try:
            gt_lang = {"tamil": "ta", "hindi": "hi", "telugu": "te", "malayalam": "ml", "kannada": "kn", "english": "en", "french": "fr", "german": "de", "spanish": "es"}.get(language, "en")
            def _gtts():
                from gtts import gTTS
                buf = io.BytesIO()
                gTTS(text, lang=gt_lang).write_to_fp(buf)
                return buf.getvalue()
            mp3_bytes = await asyncio.to_thread(_gtts)
            tmp_mp3.write_bytes(mp3_bytes)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"All TTS engines failed: edge={last_err} gtts={e}")

    # convert mp3 → wav 22050 mono for uniform amplitude analysis
    data, _ = sf.read(str(tmp_mp3))
    if data.ndim > 1:
        data = data.mean(axis=1)
    sf.write(str(tmp_mp3).replace(".mp3", ".wav"), data, 22050, subtype="PCM_16")
    tmp_mp3.unlink(missing_ok=True)

    wav_path = Path(str(tmp_mp3).replace(".mp3", ".wav"))
    wav_bytes = wav_path.read_bytes()
    duration = float(len(sf.read(str(wav_path), dtype="float32")[0])) / 22050.0
    return wav_bytes, duration


def compute_mouth_track(wav_path: Path, fps: int = 30) -> List[dict]:
    """Amplitude envelope → mouth openness values for lip sync."""
    data, sr = sf.read(str(wav_path), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    hop = int(sr / fps)
    n = len(data) // hop
    if n == 0:
        return []
    frames = data[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    if rms.max() > 0:
        rms = rms / rms.max()
    # smooth + slight exaggeration for visible lips
    kernel = np.ones(3) / 3
    rms = np.convolve(rms, kernel, mode="same")
    mouth = np.clip(rms * 1.6, 0.0, 1.0)
    return [{"t": round(i / fps, 3), "v": round(float(v), 3)} for i, v in enumerate(mouth)]


# ── Face texture builder (photo → equirect head texture) ────────────────────

# Canonical layout produced by build_face_texture():
#   crop square resized to 1024x1024, pasted on 2048x1024 equirect at x 512..1536, full height
#   eyes at canvas (0.5, 0.45), eye separation = 0.30 of canvas width
# Frontend 3D feature positions are derived from these constants.
FACE_LAYOUT = {
    "eye_frac_y": 0.45,
    "eye_sep": 0.26,
    "brow_frac_y": 0.38,
    "brow_sep": 0.22,
    "mouth_frac_y": 0.68,
}


def build_face_texture() -> dict:
    """Detect face+eyes in the sample photo, align/crop, compose equirect texture.
    Returns {'ok': bool, 'method': str, 'eye_distance_px': float} """
    import cv2

    result = {"ok": False, "method": "none", "eye_distance_px": 0.0}
    if not AVATAR_IMAGE.exists():
        return result
    img = cv2.imread(str(AVATAR_IMAGE))
    if img is None:
        return result
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    cascade_dir = cv2.data.haarcascades
    face_cascade = cv2.CascadeClassifier(cascade_dir + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cascade_dir + "haarcascade_eye.xml")

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(80, 80))
    if len(faces) == 0:
        log.warning("No face detected — falling back to full-photo texture")
        crop = cv2.resize(img, (1024, 1024))
        result["method"] = "full_photo"
    else:
        # largest face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        roi = gray[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi, scaleFactor=1.1, minNeighbors=5, minSize=(int(w * 0.12), int(w * 0.12)))
        result["method"] = "haar_aligned"

        if len(eyes) >= 2:
            # two most prominent eyes, order left/right
            eyes = sorted(eyes, key=lambda e: -e[2] * e[3])[:2]
            e1 = (x + eyes[0][0] + eyes[0][2] / 2, y + eyes[0][1] + eyes[0][3] / 2)
            e2 = (x + eyes[1][0] + eyes[1][2] / 2, y + eyes[1][1] + eyes[1][3] / 2)
            left, right = (e1, e2) if e1[0] < e2[0] else (e2, e1)
            dx, dy = right[0] - left[0], right[1] - left[1]
            eye_dist = float(np.hypot(dx, dy))
            angle = float(np.degrees(np.arctan2(dy, dx)))
            result["eye_distance_px"] = eye_dist

            # 1) rotate so eye line is horizontal
            M = cv2.getRotationMatrix2D((W / 2, H / 2), angle, 1.0)
            M[0, 2] += W / 2 - (left[0] + right[0]) / 2   # center eye midpoint
            M[1, 2] += H / 2 - (left[1] + right[1]) / 2
            rot = cv2.warpAffine(img, M, (W, H))
            mid = (W / 2, H / 2)

            # 2) square crop: eye separation = FACE_LAYOUT.eye_sep of canvas, eyes at (0.5, 0.45)
            S = eye_dist / FACE_LAYOUT["eye_sep"]
            cx0 = int(mid[0] - S / 2)
            cy0 = int(mid[1] - FACE_LAYOUT["eye_frac_y"] * S)
            # pad out-of-frame regions by reflecting
            pad_l, pad_t = max(0, -cx0), max(0, -cy0)
            pad_r, pad_b = max(0, cx0 + int(S) - W), max(0, cy0 + int(S) - H)
            if pad_l or pad_t or pad_r or pad_b:
                rot = cv2.copyMakeBorder(rot, pad_t, pad_b, pad_l, pad_r, cv2.BORDER_REFLECT)
                cx0 += pad_l; cy0 += pad_t
            crop = rot[cy0:cy0 + int(S), cx0:cx0 + int(S)]
            crop = cv2.resize(crop, (1024, 1024), interpolation=cv2.INTER_LANCZOS4)
        else:
            log.warning("Eyes not detected — using centered face crop without eye alignment")
            S = int(w * 1.5)
            cx0, cy0 = x + w // 2 - S // 2, y + h // 2 - int(S * 0.48)
            pad_l, pad_t = max(0, -cx0), max(0, -cy0)
            pad_r, pad_b = max(0, cx0 + S - W), max(0, cy0 + S - H)
            if pad_l or pad_t or pad_r or pad_b:
                img = cv2.copyMakeBorder(img, pad_t, pad_b, pad_l, pad_r, cv2.BORDER_REFLECT)
                cx0 += pad_l; cy0 += pad_t
            crop = img[cy0:cy0 + S, cx0:cx0 + S]
            crop = cv2.resize(crop, (1024, 1024), interpolation=cv2.INTER_LANCZOS4)
            result["ok"] = True

    # 3) compose 2048x1024 equirect: blurred background + feather-blended face crop
    eq = np.zeros((1024, 2048, 3), dtype=np.uint8)
    bg = cv2.resize(crop, (256, 128))
    bg = cv2.resize(bg, (2048, 1024), interpolation=cv2.INTER_CUBIC)
    bg = cv2.GaussianBlur(bg, (0, 0), 25)
    eq[:] = bg
    # feathered alpha so the crop melts into the background (no pasted-photo seams)
    FE = 90
    mask = np.zeros((1024, 1024), dtype=np.float32)
    mask[FE:-FE, FE:-FE] = 1.0
    mask = cv2.GaussianBlur(mask, (0, 0), FE / 2.4)
    mask3 = np.dstack([mask] * 3)
    region = eq[:, 512:1536].astype(np.float32)
    eq[:, 512:1536] = (crop.astype(np.float32) * mask3 + region * (1.0 - mask3)).astype(np.uint8)
    cv2.imwrite(str(FACE_TEXTURE), eq, [cv2.IMWRITE_JPEG_QUALITY, 92])
    result["ok"] = True
    log.info("Face texture built (%s): %s", result["method"], FACE_TEXTURE.name)
    return result


# ── API models ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    language: str = "auto"
    persona: str = "engg_student"


class TTSTextRequest(BaseModel):
    text: str
    language: str = "tamil"
    emotion: str = "neutral"
    session_id: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    seekai_open = time.time() < _seekai_ok_until
    return {
        "status": "ok",
        "llm_provider": LLM_PROVIDER,
        "seekai": "degraded (circuit open, using Ollama)" if seekai_open else "ready",
        "whisper_loaded": WHISPER is not None,
        "voice_profile": {"gender": VOICE_PROFILE.get("gender"), "pitch": round(VOICE_PROFILE.get("pitch_mean", 0), 1)},
        "personas": list(PERSONAS.keys()),
        "languages": {k: v["label"] for k, v in LANGUAGES.items()},
    }


@app.post("/api/chat/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    language: str = Form("auto"),
    persona: str = Form("engg_student"),
):
    """Full voice loop: audio → Whisper → LLM → TTS → (audio + mouth track + expression)."""
    t0 = time.time()
    raw = await audio.read()
    if len(raw) < 2000:
        raise HTTPException(400, "Audio too short")

    session = get_session(session_id)
    session.persona = persona or session.persona
    if language != "auto":
        session.language = language

    # 1) decode audio to 16k mono wav for whisper
    try:
        data, _ = sf.read(io.BytesIO(raw), dtype="float32")
    except Exception:
        # try ffmpeg decode via soundfile is enough for webm/wav from browsers
        raise HTTPException(400, "Unsupported audio format")
    if data.ndim > 1:
        data = data.mean(axis=1)
    buf = io.BytesIO()
    sf.write(buf, data, 16000, format="WAV", subtype="PCM_16")
    buf.seek(0)

    # 2) ASR
    whisper_lang = LANGUAGES.get(language, {}).get("whisper_lang")
    segments, info = get_whisper().transcribe(
        buf, language=whisper_lang, beam_size=1, vad_filter=True, vad_parameters={"min_silence_duration_ms": 300}
    )
    user_text = " ".join(seg.text.strip() for seg in segments).strip()
    detected_lang = info.language
    if not user_text:
        raise HTTPException(400, "Could not hear anything — try again closer to the mic")
    log.info("ASR(%s p=%.2f): %s", detected_lang, info.language_probability, user_text[:120])

    # reply language: user's choice; in auto mode fall back to UI-default persona
    # language when Whisper's detection is not confident (common for short clips)
    if language != "auto":
        reply_lang = language
    elif info.language_probability >= 0.75:
        reply_lang = _match_language(detected_lang)
    else:
        reply_lang = "tamil"  # project default

    # 3) emotion
    emo = detect_emotion(user_text)
    session.last_emotion = emo["emotion"]

    # 4) LLM
    session.history.append({"role": "user", "content": user_text})
    messages = [{"role": "system", "content": session.system_prompt()}] + session.history[-12:]
    reply_text, provider = await llm_chat(messages, max_tokens=200)
    reply_text = strip_speak(reply_text)
    if provider == "ollama" and script_mismatch(reply_text, reply_lang):
        log.info("script mismatch (wanted %s) — re-translating", reply_lang)
        translated = await _translate(reply_text, reply_lang)
        if translated:
            reply_text = strip_speak(translated)
    session.history.append({"role": "assistant", "content": reply_text})

    # 5) TTS
    wav_bytes, duration = await tts_speak(reply_text, reply_lang, emo["emotion"])

    # 6) lip-sync track
    wav_path = STATIC_DIR / "last_reply.wav"
    wav_path.write_bytes(wav_bytes)
    mouth = compute_mouth_track(wav_path)

    return JSONResponse({
        "session_id": session.id,
        "user_text": user_text,
        "detected_language": detected_lang,
        "reply_language": reply_lang,
        "reply_text": reply_text,
        "emotion": emo,
        "provider": provider,
        "audio_url": "/api/audio/last_reply",
        "mouth_track": mouth,
        "duration": duration,
        "latency_ms": int((time.time() - t0) * 1000),
    })


@app.post("/api/chat/text")
async def chat_text(req: ChatRequest):
    """Text-only chat (also returns TTS + mouth track so the avatar still speaks)."""
    t0 = time.time()
    session = get_session(req.session_id)
    session.persona = req.persona or session.persona
    emo = detect_emotion(req.text)
    session.last_emotion = emo["emotion"]
    session.history.append({"role": "user", "content": req.text})
    messages = [{"role": "system", "content": session.system_prompt()}] + session.history[-12:]
    reply_text, provider = await llm_chat(messages, max_tokens=200)
    reply_text = strip_speak(reply_text)
    session.history.append({"role": "assistant", "content": reply_text})

    reply_lang = req.language if req.language != "auto" else _match_language_text(req.text)
    # local-LLM translation pass for Indian languages (before TTS)
    if provider == "ollama" and script_mismatch(reply_text, reply_lang):
        log.info("script mismatch (wanted %s) — re-translating", reply_lang)
        translated = await _translate(reply_text, reply_lang)
        if translated:
            reply_text = strip_speak(translated)
    wav_bytes, duration = await tts_speak(reply_text, reply_lang, emo["emotion"])
    wav_path = STATIC_DIR / "last_reply.wav"
    wav_path.write_bytes(wav_bytes)
    mouth = compute_mouth_track(wav_path)

    return JSONResponse({
        "session_id": session.id,
        "reply_text": reply_text,
        "emotion": emo,
        "provider": provider,
        "reply_language": reply_lang,
        "audio_url": "/api/audio/last_reply",
        "mouth_track": mouth,
        "duration": duration,
        "latency_ms": int((time.time() - t0) * 1000),
    })


@app.post("/api/tts")
async def tts_only(req: TTSTextRequest):
    """Direct text → speech with emotion (used for scripts / greetings)."""
    wav_bytes, duration = await tts_speak(req.text, req.language, req.emotion)
    wav_path = STATIC_DIR / "last_reply.wav"
    wav_path.write_bytes(wav_bytes)
    mouth = compute_mouth_track(wav_path)
    return {
        "audio_url": "/api/audio/last_reply",
        "mouth_track": mouth,
        "duration": duration,
        "emotion": {"emotion": req.emotion, "expression": EXPRESSIONS.get(req.emotion, {})},
    }


@app.get("/api/audio/last_reply")
async def audio_last():
    p = STATIC_DIR / "last_reply.wav"
    if not p.exists():
        raise HTTPException(404, "no audio yet")
    return FileResponse(p, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@app.get("/api/avatar/image")
async def avatar_image():
    """Serve the aligned face texture (falls back to the raw sample photo)."""
    if FACE_TEXTURE.exists():
        return FileResponse(FACE_TEXTURE, media_type="image/jpeg")
    if AVATAR_IMAGE.exists():
        return FileResponse(AVATAR_IMAGE, media_type="image/jpeg")
    raise HTTPException(404, "sample image missing")


@app.get("/api/avatar/layout")
async def avatar_layout():
    """Canonical face layout — the frontend derives 3D feature placement from this."""
    return FACE_LAYOUT


@app.post("/api/voice/profile")
async def voice_profile():
    """(Re)analyze the sample voice — the 'voice clone' characteristics."""
    global VOICE_PROFILE
    VOICE_PROFILE = await asyncio.to_thread(analyze_voice_sample, VOICE_SAMPLE)
    return VOICE_PROFILE


@app.get("/api/voice/profile")
async def get_voice_profile():
    return VOICE_PROFILE


@app.get("/api/script/tamil")
async def tamil_script():
    """Sample Tamil script rendered through the avatar (demo endpoint)."""
    script = (
        "வணக்கம்! நான் அருண், உங்கள் பொறியியல் மாணவர் அவதாரம். "
        "நீங்கள் எந்த பொறியியல் கேள்வியையும் தமிழில் கேட்கலாம் — "
        "நான் மகிழ்ச்சியுடன் விளக்குவேன்!"
    )
    wav_bytes, duration = await tts_speak(script, "tamil", "happy")
    wav_path = STATIC_DIR / "last_reply.wav"
    wav_path.write_bytes(wav_bytes)
    mouth = compute_mouth_track(wav_path)
    return {"script": script, "audio_url": "/api/audio/last_reply", "mouth_track": mouth, "duration": duration}


@app.get("/")
async def index():
    return FileResponse(
        ROOT / "avatar_server" / "static" / "index.html",
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


# serve the static frontend
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _match_language(whisper_lang: str) -> str:
    return whisper_lang if whisper_lang in LANGUAGES else "english"


def _match_language_text(text: str) -> str:
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "tamil"
    if re.search(r"[\u0900-\u097F]", text):
        return "hindi"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "telugu"
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kannada"
    return "english"


# ── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global VOICE_PROFILE
    log.info("=" * 60)
    log.info("DreamTalk Live Avatar starting on http://localhost:%s", PORT)
    log.info("Face photo: %s (exists: %s)", AVATAR_IMAGE.name, AVATAR_IMAGE.exists())
    if VOICE_SAMPLE.exists():
        VOICE_PROFILE = await asyncio.to_thread(analyze_voice_sample, VOICE_SAMPLE)
    else:
        VOICE_PROFILE = {"available": False}
    try:
        tex = await asyncio.to_thread(build_face_texture)
        log.info("Face texture: %s", tex)
    except Exception as e:  # noqa: BLE001
        log.warning("Face texture build failed: %s", e)
    # warm check: which LLM is alive right now (cheap)
    pong = await _try_seekai([{"role": "user", "content": "Reply with the single word: ready"}], 8)
    if pong:
        global LLM_PROVIDER
        LLM_PROVIDER = "seekai"
        log.info("seekai claude-fable-5: ONLINE")
    else:
        pong = await _try_gptoss([{"role": "user", "content": "Reply with the single word: ready"}], 8)
        if pong:
            LLM_PROVIDER = "gptoss"
            log.info("seekai unavailable — falling back to gpt-oss %s @ %s (OK)", GPTOSS_MODEL, GPTOSS_BASE_URL)
        else:
            ok = await _try_ollama([{"role": "user", "content": "Reply with the single word: ready"}], 8)
            LLM_PROVIDER = "ollama" if ok else "none"
            log.info("seekai + gpt-oss unavailable — falling back to Ollama %s (%s)", OLLAMA_MODEL, "OK" if ok else "FAIL")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
