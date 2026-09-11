from dreamtalk.pipeline.models import (
    PipelineRequest, PipelineResult, PipelineStatus,
    FaceAnalysisResult, VoiceAnalysisResult,
    EmotionResult, BrainDecisionResult, ObjectDetectionResult,
    BrainAreaActivation, SpikingActivity,
    PipelineStep, MoodState,
)

_LAZY_IMPORTS = {
    "FacePipeline": ("dreamtalk.pipeline.face_pipeline", "FacePipeline"),
    "VoicePipeline": ("dreamtalk.pipeline.voice_pipeline", "VoicePipeline"),
    "BrainPipeline": ("dreamtalk.pipeline.brain_pipeline", "BrainPipeline"),
    "PipelineOrchestrator": ("dreamtalk.pipeline.orchestrator", "PipelineOrchestrator"),
    "LivePortraitAnimationPipeline": ("dreamtalk.pipeline.animation_pipeline", "LivePortraitAnimationPipeline"),
    "check_liveportrait_ready": ("dreamtalk.pipeline.animation_pipeline", "check_liveportrait_ready"),
    "animate_from_video": ("dreamtalk.pipeline.animation_pipeline", "animate_from_video"),
    "animate_from_image": ("dreamtalk.pipeline.animation_pipeline", "animate_from_image"),
}


def __getattr__(name):
    """Load heavyweight CV, speech, and animation modules only when used."""
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    from importlib import import_module

    module = import_module(target[0])
    value = getattr(module, target[1])
    globals()[name] = value
    return value

__all__ = [
    "PipelineRequest", "PipelineResult", "PipelineStatus",
    "FaceAnalysisResult", "VoiceAnalysisResult",
    "EmotionResult", "BrainDecisionResult", "ObjectDetectionResult",
    "BrainAreaActivation", "SpikingActivity", "PipelineStep", "MoodState",
    "FacePipeline", "VoicePipeline", "BrainPipeline", "PipelineOrchestrator",
    "LivePortraitAnimationPipeline", "check_liveportrait_ready",
    "animate_from_video", "animate_from_image",
]
