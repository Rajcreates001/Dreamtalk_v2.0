# ── Celery Tasks ──────────────────────────────────────────────────────
# Heavy / long-running operations run asynchronously via Redis broker.

from dreamtalk.backend.celery_app import celery_app
import logging

logger = logging.getLogger("dreamtalk.celery")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_full_pipeline(self, image_path: str, voice_path: str, twin_id: str = None):
    """Run the full face + voice + brain pipeline asynchronously."""
    try:
        from dreamtalk.pipeline.face_pipeline import FacePipeline
        from dreamtalk.pipeline.voice_pipeline import VoicePipeline
        from dreamtalk.digital_twin.personality import PersonalityEngine

        face_pipe = FacePipeline()
        voice_pipe = VoicePipeline()

        face_result = face_pipe.process(image_path)
        if not face_result:
            return {"status": "error", "step": "face", "error": "Face processing failed"}

        voice_result = voice_pipe.process(voice_path)
        if not voice_result:
            return {"status": "error", "step": "voice", "error": "Voice processing failed"}

        if twin_id:
            pe = PersonalityEngine(twin_id=twin_id)
            pe.update_from_pipeline({"face": face_result, "voice": voice_result})

        return {
            "status": "completed",
            "face": face_result,
            "voice": voice_result,
        }
    except Exception as exc:
        logger.error(f"Pipeline task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_tts_async(self, text: str, language: str = "en", voice: str = None):
    """Generate TTS audio in the background."""
    try:
        import os
        import uuid
        import numpy as np
        import soundfile as sf

        output_dir = os.getenv("TTS_OUTPUT_DIR", "/app/pipeline_outputs/tts")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"tts_{uuid.uuid4().hex[:8]}.wav")

        # Try Edge-TTS first
        import edge_tts

        lang_map = {
            "en": ("en-US-JennyNeural", "en-US-GuyNeural"),
            "kn": ("kn-IN-SapnaNeural", "kn-IN-GaganNeural"),
            "ta": ("ta-IN-PallaviNeural", "ta-IN-ValluvarNeural"),
            "hi": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"),
        }
        voice_name = lang_map.get(language, lang_map["en"])[0]
        communicate = edge_tts.Communicate(text, voice_name)
        communicate.save(output_path)
        import asyncio
        asyncio.get_event_loop().run_until_complete(communicate.save(output_path))

        if os.path.getsize(output_path) > 1000:
            return {"status": "completed", "path": output_path, "engine": "edge-tts"}

        # Fallback: Kokoro
        try:
            from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
            kokoro = KokoroTTSEngine(device="cpu")
            chunks = kokoro.synthesize(text, voice="af_heart", lang_code="a", speed=1.0)
            if chunks:
                combined = np.concatenate(chunks)
                sf.write(output_path, combined, 24000)
                return {"status": "completed", "path": output_path, "engine": "kokoro"}
        except Exception:
            pass

        return {"status": "error", "error": "All TTS engines failed"}
    except Exception as exc:
        logger.error(f"TTS task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2)
def run_brain_inference(self, text: str, twin_id: str = None, language: str = "en"):
    """Run brain/LLM inference asynchronously."""
    try:
        from dreamtalk.backend.services.llm_service import LLMService
        from dreamtalk.backend.services.knowledge_base import StudentKnowledgeBase

        kb = StudentKnowledgeBase()
        kb_response = kb.query(text)
        if kb_response:
            return {"status": "completed", "response": kb_response, "source": "knowledge_base"}

        llm = LLMService()
        response = llm.chat(text)
        return {"status": "completed", "response": response, "source": "llm"}
    except Exception as exc:
        logger.error(f"Brain task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
