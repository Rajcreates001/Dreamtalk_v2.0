# Dreamtalk - Voice Module
# Migrated from Dreamtalk-Voice-Cloning-Module
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import tempfile

from dreamtalk.backend.services.voice_orchestrator import VoiceOrchestrator
from dreamtalk.backend.services.text_cleaner import clean_text_for_tts

import logging
logger = logging.getLogger("dreamtalk.voice")

router = APIRouter(prefix="/api/v1/voice", tags=["Voice"])

_orchestrator = None


def _get_orchestrator() -> VoiceOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = VoiceOrchestrator()
    return _orchestrator


class GenerateVoiceRequest(BaseModel):
    text: str
    voice_id: str
    emotion: Optional[str] = "neutral"
    pitch: Optional[float] = 1.0
    speed: Optional[float] = 1.0
    tone: Optional[str] = "neutral"
    engine: Optional[str] = "kokoro"
    language: Optional[str] = "auto"


@router.get("/status")
async def get_status():
    return {"status": "online", "message": "Voice Module is ready."}


@router.get("/voices")
async def get_voices():
    try:
        voices_data = await _get_orchestrator().get_all_voices()
        return voices_data
    except Exception as e:
        print(f"Backend error in get_voices: {e}")
        return {"kokoro": {}}


@router.get("/engines")
async def get_engines():
    try:
        engines = await _get_orchestrator().list_engines()
        return {"engines": engines}
    except Exception as e:
        print(f"Backend error in get_engines: {e}")
        return {"engines": []}


@router.post("/clone-voice")
async def clone_voice(
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...)
):
    try:
        os.makedirs("voice_module/assets/voices", exist_ok=True)
        temp_filename = f"voice_module/assets/voices/{uuid.uuid4()}_{file.filename}"
        with open(temp_filename, "wb") as f:
            f.write(await file.read())

        voice_id = await _get_orchestrator().clone_voice(name, description, [temp_filename])
        return {"voice_id": voice_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-voice")
async def generate_voice(request: GenerateVoiceRequest):
    try:
        cleaned_text = clean_text_for_tts(request.text)

        filename = await _get_orchestrator().generate_speech(
            text=cleaned_text,
            voice_id=request.voice_id,
            emotion=request.emotion,
            pitch=request.pitch,
            speed=request.speed,
            tone=request.tone,
            engine=request.engine,
            language=request.language or "auto",
        )

        return {"audio_url": f"/outputs/{filename}"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clone-and-speak")
async def clone_and_speak(
    file: UploadFile = File(...),
    text: str = Form(...),
    language: str = Form("auto"),
    name: str = Form("Cloned Voice"),
    persist: bool = Form(True),
):
    """Unified endpoint: upload reference audio → clone voice → generate speech.

    This chains the clone and generate steps into a single API call:
    1. Upload a reference audio file (the voice you want to clone)
    2. Provide the text to speak
    3. Returns the generated WAV audio in the cloned voice        Args:
            file: Reference audio file (WAV/MP3, the speaker to clone)
            text: Text to synthesize in the cloned voice
            language: Language code (auto, en, hi, ta, kn, etc.)
            name: Name for the cloned voice profile
            persist: If True (default), keep the cloned voice profile for reuse; otherwise delete after generation
    """
    temp_filename = None
    voice_id = None
    try:
        # Validate text
        cleaned_text = clean_text_for_tts(text)

        # Save uploaded audio to temp
        os.makedirs("voice_module/assets/voices", exist_ok=True)
        temp_filename = f"voice_module/assets/voices/clone_speak_{uuid.uuid4().hex[:12]}_{file.filename}"
        with open(temp_filename, "wb") as f:
            f.write(await file.read())

        # Step 1: Clone the voice
        voice_id = await _get_orchestrator().clone_voice(name, f"Auto-cloned for: {text[:50]}", [temp_filename])

        # Step 2: Generate speech using the cloned voice
        filename = await _get_orchestrator().generate_speech(
            text=cleaned_text,
            voice_id=voice_id,
            language=language,
        )

        # Step 3: Clean up the cloned profile unless persist=True
        if not persist and voice_id:
            try:
                await _get_orchestrator().delete_voice_profile(voice_id)
            except Exception:
                pass

        # Read the generated audio for direct return
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                audio_bytes = f.read()
            media_type = "audio/wav"

            return Response(
                content=audio_bytes,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="cloned_speech_{voice_id[:8]}.wav"',
                    "X-Voice-ID": voice_id,
                },
            )

        # Fallback: return path info
        return {
            "voice_id": voice_id,
            "audio_url": f"/outputs/{filename}",
            "text": cleaned_text[:100],
            "language": language,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always clean up temp upload file
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass


# ── Free Local STT (faster-whisper, no API key) ────────────────────────
_stt_model = None

def _get_stt_model():
    global _stt_model
    if _stt_model is None:
        try:
            from faster_whisper import WhisperModel
            _stt_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            logger.info("faster-whisper STT model loaded (tiny, cpu)")
        except Exception as e:
            logger.error(f"Failed to load STT model: {e}")
    return _stt_model


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en"),
):
    """Free local speech-to-text using faster-whisper.

    Accepts WAV, MP3, WEBM, OGG audio files.
    Returns transcribed text.
    """
    model = _get_stt_model()
    if model is None:
        raise HTTPException(status_code=503, detail="STT model not available")

    # Save uploaded audio to temp file
    ext = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    temp_path = f"/tmp/stt_upload_{uuid.uuid4().hex[:8]}{ext}"
    try:
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Transcribe with faster-whisper
        segments, info = model.transcribe(
            temp_path,
            language=language if language != "auto" else None,
            beam_size=1,  # Fast mode
            vad_filter=True,  # Voice activity detection
        )

        text = " ".join([seg.text for seg in segments])

        return {
            "text": text.strip(),
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 2),
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
