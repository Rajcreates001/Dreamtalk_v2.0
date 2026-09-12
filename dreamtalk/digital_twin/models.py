from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────

class TwinRole(str, Enum):
    PERSONAL = "personal"
    HEALTHCARE = "healthcare"
    BUSINESS = "business"


class TwinStatus(str, Enum):
    DRAFT = "draft"
    APPEARANCE_COMPLETE = "appearance_complete"
    VOICE_COMPLETE = "voice_complete"
    PERSONALITY_COMPLETE = "personality_complete"
    INTELLIGENCE_COMPLETE = "intelligence_complete"
    PUBLISHED = "published"


class PipelineStatus(str, Enum):
    """Pipeline step status. Canonical values: pending, processing, complete, failed.
    Additional aliases for backward compatibility with existing DB data.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"  # Canonical "success" value
    FAILED = "failed"
    # ── DB backward-compat aliases ──
    COMPLETED = "completed"
    CLONED = "cloned"
    SYNTHETIC = "synthetic"
    NO_FACE = "no_face_detected"


class RelationshipType(str, Enum):
    FRIEND = "friend"
    FATHER = "father"
    MOTHER = "mother"
    BROTHER = "brother"
    SISTER = "sister"
    PARTNER = "partner"
    MENTOR = "mentor"
    TEACHER = "teacher"
    COACH = "coach"
    THERAPIST = "therapist"
    CUSTOM = "custom"


class KnowledgeSourceType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    URL = "url"
    GOOGLE_DRIVE = "googledrive"
    NOTION = "notion"
    ONEDRIVE = "onedrive"
    SHAREPOINT = "sharepoint"
    GITHUB = "github"
    CONFLUENCE = "confluence"
    SLACK = "slack"
    TEAMS = "teams"
    API = "api"
    DATABASE = "database"
    PLAINTEXT = "plaintext"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    SCANNED_DOC = "scanned_doc"
    FHIR = "fhir"
    HL7 = "hl7"
    CUSTOM = "custom"


class ObservationType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    CORRECTION = "correction"
    PERSONALITY_SIGNAL = "personality_signal"
    RELATIONSHIP_UPDATE = "relationship_update"
    COMMUNICATION_STYLE = "communication_style"
    EMOTIONAL_SIGNAL = "emotional_signal"
    BEHAVIORAL_PATTERN = "behavioral_pattern"


# ─── Step 1: Digital Identity ───────────────────────────────────────────────

class CreateDigitalTwinRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    category: str = "personal"
    language: str = "en"
    timezone: str = "UTC"
    visibility: str = "private"
    role: TwinRole = TwinRole.PERSONAL
    avatar_image: Optional[str] = None


class UpdateDigitalTwinRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    visibility: Optional[str] = None
    avatar_image_url: Optional[str] = None


# ─── Step 2: Appearance ──────────────────────────────────────────────────────

class AppearanceProfile(BaseModel):
    source_media: list[str] = []
    validated_frames: list[str] = []
    face_detected: bool = False
    face_count: int = 0
    face_bbox: Optional[list[float]] = None
    face_confidence: float = 0.0
    landmarks_2d: list[list[float]] = []
    landmarks_3d: list[list[float]] = []
    blendshapes: dict[str, float] = {}
    head_pose: dict[str, float] = {}
    face_embedding: list[float] = []
    identity_vector: list[float] = []
    quality_score: float = 0.0
    lighting_quality: float = 0.0
    background_removed: bool = False
    aligned: bool = False
    expression_library: dict[str, list[float]] = {}
    facial_motion_data: Optional[dict[str, Any]] = None
    reconstructed_3d_mesh_url: Optional[str] = None
    preview_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    skin_profile: dict[str, Any] = {}
    eye_profile: dict[str, Any] = {}
    mouth_profile: dict[str, Any] = {}
    hair_profile: dict[str, Any] = {}
    analysis_log: list[dict[str, Any]] = []
    processing_time_ms: int = 0


# ─── Step 3: Voice ───────────────────────────────────────────────────────────

class VoiceSampleInfo(BaseModel):
    file_path: str = ""
    original_name: str = ""
    duration_seconds: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    quality_score: float = 0.0
    noise_level: float = 0.0
    language: str = ""
    accent: str = ""
    speaker_match: bool = False
    speaker_confidence: float = 0.0
    speech_rate_wpm: float = 0.0
    prosody_features: dict[str, Any] = {}
    # Analysis blobs, not pure float maps: `emotion_profile` carries a string
    # `label` and `pitch_stats` a `quartiles` list. Declaring them as
    # dict[str, float] made GET /voice/result raise a ValidationError (500),
    # which surfaced in the UI as "Failed to fetch" and blocked create-twin.
    emotion_profile: dict[str, Any] = {}
    pitch_stats: dict[str, Any] = {}


class SynthesizedVoiceConfig(BaseModel):
    gender: str = "neutral"
    age: str = "adult"
    language: str = "en"
    accent: str = "neutral"
    pitch: float = 1.0
    speed: float = 1.0
    warmth: float = 0.7
    emotional_tone: str = "neutral"
    style: str = "conversational"


class VoiceProfile(BaseModel):
    source_samples: list[VoiceSampleInfo] = []
    cloned_voice_id: Optional[str] = None
    synthetic_voice_id: Optional[str] = None
    voice_embedding: list[float] = []
    is_cloned: bool = False
    is_synthetic: bool = False
    speaking_style: str = "conversational"
    accent: str = "neutral"
    language: str = "en"
    speech_rate_wpm: float = 150.0
    pitch_range: dict[str, float] = {}
    rhythm_profile: dict[str, Any] = {}
    pause_pattern: dict[str, Any] = {}
    preview_audio_url: Optional[str] = None
    quality_score: float = 0.0
    processing_log: list[dict[str, Any]] = []


# ─── Step 4: Personality (Structured Traits) ─────────────────────────────────

class PersonalityProfile(BaseModel):
    empathy: float = 0.5
    professionalism: float = 0.7
    humor: float = 0.4
    creativity: float = 0.5
    confidence: float = 0.6
    patience: float = 0.7
    friendliness: float = 0.7
    leadership: float = 0.5
    curiosity: float = 0.6
    formality: float = 0.5
    optimism: float = 0.6
    emotional_stability: float = 0.7
    communication_style: str = "balanced"
    response_length_preference: str = "medium"
    small_talk_affinity: float = 0.5
    interruption_tolerance: float = 0.3
    topic_change_style: str = "smooth"


# ─── Step 5: Role-Specific Intelligence ──────────────────────────────────────

# Personal
class RelationshipConfig(BaseModel):
    relationship_type: RelationshipType = RelationshipType.FRIEND
    custom_type_label: str = ""
    preferred_greeting: str = "Hey"
    nickname: str = ""
    relationship_goal: str = ""
    favorite_topics: list[str] = []
    shared_interests: list[str] = []
    conversation_style: str = "casual"
    communication_preferences: dict[str, Any] = {}
    special_dates: dict[str, str] = {}
    memory_preferences: dict[str, Any] = {}


# Healthcare / Business
class KnowledgeSourceEntry(BaseModel):
    id: str = ""
    source_type: KnowledgeSourceType
    source_name: str
    original_filename: str = ""
    file_path: str = ""
    file_size: int = 0
    mime_type: str = ""
    status: str = "uploaded"
    page_count: int = 0
    word_count: int = 0
    chunk_count: int = 0
    error_message: str = ""
    created_at: str = ""

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)


class KnowledgeChunk(BaseModel):
    id: str = ""
    source_id: str
    twin_id: str = ""
    chunk_index: int
    content: str
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = {}


class IntelligenceConfig(BaseModel):
    role: TwinRole
    relationship: Optional[RelationshipConfig] = None
    knowledge_sources: list[KnowledgeSourceEntry] = []
    total_chunks: int = 0
    indexed: bool = False
    knowledge_status: str = "not_started"
    knowledge_summary: str = ""


# ─── Digital Twin ────────────────────────────────────────────────────────────

class DigitalTwinResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str = ""
    category: str = "personal"
    language: str = "en"
    timezone: str = "UTC"
    visibility: str = "private"
    role: TwinRole
    status: TwinStatus
    avatar_image_url: Optional[str] = None

    appearance: AppearanceProfile = AppearanceProfile()
    appearance_status: PipelineStatus = PipelineStatus.PENDING
    appearance_preview_url: Optional[str] = None

    voice: VoiceProfile = VoiceProfile()
    voice_status: PipelineStatus = PipelineStatus.PENDING
    voice_preview_url: Optional[str] = None

    personality: PersonalityProfile = PersonalityProfile()
    personality_status: PipelineStatus = PipelineStatus.PENDING

    intelligence: IntelligenceConfig = Field(default_factory=lambda: IntelligenceConfig(role=TwinRole.PERSONAL))
    intelligence_status: PipelineStatus = PipelineStatus.PENDING

    twin_version: str = "1.0.0"
    interaction_count: int = 0
    evolution_count: int = 0
    last_interaction: Optional[str] = None

    custom_dh_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    published_at: Optional[str] = None


class LearningObservation(BaseModel):
    id: str = ""
    twin_id: str
    observation_type: ObservationType
    key: str
    value: str
    confidence: float = 0.3
    source: str = "conversation"
    source_excerpt: str = ""
    is_reviewed: bool = False
    is_confirmed: bool = False
    created_at: str = ""
    confirmed_at: Optional[str] = None


class TwinStatusResponse(BaseModel):
    id: str
    name: str
    role: TwinRole
    status: TwinStatus
    steps: dict[str, str]  # step_name -> status
    twin_version: str
    interaction_count: int
    evolution_count: int
    published: bool
    created_at: str
    updated_at: str
