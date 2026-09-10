from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.digital_twin.models import (
    CreateDigitalTwinRequest, UpdateDigitalTwinRequest,
    DigitalTwinResponse, TwinStatus, PipelineStatus, TwinRole,
    AppearanceProfile, VoiceProfile, PersonalityProfile,
    IntelligenceConfig, RelationshipConfig,
    TwinStatusResponse,
)

logger = logging.getLogger("dreamtalk.digital_twin")

TWIN_STORAGE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "storage", "twins",
)


class DigitalTwinEngine:
    """Lifecycle manager for role-aware digital twin creation."""

    # ─── CRUD ────────────────────────────────────────────────────────────────

    @staticmethod
    async def create(user_id: str, req: CreateDigitalTwinRequest) -> DigitalTwinResponse:
        twin_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Create storage folders
        twin_root = os.path.join(TWIN_STORAGE_ROOT, twin_id)
        for sub in ["appearance", "voice", "knowledge", "previews"]:
            os.makedirs(os.path.join(twin_root, sub), exist_ok=True)

        await execute(
            """INSERT INTO digital_twins
               (id, user_id, name, description, category, language, timezone,
                visibility, role, status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
            twin_id, user_id, req.name, req.description,
            req.category, req.language, req.timezone,
            req.visibility, req.role.value, TwinStatus.DRAFT.value,
            now, now,
        )

        # Initialize personality defaults for role
        personality = PersonalityProfile()
        if req.role == TwinRole.HEALTHCARE:
            personality.professionalism = 0.9
            personality.empathy = 0.85
            personality.formality = 0.7
            personality.communication_style = "professional_warm"
        elif req.role == TwinRole.BUSINESS:
            personality.professionalism = 0.9
            personality.confidence = 0.8
            personality.leadership = 0.75
            personality.formality = 0.7
            personality.communication_style = "professional"

        await execute(
            """UPDATE digital_twins SET personality_data = $1::jsonb WHERE id = $2""",
            json.dumps(personality.model_dump()), twin_id,
        )

        return await DigitalTwinEngine.get(twin_id)

    @staticmethod
    async def get(twin_id: str) -> Optional[DigitalTwinResponse]:
        row = await fetchrow("SELECT * FROM digital_twins WHERE id = $1", twin_id)
        if not row:
            return None
        return DigitalTwinEngine._row_to_response(row)

    @staticmethod
    async def get_by_user(user_id: str) -> list[DigitalTwinResponse]:
        rows = await fetch(
            "SELECT * FROM digital_twins WHERE user_id = $1 ORDER BY updated_at DESC",
            user_id,
        )
        return [DigitalTwinEngine._row_to_response(r) for r in rows]

    @staticmethod
    async def update(
        twin_id: str, req: UpdateDigitalTwinRequest,
    ) -> Optional[DigitalTwinResponse]:
        fields = []
        values = []
        idx = 1
        for key, val in req.model_dump(exclude_none=True).items():
            fields.append(f"{key} = ${idx}")
            values.append(val)
            idx += 1
        if not fields:
            return await DigitalTwinEngine.get(twin_id)

        fields.append(f"updated_at = ${idx}")
        values.append(datetime.now(timezone.utc))
        idx += 1
        values.append(twin_id)

        sql = f"UPDATE digital_twins SET {', '.join(fields)} WHERE id = ${idx}"
        await execute(sql, *values)
        return await DigitalTwinEngine.get(twin_id)

    @staticmethod
    async def delete(twin_id: str, user_id: str) -> bool:
        row = await fetchrow(
            "SELECT id FROM digital_twins WHERE id = $1 AND user_id = $2",
            twin_id, user_id,
        )
        if not row:
            return False
        await execute("DELETE FROM digital_twins WHERE id = $1", twin_id)
        return True

    # ─── Status / Lifecycle ──────────────────────────────────────────────────

    @staticmethod
    async def get_status(twin_id: str) -> Optional[TwinStatusResponse]:
        row = await fetchrow("SELECT * FROM digital_twins WHERE id = $1", twin_id)
        if not row:
            return None

        status = row["status"]
        steps = {
            "identity": "complete",
            "appearance": row.get("appearance_status", "pending"),
            "voice": row.get("voice_status", "pending"),
            "personality": row.get("personality_status", "pending"),
            "intelligence": row.get("intelligence_status", "pending"),
        }

        return TwinStatusResponse(
            id=str(row["id"]),
            name=row["name"],
            role=row["role"],
            status=status,
            steps=steps,
            twin_version=row.get("twin_version", "1.0.0"),
            interaction_count=row.get("interaction_count", 0),
            evolution_count=row.get("evolution_count", 0),
            published=(status == TwinStatus.PUBLISHED.value),
            created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        )

    @staticmethod
    async def advance_status(twin_id: str, completed_step: str) -> Optional[DigitalTwinResponse]:
        """Advance the twin creation status after a step completes."""
        status_map = {
            "appearance": TwinStatus.APPEARANCE_COMPLETE,
            "voice": TwinStatus.VOICE_COMPLETE,
            "personality": TwinStatus.PERSONALITY_COMPLETE,
            "intelligence": TwinStatus.INTELLIGENCE_COMPLETE,
        }
        target = status_map.get(completed_step)
        if not target:
            return await DigitalTwinEngine.get(twin_id)

        # Check all prerequisites are met
        row = await fetchrow("SELECT * FROM digital_twins WHERE id = $1", twin_id)
        if not row:
            return None

        current = TwinStatus(row["status"])
        new_status = target

        await execute(
            "UPDATE digital_twins SET status = $1, updated_at = $2 WHERE id = $3",
            new_status.value, datetime.now(timezone.utc), twin_id,
        )
        return await DigitalTwinEngine.get(twin_id)

    @staticmethod
    async def publish(twin_id: str) -> Optional[DigitalTwinResponse]:
        """Publish the twin — all prerequisites must be met."""
        row = await fetchrow("SELECT * FROM digital_twins WHERE id = $1", twin_id)
        if not row:
            return None

        complete_statuses = {"complete", "completed", "cloned", "synthetic"}
        required = ["appearance", "voice", "personality"]
        for step in required:
            status_key = f"{step}_status"
            if row.get(status_key) not in complete_statuses:
                raise ValueError(
                    f"Cannot publish: {step} is not complete "
                    f"(status: {row.get(status_key, 'unknown')})",
                )

        now = datetime.now(timezone.utc)
        await execute(
            """UPDATE digital_twins
               SET status = $1, published_at = $2, updated_at = $3
               WHERE id = $4""",
            TwinStatus.PUBLISHED.value, now, now, twin_id,
        )
        return await DigitalTwinEngine.get(twin_id)

    # ─── Step 2: Appearance ──────────────────────────────────────────────────

    @staticmethod
    async def save_appearance(
        twin_id: str, appearance: AppearanceProfile,
    ) -> Optional[DigitalTwinResponse]:
        now = datetime.now(timezone.utc)
        status = PipelineStatus.COMPLETE.value if appearance.face_detected else PipelineStatus.FAILED.value
        await execute(
            """UPDATE digital_twins SET
               appearance_data = $1::jsonb,
               appearance_status = $2,
               appearance_preview_url = $3,
               updated_at = $4
               WHERE id = $5""",
            json.dumps(appearance.model_dump()),
            status,
            appearance.preview_image_url,
            now,
            twin_id,
        )
        if status == PipelineStatus.COMPLETE.value:
            await DigitalTwinEngine.advance_status(twin_id, "appearance")
        return await DigitalTwinEngine.get(twin_id)

    @staticmethod
    async def set_appearance_processing(twin_id: str) -> None:
        await execute(
            "UPDATE digital_twins SET appearance_status = $1, updated_at = $2 WHERE id = $3",
            PipelineStatus.PROCESSING.value, datetime.now(timezone.utc), twin_id,
        )

    # ─── Step 3: Voice ───────────────────────────────────────────────────────

    @staticmethod
    async def save_voice(
        twin_id: str, voice: VoiceProfile,
    ) -> Optional[DigitalTwinResponse]:
        now = datetime.now(timezone.utc)
        status = PipelineStatus.COMPLETE.value if (voice.cloned_voice_id or voice.synthetic_voice_id) else PipelineStatus.FAILED.value
        await execute(
            """UPDATE digital_twins SET
               voice_data = $1::jsonb,
               voice_status = $2,
               voice_preview_url = $3,
               updated_at = $4
               WHERE id = $5""",
            json.dumps(voice.model_dump()),
            status,
            voice.preview_audio_url,
            now,
            twin_id,
        )
        if status == PipelineStatus.COMPLETE.value:
            await DigitalTwinEngine.advance_status(twin_id, "voice")
        return await DigitalTwinEngine.get(twin_id)

    @staticmethod
    async def set_voice_processing(twin_id: str) -> None:
        await execute(
            "UPDATE digital_twins SET voice_status = $1, updated_at = $2 WHERE id = $3",
            PipelineStatus.PROCESSING.value, datetime.now(timezone.utc), twin_id,
        )

    # ─── Step 4: Personality ─────────────────────────────────────────────────

    @staticmethod
    async def save_personality(
        twin_id: str, personality: PersonalityProfile,
    ) -> Optional[DigitalTwinResponse]:
        now = datetime.now(timezone.utc)
        await execute(
            """UPDATE digital_twins SET
               personality_data = $1::jsonb,
               personality_status = $2,
               updated_at = $3
               WHERE id = $4""",
            json.dumps(personality.model_dump()),
            PipelineStatus.COMPLETE.value,
            now,
            twin_id,
        )
        await DigitalTwinEngine.advance_status(twin_id, "personality")
        return await DigitalTwinEngine.get(twin_id)

    # ─── Step 5: Relationship (Personal) ─────────────────────────────────────

    @staticmethod
    async def save_relationship(
        twin_id: str, relationship: RelationshipConfig,
    ) -> Optional[DigitalTwinResponse]:
        now = datetime.now(timezone.utc)
        await execute(
            """UPDATE digital_twins SET
               relationship_data = $1::jsonb,
               updated_at = $2
               WHERE id = $3""",
            json.dumps(relationship.model_dump()),
            now,
            twin_id,
        )
        return await DigitalTwinEngine.get(twin_id)

    @staticmethod
    async def get_relationship(twin_id: str) -> Optional[RelationshipConfig]:
        row = await fetchrow(
            "SELECT relationship_data FROM digital_twins WHERE id = $1", twin_id,
        )
        if not row or not row["relationship_data"]:
            return None
        data = row["relationship_data"]
        if isinstance(data, str):
            data = json.loads(data)
        return RelationshipConfig(**data)

    # ─── Version Tracking ────────────────────────────────────────────────────

    @staticmethod
    async def bump_version(twin_id: str) -> str:
        row = await fetchrow(
            "SELECT twin_version, evolution_count FROM digital_twins WHERE id = $1",
            twin_id,
        )
        if not row:
            return "0.0.0"
        parts = row["twin_version"].split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        new_version = f"{major}.{minor}.{patch + 1}"
        await execute(
            """UPDATE digital_twins SET
               twin_version = $1,
               evolution_count = evolution_count + 1,
               updated_at = $2
               WHERE id = $3""",
            new_version, datetime.now(timezone.utc), twin_id,
        )
        return new_version

    @staticmethod
    async def increment_interactions(twin_id: str) -> None:
        await execute(
            "UPDATE digital_twins SET interaction_count = interaction_count + 1 WHERE id = $1",
            twin_id,
        )

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_response(row) -> DigitalTwinResponse:
        def _safe_json(val: Any) -> dict:
            if isinstance(val, dict):
                return val
            if val is None:
                return {}
            try:
                return json.loads(val) if isinstance(val, str) else {}
            except (json.JSONDecodeError, TypeError):
                return {}

        def _iso(val: Any) -> str:
            if hasattr(val, "isoformat"):
                return val.isoformat()
            return str(val) if val else ""

        appearance = _safe_json(row.get("appearance_data"))
        voice = _safe_json(row.get("voice_data"))
        personality = _safe_json(row.get("personality_data"))
        relationship_data = _safe_json(row.get("relationship_data"))
        role = TwinRole(row["role"])

        # Gracefully handle Pydantic model construction with partial data
        try:
            appearance_model = AppearanceProfile(**appearance)
        except (ValueError, TypeError, KeyError):
            appearance_model = AppearanceProfile()

        try:
            voice_model = VoiceProfile(**voice)
        except (ValueError, TypeError, KeyError):
            voice_model = VoiceProfile()

        try:
            personality_model = PersonalityProfile(**personality)
        except (ValueError, TypeError, KeyError):
            personality_model = PersonalityProfile()

        try:
            relationship_model = RelationshipConfig(**relationship_data) if relationship_data else None
        except (ValueError, TypeError, KeyError):
            relationship_model = None

        intelligence = IntelligenceConfig(
            role=role,
            relationship=relationship_model,
        )

        return DigitalTwinResponse(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            name=row["name"],
            description=row.get("description", ""),
            category=row.get("category", "personal"),
            language=row.get("language", "en"),
            timezone=row.get("timezone", "UTC"),
            visibility=row.get("visibility", "private"),
            role=role,
            status=TwinStatus(row.get("status", "draft")),
            avatar_image_url=row.get("avatar_image_url"),
            appearance=appearance,
            appearance_status=PipelineStatus(row.get("appearance_status", "pending")),
            appearance_preview_url=row.get("appearance_preview_url"),
            voice=voice,
            voice_status=PipelineStatus(row.get("voice_status", "pending")),
            voice_preview_url=row.get("voice_preview_url"),
            personality=personality,
            personality_status=PipelineStatus(row.get("personality_status", "pending")),
            intelligence=intelligence,
            intelligence_status=PipelineStatus(row.get("intelligence_status", "pending")),
            twin_version=row.get("twin_version", "1.0.0"),
            interaction_count=row.get("interaction_count", 0),
            evolution_count=row.get("evolution_count", 0),
            custom_dh_id=str(row["custom_dh_id"]) if row.get("custom_dh_id") else None,
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
            published_at=_iso(row.get("published_at")) if row.get("published_at") else None,
        )
