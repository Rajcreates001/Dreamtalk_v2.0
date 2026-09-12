from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List

from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class EmotionModel(str, Enum):
    VADER = "vader"
    DEEP_AFFECT = "deep_affect"
    FACIAL = "facial"
    ENSEMBLE = "ensemble"


class MoodState(str, Enum):
    CALM = "calm"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"
    ANXIOUS = "anxious"
    CONTENT = "content"
    FRUSTRATED = "frustrated"
    FURIOUS = "furious"
    DEFENSIVE = "defensive"
    ANNOYED = "annoyed"
    PLAYFUL = "playful"
    SARCASTIC = "sarcastic"
    LOVING = "loving"
    HOPEFUL = "hopeful"
    GRATEFUL = "grateful"
    EMBARRASSED = "embarrassed"
    CONFUSED = "confused"
    TRUSTING = "trusting"
    ANTICIPATORY = "anticipatory"


class BrainAreaActivation(BaseModel):
    area: str
    firing_rate_hz: float = 0.0
    membrane_potential: float = 0.0
    spike_count: int = 0
    synchrony: float = 0.0
    learning_rate: float = 0.0
    dopamine_modulation: float = 0.0


class SpikingActivity(BaseModel):
    total_firing_rate_hz: float = 0.0
    average_membrane_potential: float = 0.0
    network_synchrony: float = 0.0
    inhibitory_excitatory_ratio: float = 1.0
    theta_band_power: float = 0.0
    gamma_band_power: float = 0.0
    spike_time_entropy: float = 0.0
    burst_detection: bool = False
    population_codes: dict = Field(default_factory=dict)


class PipelineStep(BaseModel):
    step: int
    name: str
    status: str
    data: Optional[dict] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class FaceAnalysisResult(BaseModel):
    face_detected: bool = False
    face_count: int = 0
    detection_backend: str = "none"

    super_resolution_applied: bool = False
    super_resolution_factor: float = 1.0
    image_enhancement_applied: bool = False
    image_enhancement_engine: Optional[str] = None
    original_image_quality: str = "unknown"

    landmarks: Optional[list] = None
    landmark_count: int = 0
    landmark_backend: str = "none"

    mediapipe_blendshapes: Optional[dict] = None
    blendshape_count: int = 0

    flame_expression_coeffs: Optional[list] = None
    flame_jaw_pose: Optional[list] = None
    flame_eye_pose: Optional[list] = None

    face_embedding: Optional[list] = None
    embedding_model: str = "unavailable"
    embedding_dim: int = 0

    head_pose: Optional[dict] = None
    head_pose_confidence: float = 0.0

    emotion_from_face: Optional[str] = None
    emotion_confidence: float = 0.0
    emotion_scores: Optional[dict] = None

    mesh_3d_path: Optional[str] = None
    mesh_glb_path: Optional[str] = None
    mesh_vertex_count: int = 0
    mesh_face_count: int = 0
    mesh_format: str = "obj"
    # Morph targets baked into the GLB (visemes/blink/emotions) — empty when
    # the mesh is not FLAME topology, which is what gates `arkit_blendshapes`.
    mesh_blendshape_names: List[str] = Field(default_factory=list)

    texture_path: Optional[str] = None
    texture_mapped: bool = False

    identity_embedding: Optional[list] = None
    identity_confidence: float = 0.0

    quality_score: float = 0.0
    quality_factors: Optional[dict] = None

    error: Optional[str] = None


class VoiceAnalysisResult(BaseModel):
    voice_detected: bool = False
    voice_activity_frames: int = 0
    voice_activity_ratio: float = 0.0

    duration_seconds: float = 0.0
    sample_rate: int = 0
    bit_depth: int = 16
    channels: int = 1

    enhancement_applied: bool = False
    noise_reduction_db: float = 0.0
    snr_estimate: float = 0.0

    pitch_mean: float = 0.0
    pitch_std: float = 0.0
    pitch_median: float = 0.0
    pitch_quartiles: Optional[list] = None
    pitch_contour: Optional[list] = None
    vibrato_rate: float = 0.0
    vibrato_extent: float = 0.0

    energy_mean: float = 0.0
    energy_std: float = 0.0
    energy_envelope: Optional[list] = None

    spectral_centroid_mean: float = 0.0
    spectral_bandwidth: float = 0.0
    spectral_rolloff: float = 0.0
    spectral_contrast: Optional[list] = None
    mfccs_mean: Optional[list] = None
    mfccs_covariance: Optional[list] = None
    formant_frequencies: Optional[list] = None
    formant_bandwidths: Optional[list] = None

    jitter_local: float = 0.0
    jitter_rap: float = 0.0
    jitter_ppq5: float = 0.0
    shimmer_local: float = 0.0
    shimmer_apq3: float = 0.0
    shimmer_apq5: float = 0.0
    harmonicity_hnr: float = 0.0

    speaking_rate: float = 0.0
    words_per_minute: float = 0.0
    pause_duration_mean: float = 0.0
    pause_count: int = 0

    voice_embedding: Optional[list] = None
    embedding_dim: int = 256
    embedding_model: str = "wavlm"

    timbre_embedding: Optional[list] = None
    timbre_similarity_to_source: float = 0.0

    gender_prediction: Optional[str] = None
    age_prediction: Optional[float] = None
    emotion_from_voice: Optional[str] = None
    emotion_from_voice_scores: Optional[dict] = None

    cloned_voice_path: Optional[str] = None
    clone_method: str = "none"
    clone_confidence: float = 0.0
    clone_speaker_id: Optional[str] = None

    tts_sample_path: Optional[str] = None
    tts_method: str = "none"
    tts_duration_seconds: float = 0.0

    # ── Diarization (multi-speaker detection) ──
    speaker_count: int = 0
    speaker_segments: list[SpeakerSegment] = Field(default_factory=list)
    speaker_diarization_method: str = "none"

    error: Optional[str] = None


class EmotionResult(BaseModel):
    primary_mood: MoodState = MoodState.NEUTRAL
    secondary_mood: Optional[MoodState] = None
    tertiary_mood: Optional[MoodState] = None
    mood_confidences: Optional[dict] = None

    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    pleasure: float = 0.0

    intensity: str = "low"
    intensity_score: float = 0.0
    is_hostile: bool = False
    hostility_score: float = 0.0
    hostility_triggers: Optional[list] = None

    sentiment_compound: float = 0.0
    sentiment_pos: float = 0.0
    sentiment_neg: float = 0.0
    sentiment_neu: float = 0.0

    ema_valence: float = 0.0
    ema_alpha: float = 0.35
    valence_trend: str = "stable"
    arousal_trend: str = "stable"

    emotion_source: str = "text"
    confidence: float = 0.0

    facial_expression_contribution: Optional[dict] = None
    vocal_emotion_contribution: Optional[dict] = None
    textual_emotion_contribution: Optional[dict] = None
    ensemble_weights: Optional[dict] = None

    pad_activation: Optional[str] = None
    cognitive_appraisal: Optional[str] = None
    action_tendency: Optional[str] = None

    brain_insula_activation: float = 0.0
    brain_amgydala_activation: float = 0.0
    brain_pfc_regulation: float = 0.0


class BrainDecisionResult(BaseModel):
    response_text: str = ""
    response_tone: str = "neutral"
    response_strategy: str = "direct"

    confidence: float = 0.0
    uncertainty: float = 0.0
    entropy: float = 0.0

    reasoning_path: Optional[list] = None
    reasoning_depth: int = 0
    reasoning_framework: str = "rule_based"

    decision_type: str = "response"
    decision_confidence: float = 0.0
    decision_alternatives: Optional[list] = None
    decision_criteria: Optional[dict] = None

    tokens_used: int = 0
    processing_time_ms: float = 0.0
    model_name: str = ""

    brain_region_activations: Optional[list[BrainAreaActivation]] = None
    spiking_activity: Optional[SpikingActivity] = None
    stdp_weight_updates: Optional[dict] = None
    hebbian_trace: Optional[dict] = None

    pfc_output: Optional[list] = None
    dacc_conflict_score: float = 0.0
    insula_emotional_valence: float = 0.0
    ipl_integration: Optional[dict] = None
    basal_ganglia_action: Optional[str] = None
    basal_ganglia_action_value: float = 0.0

    encoding_method: str = "rate"
    encoding_parameters: Optional[dict] = None
    decoded_spike_train: Optional[list] = None

    working_memory_updated: bool = False
    long_term_memory_updated: bool = False
    learning_rule_applied: Optional[str] = None
    synaptic_plasticity_delta: float = 0.0


class SpeakerSegment(BaseModel):
    """A single speaker segment from diarization."""
    speaker_id: str = "speaker_00"
    start_sec: float = 0.0
    end_sec: float = 0.0
    confidence: float = 0.0
    pitch_mean: float = 0.0
    energy_mean: float = 0.0
    spectral_centroid_mean: float = 0.0


class ObjectDetectionResult(BaseModel):
    objects_detected: list = Field(default_factory=list)
    object_count: int = 0
    labels: list = Field(default_factory=list)
    confidence_scores: list = Field(default_factory=list)
    bounding_boxes: Optional[list] = None
    segmentation_masks: Optional[list] = None
    detection_backend: str = "none"

    processed_image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None

    scene_classification: Optional[str] = None
    scene_confidence: float = 0.0

    salient_objects: Optional[list] = None
    object_relationships: Optional[list] = None

    error: Optional[str] = None


class AnimationResult(BaseModel):
    """Result from the LivePortrait facial animation pipeline."""
    video_path: Optional[str] = None
    concat_video_path: Optional[str] = None
    frame_count: int = 0
    fps: float = 0.0
    duration_seconds: float = 0.0
    status: str = "pending"
    output_dir: Optional[str] = None
    emotion_label: Optional[str] = None
    method: str = "none"


class PipelineRequest(BaseModel):
    twin_id: str = ""
    user_id: str = ""
    role: str = "normal_user"
    image_paths: list[str] = Field(default_factory=list)
    voice_paths: list[str] = Field(default_factory=list)
    text_input: str = ""
    knowledge_base_path: Optional[str] = None
    enable_3d_face: bool = True
    enable_voice_clone: bool = True
    enable_emotion: bool = True
    enable_decision: bool = True
    enable_animation: bool = False
    enable_object_detection: bool = False
    enable_super_resolution: bool = True
    enable_audio_enhancement: bool = True
    enable_learning: bool = False
    driving_video_path: Optional[str] = None
    model_name: str = "deepseek"
    snn_encoding: str = "rate"
    snn_timesteps: int = 16
    learning_rate: float = 0.001
    skip_if_no_gpu: bool = False


class PipelineResult(BaseModel):
    pipeline_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    twin_id: str = ""
    status: PipelineStatus = PipelineStatus.PENDING
    steps: list[PipelineStep] = Field(default_factory=list)
    face_result: Optional[FaceAnalysisResult] = None
    voice_result: Optional[VoiceAnalysisResult] = None
    emotion_result: Optional[EmotionResult] = None
    brain_result: Optional[BrainDecisionResult] = None
    animation_result: Optional[AnimationResult] = None
    object_result: Optional[ObjectDetectionResult] = None
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
