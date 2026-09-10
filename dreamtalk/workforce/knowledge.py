from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.workforce.models import OrgKnowledgeEntry, KnowledgeScope
from dreamtalk.digital_twin.engine import DigitalTwinEngine

logger = logging.getLogger("dreamtalk.workforce.knowledge")


class OrganizationMemory:
    """Shared organizational knowledge that every digital employee can access."""

    @staticmethod
    async def add_entry(
        org_id: str,
        title: str,
        content: str,
        content_type: str = "knowledge",
        scope: KnowledgeScope = KnowledgeScope.ORGANIZATION,
        department_id: str = "",
        source_assignment_id: str = "",
        source_employee_id: str = "",
        approved_by: str = "",
    ) -> OrgKnowledgeEntry:
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            """INSERT INTO org_knowledge_base
               (id, org_id, department_id, source, source_assignment_id, source_employee_id,
                title, content, content_type, scope, approved_by, is_approved, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)""",
            entry_id, org_id, department_id, "meeting" if source_assignment_id else "manual",
            source_assignment_id, source_employee_id,
            title, content, content_type, scope.value,
            approved_by, bool(approved_by), now, now,
        )
        return await OrganizationMemory.get_entry(entry_id)

    @staticmethod
    async def get_entry(entry_id: str) -> Optional[OrgKnowledgeEntry]:
        row = await fetchrow(
            "SELECT * FROM org_knowledge_base WHERE id = $1", entry_id,
        )
        if not row:
            return None
        return OrganizationMemory._row_to_entry(row)

    @staticmethod
    async def get_org_knowledge(
        org_id: str, approved_only: bool = True, limit: int = 100, offset: int = 0,
    ) -> list[OrgKnowledgeEntry]:
        if approved_only:
            rows = await fetch(
                "SELECT * FROM org_knowledge_base WHERE org_id = $1 AND is_approved = TRUE ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
                org_id, limit, offset,
            )
        else:
            rows = await fetch(
                "SELECT * FROM org_knowledge_base WHERE org_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
                org_id, limit, offset,
            )
        return [OrganizationMemory._row_to_entry(r) for r in rows]

    @staticmethod
    async def get_pending_approval(org_id: str) -> list[OrgKnowledgeEntry]:
        rows = await fetch(
            "SELECT * FROM org_knowledge_base WHERE org_id = $1 AND is_approved = FALSE ORDER BY created_at DESC",
            org_id,
        )
        return [OrganizationMemory._row_to_entry(r) for r in rows]

    @staticmethod
    async def promote_from_meeting(
        assignment_id: str,
        org_id: str,
        employee_id: str,
        suggestions: list[str],
        transcript_summary: str,
    ) -> list[OrgKnowledgeEntry]:
        """Promote meeting insights to org knowledge."""
        entries = []
        for suggestion in suggestions[:5]:  # max 5 per meeting
            entry = await OrganizationMemory.add_entry(
                org_id=org_id,
                title=suggestion[:200],
                content=f"Source: Meeting {assignment_id}\n\n{suggestion}\n\nContext: {transcript_summary[:500]}",
                content_type="knowledge",
                scope=KnowledgeScope.ORGANIZATION,
                source_assignment_id=assignment_id,
                source_employee_id=employee_id,
            )
            entries.append(entry)
        return entries

    @staticmethod
    async def approve_entry(entry_id: str, approved_by: str) -> Optional[OrgKnowledgeEntry]:
        now = datetime.now(timezone.utc).isoformat()
        row = await fetchrow(
            "UPDATE org_knowledge_base SET is_approved = TRUE, approved_by = $1, updated_at = $2 WHERE id = $3 RETURNING *",
            approved_by, now, entry_id,
        )
        if not row:
            return None
        return OrganizationMemory._row_to_entry(row)

    @staticmethod
    async def reject_entry(entry_id: str) -> bool:
        r = await fetchrow(
            "DELETE FROM org_knowledge_base WHERE id = $1 RETURNING id", entry_id,
        )
        return r is not None

    @staticmethod
    async def search_knowledge(org_id: str, query: str, limit: int = 20) -> list[OrgKnowledgeEntry]:
        rows = await fetch(
            """SELECT * FROM org_knowledge_base
               WHERE org_id = $1 AND is_approved = TRUE
               AND (title ILIKE $2 OR content ILIKE $2)
               ORDER BY updated_at DESC LIMIT $3""",
            org_id, f"%{query}%", limit,
        )
        return [OrganizationMemory._row_to_entry(r) for r in rows]

    @staticmethod
    def _row_to_entry(row) -> OrgKnowledgeEntry:
        def _iso(val):
            return val.isoformat() if hasattr(val, "isoformat") else str(val) if val else ""
        return OrgKnowledgeEntry(
            id=row["id"], org_id=row["org_id"],
            department_id=row.get("department_id", ""),
            source=row.get("source", ""),
            source_assignment_id=str(row["source_assignment_id"]) if row.get("source_assignment_id") else "",
            source_employee_id=str(row["source_employee_id"]) if row.get("source_employee_id") else "",
            title=row["title"], content=row["content"],
            content_type=row.get("content_type", "knowledge"),
            scope=KnowledgeScope(row["scope"]) if row.get("scope") else KnowledgeScope.ORGANIZATION,
            is_approved=row.get("is_approved", False),
            approved_by=str(row["approved_by"]) if row.get("approved_by") else None,
            version=row.get("version", "1.0.0"),
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )
