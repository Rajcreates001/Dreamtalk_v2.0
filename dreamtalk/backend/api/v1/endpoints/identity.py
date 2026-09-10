from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
import uuid

from dreamtalk.backend.api.v1.endpoints.auth import get_current_user
from dreamtalk.backend.db.database import fetchrow, execute, fetch
from dreamtalk.identity.models import (
    IdentityProfile, AppearanceProfile, VoiceProfile, PersonalityProfile,
    EvolutionDelta, EvolutionLogEntry,
)
from dreamtalk.identity.engine import IdentityEngine
from dreamtalk.identity.appearance import AppearancePipeline
from dreamtalk.identity.evolution import EvolutionEngine

router = APIRouter(prefix="/api/v1/identity", tags=["Identity Engine"])


@router.get("/by-user")
async def list_identities(current_user: dict = Depends(get_current_user)):
    profiles = await IdentityEngine.get_by_user(current_user["sub"])
    return [p.model_dump() for p in profiles]


@router.get("/{identity_id}")
async def get_identity(identity_id: str, current_user: dict = Depends(get_current_user)):
    profile = await IdentityEngine.get(identity_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity not found")
    return profile.model_dump()


@router.get("/by-custom-dh/{custom_dh_id}")
async def get_identity_by_custom_dh(custom_dh_id: str, current_user: dict = Depends(get_current_user)):
    profile = await IdentityEngine.get_by_custom_dh(custom_dh_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity not found for this avatar")
    return profile.model_dump()


@router.post("", status_code=201)
async def create_identity(
    custom_dh_id: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    existing = await IdentityEngine.get_by_custom_dh(custom_dh_id)
    if existing:
        raise HTTPException(status_code=409, detail="Identity already exists for this avatar")

    profile = IdentityProfile.blank(user_id=current_user["sub"], custom_dh_id=custom_dh_id)
    created = await IdentityEngine.create(profile)
    return created.model_dump()


@router.put("/{identity_id}/appearance")
async def update_appearance(
    identity_id: str,
    appearance: AppearanceProfile,
    current_user: dict = Depends(get_current_user),
):
    try:
        profile = await IdentityEngine.update_appearance(identity_id, appearance)
        return profile.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{identity_id}/voice")
async def update_voice(
    identity_id: str,
    voice: VoiceProfile,
    current_user: dict = Depends(get_current_user),
):
    try:
        profile = await IdentityEngine.update_voice(identity_id, voice)
        return profile.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{identity_id}/personality")
async def update_personality(
    identity_id: str,
    personality: PersonalityProfile,
    current_user: dict = Depends(get_current_user),
):
    try:
        profile = await IdentityEngine.update_personality(identity_id, personality)
        return profile.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{identity_id}/appearance/upload", status_code=202)
async def upload_for_appearance(
    identity_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    pipeline = AppearancePipeline()
    result = await pipeline.process_upload(identity_id, file)
    return result


@router.post("/{identity_id}/appearance/analyze", status_code=202)
async def analyze_appearance(
    identity_id: str,
    media_urls: list[str] = Form(...),
    current_user: dict = Depends(get_current_user),
):
    pipeline = AppearancePipeline()
    result = await pipeline.analyze(identity_id, media_urls)
    return result


@router.get("/{identity_id}/evolution/log")
async def get_evolution_log(
    identity_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    profile = await IdentityEngine.get(identity_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity not found")
    rows = await fetch(
        "SELECT * FROM evolution_log WHERE identity_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        identity_id, limit, offset,
    )
    return [dict(r) for r in rows]


@router.get("/{identity_id}/evolution/deltas")
async def get_evolution_deltas(
    identity_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
):
    profile = await IdentityEngine.get(identity_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity not found")
    rows = await fetch(
        "SELECT * FROM evolution_deltas WHERE identity_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        identity_id, limit, offset,
    )
    return [dict(r) for r in rows]
