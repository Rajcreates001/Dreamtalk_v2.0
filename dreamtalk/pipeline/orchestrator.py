"""Master Pipeline Orchestrator — ties Face + Voice + Brain + Animation into a single end-to-end flow."""

import asyncio
import json
import logging
import os
import time
import traceback
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

import numpy as np

from dreamtalk.pipeline.models import (
    PipelineRequest,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    FaceAnalysisResult,
    VoiceAnalysisResult,
    EmotionResult,
    BrainDecisionResult,
    ObjectDetectionResult,
)
from dreamtalk.pipeline.face_pipeline import FacePipeline
from dreamtalk.pipeline.voice_pipeline import VoicePipeline
from dreamtalk.pipeline.brain_pipeline import BrainPipeline
from dreamtalk.pipeline.lipsync_pipeline import get_lipsync_pipeline
from dreamtalk.pipeline.emotion_animation import get_emotion_animation_mapper

logger = logging.getLogger("dreamtalk.pipeline.orchestrator")


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.bool_, np.bool)):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

try:
    from dreamtalk.backend.db.database import execute, fetchrow
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

try:
    from dreamtalk.media.repository import MediaRepository
    MEDIA_REPO_AVAILABLE = True
except ImportError:
    MEDIA_REPO_AVAILABLE = False


class PipelineOrchestrator:
    """Orchestrates the complete end-to-end Digital Twin pipeline.

    Flow:
      1. Face: upload image → detect face → landmarks → 3D mesh → emotion → store
      2. Voice: upload voice → analyze → clone → TTS → store
      3. Brain: text → emotion → decision/response → store
      4. Object Detection: image → detect objects → store
      5. Save all results to DB + media repository
    """

    def __init__(self, api_endpoint: str = None):
        self.face_pipeline = FacePipeline()
        self.voice_pipeline = VoicePipeline()
        self.brain_pipeline = BrainPipeline(api_endpoint)
        self.media_repo = MediaRepository() if MEDIA_REPO_AVAILABLE else None

    async def run_full_pipeline(self, request: PipelineRequest) -> PipelineResult:
        """Run the complete pipeline across all enabled modules."""
        pipeline_id = uuid.uuid4().hex
        result = PipelineResult(
            pipeline_id=pipeline_id,
            twin_id=request.twin_id,
            status=PipelineStatus.RUNNING,
        )
        steps = []
        errors = []

        twin_id = request.twin_id or pipeline_id
        role = request.role

        # Ensure output dirs exist
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "pipeline_outputs", pipeline_id,
        )
        os.makedirs(output_dir, exist_ok=True)

        # Create media repo folders if twin_id provided
        if self.media_repo and twin_id:
            try:
                self.media_repo.create_twin_folders(twin_id, role)
            except Exception as e:
                logger.warning(f"Media repo folder creation failed (non-fatal): {e}")

        # ── Step 1: Face Analysis ──────────────────────────────────────────
        if request.image_paths and request.enable_3d_face:
            step_start = time.time()
            step = PipelineStep(step=1, name="face_analysis", status="running", started_at=datetime.utcnow().isoformat())
            try:
                face_result = await self.face_pipeline.run(
                    request.image_paths,
                    output_dir=os.path.join(output_dir, "face"),
                )
                result.face_result = face_result

                # Save to media repo
                if self.media_repo and twin_id and face_result.mesh_3d_path and os.path.exists(face_result.mesh_3d_path):
                    try:
                        with open(face_result.mesh_3d_path, "rb") as f:
                            content = f.read()
                        asset = await self.media_repo.store_file(
                            twin_id=twin_id, role=role,
                            category="face/3d_mesh",
                            filename=os.path.basename(face_result.mesh_3d_path),
                            content=content,
                            metadata={"processing_step": "face_3d_mesh", "pipeline_id": pipeline_id},
                        )
                        step.data = {"media_asset_id": asset.asset_id}
                    except Exception as e:
                        logger.warning(f"Media repo save failed (non-fatal): {e}")

                step.status = "completed"
                step.data = step.data or {}
                step.data.update({
                    "face_detected": face_result.face_detected,
                    "face_count": face_result.face_count,
                    "quality_score": face_result.quality_score,
                    "mesh_generated": face_result.mesh_3d_path is not None,
                })
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                errors.append(f"Face pipeline failed: {e}")
            step.completed_at = datetime.utcnow().isoformat()
            steps.append(step)

        # ── Step 2: Voice Analysis ─────────────────────────────────────────
        if request.voice_paths and request.enable_voice_clone:
            step_start = time.time()
            step = PipelineStep(step=2, name="voice_analysis", status="running", started_at=datetime.utcnow().isoformat())
            try:
                voice_result = await self.voice_pipeline.run(
                    request.voice_paths,
                    text_input=request.text_input,
                    output_dir=os.path.join(output_dir, "voice"),
                )
                result.voice_result = voice_result

                if self.media_repo and twin_id:
                    for attr, category in [("cloned_voice_path", "voice/cloned"), ("tts_sample_path", "voice/tts")]:
                        path = getattr(voice_result, attr, None)
                        if path and os.path.exists(path):
                            try:
                                with open(path, "rb") as f:
                                    content = f.read()
                                await self.media_repo.store_file(
                                    twin_id=twin_id, role=role,
                                    category=category,
                                    filename=os.path.basename(path),
                                    content=content,
                                    metadata={"processing_step": attr, "pipeline_id": pipeline_id},
                                )
                            except Exception as e:
                                logger.warning(f"Media repo save failed for {attr}: {e}")

                step.status = "completed"
                step.data = {
                    "voice_detected": voice_result.voice_detected,
                    "duration": voice_result.duration_seconds,
                    "cloned": voice_result.cloned_voice_path is not None,
                    "tts_generated": voice_result.tts_sample_path is not None,
                }
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                errors.append(f"Voice pipeline failed: {e}")
            step.completed_at = datetime.utcnow().isoformat()
            steps.append(step)

        # ── Step 3: Emotion Detection ──────────────────────────────────────
        if request.text_input and request.enable_emotion:
            step_start = time.time()
            step = PipelineStep(step=3, name="emotion_detection", status="running", started_at=datetime.utcnow().isoformat())
            try:
                emotion_result = await self.brain_pipeline.detect_emotion(request.text_input)
                result.emotion_result = emotion_result

                # ── WIRE: Fuse brain emotion into voice pipeline ──────────
                # If both voice and text emotion are available, fuse them into
                # a more accurate ensemble emotion profile.
                fusion_details = None
                # Use result.voice_result (safe default None) rather than
                # the bare voice_result local (may not exist if Step 2 skipped)
                _vr = result.voice_result
                if _vr is not None and emotion_result is not None \
                        and _vr.voice_detected:
                    try:
                        fused_emotion = self.voice_pipeline.fuse_emotion_profiles(
                            _vr, emotion_result
                        )
                        result.emotion_result = fused_emotion
                        logger.info(f"Emotion fusion: voice→text ensemble complete "
                                    f"(fused={_vr.emotion_from_voice})")
                        fusion_details = {
                            "voice_mood": _vr.emotion_from_voice_scores["voice"]["mood"],
                            "text_mood": _vr.emotion_from_voice_scores["text"]["mood"],
                            "fused_mood": _vr.emotion_from_voice_scores["fused"]["mood"],
                            "fusion_weights": {
                                "voice": _vr.emotion_from_voice_scores["voice"]["weight"],
                                "text": _vr.emotion_from_voice_scores["text"]["weight"],
                            },
                        }
                    except Exception as fuse_err:
                        logger.warning(f"Emotion fusion skipped (non-fatal): {fuse_err}")

                step.status = "completed"
                step.data = {
                    "primary_mood": emotion_result.primary_mood.value if emotion_result else "unknown",
                    "valence": emotion_result.valence if emotion_result else 0.0,
                    "intensity": emotion_result.intensity if emotion_result else "low",
                    "is_hostile": emotion_result.is_hostile if emotion_result else False,
                    "confidence": emotion_result.confidence if emotion_result else 0.0,
                }
                if fusion_details:
                    step.data["fusion"] = fusion_details
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                errors.append(f"Emotion detection failed: {e}")
            step.completed_at = datetime.utcnow().isoformat()
            steps.append(step)

        # ── Step 4: Brain Decision / Response ──────────────────────────────
        if request.text_input and request.enable_decision:
            step_start = time.time()
            step = PipelineStep(step=4, name="brain_decision", status="running", started_at=datetime.utcnow().isoformat())
            try:
                brain_result = await self.brain_pipeline.make_decision(
                    text=request.text_input,
                    role=role,
                    emotion=result.emotion_result,
                    model_name=request.model_name,
                )
                result.brain_result = brain_result

                # Save decision to DB
                if DB_AVAILABLE and twin_id:
                    try:
                        await execute("""
                            INSERT INTO pipeline_results
                            (pipeline_id, twin_id, step_name, result_type, result_data, created_at)
                            VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
                            ON CONFLICT DO NOTHING
                        """, pipeline_id, twin_id, "brain_decision", "brain_decision",
                            json.dumps(brain_result.model_dump()))
                    except Exception as e:
                        logger.warning(f"DB save failed (non-fatal): {e}")

                step.status = "completed"
                step.data = {
                    "response_length": len(brain_result.response_text),
                    "confidence": brain_result.confidence,
                    "decision_type": brain_result.decision_type,
                    "processing_time_ms": brain_result.processing_time_ms,
                }
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                errors.append(f"Brain decision failed: {e}")
            step.completed_at = datetime.utcnow().isoformat()
            steps.append(step)

        # ── Step 5: Facial Animation via LivePortrait ────────────────────────
        if request.image_paths and request.enable_animation:
            step_start = time.time()
            step = PipelineStep(step=5, name="facial_animation", status="running", started_at=datetime.utcnow().isoformat())
            try:
                from dreamtalk.pipeline.animation_pipeline import LivePortraitAnimationPipeline, check_liveportrait_ready

                anim_status = check_liveportrait_ready()
                if anim_status["ready"]:
                    anim_pipeline = LivePortraitAnimationPipeline()

                    # If we have a driving video, use it; otherwise animate with emotion
                    driving_video = None
                    if hasattr(request, 'driving_video_path') and request.driving_video_path:
                        driving_video = request.driving_video_path

                    animation_dir = os.path.join(output_dir, "animation")
                    os.makedirs(animation_dir, exist_ok=True)

                    if driving_video and os.path.exists(driving_video):
                        anim_result = anim_pipeline.drive_from_video(
                            source_image_path=request.image_paths[0],
                            driving_video_path=driving_video,
                            output_dir=animation_dir,
                        )
                    elif result.emotion_result:
                        emotion_label = result.emotion_result.primary_mood.value
                        anim_result = anim_pipeline.drive_from_emotion(
                            source_image_path=request.image_paths[0],
                            output_dir=animation_dir,
                            emotion_label=emotion_label,
                        )
                    else:
                        anim_result = anim_pipeline.drive_from_image(
                            source_image_path=request.image_paths[0],
                            driving_image_path=request.image_paths[0],
                            output_dir=animation_dir,
                        )

                    result.animation_result = anim_result

                    step.status = "completed"
                    step.data = {
                        "video_path": anim_result.get("video_path"),
                        "frame_count": anim_result.get("frame_count", 0),
                        "status": anim_result.get("status"),
                    }
                else:
                    step.status = "skipped"
                    step.data = {"reason": "LivePortrait weights not ready", "details": anim_status}

            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                errors.append(f"Facial animation failed: {e}")
            step.completed_at = datetime.utcnow().isoformat()
            steps.append(step)

        # ── Step 6: Object Detection ───────────────────────────────────────
        if request.image_paths and request.enable_object_detection:
            step_start = time.time()
            step = PipelineStep(step=6, name="object_detection", status="running", started_at=datetime.utcnow().isoformat())
            try:
                obj_results = []
                for img_path in request.image_paths:
                    obj = await self.brain_pipeline.detect_objects(img_path)
                    obj_results.append(obj)
                result.object_result = obj_results[0] if obj_results else ObjectDetectionResult()

                # Save annotated image
                if obj_results and obj_results[0].objects_detected and os.path.exists(request.image_paths[0]):
                    try:
                        import cv2
                        img = cv2.imread(request.image_paths[0])
                        for det in obj_results[0].objects_detected:
                            bbox = det.get("bbox", [0, 0, 0, 0])
                            label = det.get("label", "object")
                            if len(bbox) == 4:
                                cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                                cv2.putText(img, label, (bbox[0], bbox[1] - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        annotated_path = os.path.join(output_dir, "objects", "annotated.jpg")
                        os.makedirs(os.path.dirname(annotated_path), exist_ok=True)
                        cv2.imwrite(annotated_path, img)
                        result.object_result.processed_image_path = annotated_path
                    except Exception as e:
                        logger.warning(f"Annotated image save failed: {e}")

                step.status = "completed"
                step.data = {
                    "objects_found": result.object_result.object_count,
                    "labels": result.object_result.labels,
                }
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                errors.append(f"Object detection failed: {e}")
            step.completed_at = datetime.utcnow().isoformat()
            steps.append(step)

        # ── Step 6: Persist Pipeline Record ────────────────────────────────
        if DB_AVAILABLE and twin_id:
            try:
                payload = {
                    "face": result.face_result.model_dump() if result.face_result else None,
                    "voice": result.voice_result.model_dump() if result.voice_result else None,
                    "emotion": result.emotion_result.model_dump() if result.emotion_result else None,
                    "brain": result.brain_result.model_dump() if result.brain_result else None,
                    "animation": result.animation_result.model_dump() if result.animation_result else None,
                    "objects": result.object_result.model_dump() if result.object_result else None,
                    "steps": [s.model_dump() for s in steps],
                    "errors": errors,
                }
                await execute("""
                    INSERT INTO pipeline_results
                    (pipeline_id, twin_id, step_name, result_type, result_data, created_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
                    ON CONFLICT DO NOTHING
                """, pipeline_id, twin_id, "pipeline_complete", "pipeline_result",
                    json.dumps(payload, cls=_NumpyEncoder))
            except Exception as e:
                logger.warning(f"Final pipeline DB save failed: {e}")

        # ── Finalize ───────────────────────────────────────────────────────
        result.steps = steps
        result.completed_at = datetime.utcnow().isoformat()

        if errors:
            result.status = PipelineStatus.PARTIAL
            result.error = "; ".join(errors[:3])
        else:
            result.status = PipelineStatus.COMPLETED

        logger.info(f"Pipeline {pipeline_id} complete: {result.status.value} "
                    f"({len(steps)} steps, {len(errors)} errors)")

        return result

    async def run_face_only(self, request: PipelineRequest) -> FaceAnalysisResult:
        """Run only the face analysis pipeline."""
        if not request.image_paths:
            return FaceAnalysisResult(error="No image paths provided")
        return await self.face_pipeline.run(request.image_paths)

    async def run_voice_only(self, request: PipelineRequest) -> VoiceAnalysisResult:
        """Run only the voice analysis pipeline."""
        if not request.voice_paths:
            return VoiceAnalysisResult(error="No voice paths provided")
        return await self.voice_pipeline.run(request.voice_paths, request.text_input)

    async def run_decision_only(self, request: PipelineRequest) -> dict:
        """Run only the brain/decision pipeline."""
        return await self.brain_pipeline.run(
            text_input=request.text_input,
            role=request.role,
            image_paths=request.image_paths,
            model_name=request.model_name,
            enable_emotion=request.enable_emotion,
            enable_decision=request.enable_decision,
            enable_object_detection=request.enable_object_detection,
        )

    async def run_full_avatar_pipeline(self, text: str, role: str = "normal_user") -> Dict:
        """Full avatar pipeline: text → brain → emotion → TTS → lip sync → animation params."""
        import time
        start = time.time()
        result = {}

        # Step 1: Brain processing
        brain_result = await self.brain_pipeline.make_decision(
            text=text, role=role, model_name="deepseek-r1:7b"
        )
        result["brain"] = brain_result

        # Step 2: Emotion detection
        emotion = await self.brain_pipeline.detect_emotion(text)
        result["emotion"] = emotion

        # Step 3: Map emotion to avatar expression
        mapper = get_emotion_animation_mapper()
        expression = mapper.map_emotion(
            primary_mood=emotion.primary_mood.value,
            valence=emotion.valence,
            arousal=emotion.arousal,
            dominance=emotion.dominance,
            intensity_score=emotion.intensity_score,
        )
        result["expression"] = expression.to_dict()

        # Step 4: TTS generation
        try:
            tts_result = await self._generate_tts(
                text=brain_result.response_text,
                emotion=emotion,
            )
            result["tts"] = tts_result

            # Step 5: Lip sync from TTS audio
            if tts_result and tts_result.get("audio_path"):
                lipsync = get_lipsync_pipeline()
                lip_result = lipsync.extract_from_audio(
                    tts_result["audio_path"],
                    emotion={"primary_mood": emotion.primary_mood.value, "arousal": emotion.arousal},
                )
                result["lipsync"] = lip_result.to_dict()
        except Exception as e:
            logger.warning(f"TTS/LipSync failed: {e}")
            result["tts"] = {"error": str(e)}
            result["lipsync"] = {"error": str(e)}

        result["processing_time_ms"] = round((time.time() - start) * 1000, 2)
        return result

    async def _generate_tts(self, text: str, emotion) -> Dict:
        """Generate TTS audio from response text."""
        try:
            voice_pipeline = VoicePipeline()
            output_dir = os.path.join("pipeline_outputs", "tts")
            os.makedirs(output_dir, exist_ok=True)

            audio_path, tts_info = voice_pipeline.generate_tts(
                text=text,
                output_dir=output_dir,
                emotion=emotion.primary_mood.value if emotion else "neutral",
            )
            return {"audio_path": audio_path, **tts_info}
        except Exception as e:
            logger.warning(f"TTS generation failed: {e}")
            return {"error": str(e)}
