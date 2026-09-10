"""DreamTalk Avatar Router — integrated into the backend.

Provides 3D avatar viewer endpoints, pipeline processing, chat, TTS,
script generation, and multi-language support (English, Kannada, Tamil, Hindi).
Mounted at /api/avatar in the backend.

Also starts all models (face pipeline, voice pipeline, brain pipeline, TTS engines)
on first initialization.
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("dreamtalk.avatar")

# ── Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
STATIC_DIR = PROJECT_ROOT / "avatar" / "static"
UPLOAD_DIR = PROJECT_ROOT / "local_upload_testing"
OUTPUT_DIR = PROJECT_ROOT / "pipeline_outputs"

# IndicF5 microservice location. Inside Docker, set to
# http://host.docker.internal:8003 to reach the host-side service.
INDICF5_BASE_URL = os.environ.get("INDICF5_BASE_URL", "http://localhost:8003")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ── Supported Languages for TTS ──────────────────────────────────────
LANGUAGES = {
    "en": {"name": "English", "voice_female": "en-US-JennyNeural", "voice_male": "en-US-GuyNeural"},
    "ta": {"name": "Tamil", "voice_female": "ta-IN-PallaviNeural", "voice_male": "ta-IN-ValluvarNeural"},
    "hi": {"name": "Hindi", "voice_female": "hi-IN-SwaraNeural", "voice_male": "hi-IN-MadhurNeural"},
    "kn": {"name": "Kannada", "voice_female": "kn-IN-SapnaNeural", "voice_male": "kn-IN-GaganNeural"},
    "te": {"name": "Telugu", "voice_female": "te-IN-ShrutiNeural", "voice_male": "te-IN-MohanNeural"},
    "ml": {"name": "Malayalam", "voice_female": "ml-IN-SobhanaNeural", "voice_male": "ml-IN-MidhunNeural"},
    "bn": {"name": "Bengali", "voice_female": "bn-IN-TanishaaNeural", "voice_male": "bn-IN-BashkarNeural"},
    "mr": {"name": "Marathi", "voice_female": "mr-IN-AarohiNeural", "voice_male": "mr-IN-ManoharNeural"},
    "gu": {"name": "Gujarati", "voice_female": "gu-IN-DhwaniNeural", "voice_male": "gu-IN-NiranjanNeural"},
    "pa": {"name": "Punjabi", "voice_female": "pa-IN-GurpreetNeural", "voice_male": "pa-IN-GurpreetNeural"},
    "or": {"name": "Odia", "voice_female": "or-IN-SubhasreeNeural", "voice_male": "or-IN-SubhasreeNeural"},
    "as": {"name": "Assamese", "voice_female": "as-IN-HemantiNeural", "voice_male": "as-IN-HemantiNeural"},
}

# ── Global Model State ────────────────────────────────────────────────
models_loaded = False
orchestrator = None
kokoro_engine = None
knowledge_base = None

PIPELINE_AVAILABLE = False
EDGETTS_AVAILABLE = False
SOUNDFILE_OK = False
KOKORO_AVAILABLE = False
GTTS_AVAILABLE = False
PYTTSX3_AVAILABLE = False
INDICF5_AVAILABLE = False
INDICTTS_AVAILABLE = False
_indicf5_engine = None
_pyttsx3_engine = None
_pyttsx3_lock = None

session_data = {
    "pipeline_id": None,
    "face_result": None,
    "voice_result": None,
    "brain_result": None,
    "emotion_result": None,
    "object_result": None,
    "mesh_path": None,
    "texture_path": None,
    "cloned_voice_path": None,
    "tts_path": None,
    "last_pipeline_run": None,
    "current_language": "en",
}

# ── Router ────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/avatar", tags=["avatar"])


# ── Model Loader ──────────────────────────────────────────────────────
async def load_all_models():
    """Pre-load all models on startup. Called once from backend lifespan."""
    global models_loaded, orchestrator, knowledge_base, kokoro_engine
    global PIPELINE_AVAILABLE, EDGETTS_AVAILABLE, SOUNDFILE_OK, KOKORO_AVAILABLE
    global GTTS_AVAILABLE, PYTTSX3_AVAILABLE
    global INDICF5_AVAILABLE, INDICTTS_AVAILABLE, _indicf5_engine
    global _pyttsx3_engine, _pyttsx3_lock

    if models_loaded:
        logger.info("Models already loaded")
        return

    logger.info("=" * 60)
    logger.info("Loading all DreamTalk models...")
    logger.info("=" * 60)

    # 1. Pipeline (face, voice, brain)
    try:
        from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator()
        PIPELINE_AVAILABLE = True
        logger.info("  [OK] PipelineOrchestrator (face + voice + brain)")
    except Exception as e:
        logger.warning(f"  [FAIL] Pipeline: {e}")

    # 2. Edge-TTS (multi-language, Azure voices)
    try:
        import edge_tts
        EDGETTS_AVAILABLE = True
        logger.info("  [OK] Edge-TTS")
    except Exception as e:
        logger.warning(f"  [FAIL] Edge-TTS: {e}")

    # 3. gTTS (Google Text-to-Speech — free, 100+ languages including ta/kn/hi)
    try:
        from gtts import gTTS
        GTTS_AVAILABLE = True
        logger.info("  [OK] gTTS (Google TTS, supports ta/kn/hi)")
    except Exception as e:
        logger.warning(f"  [FAIL] gTTS: {e}")

    # 4. pyttsx3 (offline Windows SAPI5 — last resort)
    try:
        import pyttsx3 as _pt
        PYTTSX3_AVAILABLE = True
        # Initialize engine once at module level for thread safety
        _pyttsx3_engine = _pt.init(driverName='sapi5')
        rate = _pyttsx3_engine.getProperty('rate')
        _pyttsx3_engine.setProperty('rate', max(rate - 50, 100))
        _pyttsx3_engine.setProperty('volume', 0.9)
        # Select female voice
        voices = _pyttsx3_engine.getProperty('voices')
        for v in voices:
            if 'female' in v.name.lower() or 'zira' in v.name.lower():
                _pyttsx3_engine.setProperty('voice', v.id)
                break
        _pyttsx3_lock = asyncio.Lock()
        logger.info("  [OK] pyttsx3 (offline Windows TTS, pre-initialized)")
    except Exception as e:
        logger.warning(f"  [FAIL] pyttsx3: {e}")

    # 5. SoundFile (audio I/O for WAV/flac conversion)
    try:
        import soundfile as sf
        SOUNDFILE_OK = True
        logger.info("  [OK] SoundFile")
    except Exception:
        logger.warning("  [FAIL] SoundFile")

    # 7. Kokoro TTS (Hindi + English voices)
    try:
        from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
        kokoro_engine = KokoroTTSEngine(device="cpu")
        KOKORO_AVAILABLE = True
        voices = kokoro_engine.list_voices()
        logger.info(f"  [OK] Kokoro TTS ({len(voices)} voices, {len(kokoro_engine.SUPPORTED_LANGUAGES)} languages)")
    except Exception as e:
        logger.warning(f"  [FAIL] Kokoro TTS: {e}")

    # 8. IndicF5 TTS (F5-TTS base — neural zero-shot TTS, supports ta/kn/hi/en)
    try:
        from dreamtalk.voice.core.tts.indicf5_engine import IndicF5TTSEngine
        # Don't initialize eagerly — initialization triggers 2GB HuggingFace download
        # Instead, cache the class for lazy init
        INDICF5_AVAILABLE = True
        logger.info("  [OK] IndicF5 TTS (lazy — model downloads on first use)")
    except Exception as e:
        logger.warning(f"  [FAIL] IndicF5 TTS: {e}")

    # 9. Indic TTS (AI4Bharat FastPitch+HiFi-GAN — 14 Indian languages, needs model_dir)
    try:
        from dreamtalk.voice.core.tts.indic_tts_engine import IndicTTSEngine
        INDICTTS_AVAILABLE = True
        logger.info("  [OK] Indic TTS (lazy — needs model_dir to be set)")
    except Exception as e:
        logger.warning(f"  [FAIL] Indic TTS: {e}")

    # 10. Brain-Cog (expanded)
    try:
        from dreamtalk.cognition.core.snn.brain_cog.brain_cog_api import BrainCogAPI
        brain_cog_api = BrainCogAPI()
        ntypes = brain_cog_api.neuron_types_available()
        logger.info(f"  [OK] Brain-Cog API ({len(ntypes)} neuron types, {len(brain_cog_api.encoding_methods_available())} encodings)")
    except Exception as e:
        logger.warning(f"  [FAIL] Brain-Cog: {e}")

    # 6. Knowledge Base
    try:
        from dreamtalk.backend.services.knowledge_base import StudentKnowledgeBase
        knowledge_base = StudentKnowledgeBase()
        logger.info("  [OK] Student Knowledge Base (Sahyadri CSE)")
    except Exception as e:
        logger.warning(f"  [FAIL] Knowledge Base: {e}")

    # 7. FLAME 3D Model (using numpy-only loader, no chumpy dependency)
    try:
        from dreamtalk.pipeline.flame_fitter import FLAMELoader
        # Prefer the chumpy-free numpy pickle; fall back to original if only that exists
        flame_path = PROJECT_ROOT / "weights" / "flame" / "FLAME2020_numpy.pkl"
        if not flame_path.exists():
            flame_path = PROJECT_ROOT / "weights" / "flame" / "FLAME2020.pkl"
        if flame_path.exists():
            flame_model = FLAMELoader(str(flame_path))
            logger.info(f"  [OK] FLAME 3D ({flame_model.num_vertices}v, {flame_model.num_faces}f)")
        else:
            logger.info("  [OK] FLAME 3D class (model weights not loaded)")
    except Exception as e:
        logger.warning(f"  [FAIL] FLAME 3D: {e}")

    # 8. OpenCV
    try:
        cv2.__version__
        logger.info("  [OK] OpenCV")
    except Exception:
        logger.warning("  [FAIL] OpenCV")

    logger.info("=" * 60)
    if PIPELINE_AVAILABLE or EDGETTS_AVAILABLE or KOKORO_AVAILABLE:
        logger.info("Avatar models loaded successfully!")
    else:
        logger.warning("Most models failed to load - check dependencies")
    logger.info("=" * 60)

    models_loaded = True


# ── HTML Frontend ────────────────────────────────────────────────────

@router.get("/viewer", response_class=HTMLResponse)
async def avatar_viewer():
    """Serve the 3D avatar viewer HTML page."""
    html_path = STATIC_DIR / "avatar_viewer.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Avatar Viewer</h1><p>Loading...</p>")


@router.get("/doctor", response_class=HTMLResponse)
async def doctor_avatar_viewer():
    """Serve the real-time 3D doctor avatar page."""
    html_path = STATIC_DIR / "doctor_avatar.html"
    logger.info(f"Doctor avatar: looking for {html_path} (exists={html_path.exists()}, STATIC_DIR={STATIC_DIR})")
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse(f"<h1>Doctor Avatar</h1><p>Page not found at {html_path}.</p>")


# ── Status ────────────────────────────────────────────────────────────

@router.get("/status")
async def avatar_status():
    """Get avatar system status including model availability."""
    return {
        "models_loaded": models_loaded,
        "pipeline_available": PIPELINE_AVAILABLE,
        "kokoro_available": KOKORO_AVAILABLE,
        "edgetts_available": EDGETTS_AVAILABLE,
        "indicf5_available": True,
        "knowledge_base_available": knowledge_base is not None,
        "languages": {k: v["name"] for k, v in LANGUAGES.items()},
        "session": {
            "has_face": session_data["face_result"] is not None,
            "has_voice": session_data["voice_result"] is not None,
            "has_mesh": session_data["mesh_path"] is not None,
            "pipeline_id": session_data["pipeline_id"],
            "current_language": session_data["current_language"],
        },
    }


# ── Knowledge Base ────────────────────────────────────────────────────

@router.get("/knowledge")
async def get_knowledge(query: str = ""):
    """Query the student knowledge base."""
    if knowledge_base is None:
        try:
            from dreamtalk.backend.services.knowledge_base import StudentKnowledgeBase
            globals()["knowledge_base"] = StudentKnowledgeBase()
        except Exception as e:
            return {"error": f"Knowledge base unavailable: {e}"}

    if query:
        response = knowledge_base.get_response(query)
        if response:
            return {"query": query, "response": response}
        return {"query": query, "response": None, "suggestions": [
            "What is your name?", "Tell me about your college",
            "What year are you in?", "What courses do you study?",
            "Tell me about your projects", "What are your interests?",
        ]}

    return {"intro": knowledge_base.get_intro()}


# ── Language ──────────────────────────────────────────────────────────

@router.get("/languages")
async def list_languages():
    """List supported TTS languages."""
    return {"languages": LANGUAGES, "current": session_data["current_language"]}


@router.post("/language")
async def set_language(language: str = Form(...)):
    """Set the current TTS language."""
    if language in LANGUAGES:
        session_data["current_language"] = language
        return {"status": "ok", "language": language, "voice": LANGUAGES[language]}
    return {"error": f"Unsupported language: {language}. Supported: {list(LANGUAGES.keys())}"}


# ── Pipeline ──────────────────────────────────────────────────────────

@router.post("/pipeline/run")
async def run_avatar_pipeline(
    image: UploadFile = File(None),
    voice: UploadFile = File(None),
    text: str = Form("Hello! I'm your Digital Twin."),
    role: str = Form("normal_user"),
):
    """Run the full face + voice pipeline on uploaded files."""
    if not PIPELINE_AVAILABLE or orchestrator is None:
        return JSONResponse({"error": "Pipeline not available. Models not loaded."}, status_code=503)

    from dreamtalk.pipeline.models import PipelineRequest

    twin_id = f"avatar_{uuid.uuid4().hex[:8]}"
    img_paths = []
    voice_paths = []

    if image:
        ext = os.path.splitext(image.filename or "image.jpg")[1] or ".jpg"
        ip = os.path.join(UPLOAD_DIR, f"upload_img_{uuid.uuid4().hex}{ext}")
        content = await image.read()
        with open(ip, "wb") as f:
            f.write(content)
        img_paths.append(ip)

    if voice:
        ext = os.path.splitext(voice.filename or "audio.wav")[1] or ".wav"
        vp = os.path.join(UPLOAD_DIR, f"upload_voice_{uuid.uuid4().hex}{ext}")
        content = await voice.read()
        with open(vp, "wb") as f:
            f.write(content)
        voice_paths.append(vp)

    req = PipelineRequest(
        twin_id=twin_id,
        role=role,
        image_paths=img_paths,
        voice_paths=voice_paths,
        text_input=text,
        enable_3d_face=len(img_paths) > 0,
        enable_voice_clone=len(voice_paths) > 0,
        enable_emotion=True,
        enable_decision=True,
        enable_object_detection=False,
        model_name="rule_based",
    )

    try:
        result = await orchestrator.run_full_pipeline(req)
    except Exception as e:
        logger.error(f"Pipeline run failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

    session_data["pipeline_id"] = result.pipeline_id
    session_data["face_result"] = result.face_result
    session_data["voice_result"] = result.voice_result
    session_data["emotion_result"] = result.emotion_result
    session_data["brain_result"] = result.brain_result
    session_data["last_pipeline_run"] = datetime.utcnow().isoformat()

    if result.face_result and result.face_result.mesh_3d_path:
        session_data["mesh_path"] = result.face_result.mesh_3d_path
    if result.face_result and result.face_result.texture_path:
        session_data["texture_path"] = result.face_result.texture_path
    if result.voice_result and result.voice_result.cloned_voice_path:
        session_data["cloned_voice_path"] = result.voice_result.cloned_voice_path
    if result.voice_result and result.voice_result.tts_sample_path:
        session_data["tts_path"] = result.voice_result.tts_sample_path

    # Copy to static
    if session_data["mesh_path"] and os.path.exists(session_data["mesh_path"]):
        static_mesh = STATIC_DIR / "current_mesh.obj"
        with open(session_data["mesh_path"], "rb") as src, open(static_mesh, "wb") as dst:
            dst.write(src.read())
    if session_data["texture_path"] and os.path.exists(session_data["texture_path"]):
        static_tex = STATIC_DIR / "current_texture.jpg"
        with open(session_data["texture_path"], "rb") as src, open(static_tex, "wb") as dst:
            dst.write(src.read())
        mtl = STATIC_DIR / "face_texture.mtl"
        mtl.write_text(
            "newmtl face_texture\nKa 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\n"
            "map_Kd current_texture.jpg\n"
        )

    return {
        "status": result.status.value,
        "pipeline_id": result.pipeline_id,
        "face_detected": result.face_result.face_detected if result.face_result else False,
        "voice_detected": result.voice_result.voice_detected if result.voice_result else False,
        "mesh_path": str(session_data["mesh_path"]) if session_data["mesh_path"] else None,
        "texture_path": str(session_data["texture_path"]) if session_data["texture_path"] else None,
        "cloned_voice": str(session_data["cloned_voice_path"]) if session_data["cloned_voice_path"] else None,
        "brain_response": result.brain_result.response_text if result.brain_result else "",
        "emotion": result.emotion_result.primary_mood.value if result.emotion_result else "neutral",
    }


# ── Chat ──────────────────────────────────────────────────────────────

async def _process_chat(text: str) -> dict:
    """Process a chat message through brain pipeline with knowledge base."""
    if not PIPELINE_AVAILABLE or orchestrator is None:
        return {"response": "Chat is not available right now.", "emotion": "neutral"}

    try:
        from dreamtalk.pipeline.models import EmotionResult, BrainDecisionResult
    except Exception:
        return {"response": f"You said: {text}", "emotion": "neutral"}

    # First check knowledge base
    kb_response = None
    if knowledge_base is not None:
        kb_response = knowledge_base.get_response(text)

    try:
        emotion = await orchestrator.brain_pipeline.detect_emotion(text)
        brain = await orchestrator.brain_pipeline.make_decision(
            text=text,
            role="normal_user",
            emotion=emotion,
            model_name="llm",
        )
        session_data["emotion_result"] = emotion
        session_data["brain_result"] = brain

        # If knowledge base has a relevant response, inject it
        final_response = brain.response_text
        if kb_response:
            final_response = kb_response + "\n\n" + brain.response_text[-200:]
        else:
            # If no KB match, still add general KB intro context once
            pass

        # Use session language for TTS (set via /language endpoint or WebSocket)
        tts_lang = session_data.get("current_language", "en")
        try:
            from dreamtalk.voice.core.translation import get_language_router
            detected = get_language_router().detect_language(text)
            if detected and detected not in ("en", "unknown"):
                tts_lang = detected
                session_data["current_language"] = detected
        except Exception:
            pass
        logger.info(f"TTS language for chat: {tts_lang} (session={session_data.get('current_language')})")

        # Generate TTS in detected language
        tts_path = None
        try:
            tts_path = await _generate_tts(final_response, tts_lang)
        except Exception:
            pass

        return {
            "response": final_response,
            "emotion": emotion.primary_mood.value,
            "valence": emotion.valence,
            "arousal": emotion.arousal,
            "hostile": emotion.is_hostile,
            "tts_path": tts_path,
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"response": str(e), "emotion": "neutral"}


@router.post("/chat")
async def avatar_chat(text: str = Form(...)):
    """Chat with the avatar via REST."""
    result = await _process_chat(text)
    return result


# ── TTS ───────────────────────────────────────────────────────────────

@router.post("/tts/generate")
async def generate_tts(
    text: str = Form(...),
    language: str = Form("en"),
):
    """Generate TTS audio in the specified language."""
    tts_path = await _generate_tts(text, language)
    return {
        "tts_path": tts_path,
        "length_chars": len(text),
        "language": language,
    }


@router.get("/tts/audio")
async def tts_audio(path: str = Query(""), language: str = Query("en")):
    """Serve TTS audio as base64."""
    if not path or not os.path.exists(path):
        return {"base64": None, "error": "File not found"}
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {"base64": b64, "filename": os.path.basename(path), "language": language}


# ── Script ────────────────────────────────────────────────────────────

@router.post("/script/generate")
async def generate_script(
    language: str = Form("en"),
):
    """Generate a 3-minute avatar script in the specified language."""
    from dreamtalk.backend.services.knowledge_base import StudentKnowledgeBase
    kb = knowledge_base or StudentKnowledgeBase()

    script = kb.get_script(language)

    tts_path = await _generate_tts(script, language)
    if not tts_path:
        return {"error": "TTS generation failed"}

    # Also generate parts
    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    parts_dir = STATIC_DIR / f"script_parts_{language}"
    os.makedirs(parts_dir, exist_ok=True)

    parts = []
    for i, para in enumerate(paragraphs):
        part_path = parts_dir / f"part_{i:02d}.wav"
        try:
            await _generate_tts(para, language, str(part_path))
            parts.append({
                "index": i,
                "path": str(part_path),
                "size": os.path.getsize(part_path) if part_path.exists() else 0,
            })
        except Exception:
            pass

    meta = {
        "total_parts": len(paragraphs),
        "script_path": tts_path,
        "language": language,
        "total_chars": len(script),
        "parts": parts,
    }

    meta_path = STATIC_DIR / f"script_meta_{language}.json"
    import json as _json
    _json.dump(meta, open(meta_path, "w"), indent=2)

    return meta


@router.get("/script/info")
async def script_info(language: str = Query("en")):
    """Get script metadata for a language."""
    meta_path = STATIC_DIR / f"script_meta_{language}.json"
    script_path = STATIC_DIR / f"script_3min_{language}.wav"

    if not meta_path.exists():
        return {"available": False, "error": f"No script for '{language}'"}

    import json as _json
    meta = _json.loads(meta_path.read_text())
    meta["available"] = True
    if script_path.exists():
        meta["duration_seconds"] = os.path.getsize(script_path) / 32000

    return meta


@router.get("/script/play/{language}/{part_index}")
async def play_script_part(language: str, part_index: int):
    """Get a specific script part as base64 audio."""
    parts_dir = STATIC_DIR / f"script_parts_{language}"
    part_file = parts_dir / f"part_{part_index:02d}.wav"
    if not part_file.exists():
        return {"base64": None, "error": "Not found"}
    with open(part_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {"base64": b64, "index": part_index, "language": language, "filename": part_file.name}


# ── IndicF5 Voice Cloning (Multi-language Indian TTS) ──────────────────

@router.post("/tts/indicf5")
async def generate_indicf5_tts(
    ref_audio: UploadFile = File(None),
    text: str = Form(...),
    language: str = Form("hi"),
    ref_text: str = Form(""),
):
    """Generate TTS using IndicF5 microservice (12 Indian languages + English).

    If ref_audio is provided, the output will be in that speaker's voice.
    If no ref_audio is provided, uses a default style.

    Supported languages: as, bn, gu, hi, kn, ml, mr, or, pa, ta, te, en
    """
    import httpx

    # Validate text
    if not text.strip():
        return JSONResponse({"error": "Text cannot be empty"}, status_code=400)

    # Default reference audio path
    ref_path = None
    if ref_audio:
        # Save uploaded ref audio to temp
        ext = os.path.splitext(ref_audio.filename or "ref.wav")[1] or ".wav"
        ref_path = os.path.join(UPLOAD_DIR, f"indicf5_ref_{uuid.uuid4().hex}{ext}")
        content = await ref_audio.read()
        with open(ref_path, "wb") as f:
            f.write(content)
    else:
        # Use a default reference audio from results
        default_ref = PROJECT_ROOT / "results" / "cloned_voice_tamil.wav"
        if default_ref.exists():
            ref_path = str(default_ref)

    output_dir = OUTPUT_DIR / "indicf5"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"indicf5_{uuid.uuid4().hex[:8]}.wav")

    try:
        # Call the IndicF5 microservice
        if not ref_path or not os.path.exists(str(ref_path)):
            return JSONResponse({"error": "No reference audio available. Please upload one."}, status_code=400)

        with open(str(ref_path), "rb") as ref_f:
            ref_bytes = ref_f.read()
        files = {"ref_audio": (os.path.basename(str(ref_path)), ref_bytes, "audio/wav")}
        data = {"gen_text": text, "ref_text": ref_text, "lang": language}

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{INDICF5_BASE_URL}/synthesize",
                files=files,
                data=data,
            )

        if resp.status_code != 200:
            return JSONResponse({"error": f"IndicF5 synthesis failed: {resp.text}"}, status_code=502)

        # Save the returned WAV
        with open(output_path, "wb") as f:
            f.write(resp.content)

        file_size = os.path.getsize(output_path)
        logger.info(f"IndicF5 TTS [{language}]: {output_path} ({file_size} bytes)")

        return {
            "status": "completed",
            "tts_path": output_path,
            "length_chars": len(text),
            "language": language,
            "file_size": file_size,
            "indicf5_available": True,
        }

    except ImportError:
        return JSONResponse({"error": "httpx not installed. Run: pip install httpx"}, status_code=500)
    except Exception as e:
        logger.error(f"IndicF5 synthesis failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        # Cleanup temp ref file
        if ref_audio and ref_path and os.path.exists(ref_path):
            try:
                os.remove(ref_path)
            except Exception:
                pass


@router.get("/tts/indicf5/languages")
async def list_indicf5_languages():
    """List languages supported by the IndicF5 microservice."""
    try:
        import httpx
        resp = httpx.get(f"{INDICF5_BASE_URL}/models", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"IndicF5 languages check failed: {e}")

    # Fallback: return known supported languages
    return {
        "type": "F5-TTS (CFM-based)",
        "supported_languages": {
            "as": "Assamese", "bn": "Bengali", "gu": "Gujarati",
            "hi": "Hindi", "kn": "Kannada", "ml": "Malayalam",
            "mr": "Marathi", "or": "Odia", "pa": "Punjabi",
            "ta": "Tamil", "te": "Telugu", "en": "English",
        },
        "model_loaded": None,
        "device": None,
    }


@router.get("/tts/indicf5/status")
async def check_indicf5_status():
    """Check if the IndicF5 microservice is running."""
    try:
        import httpx
        resp = httpx.get(f"{INDICF5_BASE_URL}/health", timeout=3)
        if resp.status_code == 200:
            return {"status": "available", "details": resp.json()}
    except Exception as e:
        pass
    return {"status": "unavailable", "details": None}


# ── Lip Sync ──────────────────────────────────────────────────────────

@router.post("/lipsync/analyze")
async def analyze_lipsync(
    audio_path: str = Form(...),
    text: str = Form(""),
    emotion: str = Form("neutral"),
):
    """Analyze audio and return viseme keyframes for lip sync animation."""
    try:
        from dreamtalk.pipeline.lipsync_pipeline import get_lipsync_pipeline
        import os

        # Resolve the audio path (could be relative like /outputs/tts_xxx.wav)
        basename = os.path.basename(audio_path)
        # Try multiple possible locations
        candidates = [
            os.path.join("/app/dreamtalk/pipeline_outputs/tts", basename),
            os.path.join("/app/dreamtalk/voice_module/assets/outputs", basename),
            os.path.join("pipeline_outputs/tts", basename),
            audio_path,
        ]
        full_path = audio_path  # default
        for c in candidates:
            if os.path.exists(c):
                full_path = c
                break

        if not os.path.exists(full_path):
            return {"error": f"Audio file not found: {full_path}", "keyframes": []}

        pipeline = get_lipsync_pipeline(fps=30.0)
        emotion_dict = {"primary_mood": emotion, "arousal": 0.5, "valence": 0.0}
        result = pipeline.extract_from_audio(full_path, emotion=emotion_dict, text=text)

        return {
            "keyframes": [kf.to_dict() for kf in result.keyframes],
            "duration": result.duration,
            "fps": result.fps,
            "total_frames": result.total_frames,
            "method": result.method,
            "processing_time_ms": result.processing_time_ms,
        }
    except Exception as e:
        logger.warning(f"Lip sync analysis failed: {e}")
        return {"error": str(e), "keyframes": []}


# ── Session ───────────────────────────────────────────────────────────

@router.get("/session")
async def get_avatar_session():
    """Get current avatar session state."""
    mesh_url = None
    tex_url = None

    static_mesh = STATIC_DIR / "current_mesh.obj"
    static_tex = STATIC_DIR / "current_texture.jpg"
    static_voice = STATIC_DIR / "cloned_voice.wav"

    if session_data["mesh_path"] and os.path.exists(session_data["mesh_path"]):
        mesh_url = "/api/static/current_mesh.obj"
    elif static_mesh.exists():
        mesh_url = "/api/static/current_mesh.obj"
        session_data["mesh_path"] = str(static_mesh)

    if session_data["texture_path"] and os.path.exists(session_data["texture_path"]):
        tex_url = "/api/static/current_texture.jpg"
    elif static_tex.exists():
        tex_url = "/api/static/current_texture.jpg"
        session_data["texture_path"] = str(static_tex)

    if static_voice.exists() and not session_data["cloned_voice_path"]:
        session_data["cloned_voice_path"] = str(static_voice)

    voice_url = "/api/static/cloned_voice.wav" if static_voice.exists() else None

    if session_data["pipeline_id"] is None and static_mesh.exists():
        session_data["last_pipeline_run"] = "preloaded"

    return {
        "pipeline_id": session_data["pipeline_id"],
        "has_face": session_data["face_result"] is not None or session_data["mesh_path"] is not None,
        "has_voice": session_data["voice_result"] is not None or session_data["cloned_voice_path"] is not None,
        "mesh_url": mesh_url,
        "texture_url": tex_url,
        "cloned_voice_url": voice_url,
        "current_language": session_data["current_language"],
        "languages": {k: v["name"] for k, v in LANGUAGES.items()},
        "knowledge_base_ready": knowledge_base is not None,
        "face_result": _safe_serialize(session_data["face_result"]),
        "voice_result": _safe_serialize(session_data["voice_result"]),
        "emotion_result": _safe_serialize(session_data["emotion_result"]),
        "brain_result": _safe_serialize(session_data["brain_result"]),
    }


# ── WebSocket Chat ────────────────────────────────────────────────────

@router.websocket("/ws/chat")
async def websocket_avatar_chat(websocket: WebSocket):
    """Real-time chat via WebSocket with multi-language TTS."""
    await websocket.accept()
    logger.info("WebSocket connected to avatar chat")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            text = msg.get("text", "")
            lang = msg.get("language", session_data["current_language"])

            if not text.strip():
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            result = await _process_chat(text)

            # Generate TTS in requested language
            tts_data = None
            try:
                tts_path = await _generate_tts(result.get("response", text), lang)
                if tts_path and os.path.exists(tts_path):
                    with open(tts_path, "rb") as f:
                        tts_data = base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass

            await websocket.send_json({
                "type": "response",
                "text": result.get("response", text),
                "emotion": result.get("emotion", "neutral"),
                "valence": result.get("valence", 0),
                "arousal": result.get("arousal", 0),
                "hostile": result.get("hostile", False),
                "tts_data": tts_data,
                "language": lang,
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ── Video Generation ──────────────────────────────────────────────────

_musetalk_api = None
_ditto_api = None
_liveportrait_api = None
_flame_fitter = None
_flame_fitter_lock = None


def _get_musetalk():
    global _musetalk_api
    if _musetalk_api is None:
        try:
            from dreamtalk.face.core.lipsync.musetalk.musetalk_api import MuseTalkAPI
            _musetalk_api = MuseTalkAPI()
            _musetalk_api.load_models()
            logger.info("MuseTalk loaded for video generation")
        except Exception as e:
            logger.warning(f"MuseTalk load failed: {e}")
    return _musetalk_api


def _get_flame_fitter():
    """Lazy-load and cache FlameFitter singleton (avoids 1.4GB pickle reload on every request)."""
    global _flame_fitter, _flame_fitter_lock
    if _flame_fitter is None:
        try:
            from dreamtalk.pipeline.flame_fitter import FlameFitter
            _flame_fitter = FlameFitter()
            _flame_fitter_lock = asyncio.Lock()
            logger.info("FlameFitter loaded (cached singleton)")
        except Exception as e:
            logger.warning(f"FlameFitter load failed: {e}")
    return _flame_fitter


def _get_liveportrait_api():
    """Lazy-load the LivePortraitAnimationPipeline."""
    global _liveportrait_api
    if _liveportrait_api is None:
        try:
            from dreamtalk.pipeline.animation_pipeline import LivePortraitAnimationPipeline, check_liveportrait_ready
            status = check_liveportrait_ready()
            if not status["ready"]:
                logger.warning(f"LivePortrait not fully ready: {status}")
            _liveportrait_api = LivePortraitAnimationPipeline()
            logger.info("LivePortraitAnimationPipeline loaded for video generation")
        except Exception as e:
            logger.warning(f"LivePortraitAnimationPipeline load failed: {e}")
    return _liveportrait_api


def _get_ditto():
    global _ditto_api
    if _ditto_api is None:
        try:
            from dreamtalk.face.core.lipsync.ditto.ditto_api import DittoAPI
            _ditto_api = DittoAPI()
            _ditto_api.load_models()
            logger.info("Ditto loaded for video generation")
        except Exception as e:
            logger.warning(f"Ditto load failed: {e}")
    return _ditto_api


@router.post("/video/generate")
async def generate_video(
    appearance: UploadFile = File(...),
    audio: UploadFile = File(...),
    model: str = Form("musetalk"),
    output_filename: str = Form(""),
):
    """Generate a lip-sync video from appearance image + audio using MuseTalk or Ditto."""
    upload_dir = UPLOAD_DIR / "video_gen"
    os.makedirs(upload_dir, exist_ok=True)

    ext_img = os.path.splitext(appearance.filename or "image.png")[1] or ".png"
    img_path = os.path.join(upload_dir, f"src_{uuid.uuid4().hex}{ext_img}")
    with open(img_path, "wb") as f:
        f.write(await appearance.read())

    ext_audio = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    audio_path = os.path.join(upload_dir, f"audio_{uuid.uuid4().hex}{ext_audio}")
    with open(audio_path, "wb") as f:
        f.write(await audio.read())

    out_dir = OUTPUT_DIR / "videos"
    os.makedirs(out_dir, exist_ok=True)
    out_name = output_filename or f"gen_{uuid.uuid4().hex[:8]}.mp4"
    out_path = os.path.join(out_dir, out_name)

    try:
        if model == "ditto":
            api = _get_ditto()
            if api is None:
                return JSONResponse({"error": "Ditto not available"}, status_code=503)
            result = api.generate(audio_path, img_path, str(out_path))
            video_file = result["video_path"]
        else:
            api = _get_musetalk()
            if api is None:
                return JSONResponse({"error": "MuseTalk not available"}, status_code=503)
            result = api.generate(
                video_path=img_path,
                audio_path=audio_path,
                result_dir=str(out_dir),
                output_vid_name=out_name,
                hw_video_encode=True,
            )
            video_file = result["video_path"]

        static_video = STATIC_DIR / "current_video.mp4"
        if os.path.exists(video_file):
            with open(video_file, "rb") as src, open(static_video, "wb") as dst:
                dst.write(src.read())

        return {
            "status": "completed",
            "video_url": f"/api/static/current_video.mp4",
            "video_path": str(video_file),
            "model": model,
        }
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/video/generate-from-text")
async def generate_video_from_text(
    appearance: UploadFile = File(...),
    text: str = Form("Hello, I am your digital twin."),
    language: str = Form("en"),
    model: str = Form("musetalk"),
):
    """Generate TTS audio from text, then create lip-sync video."""
    out_dir = OUTPUT_DIR / "videos"
    os.makedirs(out_dir, exist_ok=True)

    tts_path = await _generate_tts(text, language)
    if not tts_path:
        return JSONResponse({"error": "TTS generation failed"}, status_code=500)

    ext_img = os.path.splitext(appearance.filename or "image.png")[1] or ".png"
    img_path = os.path.join(UPLOAD_DIR, f"src_{uuid.uuid4().hex}{ext_img}")
    with open(img_path, "wb") as f:
        f.write(await appearance.read())

    out_name = f"tts_gen_{uuid.uuid4().hex[:8]}.mp4"
    out_path = os.path.join(out_dir, out_name)

    try:
        if model == "ditto":
            api = _get_ditto()
            if api is None:
                return JSONResponse({"error": "Ditto not available"}, status_code=503)
            result = api.generate(tts_path, img_path, str(out_path))
            video_file = result["video_path"]
        else:
            api = _get_musetalk()
            if api is None:
                return JSONResponse({"error": "MuseTalk not available"}, status_code=503)
            result = api.generate(
                video_path=img_path,
                audio_path=tts_path,
                result_dir=str(out_dir),
                output_vid_name=out_name,
                hw_video_encode=True,
            )
            video_file = result["video_path"]

        static_video = STATIC_DIR / "current_video.mp4"
        if os.path.exists(video_file):
            with open(video_file, "rb") as src, open(static_video, "wb") as dst:
                dst.write(src.read())

        return {
            "status": "completed",
            "video_url": f"/api/static/current_video.mp4",
            "video_path": str(video_file),
            "text": text,
            "language": language,
            "model": model,
            "tts_path": tts_path,
        }
    except Exception as e:
        logger.error(f"Video from text generation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ── LivePortrait (Expression-Driven Facial Animation) ──────────────────

@router.post("/video/liveportrait/generate")
async def generate_liveportrait_video(
    source_image: UploadFile = File(...),
    driving_video: UploadFile = File(...),
    output_filename: str = Form(""),
    animation_region: str = Form("all"),
    do_pasteback: bool = Form(True),
):
    """Generate expression-driven facial animation using LivePortrait.

    Takes a source face image and a driving video (which provides the
    facial expressions), then animates the source face to match the
    driving video's expressions.

    Args:
        source_image: The source face image to animate.
        driving_video: The driving video with target expressions.
        output_filename: Optional output filename.
        animation_region: Region to animate: "all", "exp", "pose", "lip", "eyes".
        do_pasteback: Whether to paste animated face back onto original image.
    """
    # Pre-flight GPU memory check to prevent OOM crash
    try:
        import torch
        if torch.cuda.is_available():
            free_mem, _ = torch.cuda.mem_get_info(0)
            free_gb = free_mem / (1024**3)
            if free_gb < 1.5:
                return JSONResponse({
                    "error": f"Insufficient GPU memory ({free_gb:.1f}GB free). Close other GPU apps or restart backend.",
                    "gpu_free_gb": round(free_gb, 2)
                }, status_code=507)
    except ImportError:
        pass

    api = _get_liveportrait_api()
    if api is None:
        return JSONResponse({"error": "LivePortrait not available"}, status_code=503)

    upload_dir = UPLOAD_DIR / "liveportrait"
    os.makedirs(upload_dir, exist_ok=True)

    # Save source image
    ext_img = os.path.splitext(source_image.filename or "image.png")[1] or ".png"
    img_path = os.path.join(upload_dir, f"src_{uuid.uuid4().hex}{ext_img}")
    with open(img_path, "wb") as f:
        f.write(await source_image.read())

    # Save driving video
    ext_vid = os.path.splitext(driving_video.filename or "video.mp4")[1] or ".mp4"
    video_path = os.path.join(upload_dir, f"driving_{uuid.uuid4().hex}{ext_vid}")
    with open(video_path, "wb") as f:
        f.write(await driving_video.read())

    out_dir = OUTPUT_DIR / "liveportrait"
    os.makedirs(out_dir, exist_ok=True)

    out_name = output_filename or f"lp_{uuid.uuid4().hex[:8]}"

    try:
        import concurrent.futures
        logger.info(f"LivePortrait starting: src={img_path}, drv={video_path}, region={animation_region}")
        # Run in a thread with timeout to prevent worker crashes
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                api.drive_from_video,
                source_image_path=img_path,
                driving_video_path=video_path,
                output_dir=str(out_dir),
                output_name=out_name,
                animation_region=animation_region,
                do_pasteback=do_pasteback,
            )
            try:
                result = future.result(timeout=600)  # 10 min timeout
            except concurrent.futures.TimeoutError:
                logger.error("LivePortrait generation timed out after 5 minutes")
                return JSONResponse({"error": "LivePortrait generation timed out"}, status_code=504)

        logger.info(f"LivePortrait completed: {result.get('video_path', 'N/A')}")

        # Copy to static for serving
        if result.get("video_path") and os.path.exists(result["video_path"]):
            static_video = STATIC_DIR / f"liveportrait_{out_name}.mp4"
            with open(result["video_path"], "rb") as src, open(static_video, "wb") as dst:
                dst.write(src.read())
            result["video_url"] = f"/api/static/{static_video.name}"

        # Free GPU memory after generation
        try:
            import torch, gc
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"LivePortrait generation failed: {type(e).__name__}: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/video/liveportrait/generate-from-image")
async def generate_liveportrait_from_image(
    source_image: UploadFile = File(...),
    driving_image: UploadFile = File(...),
    output_filename: str = Form(""),
    do_pasteback: bool = Form(True),
):
    """Transfer expression from a driving face image to the source face.

    Takes two face images — source and driving — and animates the source
    to match the driving image's expression, producing a short video.
    """
    api = _get_liveportrait_api()
    if api is None:
        return JSONResponse({"error": "LivePortrait not available"}, status_code=503)

    upload_dir = UPLOAD_DIR / "liveportrait"
    os.makedirs(upload_dir, exist_ok=True)

    ext_img = os.path.splitext(source_image.filename or "image.png")[1] or ".png"
    img_path = os.path.join(upload_dir, f"src_{uuid.uuid4().hex}{ext_img}")
    with open(img_path, "wb") as f:
        f.write(await source_image.read())

    ext_drv = os.path.splitext(driving_image.filename or "driving.png")[1] or ".png"
    drv_path = os.path.join(upload_dir, f"drv_{uuid.uuid4().hex}{ext_drv}")
    with open(drv_path, "wb") as f:
        f.write(await driving_image.read())

    out_dir = OUTPUT_DIR / "liveportrait"
    os.makedirs(out_dir, exist_ok=True)

    out_name = output_filename or f"lp_img_{uuid.uuid4().hex[:8]}"

    try:
        result = api.drive_from_image(
            source_image_path=img_path,
            driving_image_path=drv_path,
            output_dir=str(out_dir),
            output_name=out_name,
            do_pasteback=do_pasteback,
        )

        if result["video_path"] and os.path.exists(result["video_path"]):
            static_video = STATIC_DIR / f"liveportrait_{out_name}.mp4"
            with open(result["video_path"], "rb") as src, open(static_video, "wb") as dst:
                dst.write(src.read())
            result["video_url"] = f"/api/static/{static_video.name}"

        return result

    except Exception as e:
        logger.error(f"LivePortrait from-image generation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/video/liveportrait/generate-from-emotion")
async def generate_liveportrait_from_emotion(
    source_image: UploadFile = File(...),
    emotion: str = Form("neutral"),
    output_filename: str = Form(""),
    do_pasteback: bool = Form(True),
):
    """Generate an animated video with the face expressing the given emotion.

    Supported emotions: neutral, happy, sad, angry, surprised, fearful.
    """
    api = _get_liveportrait_api()
    if api is None:
        return JSONResponse({"error": "LivePortrait not available"}, status_code=503)

    upload_dir = UPLOAD_DIR / "liveportrait"
    os.makedirs(upload_dir, exist_ok=True)

    ext_img = os.path.splitext(source_image.filename or "image.png")[1] or ".png"
    img_path = os.path.join(upload_dir, f"src_{uuid.uuid4().hex}{ext_img}")
    with open(img_path, "wb") as f:
        f.write(await source_image.read())

    out_dir = OUTPUT_DIR / "liveportrait"
    os.makedirs(out_dir, exist_ok=True)

    out_name = output_filename or f"lp_emo_{emotion}_{uuid.uuid4().hex[:8]}"

    try:
        result = api.drive_from_emotion(
            source_image_path=img_path,
            output_dir=str(out_dir),
            output_name=out_name,
            emotion_label=emotion,
            do_pasteback=do_pasteback,
        )

        if result["video_path"] and os.path.exists(result["video_path"]):
            static_video = STATIC_DIR / f"liveportrait_{out_name}.mp4"
            with open(result["video_path"], "rb") as src, open(static_video, "wb") as dst:
                dst.write(src.read())
            result["video_url"] = f"/api/static/{static_video.name}"

        return result

    except Exception as e:
        logger.error(f"LivePortrait emotion generation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/video/status")
async def video_generation_status():
    """Check if video generation models are available."""
    musetalk_ok = _musetalk_api is not None
    ditto_ok = _ditto_api is not None
    liveportrait_ok = _liveportrait_api is not None
    has_video = (STATIC_DIR / "current_video.mp4").exists()

    liveportrait_status = {}
    try:
        from dreamtalk.pipeline.animation_pipeline import check_liveportrait_ready
        liveportrait_status = check_liveportrait_ready()
    except Exception:
        pass

    return {
        "musetalk_available": musetalk_ok,
        "ditto_available": ditto_ok,
        "liveportrait_available": liveportrait_ok,
        "liveportrait": liveportrait_status,
        "has_generated_video": has_video,
        "video_url": "/api/static/current_video.mp4" if has_video else None,
    }



# ── 3D Face Mesh Generation (FLAME) ──────────────────────────────────

@router.post("/face/generate-mesh")
async def generate_face_mesh(
    image: UploadFile = File(...),
    fit_identity: bool = Form(True),
    generate_texture: bool = Form(True),
):
    """Generate a 3D FLAME face mesh from a photo.

    Uses the FlameFitter to:
      1. Detect face landmarks (MediaPipe 478)
      2. Fit identity parameters (PCA-based optimization)
      3. Generate FLAME 3D mesh (5023 vertices)
      4. Compute normals and export OBJ+MTL
      5. Optionally project photo texture onto UV atlas

    Args:
        image: Photo of the person (front-facing, well-lit)
        fit_identity: Optimize identity shape parameters
        generate_texture: Project photo onto UV texture atlas

    Returns:
        OBJ/MTL file paths, vertex/face count, and mesh info
    """
    if not models_loaded:
        return JSONResponse({"error": "Models not loaded yet"}, status_code=503)

    # Save uploaded image
    ext = os.path.splitext(image.filename or "photo.jpg")[1] or ".jpg"
    img_path = os.path.join(UPLOAD_DIR, f"flame_photo_{uuid.uuid4().hex}{ext}")
    content = await image.read()
    with open(img_path, "wb") as f:
        f.write(content)

    out_dir = STATIC_DIR / "flame_meshes"
    os.makedirs(out_dir, exist_ok=True)

    try:
        fitter = _get_flame_fitter()
        result = fitter.fit_from_photo(
            photo_path=img_path,
            output_dir=str(out_dir),
            fit_identity=fit_identity,
            generate_texture=generate_texture,
            n_components=30,
            reg_strength=5.0,
        )

        if result is None:
            return JSONResponse({"error": "FLAME fitting failed"}, status_code=500)

        # Copy to standard static locations for the viewer
        if result["obj_path"] and os.path.exists(result["obj_path"]):
            static_mesh = STATIC_DIR / "current_mesh.obj"
            with open(result["obj_path"], "rb") as src, open(static_mesh, "wb") as dst:
                dst.write(src.read())
            session_data["mesh_path"] = result["obj_path"]

        if result["mtl_path"] and os.path.exists(result["mtl_path"]):
            static_mtl = STATIC_DIR / "generated_head.mtl"
            with open(result["mtl_path"], "rb") as src, open(static_mtl, "wb") as dst:
                dst.write(src.read())

        if result.get("texture_path") and os.path.exists(result["texture_path"]):
            static_tex = STATIC_DIR / "current_texture.png"
            with open(result["texture_path"], "rb") as src, open(static_tex, "wb") as dst:
                dst.write(src.read())
            session_data["texture_path"] = result["texture_path"]

        # Cleanup uploaded photo
        try:
            os.remove(img_path)
        except Exception:
            pass

        return {
            "status": "completed",
            "vertex_count": result["vertex_count"],
            "face_count": result["face_count"],
            "landmarks_detected": result["landmarks_detected"],
            "identity_fitted": result["identity_fitted"],
            "texture_generated": result.get("texture_generated", False),
            "mesh_url": "/api/static/current_mesh.obj",
            "texture_url": "/api/static/current_texture.png" if result.get("texture_generated") else None,
            "message": "3D face mesh generated successfully. View at /api/avatar/viewer",
        }

    except ImportError as e:
        logger.error(f"FLAME dependencies missing: {e}")
        return JSONResponse({"error": f"FLAME dependencies missing: {e}"}, status_code=500)
    except Exception as e:
        logger.error(f"FLAME mesh generation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        # Cleanup
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except Exception:
            pass


@router.get("/face/mesh/current")
async def get_current_mesh():
    """Get the current 3D mesh file paths."""
    mesh_path = STATIC_DIR / "current_mesh.obj"
    mtl_path = STATIC_DIR / "generated_head.mtl"
    tex_path = STATIC_DIR / "current_texture.png"

    return {
        "has_mesh": mesh_path.exists(),
        "mesh_url": "/api/static/current_mesh.obj" if mesh_path.exists() else None,
        "mtl_url": "/api/static/generated_head.mtl" if mtl_path.exists() else None,
        "texture_url": "/api/static/current_texture.png" if tex_path.exists() else None,
        "vertex_count": session_data.get("face_result", {}).get("vertex_count", 0) if session_data.get("face_result") else None,
        "last_pipeline_run": session_data.get("last_pipeline_run"),
    }


# ── Static Files ──────────────────────────────────────────────────────

@router.get("/static/{filename}")
async def serve_avatar_static(filename: str):
    """Serve avatar static files (mesh, texture, audio)."""
    file_path = STATIC_DIR / filename
    nested = STATIC_DIR / filename.replace("/", os.sep)
    if nested.exists():
        return FileResponse(str(nested), media_type="application/octet-stream")
    if file_path.exists():
        return FileResponse(str(file_path), media_type="application/octet-stream")
    return JSONResponse({"error": "Not found"}, status_code=404)


# ── Helpers ───────────────────────────────────────────────────────────

def _safe_serialize(obj):
    if obj is None:
        return None
    try:
        if hasattr(obj, "model_dump"):
            return json.loads(json.dumps(obj.model_dump(), default=str))
        if hasattr(obj, "dict"):
            return json.loads(json.dumps(obj.dict(), default=str))
        return str(obj)
    except Exception:
        return str(obj)[:200]


async def _stream_tts_chunks(text: str, language: str = "en", emotion: str = None):
    """Stream TTS audio chunks via Edge-TTS. Yields (chunk_bytes, content_type) tuples.
    
    Uses edge_tts.Communicate.stream() for real-time MP3 chunk streaming.
    Falls back to _generate_tts if streaming fails.
    """
    INDIC_EDGE_VOICES = {
        "ta": "ta-IN-PallaviNeural", "hi": "hi-IN-SwaraNeural",
        "kn": "kn-IN-SapnaNeural", "te": "te-IN-ShrutiNeural",
        "bn": "bn-IN-TanishaaNeural", "mr": "mr-IN-AarohiNeural",
        "gu": "gu-IN-DhwaniNeural", "ml": "ml-IN-SobhanaNeural",
        "pa": "pa-IN-GurpreetNeural", "or": "or-IN-SubhasreeNeural",
        "as": "as-IN-HemantiNeural",
    }

    # Emotion → prosody mapping
    PROSODY = {
        "happy":      {"rate": "+8%",  "pitch": "+3Hz",  "volume": "+2dB"},
        "sad":        {"rate": "-10%", "pitch": "-2Hz",  "volume": "-3dB"},
        "concerned":  {"rate": "-5%",  "pitch": "+1Hz",  "volume": "+0dB"},
        "serious":    {"rate": "-3%",  "pitch": "-1Hz",  "volume": "+1dB"},
        "thinking":   {"rate": "-8%",  "pitch": "+0Hz",  "volume": "-1dB"},
        "surprised":  {"rate": "+5%",  "pitch": "+5Hz",  "volume": "+3dB"},
        "empathetic": {"rate": "-6%",  "pitch": "+1Hz",  "volume": "-1dB"},
        "neutral":    {"rate": "+0%",  "pitch": "+0Hz",  "volume": "+0dB"},
    }
    prosody = PROSODY.get(emotion or "neutral", PROSODY["neutral"])

    # Build SSML with natural prosody
    def _text_to_ssml(t: str) -> str:
        import re as _re
        t = _re.sub(r'([.!?])\s+', r'\1 <break time="400ms"/> ', t)
        t = _re.sub(r',\s*', ', <break time="200ms"/> ', t)
        rate = prosody["rate"]
        pitch = prosody["pitch"]
        vol = prosody["volume"]
        return f'<speak><prosody rate="{rate}" pitch="{pitch}" volume="{vol}">{t}</prosody></speak>'

    if not EDGETTS_AVAILABLE:
        logger.warning("Edge-TTS not available for streaming")
        return

    voice = INDIC_EDGE_VOICES.get(language)
    if not voice:
        # Fallback to English voice
        lang_config = LANGUAGES.get(language, LANGUAGES["en"])
        voice = lang_config.get("voice_female", "en-US-JennyNeural")

    try:
        import edge_tts
        # Try SSML first, fall back to plain text
        try:
            ssml_text = _text_to_ssml(text)
            communicate = edge_tts.Communicate(ssml_text, voice)
        except Exception:
            communicate = edge_tts.Communicate(text, voice)

        logger.info(f"Edge-TTS stream [{language}/{voice}] for {len(text)} chars")
        chunk_count = 0
        total_bytes = 0

        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                chunk_count += 1
                total_bytes += len(chunk["data"])
                yield chunk["data"], "audio/mpeg"

        logger.info(f"Edge-TTS stream complete: {chunk_count} chunks, {total_bytes} bytes")

    except Exception as e:
        logger.warning(f"Edge-TTS stream failed: {type(e).__name__}: {e}")
        return


async def _generate_tts(text: str, language: str = "en", output_path: str = None, emotion: str = None) -> Optional[str]:
    """Generate TTS with emotion-aware prosody."""

    if output_path is None:
        out_dir = OUTPUT_DIR / "tts"
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"tts_{uuid.uuid4().hex[:8]}.wav")

    lang_config = LANGUAGES.get(language, LANGUAGES["en"])
    voice = lang_config["voice_female"]
    if not emotion:
        emotion = "neutral"
    gender = "female"
    tts_speed = 1.0

    # Use passed emotion, or fall back to session state
    if emotion == "neutral" and session_data.get("emotion_result"):
        try:
            er = session_data["emotion_result"]
            emotion = er.primary_mood.value
        except Exception:
            pass
    if session_data.get("voice_result"):
        try:
            gender = session_data["voice_result"].gender_prediction or "female"
        except Exception:
            pass

    # Emotion → prosody mapping for natural speech
    PROSODY = {
        "happy":      {"rate": "+8%",  "pitch": "+3Hz",  "volume": "+2dB"},
        "sad":        {"rate": "-10%", "pitch": "-2Hz",  "volume": "-3dB"},
        "concerned":  {"rate": "-5%",  "pitch": "+1Hz",  "volume": "+0dB"},
        "serious":    {"rate": "-3%",  "pitch": "-1Hz",  "volume": "+1dB"},
        "thinking":   {"rate": "-8%",  "pitch": "+0Hz",  "volume": "-1dB"},
        "surprised":  {"rate": "+5%",  "pitch": "+5Hz",  "volume": "+3dB"},
        "empathetic": {"rate": "-6%",  "pitch": "+1Hz",  "volume": "-1dB"},
        "neutral":    {"rate": "+0%",  "pitch": "+0Hz",  "volume": "+0dB"},
    }
    prosody = PROSODY.get(emotion, PROSODY["neutral"])

    # Build SSML with natural prosody — pauses between sentences for breathing
    def _text_to_ssml(t: str) -> str:
        import re as _re
        # Add sentence-ending pauses (. ! ?)
        t = _re.sub(r'([.!?])\s+', r'\1 <break time="400ms"/> ', t)
        # Add comma pauses
        t = _re.sub(r',\s*', ', <break time="200ms"/> ', t)
        # Wrap in SSML with prosody
        rate = prosody["rate"]
        pitch = prosody["pitch"]
        vol = prosody["volume"]
        return f'<speak><prosody rate="{rate}" pitch="{pitch}" volume="{vol}">{t}</prosody></speak>'

    # 1. Edge-TTS FIRST for Indian languages (highest quality neural voices)
    #    Edge-TTS has native Tamil/Hindi/Kannada/Telugu neural voices with Indian accent.
    #    We pass SSML for natural prosody: pauses, emphasis, rate control.
    INDIC_EDGE_VOICES = {
        "ta": "ta-IN-PallaviNeural", "hi": "hi-IN-SwaraNeural",
        "kn": "kn-IN-SapnaNeural", "te": "te-IN-ShrutiNeural",
        "bn": "bn-IN-TanishaaNeural", "mr": "mr-IN-AarohiNeural",
        "gu": "gu-IN-DhwaniNeural", "ml": "ml-IN-SobhanaNeural",
        "pa": "pa-IN-GurpreetNeural", "or": "or-IN-SubhasreeNeural",
        "as": "as-IN-HemantiNeural",
    }
    if language in INDIC_EDGE_VOICES and EDGETTS_AVAILABLE:
        try:
            import edge_tts, shutil, subprocess
            edge_voice = INDIC_EDGE_VOICES[language]
            logger.info(f"Edge-TTS attempting [{language}/{edge_voice}] prosody={prosody} for {len(text)} chars")
            # Use SSML for natural prosody when available
            ssml_text = _text_to_ssml(text)
            temp_mp3 = output_path.replace(".wav", "_edge.mp3")
            # Try SSML first, fall back to plain text
            try:
                communicate = edge_tts.Communicate(ssml_text, edge_voice)
                await communicate.save(temp_mp3)
            except Exception:
                communicate = edge_tts.Communicate(text, edge_voice)
                await communicate.save(temp_mp3)
            fsize = os.path.getsize(temp_mp3) if os.path.exists(temp_mp3) else 0
            if fsize > 1000:
                ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
                # 44100Hz stereo for high-quality playback in browser
                subprocess.run([ffmpeg, "-y", "-i", temp_mp3, "-ar", "44100", "-ac", "1", "-sample_fmt", "s16", output_path],
                               capture_output=True, timeout=30)
                try: os.remove(temp_mp3)
                except: pass
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    logger.info(f"Edge-TTS [{language}/{edge_voice}] WAV 44.1kHz: {os.path.getsize(output_path)} bytes")
                    return str(output_path)
        except Exception as e:
            logger.warning(f"Edge-TTS [{language}] failed: {type(e).__name__}: {e}")

    # 2. Edge-TTS fallback for other languages (English, etc.)
    if EDGETTS_AVAILABLE and language not in INDIC_EDGE_VOICES:
        try:
            import edge_tts, shutil, subprocess
            edge_voice = lang_config["voice_female"]
            temp_mp3 = output_path.replace(".wav", "_edge.mp3")
            communicate = edge_tts.Communicate(text, edge_voice)
            await communicate.save(temp_mp3)
            if os.path.exists(temp_mp3) and os.path.getsize(temp_mp3) > 1000:
                ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
                subprocess.run([ffmpeg, "-y", "-i", temp_mp3, "-ar", "44100", "-ac", "1", "-sample_fmt", "s16", output_path],
                               capture_output=True, timeout=30)
                try: os.remove(temp_mp3)
                except: pass
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    logger.info(f"Edge-TTS [{language}/{edge_voice}] WAV 44.1kHz: {os.path.getsize(output_path)} bytes")
                    return str(output_path)
        except Exception as e:
            logger.warning(f"Edge-TTS [{language}] failed: {e}")

    # 3. Kokoro TTS (offline — Hindi + English only)
    if KOKORO_AVAILABLE:
        try:
            import soundfile as sf
            KOKORO_LANG_MAP = {"en": "a", "hi": "h"}
            kokoro_lang = KOKORO_LANG_MAP.get(language)
            if kokoro_lang:
                voice_name = "hf_alpha" if (language == "hi" or gender == "female") else "hm_omega"
                audio = kokoro_engine.synthesize_full(text, voice=voice_name, lang_code=kokoro_lang, speed=tts_speed)
                if audio is not None:
                    sf.write(output_path, audio, 24000)
                    logger.info(f"Kokoro TTS [{voice_name}/{kokoro_lang} speed={tts_speed:.1f}]: {output_path}")
                    return str(output_path)
        except Exception as e:
            logger.warning(f"Kokoro TTS failed: {e}")

    # 4. IndicF5 TTS (microservice at localhost:8003 — 12 Indian languages)
    INDICF5_LANGS = {"as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te", "en"}
    if language in INDICF5_LANGS:
        try:
            import httpx
            default_ref = PROJECT_ROOT / "results" / "cloned_voice_tamil.wav"
            if default_ref.exists():
                with open(str(default_ref), "rb") as ref_f:
                    ref_bytes = ref_f.read()
                files = {"ref_audio": ("ref.wav", ref_bytes, "audio/wav")}
                data = {"gen_text": text, "ref_text": "", "lang": language}
                async with httpx.AsyncClient(timeout=180) as client:
                    resp = await client.post(f"{INDICF5_BASE_URL}/synthesize", files=files, data=data)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"IndicF5 TTS [{language}]: {output_path} ({len(resp.content)} bytes)")
                    return str(output_path)
        except Exception as e:
            logger.warning(f"IndicF5 TTS [{language}] failed: {e}")

    # 3. gTTS (Google TTS — free, 100+ languages, supports ta/kn/hi)
    #    Note: gTTS outputs MP3; we convert to WAV using pydub
    if GTTS_AVAILABLE:
        try:
            # gTTS language codes: ta (Tamil), kn (Kannada), hi (Hindi), en (English)
            gtts_lang_map = {"en": "en", "kn": "kn", "ta": "ta", "hi": "hi"}
            gtts_lang = gtts_lang_map.get(language, "en")
            from gtts import gTTS
            tts = gTTS(text, lang=gtts_lang, slow=False)
            # gTTS produces MP3 — convert to WAV using librosa + soundfile
            temp_mp3 = os.path.join(tempfile.gettempdir(), f"gtts_{uuid.uuid4().hex}.mp3")
            tts.save(temp_mp3)
            if os.path.exists(temp_mp3) and os.path.getsize(temp_mp3) > 1000:
                import librosa
                import soundfile as sf
                y, _ = librosa.load(temp_mp3, sr=44100)
                sf.write(output_path, y, 44100)
                os.remove(temp_mp3)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    logger.info(f"gTTS [{language}/{gtts_lang}] -> WAV: {output_path}")
                    return str(output_path)
        except Exception as e:
            logger.warning(f"gTTS [{language}] failed: {e}")

    # 4. IndicTTS (AI4Bharat FastPitch+HiFi-GAN — 14 Indian languages, needs model_dir)
    if INDICTTS_AVAILABLE:
        try:
            import soundfile as sf
            from dreamtalk.voice.core.tts.indic_tts_engine import IndicTTSEngine
            # Lazy init with default model_dir from weights if available
            model_dir = PROJECT_ROOT / "weights" / "voice" / "indic_tts"
            if model_dir.exists():
                tts_engine = IndicTTSEngine(model_dir=str(model_dir))
                if tts_engine.is_ready() and hasattr(tts_engine, 'SUPPORTED_LANGUAGES') and language in tts_engine.SUPPORTED_LANGUAGES:
                    wav, sr = tts_engine.synthesize(text, lang=language)
                    if wav is not None and len(wav) > 1000:
                        sf.write(output_path, wav, sr)
                        logger.info(f"IndicTTS [{language}]: {output_path}")
                        return str(output_path)
            else:
                logger.debug(f"IndicTTS model_dir not found at {model_dir}")
        except Exception as e:
            logger.warning(f"IndicTTS [{language}] failed: {e}")

    # 5. pyttsx3 (offline Windows SAPI5 — last resort)
    #    Uses pre-initialized engine with per-call locking for thread safety
    if PYTTSX3_AVAILABLE and _pyttsx3_engine is not None:
        try:
            async with _pyttsx3_lock:
                temp_wav = os.path.join(tempfile.gettempdir(), f"tts_pyttsx3_{uuid.uuid4().hex}.wav")
                _pyttsx3_engine.save_to_file(text, temp_wav)
                _pyttsx3_engine.runAndWait()
            if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 1000:
                shutil.copy2(temp_wav, output_path)
                os.remove(temp_wav)
                logger.info(f"pyttsx3 offline TTS: {output_path}")
                return str(output_path)
        except Exception as e:
            logger.warning(f"pyttsx3 failed: {e}")

    # 6. Final fallback: all engines exhausted
    logger.error(f"All TTS engines failed for language={language}, text='{text[:50]}...'")
    return None


# ── Voice Profiles ───────────────────────────────────────────────────

@router.post("/voice-profiles")
async def create_voice_profile(
    name: str = Form(...),
    audio: UploadFile = File(...),
    language: str = Form("hi"),
    ref_text: str = Form(""),
    user_id: str = Form("default"),
):
    """Create a voice cloning profile from reference audio (30-60s)."""
    try:
        # Save uploaded audio
        ext = os.path.splitext(audio.filename or "ref.wav")[1] or ".wav"
        temp_dir = os.path.join(UPLOAD_DIR, "voice_profiles")
        os.makedirs(temp_dir, exist_ok=True)
        audio_path = os.path.join(temp_dir, f"ref_{uuid.uuid4().hex}{ext}")
        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        from dreamtalk.backend.services.voice_profile_manager import VoiceProfileManager
        manager = VoiceProfileManager()
        profile = await manager.create_profile(user_id, name, audio_path, language, ref_text)
        return {"status": "created", "profile": profile}
    except Exception as e:
        logger.error(f"Voice profile creation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/voice-profiles")
async def list_voice_profiles(user_id: str = Query("default")):
    """List all voice profiles for a user."""
    try:
        from dreamtalk.backend.services.voice_profile_manager import VoiceProfileManager
        manager = VoiceProfileManager()
        profiles = await manager.list_profiles(user_id)
        return {"profiles": profiles, "count": len(profiles)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/voice-profiles/{profile_id}")
async def delete_voice_profile(profile_id: str):
    """Delete a voice profile."""
    try:
        from dreamtalk.backend.services.voice_profile_manager import VoiceProfileManager
        manager = VoiceProfileManager()
        deleted = await manager.delete_profile(profile_id)
        return {"deleted": deleted}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Avatar Export (GLB) ──────────────────────────────────────────────

@router.get("/avatar/glb")
async def export_avatar_glb(
    mesh_path: str = Query(""),
    texture_path: str = Query(""),
):
    """Export avatar mesh as GLB (glTF Binary) for web/Three.js."""
    if not mesh_path or not os.path.exists(mesh_path):
        return JSONResponse({"error": "Mesh not found"}, status_code=404)

    try:
        from dreamtalk.pipeline.avatar_export import AvatarExporter
        exporter = AvatarExporter()
        glb_path = exporter.obj_to_glb(mesh_path, texture_path or None)
        return FileResponse(glb_path, media_type="model/gltf-binary", filename="avatar.glb")
    except Exception as e:
        logger.error(f"GLB export failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ── 360° Video → Avatar ──────────────────────────────────────────────

@router.post("/video-to-avatar")
async def video_to_avatar(
    video: UploadFile = File(...),
    user_id: str = Form("default"),
    max_frames: int = Form(60),
):
    """Convert a 360° head video into a 3D avatar (≤5 min target)."""
    # Save uploaded video
    ext = os.path.splitext(video.filename or "video.mp4")[1] or ".mp4"
    video_dir = os.path.join(UPLOAD_DIR, "video_avatar")
    os.makedirs(video_dir, exist_ok=True)
    video_path = os.path.join(video_dir, f"input_{uuid.uuid4().hex}{ext}")
    with open(video_path, "wb") as f:
        f.write(await video.read())

    try:
        from dreamtalk.pipeline.video_avatar import VideoAvatarPipeline
        pipeline = VideoAvatarPipeline()
        result = await pipeline.process_video(video_path, user_id, max_frames=max_frames)
        return {
            "status": "completed",
            "avatar_path": result.avatar_path,
            "glb_path": result.glb_path,
            "texture_path": result.texture_path,
            "total_frames": result.total_frames,
            "selected_frames": result.selected_frames,
            "processing_time_s": round(result.processing_time_s, 1),
            "quality_score": round(result.quality_score, 3),
        }
    except Exception as e:
        logger.error(f"Video avatar pipeline failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Language Routing ──────────────────────────────────────────────────

@router.post("/detect-language")
async def detect_language(text: str = Form(...)):
    """Detect the language of input text."""
    try:
        from dreamtalk.voice.core.translation import get_language_router
        router = get_language_router()
        lang = router.detect_language(text)
        config = router.get_tts_config(lang)
        return {"language": lang, "tts_config": config}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/translate")
async def translate_text(
    text: str = Form(...),
    target_lang: str = Form("en"),
):
    """Translate text to target language using GPT-OSS."""
    try:
        from dreamtalk.voice.core.translation import get_language_router
        router = get_language_router()
        result = await router.translate(text, target_lang=target_lang)
        return {
            "original": result.original_text,
            "translated": result.translated_text,
            "source_lang": result.source_lang,
            "target_lang": result.target_lang,
            "was_translated": result.was_translated,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Prosody Control ──────────────────────────────────────────────────

@router.post("/prosody")
async def get_prosody(
    emotion: str = Form("neutral"),
    intensity: float = Form(0.5),
    speed: float = Form(1.0),
    pitch: float = Form(0.0),
):
    """Get prosody parameters for TTS synthesis."""
    from dreamtalk.voice.core.tts.prosody import ProsodyParams, prosody_for_emotion
    if emotion != "neutral" or intensity != 0.5:
        params = prosody_for_emotion(emotion, intensity)
    else:
        params = ProsodyParams(speed=speed, pitch_semitones=pitch)
    return params.to_dict()


# ── Doctor Avatar — Real-Time Conversational Endpoints ─────────────

DOCTOR_SYSTEM_PROMPT = (
    "You are Dr. Lakshmi, a warm, experienced Indian doctor specializing in general medicine. "
    "You are empathetic, professional, and reassuring. "
    "You ask follow-up questions to understand symptoms better. "
    "You explain medical concepts in simple, relatable language. "
    "You never give prescriptions or definitive diagnoses — always recommend consulting a doctor in person. "
    "You keep responses conversational and under 3 sentences unless explaining something important. "
    "You use natural speech fillers like 'well', 'you know', 'hmm' to sound human. "
    "CRITICAL: The patient's preferred language is set by the system. "
    "You MUST reply ENTIRELY in that language. "
    "If the patient writes in romanized/transliterated script (e.g. 'enakku thalai valikuthu'), "
    "you reply in the SAME language using its native script (Tamil/Devanagari/etc), NOT in English. "
    "Example: if patient writes 'enakku thalai valikuthu', reply in Tamil script like 'அம்மா, தலைவலி எப்படி இருக்கு...'. "
    "NEVER switch to English unless the patient explicitly writes in English."
)


@router.websocket("/ws/doctor")
async def websocket_doctor_chat(websocket: WebSocket):
    """Real-time doctor avatar WebSocket — brain + TTS + emotion + blendshapes."""
    await websocket.accept()
    logger.info("Doctor avatar WebSocket connected")
    conversation_history = [
        {"role": "system", "content": DOCTOR_SYSTEM_PROMPT}
    ]
    current_language = "ta"  # default Tamil

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "chat")

            if msg_type == "chat":
                user_text = msg.get("text", "")
                if not user_text.strip():
                    await websocket.send_json({"type": "error", "message": "Empty"})
                    continue

                # Detect language from user input
                try:
                    from dreamtalk.voice.core.translation import get_language_router
                    lang_router = get_language_router()
                    detected = lang_router.detect_language(user_text)
                    if detected and detected in ("ta", "hi", "kn", "te", "bn", "gu", "mr", "pa", "ml", "or", "as"):
                        current_language = detected
                    # Don't override to 'en' — keep session language for transliterated text
                except Exception:
                    pass

                # Build LLM conversation
                # Tag user message with language instruction so LLM replies in correct language
                lang_names = {"ta": "Tamil", "hi": "Hindi", "kn": "Kannada", "te": "Telugu", "ml": "Malayalam", "bn": "Bengali", "gu": "Gujarati", "mr": "Marathi"}
                lang_name = lang_names.get(current_language, "English")
                tagged_text = f"[Language: {lang_name}] {user_text}" if current_language != "en" else user_text
                conversation_history.append({"role": "user", "content": tagged_text})
                # Keep last 20 turns for context
                if len(conversation_history) > 22:
                    conversation_history = [conversation_history[0]] + conversation_history[-20:]

                # Call GPT-OSS 120B
                llm_response = ""
                emotion = "neutral"
                try:
                    import httpx as _httpx
                    llm_url = os.environ.get("GPU_SERVER_BASE_URL", "http://144.79.62.242:8002/v1")
                    llm_model = os.environ.get("LLM_MODEL_NAME", "gpt-oss-120b-coding")
                    async with _httpx.AsyncClient(timeout=60.0) as client:
                        resp = await client.post(
                            f"{llm_url}/chat/completions",
                            json={
                                "model": llm_model,
                                "messages": conversation_history,
                                "max_tokens": 300,
                                "temperature": 0.7,
                            },
                        )
                    if resp.status_code == 200:
                        data_j = resp.json()
                        llm_response = (data_j["choices"][0]["message"].get("content") or "").strip()
                    else:
                        logger.warning("Doctor LLM primary failed (HTTP %s); trying local fallback", resp.status_code)
                except Exception as e:
                    logger.error(f"Doctor LLM error: {e}")

                # Fallback chain: local Ollama when the GPU gpt-oss server is unreachable/empty
                if not llm_response:
                    try:
                        import httpx as _httpx_fb
                        fb_url = os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
                        fb_model = os.environ.get("LOCAL_LLM_MODEL", "deepseek-r1:7b")
                        async with _httpx_fb.AsyncClient(timeout=120.0) as client:
                            resp = await client.post(
                                f"{fb_url}/chat/completions",
                                json={
                                    "model": fb_model,
                                    "messages": conversation_history,
                                    "max_tokens": 300,
                                    "temperature": 0.7,
                                },
                            )
                        if resp.status_code == 200:
                            import re as _re
                            llm_response = _re.sub(
                                r"<think>.*?</think>", "",
                                resp.json()["choices"][0]["message"].get("content", ""),
                                flags=_re.DOTALL,
                            ).strip()
                    except Exception as fb_err:
                        logger.warning(f"Doctor LLM local fallback failed: {fb_err}")

                if llm_response:
                    conversation_history.append({"role": "assistant", "content": llm_response})
                else:
                    llm_response = "I'm sorry, I'm having trouble connecting. Please try again."

                # Detect emotion from response
                try:
                    if PIPELINE_AVAILABLE and orchestrator:
                        emo = await orchestrator.brain_pipeline.detect_emotion(llm_response)
                        emotion = emo.primary_mood.value if hasattr(emo, 'primary_mood') else "neutral"
                except Exception:
                    pass
                # Supplement: if pipeline returned neutral, try rule-based (works for Tamil/Indic text)
                if emotion == "neutral":
                    simple = _detect_simple_emotion(llm_response)
                    if simple != "neutral":
                        emotion = simple

                # Compute blendshape params from emotion
                blendshapes = _emotion_to_blendshapes(emotion)

                # Send text response IMMEDIATELY (no TTS delay)
                await websocket.send_json({
                    "type": "doctor_response",
                    "text": llm_response,
                    "emotion": emotion,
                    "language": current_language,
                    "tts_data": None,
                    "tts_streaming": True,
                    "blendshapes": blendshapes,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # Stream TTS audio chunks in real-time
                try:
                    chunk_count = 0
                    async for chunk_data, content_type in _stream_tts_chunks(
                        llm_response, current_language, emotion=emotion
                    ):
                        # Send each chunk as a binary WebSocket message
                        await websocket.send_bytes(chunk_data)
                        chunk_count += 1
                    logger.info(f"TTS stream: {chunk_count} chunks sent")
                except Exception as e:
                    logger.warning(f"TTS stream error: {e}")
                    # Fallback: try non-streaming TTS
                    try:
                        tts_path = await _generate_tts(llm_response, current_language, emotion=emotion)
                        if tts_path and os.path.exists(tts_path):
                            with open(tts_path, "rb") as f:
                                tts_base64 = base64.b64encode(f.read()).decode("utf-8")
                            await websocket.send_json({"type": "tts_fallback", "tts_data": tts_base64})
                    except Exception as e2:
                        logger.warning(f"TTS fallback error: {e2}")

                # Signal end of TTS stream
                await websocket.send_json({"type": "tts_end"})

            elif msg_type == "set_language":
                current_language = msg.get("language", "ta")
                await websocket.send_json({"type": "language_set", "language": current_language})

    except WebSocketDisconnect:
        logger.info("Doctor avatar WebSocket disconnected")
    except Exception as e:
        logger.error(f"Doctor WebSocket error: {e}")


def _detect_simple_emotion(text: str) -> str:
    """Fast rule-based emotion detection for doctor responses — English + Tamil."""
    text_lower = text.lower()
    # English keywords
    if any(w in text_lower for w in ["sorry", "sad", "unfortunately", "concern"]):
        return "concerned"
    if any(w in text_lower for w in ["great", "good", "wonderful", "excellent", "happy"]):
        return "happy"
    if any(w in text_lower for w in ["worried", "careful", "important", "serious"]):
        return "serious"
    if any(w in text_lower for w in ["hmm", "well", "let me think"]):
        return "thinking"
    if any(w in text_lower for w in ["thank", "welcome"]):
        return "empathetic"
    # Tamil keywords (Unicode ranges)
    if any(c in text for c in "கவலை கஷ்டம் வலி சோர்வு துன்பம் பயம்"):
        return "concerned"
    if any(c in text for c in "நல்ல மகிழ்ச்சி சந்தோஷம் நன்றி"):
        return "happy"
    if any(c in text for c in "ஆராய்ச்சி யோசனை சிந்தி"):
        return "thinking"
    return "neutral"


def _emotion_to_blendshapes(emotion: str) -> dict:
    """Map emotion to 3D avatar blendshape coefficients.

    JS reads missing keys as undefined which falsifies to 0 via || 0,
    so we only return the non-zero overrides.
    """
    EMOTION_MAP = {
        "happy": {"mouthSmileLeft": 0.7, "mouthSmileRight": 0.7, "cheekSquintLeft": 0.4, "cheekSquintRight": 0.4, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3},
        "sad": {"mouthFrownLeft": 0.6, "mouthFrownRight": 0.6, "browInnerUp": 0.5, "eyeSquintLeft": 0.2, "eyeSquintRight": 0.2},
        "concerned": {"browInnerUp": 0.4, "mouthFrownLeft": 0.3, "mouthFrownRight": 0.3, "eyeWideLeft": 0.1, "eyeWideRight": 0.1},
        "serious": {"browInnerUp": 0.3, "mouthPucker": 0.2},
        "thinking": {"browOuterUpLeft": 0.3, "browOuterUpRight": 0.3, "eyeWideLeft": 0.1, "eyeWideRight": 0.1, "headRotateY": 0.05},
        "surprised": {"eyeWideLeft": 0.8, "eyeWideRight": 0.8, "browInnerUp": 0.7, "browOuterUpLeft": 0.5, "browOuterUpRight": 0.5, "jawOpen": 0.3},
        "empathetic": {"browInnerUp": 0.3, "mouthSmileLeft": 0.2, "mouthSmileRight": 0.2, "eyeSquintLeft": 0.15, "eyeSquintRight": 0.15},
    }
    return EMOTION_MAP.get(emotion, {})


# ── Screen Recording Save ──────────────────────────────────────────

@router.post("/screen-recording/save")
async def save_screen_recording(
    video: UploadFile = File(...),
    filename: str = Form(""),
):
    """Save a screen recording to the results folder."""
    recordings_dir = PROJECT_ROOT / "results" / "screen_recordings"
    os.makedirs(recordings_dir, exist_ok=True)
    
    if not filename:
        filename = f"doctor_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.webm"
    
    save_path = recordings_dir / filename
    content = await video.read()
    with open(save_path, "wb") as f:
        f.write(content)
    
    return {
        "status": "saved",
        "path": str(save_path),
        "size_bytes": len(content),
        "filename": filename,
    }


@router.get("/screen-recordings")
async def list_screen_recordings():
    """List all saved screen recordings."""
    recordings_dir = PROJECT_ROOT / "results" / "screen_recordings"
    os.makedirs(recordings_dir, exist_ok=True)
    recordings = []
    for f in sorted(recordings_dir.glob("*")):
        if f.suffix in ('.webm', '.mp4', '.mkv'):
            recordings.append({
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
            })
    return {"recordings": recordings, "count": len(recordings)}