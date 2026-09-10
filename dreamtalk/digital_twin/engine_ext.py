"""Extensions to DigitalTwinEngine for the new Digital Twin Operating System architecture.

Adds pipeline-based creation, personality integration, media repository integration,
and backward-compatible wrappers without modifying the existing engine.py.
"""

from typing import Optional
from datetime import datetime, timezone

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.digital_twin.engine import DigitalTwinEngine
from dreamtalk.digital_twin.models import (
    CreateDigitalTwinRequest, DigitalTwinResponse, TwinStatus, TwinRole,
    UpdateDigitalTwinRequest,
)
from dreamtalk.digital_twin.creation_pipeline import CreationPipeline
from dreamtalk.digital_twin.personality import PersonalityEngine, PersonalityProfile as PersonalityProfileModel
from dreamtalk.digital_twin.learning_orchestrator import LearningOrchestrator
from dreamtalk.media.repository import MediaRepository


class DigitalTwinEngineExt:
    """Extended Digital Twin operations using the new architecture."""

    def __init__(self):
        self.creation_pipeline = CreationPipeline()
        self.media_repo = MediaRepository()

    # ─── Pipeline-Based Creation ──────────────────────────────────────────

    async def create_with_pipeline(
        self,
        user_id: str,
        request: CreateDigitalTwinRequest,
    ) -> dict:
        """Create a Digital Twin using the full 11-step pipeline.

        Returns pipeline execution details including twin_id, media paths,
        and status of each initialization step.
        """
        return await self.creation_pipeline.execute(user_id, request)

    # ─── Personality Management ──────────────────────────────────────────

    async def get_personality(self, twin_id: str) -> Optional[dict]:
        profile = await PersonalityEngine.get(twin_id)
        if not profile:
            # Initialize if not exists (backward compat)
            row = await fetchrow(
                "SELECT role FROM digital_twins WHERE id = $1", twin_id,
            )
            if not row:
                return None
            profile = await PersonalityEngine.initialize(twin_id, row["role"])
        import dataclasses
        return dataclasses.asdict(profile)

    async def update_personality(self, twin_id: str, updates: dict) -> bool:
        return await PersonalityEngine.update(twin_id, updates)

    # ─── Learning ─────────────────────────────────────────────────────────

    async def run_learning_pipeline(
        self,
        twin_id: str,
        conversation_text: str,
        interaction_id: Optional[str] = None,
    ) -> dict:
        row = await fetchrow("SELECT role FROM digital_twins WHERE id = $1", twin_id)
        role = row["role"] if row else "personal"
        summary = await LearningOrchestrator.run_pipeline(
            twin_id=twin_id,
            role=role,
            conversation_text=conversation_text,
            interaction_id=interaction_id,
        )
        import dataclasses
        return dataclasses.asdict(summary)

    async def get_learning_history(self, twin_id: str, limit: int = 20) -> list:
        return await LearningOrchestrator.get_learning_history(twin_id, limit)

    # ─── Media Repository ─────────────────────────────────────────────────

    async def get_media_report(self, twin_id: str) -> Optional[dict]:
        row = await fetchrow(
            "SELECT id, role FROM digital_twins WHERE id = $1", twin_id,
        )
        if not row:
            return None
        media_role = self._map_role(row["role"])
        return self.media_repo.twin_storage_report(twin_id, media_role)

    def _map_role(self, role: str) -> str:
        if role in ("personal", "normal_user"):
            return "normal_user"
        elif role == "healthcare":
            return "healthcare"
        elif role == "business":
            return "business"
        return "normal_user"

    # ─── Full Twin Status ─────────────────────────────────────────────────

    async def get_full_status(self, twin_id: str) -> Optional[dict]:
        """Get comprehensive twin status including all sub-systems."""
        twin = await DigitalTwinEngine.get(twin_id)
        if not twin:
            return None

        personality = await self.get_personality(twin_id)
        media_report = await self.get_media_report(twin_id)
        pipeline_status = await self.creation_pipeline.get_pipeline_status(twin_id)

        return {
            "twin": twin.model_dump() if hasattr(twin, 'model_dump') else str(twin),
            "personality": personality,
            "media": media_report,
            "pipeline": pipeline_status,
        }

    # ─── Folder Management ────────────────────────────────────────────────

    async def ensure_folders(self, twin_id: str) -> bool:
        """Ensure media folders exist for a twin (recreate if missing)."""
        row = await fetchrow(
            "SELECT id, role FROM digital_twins WHERE id = $1", twin_id,
        )
        if not row:
            return False
        media_role = self._map_role(row["role"])
        self.media_repo.create_twin_folders(twin_id, media_role)
        return True

    async def delete_twin_media(self, twin_id: str) -> bool:
        """Delete all media folders for a twin."""
        row = await fetchrow(
            "SELECT id, role FROM digital_twins WHERE id = $1", twin_id,
        )
        if not row:
            return False
        media_role = self._map_role(row["role"])
        self.media_repo.remove_twin_folders(twin_id, media_role)
        return True
