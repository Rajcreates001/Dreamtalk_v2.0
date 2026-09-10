from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid

from dreamtalk.backend.api.v1.endpoints.auth import get_current_user
from dreamtalk.backend.api.v1.models.digital_human import (
    CreateDigitalHumanRequest, UpdateDigitalHumanRequest, DigitalHumanResponse,
)
from dreamtalk.backend.db.database import fetchrow, execute, fetch

router = APIRouter(prefix="/api/v1/digital-humans", tags=["Digital Humans"])


@router.get("")
async def list_digital_humans(current_user: dict = Depends(get_current_user)):
    rows = await fetch(
        """SELECT * FROM custom_digital_humans
           WHERE user_id = $1 AND is_active = TRUE
           ORDER BY created_at DESC""",
        current_user["sub"],
    )
    return [DigitalHumanResponse(
        id=str(r["id"]),
        name=r["name"],
        description=r["description"],
        category=r["category"],
        personality=r["personality"],
        style=r["style"],
        color_scheme=r["color_scheme"],
        outfit=r["outfit"],
        hair_style=r["hair_style"],
        eye_glow=r["eye_glow"],
        thumbnail_url=r["thumbnail_url"],
        is_active=r["is_active"],
        created_at=r["created_at"].isoformat(),
        updated_at=r["updated_at"].isoformat(),
    ) for r in rows]


@router.post("", status_code=201)
async def create_digital_human(req: CreateDigitalHumanRequest, current_user: dict = Depends(get_current_user)):
    dh_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await execute(
        """INSERT INTO custom_digital_humans
           (id, user_id, name, description, category, personality, style, color_scheme, outfit, hair_style, eye_glow, created_at, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
        dh_id, current_user["sub"], req.name, req.description, req.category,
        req.personality, req.style, req.color_scheme, req.outfit, req.hair_style,
        req.eye_glow, now, now,
    )
    dh = await fetchrow("SELECT * FROM custom_digital_humans WHERE id = $1", dh_id)
    return DigitalHumanResponse(
        id=str(dh["id"]),
        name=dh["name"],
        description=dh["description"],
        category=dh["category"],
        personality=dh["personality"],
        style=dh["style"],
        color_scheme=dh["color_scheme"],
        outfit=dh["outfit"],
        hair_style=dh["hair_style"],
        eye_glow=dh["eye_glow"],
        thumbnail_url=dh["thumbnail_url"],
        is_active=dh["is_active"],
        created_at=dh["created_at"].isoformat(),
        updated_at=dh["updated_at"].isoformat(),
    )


@router.get("/{dh_id}")
async def get_digital_human(dh_id: str, current_user: dict = Depends(get_current_user)):
    dh = await fetchrow(
        "SELECT * FROM custom_digital_humans WHERE id = $1 AND user_id = $2",
        dh_id, current_user["sub"],
    )
    if not dh:
        raise HTTPException(status_code=404, detail="Digital human not found")
    return DigitalHumanResponse(
        id=str(dh["id"]),
        name=dh["name"],
        description=dh["description"],
        category=dh["category"],
        personality=dh["personality"],
        style=dh["style"],
        color_scheme=dh["color_scheme"],
        outfit=dh["outfit"],
        hair_style=dh["hair_style"],
        eye_glow=dh["eye_glow"],
        thumbnail_url=dh["thumbnail_url"],
        is_active=dh["is_active"],
        created_at=dh["created_at"].isoformat(),
        updated_at=dh["updated_at"].isoformat(),
    )


@router.put("/{dh_id}")
async def update_digital_human(dh_id: str, req: UpdateDigitalHumanRequest, current_user: dict = Depends(get_current_user)):
    existing = await fetchrow(
        "SELECT id FROM custom_digital_humans WHERE id = $1 AND user_id = $2",
        dh_id, current_user["sub"],
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Digital human not found")

    fields = []
    values = []
    idx = 1
    for key, val in req.model_dump(exclude_none=True).items():
        fields.append(f"{key} = ${idx}")
        values.append(val)
        idx += 1

    if not fields:
        dh = await fetchrow("SELECT * FROM custom_digital_humans WHERE id = $1", dh_id)
        return DigitalHumanResponse(
            id=str(dh["id"]), name=dh["name"], description=dh["description"],
            category=dh["category"], personality=dh["personality"],
            style=dh["style"], color_scheme=dh["color_scheme"],
            outfit=dh["outfit"], hair_style=dh["hair_style"],
            eye_glow=dh["eye_glow"], thumbnail_url=dh["thumbnail_url"],
            is_active=dh["is_active"],
            created_at=dh["created_at"].isoformat(),
            updated_at=dh["updated_at"].isoformat(),
        )

    fields.append("updated_at = NOW()")
    sql = f"UPDATE custom_digital_humans SET {', '.join(fields)} WHERE id = ${idx}"
    values.append(dh_id)
    await execute(sql, *values)

    dh = await fetchrow("SELECT * FROM custom_digital_humans WHERE id = $1", dh_id)
    return DigitalHumanResponse(
        id=str(dh["id"]), name=dh["name"], description=dh["description"],
        category=dh["category"], personality=dh["personality"],
        style=dh["style"], color_scheme=dh["color_scheme"],
        outfit=dh["outfit"], hair_style=dh["hair_style"],
        eye_glow=dh["eye_glow"], thumbnail_url=dh["thumbnail_url"],
        is_active=dh["is_active"],
        created_at=dh["created_at"].isoformat(),
        updated_at=dh["updated_at"].isoformat(),
    )


@router.delete("/{dh_id}")
async def delete_digital_human(dh_id: str, current_user: dict = Depends(get_current_user)):
    existing = await fetchrow(
        "SELECT id FROM custom_digital_humans WHERE id = $1 AND user_id = $2",
        dh_id, current_user["sub"],
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Digital human not found")

    await execute(
        "UPDATE custom_digital_humans SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
        dh_id,
    )
    return {"detail": "Digital human deleted"}
