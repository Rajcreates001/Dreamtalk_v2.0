from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, List
import uuid

from dreamtalk.backend.api.v1.endpoints.auth import get_current_user
from dreamtalk.backend.db.database import fetchrow, execute
from dreamtalk.digital_twin.models import (
    CreateDigitalTwinRequest, UpdateDigitalTwinRequest,
    DigitalTwinResponse, TwinStatus, PipelineStatus, TwinRole,
    RelationshipConfig, SynthesizedVoiceConfig,
    PersonalityProfile, KnowledgeSourceType, ObservationType,
)
from dreamtalk.digital_twin.engine import DigitalTwinEngine
from dreamtalk.digital_twin.appearance import AppearancePipeline
from dreamtalk.digital_twin.voice_cloning import VoicePipeline
from dreamtalk.digital_twin.knowledge import KnowledgeIngestionPipeline
from dreamtalk.digital_twin.learning import ContinuousLearningEngine
from dreamtalk.digital_twin.engine_ext import DigitalTwinEngineExt
from dreamtalk.digital_twin.creation_pipeline import CreationPipeline
from dreamtalk.digital_twin.personality import PersonalityEngine as PersonalityEngineService
from dreamtalk.digital_twin.learning_orchestrator import LearningOrchestrator
from dreamtalk.media.repository import MediaRepository

router = APIRouter(prefix="/api/v1/digital-twins", tags=["Digital Twin Creation Engine"])


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Digital Identity
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("")
async def list_twins(current_user: dict = Depends(get_current_user)):
    twins = await DigitalTwinEngine.get_by_user(current_user["sub"])
    return [t.model_dump() for t in twins]


@router.post("", status_code=201)
async def create_twin(
    req: CreateDigitalTwinRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        twin = await DigitalTwinEngine.create(current_user["sub"], req)
    except Exception as exc:
        # (user_id, name) is unique. Without this the driver's
        # UniqueViolationError escaped as an unhandled 500, which is emitted
        # without CORS headers — so the browser reported a network failure and
        # the UI said "Couldn't reach the backend" for what is really a
        # name clash.
        if "digital_twins_user_id_name_key" in str(exc) or "UniqueViolation" in type(exc).__name__:
            raise HTTPException(
                status_code=409,
                detail=f"You already have a digital twin named '{req.name}'. Pick another name.",
            ) from exc
        raise
    return twin.model_dump()


@router.get("/{twin_id}")
async def get_twin(twin_id: str, current_user: dict = Depends(get_current_user)):
    twin = await DigitalTwinEngine.get(twin_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return twin.model_dump()


@router.put("/{twin_id}")
async def update_twin(
    twin_id: str, req: UpdateDigitalTwinRequest,
    current_user: dict = Depends(get_current_user),
):
    twin = await DigitalTwinEngine.update(twin_id, req)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return twin.model_dump()


@router.delete("/{twin_id}")
async def delete_twin(twin_id: str, current_user: dict = Depends(get_current_user)):
    deleted = await DigitalTwinEngine.delete(twin_id, current_user["sub"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return {"detail": "Digital twin deleted"}


@router.get("/{twin_id}/status")
async def get_twin_status(twin_id: str, current_user: dict = Depends(get_current_user)):
    status = await DigitalTwinEngine.get_status(twin_id)
    if not status:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return status.model_dump()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Appearance (AI-Driven, No Manual Params)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{twin_id}/appearance/upload", status_code=202)
async def upload_appearance(
    twin_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    pipeline = AppearancePipeline()
    result = await pipeline.upload_and_analyze(twin_id, files)
    return result


@router.get("/{twin_id}/appearance/result")
async def get_appearance_result(twin_id: str, current_user: dict = Depends(get_current_user)):
    twin = await DigitalTwinEngine.get(twin_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return {
        "status": twin.appearance_status.value,
        "face_detected": twin.appearance.face_detected,
        "quality_score": twin.appearance.quality_score,
        "preview_url": twin.appearance_preview_url,
        "landmarks_2d_count": len(twin.appearance.landmarks_2d),
        "blendshapes_count": len(twin.appearance.blendshapes),
        "analysis_log": twin.appearance.analysis_log,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Voice (Cloning-First, Synthetic Fallback)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{twin_id}/voice/upload", status_code=202)
async def upload_voice_samples(
    twin_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    pipeline = VoicePipeline()
    result = await pipeline.upload_and_clone(twin_id, files)
    return result


@router.post("/{twin_id}/voice/synthetic")
async def create_synthetic_voice(
    twin_id: str,
    config: SynthesizedVoiceConfig,
    current_user: dict = Depends(get_current_user),
):
    pipeline = VoicePipeline()
    result = await pipeline.create_synthetic(twin_id, config)
    return result


@router.get("/{twin_id}/voice/result")
async def get_voice_result(twin_id: str, current_user: dict = Depends(get_current_user)):
    twin = await DigitalTwinEngine.get(twin_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return {
        "status": twin.voice_status.value,
        "is_cloned": twin.voice.is_cloned,
        "is_synthetic": twin.voice.is_synthetic,
        "quality_score": twin.voice.quality_score,
        "preview_url": twin.voice_preview_url,
        "samples": [s.model_dump() for s in twin.voice.source_samples],
        "processing_log": twin.voice.processing_log,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Personality (Structured Traits)
# ═══════════════════════════════════════════════════════════════════════════════

@router.put("/{twin_id}/personality")
async def set_personality(
    twin_id: str,
    personality: PersonalityProfile,
    current_user: dict = Depends(get_current_user),
):
    twin = await DigitalTwinEngine.save_personality(twin_id, personality)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return twin.model_dump()


@router.get("/{twin_id}/personality")
async def get_personality(twin_id: str, current_user: dict = Depends(get_current_user)):
    twin = await DigitalTwinEngine.get(twin_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return twin.personality.model_dump()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5a — Relationship (Personal Only)
# ═══════════════════════════════════════════════════════════════════════════════

@router.put("/{twin_id}/relationship")
async def set_relationship(
    twin_id: str,
    relationship: RelationshipConfig,
    current_user: dict = Depends(get_current_user),
):
    twin = await DigitalTwinEngine.get(twin_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    if twin.role != TwinRole.PERSONAL:
        raise HTTPException(status_code=400, detail="Relationship config is only for personal twins")
    updated = await DigitalTwinEngine.save_relationship(twin_id, relationship)
    return updated.model_dump()


@router.get("/{twin_id}/relationship")
async def get_relationship(twin_id: str, current_user: dict = Depends(get_current_user)):
    rel = await DigitalTwinEngine.get_relationship(twin_id)
    if not rel:
        return {}
    return rel.model_dump()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5b — Knowledge Ingestion (Healthcare / Business Only)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{twin_id}/knowledge/upload", status_code=202)
async def upload_knowledge(
    twin_id: str,
    files: List[UploadFile] = File(...),
    source_type: str = Form("pdf"),
    current_user: dict = Depends(get_current_user),
):
    """Upload knowledge documents.

    For personal/normal_user: returns rejection — knowledge is auto-derived from conversation.
    For healthcare/business: accepts PDF, DOCX, TXT, PPTX, XLSX, CSV and runs 12-step pipeline.
    """
    twin = await DigitalTwinEngine.get(twin_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")

    pipeline = KnowledgeIngestionPipeline()
    role = twin.role.value if hasattr(twin.role, 'value') else str(twin.role)
    result = await pipeline.upload_knowledge(twin_id, role, files, source_type)

    if result.get("status") == "rejected":
        raise HTTPException(status_code=400, detail=result["reason"])

    return result


@router.get("/{twin_id}/knowledge/sources")
async def list_knowledge_sources(twin_id: str, current_user: dict = Depends(get_current_user)):
    pipeline = KnowledgeIngestionPipeline()
    sources = await pipeline.get_knowledge_sources(twin_id)
    return sources


@router.delete("/{twin_id}/knowledge/sources/{source_id}")
async def delete_knowledge_source(
    twin_id: str, source_id: str,
    current_user: dict = Depends(get_current_user),
):
    pipeline = KnowledgeIngestionPipeline()
    deleted = await pipeline.delete_knowledge_source(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    return {"detail": "Knowledge source deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLISH
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{twin_id}/publish")
async def publish_twin(twin_id: str, current_user: dict = Depends(get_current_user)):
    try:
        twin = await DigitalTwinEngine.publish(twin_id)
        return twin.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# CONTINUOUS LEARNING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{twin_id}/learning/observations")
async def get_learning_observations(
    twin_id: str,
    current_user: dict = Depends(get_current_user),
    reviewed: Optional[bool] = None,
    confirmed: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
):
    obs = await ContinuousLearningEngine.get_observations(twin_id, reviewed, confirmed, limit, offset)
    return [o.model_dump() for o in obs]


@router.post("/{twin_id}/learning/observations/{obs_id}/confirm")
async def confirm_observation(
    twin_id: str, obs_id: str,
    current_user: dict = Depends(get_current_user),
):
    obs = await ContinuousLearningEngine.confirm_observation(obs_id, current_user["sub"])
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs.model_dump()


@router.get("/{twin_id}/learning/stats")
async def learning_stats(twin_id: str, current_user: dict = Depends(get_current_user)):
    return await ContinuousLearningEngine.get_learning_stats(twin_id)


# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Pipeline-Based Creation — 11-step Digital Twin initialization
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/pipeline", status_code=201)
async def create_twin_pipeline(
    req: CreateDigitalTwinRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a Digital Twin using the full 11-step initialization pipeline.

    Creates UUID, determines role, creates folder structure,
    initializes DB records, identity profile, memory, personality,
    analytics, learning engine, and media repository.
    """
    ext = DigitalTwinEngineExt()
    result = await ext.create_with_pipeline(current_user["sub"], req)
    if result.get("status") == "partial_failure":
        raise HTTPException(status_code=207, detail=result)
    return result


@router.get("/{twin_id}/pipeline/status")
async def get_pipeline_status(twin_id: str, current_user: dict = Depends(get_current_user)):
    """Get the initialization pipeline status for a Digital Twin."""
    status = await CreationPipeline.get_pipeline_status(twin_id)
    if not status:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return status


# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Personality v2 — Standalone personality engine (Big Five + 7 traits)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{twin_id}/personality/v2")
async def get_personality_v2(twin_id: str, current_user: dict = Depends(get_current_user)):
    """Get the standalone personality profile (Big Five + traits + communication + behavior rules)."""
    ext = DigitalTwinEngineExt()
    profile = await ext.get_personality(twin_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Personality not found")
    return profile


@router.put("/{twin_id}/personality/v2")
async def update_personality_v2(
    twin_id: str,
    updates: dict,
    current_user: dict = Depends(get_current_user),
):
    """Update personality traits. Supports: tone, humor_level, empathy_level,
    professionalism, confidence, creativity, patience, friendliness,
    big_five (dict), communication_style (dict), behavior_rules (dict)."""
    ext = DigitalTwinEngineExt()
    updated = await ext.update_personality(twin_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return await ext.get_personality(twin_id)


@router.post("/{twin_id}/personality/initialize")
async def initialize_personality(
    twin_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Initialize personality profile with role-appropriate defaults."""
    row = await fetchrow("SELECT role FROM digital_twins WHERE id = $1", twin_id)
    if not row:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    profile = await PersonalityEngineService.initialize(twin_id, row["role"])
    import dataclasses
    return dataclasses.asdict(profile)


# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Learning Orchestrator — 14-step async post-conversation learning
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{twin_id}/learning/run")
async def run_learning_pipeline(
    twin_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Run the 14-step learning pipeline on conversation text.

    Extracts facts, preferences, corrections, emotional signals,
    updates memory, personality, relationship, knowledge, and analytics.
    Runs asynchronously — does not block the user.
    """
    conversation_text = body.get("conversation_text", "")
    interaction_id = body.get("interaction_id")
    if not conversation_text:
        raise HTTPException(status_code=400, detail="conversation_text is required")

    ext = DigitalTwinEngineExt()
    result = await ext.run_learning_pipeline(twin_id, conversation_text, interaction_id)
    return result


@router.get("/{twin_id}/learning/history")
async def get_learning_history(
    twin_id: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Get learning pipeline execution history for a Digital Twin."""
    history = await LearningOrchestrator.get_learning_history(twin_id, limit)
    return history


# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Media Repository — Digital Twin asset management
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{twin_id}/media/report")
async def get_media_report(twin_id: str, current_user: dict = Depends(get_current_user)):
    """Get storage report for all media categories of a Digital Twin."""
    ext = DigitalTwinEngineExt()
    report = await ext.get_media_report(twin_id)
    if not report:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return report


@router.get("/{twin_id}/media/{category}")
async def list_media_category(
    twin_id: str,
    category: str,
    current_user: dict = Depends(get_current_user),
):
    """List all assets in a media category (appearance, voice, knowledge, etc.)."""
    row = await fetchrow("SELECT id, role FROM digital_twins WHERE id = $1", twin_id)
    if not row:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    media_role = row["role"] if row["role"] in ("normal_user", "healthcare", "business") else "normal_user"
    repo = MediaRepository()
    collection = repo.get_collection(twin_id, media_role, category)
    return {
        "twin_id": collection.twin_id,
        "category": category,
        "asset_count": collection.asset_count,
        "total_size": collection.total_size,
        "assets": [
            {
                "asset_id": a.asset_id,
                "filename": a.filename,
                "file_path": a.file_path,
                "file_size": a.metadata.file_size,
                "mime_type": a.metadata.mime_type,
                "is_original": a.is_original,
                "version": a.version,
                "created_at": a.created_at,
            }
            for a in collection.assets
        ],
    }


@router.post("/{twin_id}/folders/ensure")
async def ensure_twin_folders(twin_id: str, current_user: dict = Depends(get_current_user)):
    """Ensure media folders exist for a Digital Twin (recreate if missing)."""
    ext = DigitalTwinEngineExt()
    result = await ext.ensure_folders(twin_id)
    if not result:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return {"status": "completed", "detail": "Media folders ensured"}


# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Full Twin Status
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{twin_id}/full-status")
async def get_full_twin_status(twin_id: str, current_user: dict = Depends(get_current_user)):
    """Get comprehensive twin status including personality, media, and pipeline."""
    ext = DigitalTwinEngineExt()
    status = await ext.get_full_status(twin_id)
    if not status:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return status
