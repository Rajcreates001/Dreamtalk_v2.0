from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid

from dreamtalk.backend.api.v1.endpoints.auth import get_current_user
from dreamtalk.backend.api.v1.models.digital_human import (
    UpdateProfileRequest, SettingsResponse, UpdateSettingsRequest,
    SubscriptionResponse,
)
from dreamtalk.backend.db.database import fetchrow, execute

router = APIRouter(prefix="/api/v1", tags=["Profile"])


@router.put("/auth/profile")
async def update_profile(req: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    user = await fetchrow("SELECT * FROM users WHERE id = $1", current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    fields = []
    values = []
    idx = 1
    if req.full_name is not None:
        fields.append(f"full_name = ${idx}")
        values.append(req.full_name)
        idx += 1
    if req.avatar_url is not None:
        fields.append(f"avatar_url = ${idx}")
        values.append(req.avatar_url)
        idx += 1

    if fields:
        fields.append(f"updated_at = NOW()")
        sql = f"UPDATE users SET {', '.join(fields)} WHERE id = ${idx}"
        values.append(current_user["sub"])
        await execute(sql, *values)

    user = await fetchrow("SELECT * FROM users WHERE id = $1", current_user["sub"])
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "avatar_url": user["avatar_url"],
        "is_verified": user["is_verified"],
        "created_at": user["created_at"].isoformat(),
    }


@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    settings = await fetchrow(
        "SELECT * FROM user_settings WHERE user_id = $1", current_user["sub"]
    )
    if not settings:
        return SettingsResponse(id="", llm_provider="openai")
    return SettingsResponse(
        id=str(settings["id"]),
        llm_provider=settings["llm_provider"],
        llm_model=settings["llm_model"],
        tts_provider=settings["tts_provider"],
        tts_voice=settings["tts_voice"],
        stt_provider=settings["stt_provider"],
        theme=settings["theme"],
        language=settings["language"],
        notification_enabled=settings["notification_enabled"],
    )


@router.put("/settings")
async def update_settings(req: UpdateSettingsRequest, current_user: dict = Depends(get_current_user)):
    existing = await fetchrow(
        "SELECT id FROM user_settings WHERE user_id = $1", current_user["sub"]
    )
    if not existing:
        sid = str(uuid.uuid4())
        await execute(
            """INSERT INTO user_settings (id, user_id) VALUES ($1, $2)""",
            sid, current_user["sub"],
        )
        existing = {"id": sid}

    fields = []
    values = []
    idx = 1
    for key, val in req.model_dump(exclude_none=True).items():
        fields.append(f"{key} = ${idx}")
        values.append(val)
        idx += 1

    if fields:
        sql = f"UPDATE user_settings SET {', '.join(fields)} WHERE id = ${idx}"
        values.append(str(existing["id"]))
        await execute(sql, *values)

    settings = await fetchrow(
        "SELECT * FROM user_settings WHERE user_id = $1", current_user["sub"]
    )
    return SettingsResponse(
        id=str(settings["id"]),
        llm_provider=settings["llm_provider"],
        llm_model=settings["llm_model"],
        tts_provider=settings["tts_provider"],
        tts_voice=settings["tts_voice"],
        stt_provider=settings["stt_provider"],
        theme=settings["theme"],
        language=settings["language"],
        notification_enabled=settings["notification_enabled"],
    )


@router.get("/subscription")
async def get_subscription(current_user: dict = Depends(get_current_user)):
    sub = await fetchrow(
        "SELECT * FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        current_user["sub"],
    )
    if not sub:
        return SubscriptionResponse(
            id="", tier="free", status="active",
            current_period_start=datetime.now(timezone.utc).isoformat(),
        )
    return SubscriptionResponse(
        id=str(sub["id"]),
        tier=sub["tier"],
        status=sub["status"],
        current_period_start=sub["current_period_start"].isoformat(),
        current_period_end=sub["current_period_end"].isoformat() if sub["current_period_end"] else None,
    )
