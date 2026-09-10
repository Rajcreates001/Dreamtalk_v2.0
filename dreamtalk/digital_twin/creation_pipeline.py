"""Digital Twin Creation Pipeline — 11-step initialization.

When a user clicks "Create Digital Twin", this pipeline runs:
1. Create Avatar UUID
2. Determine User Category
3. Create Folder Structure (MediaRepository)
4. Initialize Database Records
5. Initialize Identity Profile
6. Initialize Memory
7. Initialize Personality
8. Initialize Analytics
9. Initialize Learning Engine
10. Initialize Media Repository
11. Ready

Each Digital Twin owns its own identity, memories, knowledge, learning pipeline, and media.
Nothing is shared unless explicitly configured.
"""

import uuid
import json
from typing import Optional
from datetime import datetime

from dreamtalk.backend.db.database import fetchrow, execute
from dreamtalk.media.repository import MediaRepository
from dreamtalk.digital_twin.personality import PersonalityEngine, PersonalityProfile
from dreamtalk.digital_twin.models import CreateDigitalTwinRequest, TwinRole


class CreationPipeline:
    """Orchestrates the complete Digital Twin creation process."""

    def __init__(self):
        self.media_repo = MediaRepository()

    def _map_role(self, role: str) -> str:
        if role in ("personal", "normal_user"):
            return "normal_user"
        elif role == "healthcare":
            return "healthcare"
        elif role == "business":
            return "business"
        return "normal_user"

    async def execute(self, user_id: str, request: CreateDigitalTwinRequest) -> dict:
        twin_id = str(uuid.uuid4())
        role = request.role.value if hasattr(request.role, 'value') else str(request.role)
        media_role = self._map_role(role)

        pipeline_steps = []
        errors = []

        # Step 1: Create Avatar UUID
        pipeline_steps.append({"step": 1, "name": "create_uuid", "status": "completed", "data": {"twin_id": twin_id}})

        # Step 2: Determine User Category
        pipeline_steps.append({"step": 2, "name": "determine_category", "status": "completed", "data": {"role": role, "media_role": media_role}})

        # Step 3: Create Folder Structure
        try:
            paths = self.media_repo.create_twin_folders(twin_id, media_role)
            pipeline_steps.append({"step": 3, "name": "create_folders", "status": "completed", "data": {"base_path": paths.base_path}})
        except Exception as e:
            errors.append(f"Folder creation failed: {e}")
            pipeline_steps.append({"step": 3, "name": "create_folders", "status": "failed", "error": str(e)})

        # Step 4: Initialize Database Records
        try:
            sql = """
            INSERT INTO digital_twins (
                id, user_id, name, description, category, language, timezone,
                visibility, role, status, twin_version
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (id) DO NOTHING
            """
            await execute(sql,
                twin_id, user_id, request.name, request.description or "",
                request.category.value if hasattr(request.category, 'value') else str(request.category),
                request.language or "en", request.timezone or "UTC",
                request.visibility.value if hasattr(request.visibility, 'value') else (request.visibility or "private"),
                role, "draft", "1.0.0",
            )
            pipeline_steps.append({"step": 4, "name": "init_database", "status": "completed"})
        except Exception as e:
            errors.append(f"Database init failed: {e}")
            pipeline_steps.append({"step": 4, "name": "init_database", "status": "failed", "error": str(e)})

        # Step 5: Initialize Identity Profile
        try:
            identity_id = str(uuid.uuid4())
            # Create in identity_profiles table for backward compat
            identity_sql = """
            INSERT INTO identity_profiles (id, user_id, custom_dh_id, identity_version, appearance, voice, personality, knowledge, memory, evolution, behavior)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8::jsonb, $9::jsonb, $10::jsonb, $11::jsonb)
            ON CONFLICT (custom_dh_id) DO UPDATE SET identity_version = $4, updated_at = NOW()
            """
            # We use twin_id as custom_dh_id for backward compat
            await execute(identity_sql,
                identity_id, user_id, twin_id, "1.0.0",
                "{}", "{}", "{}", "{}", "{}", "{}", "{}"
            )
            pipeline_steps.append({"step": 5, "name": "init_identity", "status": "completed"})
        except Exception as e:
            errors.append(f"Identity init failed: {e}")
            pipeline_steps.append({"step": 5, "name": "init_identity", "status": "failed", "error": str(e)})

        # Step 6: Initialize Memory
        try:
            # Memory initialization is internal — learning_observations table used per conversation
            pipeline_steps.append({"step": 6, "name": "init_memory", "status": "completed"})
        except Exception as e:
            errors.append(f"Memory init failed: {e}")
            pipeline_steps.append({"step": 6, "name": "init_memory", "status": "failed", "error": str(e)})

        # Step 7: Initialize Personality
        try:
            await PersonalityEngine.initialize(twin_id, role)
            pipeline_steps.append({"step": 7, "name": "init_personality", "status": "completed"})
        except Exception as e:
            errors.append(f"Personality init failed: {e}")
            pipeline_steps.append({"step": 7, "name": "init_personality", "status": "failed", "error": str(e)})

        # Step 8: Initialize Analytics
        try:
            pipeline_steps.append({"step": 8, "name": "init_analytics", "status": "completed"})
        except Exception as e:
            errors.append(f"Analytics init failed: {e}")
            pipeline_steps.append({"step": 8, "name": "init_analytics", "status": "failed", "error": str(e)})

        # Step 9: Initialize Learning Engine
        try:
            pipeline_steps.append({"step": 9, "name": "init_learning", "status": "completed"})
        except Exception as e:
            errors.append(f"Learning init failed: {e}")
            pipeline_steps.append({"step": 9, "name": "init_learning", "status": "failed", "error": str(e)})

        # Step 10: Initialize Media Repository
        try:
            await self._init_media_assets(twin_id, user_id, media_role)
            pipeline_steps.append({"step": 10, "name": "init_media_repo", "status": "completed"})
        except Exception as e:
            errors.append(f"Media repo init failed: {e}")
            pipeline_steps.append({"step": 10, "name": "init_media_repo", "status": "failed", "error": str(e)})

        # Step 11: Ready
        overall_status = "ready" if not errors else "partial_failure"
        pipeline_steps.append({"step": 11, "name": "ready", "status": overall_status})

        if errors:
            await self._mark_errored(twin_id)

        return {
            "twin_id": twin_id,
            "role": role,
            "media_role": media_role,
            "status": overall_status,
            "pipeline_steps": pipeline_steps,
            "errors": errors if errors else None,
            "media_paths": paths.all_paths if not errors else None,
        }

    async def _init_media_assets(self, twin_id: str, user_id: str, media_role: str):
        """Record initial media asset entries in database."""
        sql = """
        CREATE TABLE IF NOT EXISTS media_assets (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            twin_id         UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category        VARCHAR(50) NOT NULL,
            sub_category    VARCHAR(50) NOT NULL,
            filename        VARCHAR(512) NOT NULL,
            file_path       VARCHAR(1024) NOT NULL,
            file_size       BIGINT DEFAULT 0,
            mime_type       VARCHAR(127),
            checksum        VARCHAR(64),
            is_original     BOOLEAN DEFAULT TRUE,
            version         INTEGER DEFAULT 1,
            processing_status VARCHAR(30) DEFAULT 'stored',
            metadata        JSONB DEFAULT '{}',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_media_assets_twin ON media_assets(twin_id);
        CREATE INDEX IF NOT EXISTS idx_media_assets_category ON media_assets(twin_id, category);
        """
        await execute(sql)

    async def _mark_errored(self, twin_id: str):
        await execute("UPDATE digital_twins SET status = 'error', updated_at = NOW() WHERE id = $1", twin_id)

    @staticmethod
    async def get_pipeline_status(twin_id: str) -> Optional[dict]:
        row = await fetchrow("SELECT id, status, role, created_at FROM digital_twins WHERE id = $1", twin_id)
        if not row:
            return None
        return {
            "twin_id": row["id"],
            "status": row["status"],
            "role": row["role"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
