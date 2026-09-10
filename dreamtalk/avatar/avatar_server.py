"""DreamTalk 3D Avatar Interactive Web Server.

Serves an interactive 3D avatar viewer with real-time chat, voice cloning,
3D face mesh from uploaded image, and script reading capabilities.

Run: uvicorn dreamtalk.avatar.avatar_server:app --host 0.0.0.0 --port 5000
"""

import asyncio
import json
import logging
import os
import sys
import uuid
import base64
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# ── Fix Torch DLL loading on Windows ────────────────────────────────
_torch_lib = Path(os.path.dirname(os.__file__)).parent / "Lib" / "site-packages" / "torch" / "lib"
if _torch_lib.exists():
    os.environ.setdefault("PATH", "")
    os.environ["PATH"] = str(_torch_lib) + os.pathsep + os.environ["PATH"]
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dreamtalk.avatar.server")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = PROJECT_ROOT / "local_upload_testing"
OUTPUT_DIR = PROJECT_ROOT / "pipeline_outputs"
STATIC_DIR = Path(__file__).resolve().parent / "static"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ── Lazy imports ─────────────────────────────────────────────────────

try:
    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
    PIPELINE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Pipeline import failed: {e}")
    PIPELINE_AVAILABLE = False

try:
    import edge_tts
    EDGETTS_AVAILABLE = True
    logger.info("Edge-TTS available")
except Exception as e:
    EDGETTS_AVAILABLE = False
    logger.warning(f"Edge-TTS import failed: {e}")

try:
    import soundfile as sf
    SOUNDFILE_OK = True
except Exception:
    SOUNDFILE_OK = False

# Kokoro as secondary option
try:
    from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
    KOKORO_AVAILABLE = True
except Exception:
    KOKORO_AVAILABLE = False

# ── App Setup ────────────────────────────────────────────────────────

app = FastAPI(title="DreamTalk 3D Avatar", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

orchestrator = PipelineOrchestrator() if PIPELINE_AVAILABLE else None
kokoro = None

# Active pipeline results for the current session
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
}


# ── Static Files ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC_DIR / "avatar_viewer.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Avatar Viewer</h1><p>Loading...</p>")


@app.get("/api/status")
async def status():
    return {
        "pipeline_available": PIPELINE_AVAILABLE,
        "kokoro_available": KOKORO_AVAILABLE,
        "session": {
            "has_face": session_data["face_result"] is not None,
            "has_voice": session_data["voice_result"] is not None,
            "has_mesh": session_data["mesh_path"] is not None,
            "pipeline_id": session_data["pipeline_id"],
        }
    }


# ── Pipeline API ─────────────────────────────────────────────────────

@app.post("/api/pipeline/run")
async def run_pipeline(
    image: UploadFile = File(None),
    voice: UploadFile = File(None),
    text: str = Form("Hello! I'm your Digital Twin."),
    role: str = Form("normal_user"),
):
    if not PIPELINE_AVAILABLE or orchestrator is None:
        return JSONResponse({"error": "Pipeline not available"}, status_code=503)

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

    # Store session
    session_data["pipeline_id"] = result.pipeline_id
    session_data["face_result"] = result.face_result
    session_data["voice_result"] = result.voice_result
    session_data["emotion_result"] = result.emotion_result
    session_data["brain_result"] = result.brain_result
    session_data["last_pipeline_run"] = datetime.utcnow().isoformat()

    # Find mesh and texture
    if result.face_result and result.face_result.mesh_3d_path:
        session_data["mesh_path"] = result.face_result.mesh_3d_path
    if result.face_result and result.face_result.texture_path:
        session_data["texture_path"] = result.face_result.texture_path
    if result.voice_result and result.voice_result.cloned_voice_path:
        session_data["cloned_voice_path"] = result.voice_result.cloned_voice_path
    if result.voice_result and result.voice_result.tts_sample_path:
        session_data["tts_path"] = result.voice_result.tts_sample_path

    # Copy mesh/texture to static dir for serving
    if session_data["mesh_path"] and os.path.exists(session_data["mesh_path"]):
        static_mesh = STATIC_DIR / "current_mesh.obj"
        with open(session_data["mesh_path"], "rb") as src, open(static_mesh, "wb") as dst:
            dst.write(src.read())
    if session_data["texture_path"] and os.path.exists(session_data["texture_path"]):
        static_tex = STATIC_DIR / "current_texture.jpg"
        with open(session_data["texture_path"], "rb") as src, open(static_tex, "wb") as dst:
            dst.write(src.read())
        static_tex_mtl = STATIC_DIR / "face_texture.mtl"
        static_tex_mtl.write_text(
            "newmtl face_texture\n"
            "Ka 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\n"
            f"map_Kd current_texture.jpg\n"
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


@app.post("/api/chat")
async def chat(text: str = Form(...)):
    if not PIPELINE_AVAILABLE or orchestrator is None:
        return {"response": "Chat is not available right now.", "emotion": "neutral"}

    try:
        from dreamtalk.pipeline.models import EmotionResult, BrainDecisionResult
    except Exception:
        return {"response": f"You said: {text}", "emotion": "neutral"}

    try:
        emotion = await orchestrator.brain_pipeline.detect_emotion(text)
        brain = await orchestrator.brain_pipeline.make_decision(
            text=text,
            role="normal_user",
            emotion=emotion,
            model_name="rule_based",
        )
        session_data["emotion_result"] = emotion
        session_data["brain_result"] = brain

        # Try to generate TTS for the response
        tts_path = None
        try:
            tts_path = await generate_tts(brain.response_text)
        except Exception:
            pass

        return {
            "response": brain.response_text,
            "emotion": emotion.primary_mood.value,
            "valence": emotion.valence,
            "arousal": emotion.arousal,
            "tts_path": tts_path,
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"response": f"I'm processing but encountered an issue: {str(e)}", "emotion": "neutral"}


@app.post("/api/generate-script")
async def generate_script(script_text: str = Form(...)):
    """Generate a TTS audio file for a 3-minute script in the cloned voice."""
    if not script_text:
        return {"error": "No script text provided"}

    tts_path = await generate_tts(script_text)
    return {
        "tts_path": tts_path,
        "length_chars": len(script_text),
    }


@app.get("/api/static/{filename}")
async def serve_static(filename: str):
    file_path = STATIC_DIR / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="application/octet-stream")
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/api/tts-audio")
async def tts_audio(path: str = ""):
    """Serve TTS audio as base64 for browser playback."""
    if not path or not os.path.exists(path):
        return {"base64": None, "error": "File not found"}
    import base64
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {"base64": b64, "filename": os.path.basename(path)}


@app.get("/api/script/info")
async def script_info():
    """Get script metadata for 3-minute avatar script playback."""
    meta_path = STATIC_DIR / "script_meta.json"
    script_path = STATIC_DIR / "script_3min.wav"
    if not meta_path.exists() or not script_path.exists():
        return {"available": False, "error": "No script generated yet"}
    import json
    meta = json.loads(meta_path.read_text())
    meta["available"] = True
    meta["duration_seconds"] = os.path.getsize(script_path) / 32000
    # Convert paths to URLs
    meta["script_url"] = "/api/static/script_3min.wav"
    meta["parts"] = []
    parts_dir = STATIC_DIR / "script_parts"
    if parts_dir.exists():
        for p in sorted(parts_dir.iterdir()):
            if p.suffix == ".wav":
                meta["parts"].append({
                    "index": len(meta["parts"]),
                    "url": f"/api/static/script_parts/{p.name}",
                    "size": p.stat().st_size,
                })
    return meta


@app.get("/api/script/play/{part_index}")
async def play_script_part(part_index: int):
    """Get a specific script part as base64 audio."""
    parts_dir = STATIC_DIR / "script_parts"
    part_file = parts_dir / f"part_{part_index:02d}.wav"
    if not part_file.exists():
        # Fall back to full script
        part_file = STATIC_DIR / "script_3min.wav"
    if not part_file.exists():
        return {"base64": None, "error": "Not found"}
    import base64
    with open(part_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {"base64": b64, "index": part_index, "filename": part_file.name}


@app.get("/api/session")
async def get_session():
    mesh_url = None
    tex_url = None
    mesh_path = session_data["mesh_path"]
    tex_path = session_data["texture_path"]

    # Check pre-existing static files
    static_mesh = STATIC_DIR / "current_mesh.obj"
    static_tex = STATIC_DIR / "current_texture.jpg"
    static_voice = STATIC_DIR / "cloned_voice.wav"

    if mesh_path and os.path.exists(mesh_path):
        mesh_url = "/api/static/current_mesh.obj"
    elif static_mesh.exists():
        mesh_url = "/api/static/current_mesh.obj"
        session_data["mesh_path"] = str(static_mesh)

    if tex_path and os.path.exists(tex_path):
        tex_url = "/api/static/current_texture.jpg"
    elif static_tex.exists():
        tex_url = "/api/static/current_texture.jpg"
        session_data["texture_path"] = str(static_tex)

    if static_voice.exists() and not session_data["cloned_voice_path"]:
        session_data["cloned_voice_path"] = str(static_voice)

    voice_url = "/api/static/cloned_voice.wav" if static_voice.exists() else None
    if session_data["cloned_voice_path"] and not voice_url:
        fn = os.path.basename(session_data["cloned_voice_path"])
        voice_url = f"/api/static/{fn}"

    # Also auto-run pipeline if not yet done but files exist
    if session_data["pipeline_id"] is None and static_mesh.exists():
        session_data["last_pipeline_run"] = "preloaded"

    return {
        "pipeline_id": session_data["pipeline_id"],
        "has_face": session_data["face_result"] is not None or session_data["mesh_path"] is not None,
        "has_voice": session_data["voice_result"] is not None or session_data["cloned_voice_path"] is not None,
        "mesh_url": mesh_url,
        "texture_url": tex_url,
        "cloned_voice_url": voice_url,
        "face_result": _safe_serialize(session_data["face_result"]),
        "voice_result": _safe_serialize(session_data["voice_result"]),
        "emotion_result": _safe_serialize(session_data["emotion_result"]),
        "brain_result": _safe_serialize(session_data["brain_result"]),
        "script_available": (STATIC_DIR / "script_3min.wav").exists(),
        "script_parts": len(list((STATIC_DIR / "script_parts").glob("*.wav"))) if (STATIC_DIR / "script_parts").exists() else 0,
    }


# ── WebSocket Chat ───────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            text = msg.get("text", "")

            if not text.strip():
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            # Process through brain
            try:
                emotion = await orchestrator.brain_pipeline.detect_emotion(text)
                brain = await orchestrator.brain_pipeline.make_decision(
                    text=text,
                    role="normal_user",
                    emotion=emotion,
                    model_name="rule_based",
                )
            except Exception as e:
                await websocket.send_json({
                    "type": "response",
                    "text": f"I'm having trouble processing that. Error: {str(e)}",
                    "emotion": "neutral",
                })
                continue

            # Generate TTS for response
            tts_data = None
            try:
                tts_path = await generate_tts(brain.response_text)
                if tts_path and os.path.exists(tts_path):
                    with open(tts_path, "rb") as f:
                        tts_data = base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass

            await websocket.send_json({
                "type": "response",
                "text": brain.response_text,
                "emotion": emotion.primary_mood.value,
                "valence": emotion.valence,
                "arousal": emotion.arousal,
                "hostile": emotion.is_hostile,
                "tts_data": tts_data,
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ── Helpers ──────────────────────────────────────────────────────────

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


def _get_best_voice(gender=None):
    """Choose the best Kokoro voice based on detected gender or default."""
    if gender == "male":
        return "am_adam"
    return "af_heart"


async def generate_tts(text: str, voice_name: str = None) -> Optional[str]:
    """Generate TTS using Edge-TTS (no torch needed). Returns path to WAV or None."""
    out_dir = OUTPUT_DIR / "tts"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"tts_{uuid.uuid4().hex[:8]}.wav")

    # Try Edge-TTS first (no dependencies)
    if EDGETTS_AVAILABLE:
        try:
            # Map gender to Edge-TTS voice
            edge_voice = "en-US-JennyNeural"  # default female
            if voice_name:
                edge_voice = voice_name
            elif session_data.get("voice_result") and session_data["voice_result"].gender_prediction == "male":
                edge_voice = "en-US-GuyNeural"
            communicate = edge_tts.Communicate(text, edge_voice)
            await communicate.save(out_path)
            file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
            if file_size > 1000:
                logger.info(f"Edge-TTS: {out_path} ({file_size} bytes)")
                return str(out_path)
        except Exception as e:
            logger.warning(f"Edge-TTS failed: {e}")

    # Fallback: Kokoro TTS
    if KOKORO_AVAILABLE:
        try:
            _kokoro_dev = "cuda" if torch.cuda.is_available() else "cpu"
            engine = KokoroTTSEngine(device=_kokoro_dev)
            if voice_name is None:
                gender = None
                if session_data["voice_result"]:
                    gender = session_data["voice_result"].gender_prediction
                voice_name = _get_best_voice(gender)
            chunks = engine.synthesize(text, voice=voice_name, lang_code="a", speed=1.0)
            if chunks:
                combined = np.concatenate(chunks)
                sf.write(out_path, combined, 24000)
                logger.info(f"Kokoro TTS: {out_path}")
                return str(out_path)
        except Exception as e:
            logger.warning(f"Kokoro TTS failed: {e}")

    # Final fallback: Generate placeholder sine-wave audio
    try:
        duration = min(max(len(text) * 0.08, 1.0), 30.0)
        sr = 22050
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        audio = 0.3 * np.sin(2 * np.pi * 200 * t)
        audio += 0.1 * np.sin(2 * np.pi * 400 * t)
        fade = min(int(sr * 0.02), len(audio) // 4)
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)
        sf.write(out_path, audio, sr)
        logger.info(f"Placeholder TTS: {out_path}")
        return str(out_path)
    except Exception as e:
        logger.error(f"All TTS failed: {e}")

    return None


@app.on_event("startup")
async def startup():
    logger.info("DreamTalk Avatar Server started")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("avatar_server:app", host="0.0.0.0", port=5000, reload=True)
