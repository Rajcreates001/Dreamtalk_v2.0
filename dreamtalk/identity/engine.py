from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.identity.models import (
    IdentityProfile, EvolutionDelta, EvolutionLogEntry,
    AppearanceProfile, VoiceProfile, PersonalityProfile,
    KnowledgeIndex, MemoryState, EvolutionMeta, BehaviorProfile,
)

logger = logging.getLogger("dreamtalk.identity")


class IdentityEngine:
    """Central identity store — owns all per-avatar state."""

    @staticmethod
    async def get(identity_id: str) -> Optional[IdentityProfile]:
        row = await fetchrow(
            "SELECT * FROM identity_profiles WHERE id = $1", identity_id,
        )
        if not row:
            return None
        return IdentityEngine._row_to_profile(row)

    @staticmethod
    async def get_by_custom_dh(custom_dh_id: str) -> Optional[IdentityProfile]:
        row = await fetchrow(
            "SELECT * FROM identity_profiles WHERE custom_dh_id = $1", custom_dh_id,
        )
        if not row:
            return None
        return IdentityEngine._row_to_profile(row)

    @staticmethod
    async def get_by_user(user_id: str) -> list[IdentityProfile]:
        rows = await fetch(
            "SELECT * FROM identity_profiles WHERE user_id = $1 ORDER BY updated_at DESC",
            user_id,
        )
        return [IdentityEngine._row_to_profile(r) for r in rows]

    @staticmethod
    async def create(profile: IdentityProfile) -> IdentityProfile:
        await execute(
            """INSERT INTO identity_profiles
               (id, user_id, custom_dh_id, identity_version, appearance, voice,
                personality, knowledge, memory, evolution, behavior,
                created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb,
                       $8::jsonb, $9::jsonb, $10::jsonb, $11::jsonb,
                       $12, $13)""",
            profile.id, profile.user_id, profile.custom_dh_id,
            profile.identity_version,
            json.dumps(profile.appearance.model_dump()),
            json.dumps(profile.voice.model_dump()),
            json.dumps(profile.personality.model_dump()),
            json.dumps(profile.knowledge.model_dump()),
            json.dumps(profile.memory.model_dump()),
            json.dumps(profile.evolution.model_dump()),
            json.dumps(profile.behavior.model_dump()),
            profile.created_at, profile.updated_at,
        )
        return profile

    @staticmethod
    async def upsert(profile: IdentityProfile) -> IdentityProfile:
        existing = await fetchrow(
            "SELECT id FROM identity_profiles WHERE custom_dh_id = $1",
            profile.custom_dh_id,
        )
        if existing:
            profile.id = existing["id"]
            return await IdentityEngine.update(profile)
        return await IdentityEngine.create(profile)

    @staticmethod
    async def update(profile: IdentityProfile) -> IdentityProfile:
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        await execute(
            """UPDATE identity_profiles SET
               identity_version = $2,
               appearance = $3::jsonb,
               voice = $4::jsonb,
               personality = $5::jsonb,
               knowledge = $6::jsonb,
               memory = $7::jsonb,
               evolution = $8::jsonb,
               behavior = $9::jsonb,
               updated_at = $10
               WHERE id = $1""",
            profile.id, profile.identity_version,
            json.dumps(profile.appearance.model_dump()),
            json.dumps(profile.voice.model_dump()),
            json.dumps(profile.personality.model_dump()),
            json.dumps(profile.knowledge.model_dump()),
            json.dumps(profile.memory.model_dump()),
            json.dumps(profile.evolution.model_dump()),
            json.dumps(profile.behavior.model_dump()),
            profile.updated_at,
        )
        return profile

    @staticmethod
    async def update_appearance(identity_id: str, appearance: AppearanceProfile) -> IdentityProfile:
        profile = await IdentityEngine.get(identity_id)
        if not profile:
            raise ValueError(f"Identity {identity_id} not found")
        profile.appearance = appearance
        return await IdentityEngine.update(profile)

    @staticmethod
    async def update_voice(identity_id: str, voice: VoiceProfile) -> IdentityProfile:
        profile = await IdentityEngine.get(identity_id)
        if not profile:
            raise ValueError(f"Identity {identity_id} not found")
        profile.voice = voice
        return await IdentityEngine.update(profile)

    @staticmethod
    async def update_personality(identity_id: str, personality: PersonalityProfile) -> IdentityProfile:
        profile = await IdentityEngine.get(identity_id)
        if not profile:
            raise ValueError(f"Identity {identity_id} not found")
        profile.personality = personality
        return await IdentityEngine.update(profile)

    @staticmethod
    def _row_to_profile(row) -> IdentityProfile:
        def _safe_json(val):
            if isinstance(val, dict):
                return val
            if val is None:
                return {}
            return json.loads(val) if isinstance(val, str) else {}

        def _iso(val):
            if hasattr(val, "isoformat"):
                return val.isoformat()
            return str(val) if val else ""

        return IdentityProfile(
            id=row["id"],
            user_id=row["user_id"],
            custom_dh_id=row["custom_dh_id"],
            identity_version=row.get("identity_version", "1.0.0"),
            appearance=AppearanceProfile(**_safe_json(row.get("appearance"))),
            voice=VoiceProfile(**_safe_json(row.get("voice"))),
            personality=PersonalityProfile(**_safe_json(row.get("personality"))),
            knowledge=KnowledgeIndex(**_safe_json(row.get("knowledge"))),
            memory=MemoryState(**_safe_json(row.get("memory"))),
            evolution=EvolutionMeta(**_safe_json(row.get("evolution"))),
            behavior=BehaviorProfile(**_safe_json(row.get("behavior"))),
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )
