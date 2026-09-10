"""Organization Memory — two-layer memory system.

Layer 1: Personal Digital Twin Memory (specific to one digital employee)
Layer 2: Organization Memory (shared knowledge across all employees)

Examples:
- Hospital: policies, treatment protocols, meeting decisions, medical updates, research
- Business: company policies, product updates, meeting decisions, sales strategies, FAQs

The Learning Engine decides whether extracted knowledge belongs to the Digital Twin
or to the Organization.
"""

import json
import uuid
from typing import Optional, List
from datetime import datetime

from dreamtalk.backend.db.database import execute, fetchrow, fetch


class OrgMemory:
    """Two-layer memory system for organizations."""

    TABLE = "org_memory_entries"

    @staticmethod
    async def ensure_table():
        sql = """
        CREATE TABLE IF NOT EXISTS org_memory_entries (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id            UUID REFERENCES organizations(id) ON DELETE CASCADE,
            department_id     UUID REFERENCES departments(id) ON DELETE SET NULL,
            twin_id           UUID REFERENCES digital_twins(id) ON DELETE SET NULL,
            employee_id       UUID REFERENCES digital_employees(id) ON DELETE SET NULL,

            memory_layer      VARCHAR(20) NOT NULL DEFAULT 'personal',
                -- 'personal' = Layer 1: owned by one digital employee
                -- 'organization' = Layer 2: shared across org

            title             VARCHAR(512) NOT NULL,
            content           TEXT NOT NULL,
            content_type      VARCHAR(50) DEFAULT 'memory',

            -- Scope & access
            scope             VARCHAR(20) DEFAULT 'private',
                -- 'private' = only the owning twin/employee
                -- 'department' = visible to department
                -- 'organization' = visible to entire org

            -- Source tracking
            source            VARCHAR(50) DEFAULT 'conversation',
            source_assignment_id UUID REFERENCES assignments(id) ON DELETE SET NULL,
            source_excerpt    TEXT,

            -- Approval
            is_approved       BOOLEAN DEFAULT FALSE,
            approved_by        UUID REFERENCES users(id) ON DELETE SET NULL,
            approved_at        TIMESTAMPTZ,

            -- Version
            version           VARCHAR(20) DEFAULT '1.0.0',
            is_active         BOOLEAN DEFAULT TRUE,

            tags              JSONB DEFAULT '[]',
            metadata          JSONB DEFAULT '{}',

            created_at        TIMESTAMPTZ DEFAULT NOW(),
            updated_at        TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_orgmem_org ON org_memory_entries(org_id);
        CREATE INDEX IF NOT EXISTS idx_orgmem_twin ON org_memory_entries(twin_id);
        CREATE INDEX IF NOT EXISTS idx_orgmem_layer ON org_memory_entries(memory_layer);
        CREATE INDEX IF NOT EXISTS idx_orgmem_scope ON org_memory_entries(scope);
        CREATE INDEX IF NOT EXISTS idx_orgmem_approved ON org_memory_entries(is_approved);
        CREATE INDEX IF NOT EXISTS idx_orgmem_content_type ON org_memory_entries(content_type);
        """
        await execute(sql)

    # ─── Layer 1: Personal Memory ───────────────────────────────────────

    @staticmethod
    async def store_personal_memory(
        twin_id: str,
        title: str,
        content: str,
        content_type: str = "memory",
        source: str = "conversation",
        source_assignment_id: Optional[str] = None,
        source_excerpt: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        mem_id = str(uuid.uuid4())
        sql = """
        INSERT INTO org_memory_entries
            (id, twin_id, memory_layer, title, content, content_type, scope,
             source, source_assignment_id, source_excerpt, tags, metadata)
        VALUES ($1, $2, 'personal', $3, $4, $5, 'private',
                $6, $7, $8, $9::jsonb, $10::jsonb)
        """
        await execute(sql, mem_id, twin_id, title, content, content_type,
                      source, source_assignment_id, source_excerpt,
                      json.dumps(tags or []), json.dumps(metadata or {}))
        return mem_id

    @staticmethod
    async def get_personal_memories(twin_id: str, limit: int = 50) -> List[dict]:
        rows = await fetch(
            "SELECT id, title, content, content_type, source, tags, created_at "
            "FROM org_memory_entries WHERE twin_id = $1 AND memory_layer = 'personal' AND is_active = TRUE "
            "ORDER BY created_at DESC LIMIT $2",
            twin_id, limit,
        )
        return [dict(r) for r in rows]

    @staticmethod
    async def search_personal_memory(twin_id: str, query: str, limit: int = 20) -> List[dict]:
        rows = await fetch(
            "SELECT id, title, content, content_type, source, created_at "
            "FROM org_memory_entries WHERE twin_id = $1 AND memory_layer = 'personal' AND is_active = TRUE "
            "AND (title ILIKE $3 OR content ILIKE $3) ORDER BY created_at DESC LIMIT $2",
            twin_id, limit, f"%{query}%",
        )
        return [dict(r) for r in rows]

    # ─── Layer 2: Organization Memory ──────────────────────────────────

    @staticmethod
    async def store_org_memory(
        org_id: str,
        title: str,
        content: str,
        content_type: str = "knowledge",
        department_id: Optional[str] = None,
        source: str = "manual",
        source_assignment_id: Optional[str] = None,
        source_employee_id: Optional[str] = None,
        scope: str = "organization",
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        auto_approve: bool = False,
    ) -> str:
        mem_id = str(uuid.uuid4())
        is_approved = auto_approve
        sql = """
        INSERT INTO org_memory_entries
            (id, org_id, department_id, memory_layer, title, content, content_type,
             scope, source, source_assignment_id, source_excerpt,
             is_approved, tags, metadata)
        VALUES ($1, $2, $3, 'organization', $4, $5, $6, $7,
                $8, $9, $10, $11, $12::jsonb, $13::jsonb)
        """
        await execute(sql, mem_id, org_id, department_id, title, content, content_type,
                      scope, source, source_assignment_id, None,
                      is_approved, json.dumps(tags or []), json.dumps(metadata or {}))
        return mem_id

    @staticmethod
    async def get_org_memories(
        org_id: str,
        department_id: Optional[str] = None,
        only_approved: bool = True,
        content_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        conditions = ["org_id = $1", "memory_layer = 'organization'", "is_active = TRUE"]
        params = [org_id]
        param_idx = 2

        if department_id:
            conditions.append(f"(department_id = ${param_idx} OR department_id IS NULL)")
            params.append(department_id)
            param_idx += 1

        if only_approved:
            conditions.append("is_approved = TRUE")

        if content_type:
            conditions.append(f"content_type = ${param_idx}")
            params.append(content_type)
            param_idx += 1

        where = " AND ".join(conditions)
        sql = f"SELECT id, title, content, content_type, scope, department_id, tags, is_approved, created_at FROM org_memory_entries WHERE {where} ORDER BY created_at DESC LIMIT ${param_idx}"
        params.append(limit)

        rows = await fetch(sql, *params)
        return [dict(r) for r in rows]

    @staticmethod
    async def promote_to_org(
        memory_id: str,
        org_id: str,
        approved_by: str,
    ) -> bool:
        """Promote a personal memory to organization memory."""
        row = await fetchrow(
            "SELECT twin_id, title, content, content_type, tags FROM org_memory_entries WHERE id = $1",
            memory_id,
        )
        if not row:
            return False

        # Create new org memory entry
        mem_id = str(uuid.uuid4())
        sql = """
        INSERT INTO org_memory_entries
            (id, org_id, memory_layer, title, content, content_type, scope,
             source, is_approved, approved_by, approved_at, tags)
        VALUES ($1, $2, 'organization', $3, $4, $5, 'organization',
                'promoted_from_personal', TRUE, $6, NOW(), $7::jsonb)
        """
        await execute(sql, mem_id, org_id, row["title"], row["content"],
                      row["content_type"], approved_by, json.dumps(row["tags"] or []))

        # Mark original as promoted
        await execute(
            "UPDATE org_memory_entries SET metadata = metadata || '{\"promoted_to_org\": true}'::jsonb WHERE id = $1",
            memory_id,
        )
        return True

    @staticmethod
    async def approve(memory_id: str, approved_by: str) -> bool:
        await execute(
            "UPDATE org_memory_entries SET is_approved = TRUE, approved_by = $1, approved_at = NOW() WHERE id = $2",
            approved_by, memory_id,
        )
        return True

    @staticmethod
    async def reject(memory_id: str):
        await execute(
            "UPDATE org_memory_entries SET is_active = FALSE WHERE id = $1",
            memory_id,
        )

    @staticmethod
    async def search_org_memory(org_id: str, query: str, limit: int = 20) -> List[dict]:
        rows = await fetch(
            "SELECT id, title, content, content_type, scope, department_id, tags, is_approved, created_at "
            "FROM org_memory_entries WHERE org_id = $1 AND memory_layer = 'organization' AND is_active = TRUE "
            "AND is_approved = TRUE AND (title ILIKE $3 OR content ILIKE $3) "
            "ORDER BY created_at DESC LIMIT $2",
            org_id, limit, f"%{query}%",
        )
        return [dict(r) for r in rows]

    @staticmethod
    async def get_pending_approvals(org_id: str, limit: int = 20) -> List[dict]:
        rows = await fetch(
            "SELECT id, title, content, content_type, source, tags, created_at "
            "FROM org_memory_entries WHERE org_id = $1 AND memory_layer = 'organization' "
            "AND is_approved = FALSE AND is_active = TRUE ORDER BY created_at DESC LIMIT $2",
            org_id, limit,
        )
        return [dict(r) for r in rows]

    @staticmethod
    async def delete(memory_id: str):
        await execute("DELETE FROM org_memory_entries WHERE id = $1", memory_id)
