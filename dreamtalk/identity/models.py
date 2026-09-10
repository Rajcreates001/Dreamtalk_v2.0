from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class AppearanceProfile(BaseModel):
    face_embedding: list[float] = []
    face_mesh: list[list[float]] = []
    head_pose: dict[str, float] = {}
    expression_library: dict[str, list[float]] = {}
    hair_model: dict[str, Any] = {}
    skin_profile: dict[str, Any] = {}
    eye_profile: dict[str, Any] = {}
    mouth_profile: dict[str, Any] = {}
    landmarks: list[list[float]] = []
    identity_vector: list[float] = []
    quality_score: float = 0.0
    capture_type: str = "upload"
    source_media: list[str] = []
    reconstructed_3d_mesh_url: Optional[str] = None
    blendshapes: dict[str, float] = {}


class VoiceProfile(BaseModel):
    voice_embedding: list[float] = []
    voice_samples: list[str] = []
    speaking_style: str = "conversational"
    accent: str = "neutral"
    language: str = "en"
    pitch_range: dict[str, float] = {}
    rhythm_profile: dict[str, Any] = {}
    pause_pattern: dict[str, Any] = {}
    cloned_voice_id: Optional[str] = None


class BigFiveTraits(BaseModel):
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.3


class PersonalityProfile(BaseModel):
    big_five: BigFiveTraits = BigFiveTraits()
    communication_style: str = "neutral"
    humor: float = 0.4
    professionalism: float = 0.7
    empathy: float = 0.7
    leadership: float = 0.5
    creativity: float = 0.5
    patience: float = 0.7


class KnowledgeIndex(BaseModel):
    sources: list[str] = []
    indexed_documents: list[str] = []
    embedding_model: str = "bge-m3"


class MemoryState(BaseModel):
    recent_context: dict[str, Any] = {}
    facts: list[str] = []
    preferences: dict[str, Any] = {}
    corrections: dict[str, Any] = {}
    relationship: dict[str, Any] = {}


class EvolutionMeta(BaseModel):
    version: str = "1.0.0"
    previous_versions: list[str] = []
    last_evolved: Optional[str] = None
    evolution_count: int = 0
    interaction_count: int = 0


class BehaviorProfile(BaseModel):
    greeting_style: str = "formal"
    response_length: str = "medium"
    interruption_tolerance: float = 0.3
    small_talk_affinity: float = 0.6


class IdentityProfile(BaseModel):
    id: str = ""
    user_id: str = ""
    custom_dh_id: str = ""
    identity_version: str = "1.0.0"
    appearance: AppearanceProfile = AppearanceProfile()
    voice: VoiceProfile = VoiceProfile()
    personality: PersonalityProfile = PersonalityProfile()
    knowledge: KnowledgeIndex = KnowledgeIndex()
    memory: MemoryState = MemoryState()
    evolution: EvolutionMeta = EvolutionMeta()
    behavior: BehaviorProfile = BehaviorProfile()
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def blank(cls, user_id: str, custom_dh_id: str) -> IdentityProfile:
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            custom_dh_id=custom_dh_id,
            created_at=now,
            updated_at=now,
        )


class EvolutionDelta(BaseModel):
    id: str = ""
    identity_id: str = ""
    interaction_id: str = ""
    delta_type: str  # "fact", "preference", "correction", "personality_shift", "relationship_update"
    key: str
    old_value: Any = None
    new_value: Any
    confidence: float = 1.0
    source_excerpt: str = ""
    created_at: str = ""


class EvolutionLogEntry(BaseModel):
    id: str = ""
    identity_id: str
    from_version: str
    to_version: str
    deltas: list[EvolutionDelta] = []
    trigger: str = ""  # "post_conversation", "manual_update", "appearance_rebuild"
    summary: str = ""
    created_at: str = ""
