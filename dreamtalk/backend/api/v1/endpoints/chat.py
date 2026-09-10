# Dreamtalk - Chat API Endpoints

import os
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio

from dreamtalk.backend.services.llm_service import chat_completion, check_gpu_server_health
from dreamtalk.backend.api.v1.endpoints.auth import get_current_user
from dreamtalk.digital_twin.learning import ContinuousLearningEngine
from dreamtalk.emotion.core.emotion_detector import EmotionAnalyzer, AffectiveStateTracker
from dreamtalk.backend.services.voice_orchestrator import VoiceOrchestrator

router = APIRouter(prefix="/api", tags=["Chat"])

# ── Emotion detectors (lazy-loaded singletons) ────────────────────────
_emotion_analyzer = None
_affective_tracker = None
_voice_orch = None


def _get_emotion_analyzer():
    global _emotion_analyzer
    if _emotion_analyzer is None:
        _emotion_analyzer = EmotionAnalyzer()
    return _emotion_analyzer


def _get_emotion_tracker():
    global _affective_tracker
    if _affective_tracker is None:
        _affective_tracker = AffectiveStateTracker()
    return _affective_tracker


def _get_voice_orch():
    global _voice_orch
    if _voice_orch is None:
        _voice_orch = VoiceOrchestrator()
    return _voice_orch


class ChatRequest(BaseModel):
    message: str
    twin_id: Optional[str] = None
    interaction_id: Optional[str] = None
    identity_id: Optional[str] = None  # legacy alias
    history: Optional[list[dict[str, str]]] = []
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


class ChatResponse(BaseModel):
    response: str
    emotion: str = "neutral"
    emotion_detail: dict = {}
    tts_path: Optional[str] = None
    model: str = ""
    usage: dict = {}
    learning: Optional[dict] = None


async def _run_learning(
    twin_id: str,
    interaction_id: str,
    user_message: str,
    assistant_response: str,
):
    """Fire-and-forget continuous learning after chat response."""
    try:
        await ContinuousLearningEngine.process_conversation(
            twin_id=twin_id,
            interaction_id=interaction_id,
            user_message=user_message,
            assistant_response=assistant_response,
        )
    except Exception as e:
        import logging
        logging.getLogger("dreamtalk.chat").warning(
            "Continuous learning post-processing failed: %s", e,
        )


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: Optional[dict] = Depends(get_current_user),
):
    try:
        messages = []
        for msg in request.history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": request.message})

        if request.stream:
            stream_gen = await chat_completion(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
            return StreamingResponse(stream_gen, media_type="text/event-stream")

        result = await chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # ── Emotion detection ────────────────────────────────────────
        emotion_detail = {}
        emotion_name = "neutral"
        tts_path = None
        try:
            analyzer = _get_emotion_analyzer()
            tracker = _get_emotion_tracker()
            sentiment = analyzer.analyze_text(request.message)
            emotion_detail = tracker.update_state(request.message, sentiment)
            emotion_name = emotion_detail.get("mood", "neutral")

            # ── Generate emotion-aware TTS ───────────────────────────
            try:
                voice_orch = _get_voice_orch()
                tts_path = await voice_orch.generate_speech(
                    text=result["response"],
                    voice_id="af_heart",
                    emotion=emotion_name,
                    speed=1.0,
                    engine="kokoro",
                )
            except Exception as tts_err:
                import logging
                logging.getLogger("dreamtalk.chat").warning("TTS generation failed: %s", tts_err)
        except Exception as emo_err:
            import logging
            logging.getLogger("dreamtalk.chat").warning("Emotion detection failed: %s", emo_err)

        # Convert tts_path to audio_url the frontend can use
        audio_url = None
        tts_full_path = None
        if tts_path and os.path.exists(tts_path):
            audio_url = f"/outputs/{os.path.basename(tts_path)}"
            tts_full_path = tts_path
        elif tts_path:
            # tts_path may be relative — try resolving it
            for candidate in [tts_path, f"pipeline_outputs/tts/{os.path.basename(tts_path)}"]:
                if os.path.exists(candidate):
                    audio_url = f"/outputs/{os.path.basename(tts_path)}"
                    tts_full_path = candidate
                    break

        # Generate lip sync keyframes from TTS audio
        lipsync_keyframes = []
        lipsync_duration = 0.0
        if tts_full_path and os.path.exists(tts_full_path):
            try:
                from dreamtalk.pipeline.lipsync_pipeline import get_lipsync_pipeline
                lipsync_pipeline = get_lipsync_pipeline(fps=30.0)
                lipsync_result = lipsync_pipeline.extract_from_audio(
                    tts_full_path,
                    emotion={"primary_mood": emotion_name, "arousal": emotion_detail.get("arousal", 0.5) if emotion_detail else 0.5},
                )
                lipsync_keyframes = [kf.to_dict() for kf in lipsync_result.keyframes]
                lipsync_duration = lipsync_result.duration
            except Exception as ls_err:
                logging.getLogger("dreamtalk.chat").warning(f"Lip sync failed: {ls_err}")

        # Map emotion to expression blendshapes
        expression = None
        try:
            from dreamtalk.pipeline.emotion_animation import get_emotion_animation_mapper
            mapper = get_emotion_animation_mapper()
            expression = mapper.map_emotion(
                primary_mood=emotion_name,
                valence=emotion_detail.get("valence", 0) if emotion_detail else 0,
                arousal=emotion_detail.get("arousal", 0.5) if emotion_detail else 0.5,
                dominance=emotion_detail.get("dominance", 0.5) if emotion_detail else 0.5,
            ).to_dict()
        except Exception as expr_err:
            logging.getLogger("dreamtalk.chat").warning(f"Expression mapping failed: {expr_err}")

        response = ChatResponse(
            response=result["response"],
            emotion=emotion_name,
            emotion_detail=emotion_detail,
            tts_path=tts_path,
            model=result.get("model", ""),
            usage=result.get("usage", {}),
        )
        # Attach audio_url, expression, and lipsync as extra fields
        resp_dict = response.model_dump()
        resp_dict["audio_url"] = audio_url
        resp_dict["expression"] = expression
        resp_dict["lipsync"] = lipsync_keyframes
        resp_dict["lipsync_duration"] = lipsync_duration

        # Post-conversation continuous learning (fire-and-forget)
        twin_id = request.twin_id or request.identity_id
        if twin_id and request.interaction_id and current_user:
            asyncio.ensure_future(_run_learning(
                twin_id=twin_id,
                interaction_id=request.interaction_id,
                user_message=request.message,
                assistant_response=response.response,
            ))

        return resp_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    gpu = await check_gpu_server_health()
    return {
        "status": "ok",
        "gpu_server": gpu,
        "version": "0.1.0",
    }


# ── Public Chat (no auth required) ────────────────────────────────────
@router.post("/chat/public")
async def chat_public(request: ChatRequest):
    """Public chat endpoint using the brain pipeline (no auth required)."""
    try:
        from dreamtalk.pipeline.brain_pipeline import BrainPipeline
        brain = BrainPipeline()

        # Detect emotion
        emotion = await brain.detect_emotion(request.message)

        # Generate brain response
        history = [{"role": m["role"], "content": m["content"]} for m in request.history]
        brain_result = await brain.make_decision(
            text=request.message,
            role="normal_user",
            emotion=emotion,
            model_name="deepseek-r1:7b",
        )

        # Generate TTS
        tts_audio = None
        audio_path = None
        try:
            from dreamtalk.pipeline.voice_pipeline import VoicePipeline
            vp = VoicePipeline()
            audio_path, tts_info = vp.generate_tts(
                text=brain_result.response_text,
                output_dir="pipeline_outputs/tts",
            )
            if audio_path:
                tts_audio = f"/outputs/{os.path.basename(audio_path)}"
        except Exception as tts_err:
            import logging
            logging.getLogger("dreamtalk.chat").warning(f"TTS failed: {tts_err}")

        # Generate lip sync keyframes from TTS audio
        lipsync_keyframes = []
        lipsync_duration = 0.0
        if tts_audio and audio_path:
            try:
                from dreamtalk.pipeline.lipsync_pipeline import get_lipsync_pipeline
                lipsync_pipeline = get_lipsync_pipeline(fps=30.0)
                lipsync_result = lipsync_pipeline.extract_from_audio(
                    audio_path, emotion={"primary_mood": emotion.primary_mood.value if emotion else "neutral", "arousal": emotion.arousal if emotion else 0.5}
                )
                lipsync_keyframes = [kf.to_dict() for kf in lipsync_result.keyframes]
                lipsync_duration = lipsync_result.duration
            except Exception as ls_err:
                logging.getLogger("dreamtalk.chat").warning(f"Lip sync failed: {ls_err}")

        # Map emotion to expression
        expression = None
        try:
            from dreamtalk.pipeline.emotion_animation import get_emotion_animation_mapper
            mapper = get_emotion_animation_mapper()
            expression = mapper.map_emotion(
                primary_mood=emotion.primary_mood.value,
                valence=emotion.valence,
                arousal=emotion.arousal,
                dominance=emotion.dominance,
            ).to_dict()
        except Exception as expr_err:
            import logging
            logging.getLogger("dreamtalk.chat").warning(f"Expression mapping failed: {expr_err}")

        return {
            "response": brain_result.response_text,
            "emotion": emotion.primary_mood.value if emotion else "neutral",
            "emotion_detail": {
                "valence": emotion.valence if emotion else 0,
                "arousal": emotion.arousal if emotion else 0,
                "dominance": emotion.dominance if emotion else 0.5,
                "confidence": emotion.confidence if emotion else 0.5,
            } if emotion else None,
            "expression": expression,
            "audio_url": tts_audio,
            "lipsync": lipsync_keyframes,
            "lipsync_duration": lipsync_duration,
            "brain": {
                "action": brain_result.basal_ganglia_action,
                "confidence": brain_result.confidence,
                "model": brain_result.model_name,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ── Conversation History ──────────────────────────────────────────────
_conversation_store: dict[str, list[dict]] = {}  # session_id -> messages


class HistoryRequest(BaseModel):
    session_id: str
    limit: int = 50


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]
    total: int


@router.post("/chat/history")
async def get_conversation_history(req: HistoryRequest):
    """Get conversation history for a session."""
    messages = _conversation_store.get(req.session_id, [])[-req.limit:]
    return HistoryResponse(
        session_id=req.session_id,
        messages=messages,
        total=len(_conversation_store.get(req.session_id, [])),
    )


class HistoryStoreRequest(BaseModel):
    session_id: str
    role: str
    content: str


@router.post("/chat/history/store")
async def store_message(req: HistoryStoreRequest):
    """Store a message in conversation history."""
    if req.session_id not in _conversation_store:
        _conversation_store[req.session_id] = []
    _conversation_store[req.session_id].append({
        "role": req.role,
        "content": req.content,
        "timestamp": time.time(),
    })
    return {"status": "stored", "total": len(_conversation_store[req.session_id])}


import time
