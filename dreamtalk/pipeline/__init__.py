import logging
logger = logging.getLogger("dreamtalk.pipeline")

from dreamtalk.pipeline.models import (
    PipelineRequest, PipelineResult, PipelineStatus,
    FaceAnalysisResult, VoiceAnalysisResult,
    EmotionResult, BrainDecisionResult, ObjectDetectionResult,
    BrainAreaActivation, SpikingActivity,
    PipelineStep, MoodState,
)

try:
    from dreamtalk.pipeline.face_pipeline import FacePipeline
except Exception as e:
    logger.warning(f"FacePipeline import: {e}")
    FacePipeline = None

try:
    from dreamtalk.pipeline.voice_pipeline import VoicePipeline
except Exception as e:
    logger.warning(f"VoicePipeline import: {e}")
    VoicePipeline = None

try:
    from dreamtalk.pipeline.brain_pipeline import BrainPipeline
except Exception as e:
    logger.warning(f"BrainPipeline import: {e}")
    BrainPipeline = None

try:
    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
except Exception as e:
    logger.warning(f"Orchestrator import: {e}")
    PipelineOrchestrator = None

try:
    from dreamtalk.pipeline.animation_pipeline import (
        LivePortraitAnimationPipeline,
        check_liveportrait_ready,
        animate_from_video,
        animate_from_image,
    )
except Exception as e:
    logger.warning(f"AnimationPipeline import: {e}")
    LivePortraitAnimationPipeline = None
    check_liveportrait_ready = None
    animate_from_video = None
    animate_from_image = None

__all__ = [
    "PipelineRequest", "PipelineResult", "PipelineStatus",
    "FaceAnalysisResult", "VoiceAnalysisResult",
    "EmotionResult", "BrainDecisionResult", "ObjectDetectionResult",
    "BrainAreaActivation", "SpikingActivity", "PipelineStep", "MoodState",
    "FacePipeline", "VoicePipeline", "BrainPipeline", "PipelineOrchestrator",
]
