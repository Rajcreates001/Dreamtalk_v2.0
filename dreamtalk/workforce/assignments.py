from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.workforce.models import (
    Assignment, CreateAssignmentRequest, AssignmentStatus, AssignmentType, EmployeeStatus,
    DigitalEmployee, AssignmentOutput,
)
from dreamtalk.workforce.engine import WorkforceEngine
from dreamtalk.digital_twin.engine import DigitalTwinEngine

logger = logging.getLogger("dreamtalk.workforce.assignments")


class AssignmentEngine:
    """Create, schedule, execute, and monitor assignments for digital employees."""

    @staticmethod
    async def create(user_id: str, req: CreateAssignmentRequest) -> Assignment:
        assignment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await execute(
            """INSERT INTO assignments
               (id, org_id, department_id, employee_id, assigned_by, assignment_type,
                title, description, scheduled_start, scheduled_end, priority,
                instructions, agenda, patient_name, patient_id, meeting_link, participants,
                status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)""",
            assignment_id, req.org_id, req.department_id, req.employee_id,
            user_id, req.assignment_type.value,
            req.title, req.description, req.scheduled_start, req.scheduled_end,
            req.priority, req.instructions, req.agenda,
            req.patient_name, req.patient_id, req.meeting_link,
            json.dumps(req.participants) if req.participants else "[]",
            AssignmentStatus.SCHEDULED.value, now, now,
        )

        # Update employee assignment count
        emp = await WorkforceEngine.get_employee(req.employee_id)
        if emp:
            await WorkforceEngine.update_employee(
                req.employee_id,
                current_assignments=emp.current_assignments + 1,
                total_assignments=emp.total_assignments + 1,
            )

        return await AssignmentEngine.get(assignment_id)

    @staticmethod
    async def get(assignment_id: str) -> Optional[Assignment]:
        row = await fetchrow("SELECT * FROM assignments WHERE id = $1", assignment_id)
        if not row:
            return None
        return AssignmentEngine._row_to_assignment(row)

    @staticmethod
    async def get_org_assignments(org_id: str, limit: int = 100, offset: int = 0) -> list[Assignment]:
        rows = await fetch(
            "SELECT * FROM assignments WHERE org_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            org_id, limit, offset,
        )
        return [AssignmentEngine._row_to_assignment(r) for r in rows]

    @staticmethod
    async def get_employee_assignments(employee_id: str, limit: int = 50) -> list[Assignment]:
        rows = await fetch(
            "SELECT * FROM assignments WHERE employee_id = $1 ORDER BY created_at DESC LIMIT $2",
            employee_id, limit,
        )
        return [AssignmentEngine._row_to_assignment(r) for r in rows]

    @staticmethod
    async def get_active_assignments(org_id: str) -> list[Assignment]:
        rows = await fetch(
            """SELECT * FROM assignments
               WHERE org_id = $1 AND status IN ('scheduled', 'in_progress')
               ORDER BY scheduled_start ASC""",
            org_id,
        )
        return [AssignmentEngine._row_to_assignment(r) for r in rows]

    @staticmethod
    async def start(assignment_id: str) -> Optional[Assignment]:
        """Mark assignment as in-progress and set employee status."""
        now = datetime.now(timezone.utc).isoformat()
        row = await fetchrow(
            "SELECT employee_id FROM assignments WHERE id = $1", assignment_id,
        )
        if not row:
            return None

        await execute(
            "UPDATE assignments SET status = $1, actual_start = $2, updated_at = $3 WHERE id = $4",
            AssignmentStatus.IN_PROGRESS.value, now, now, assignment_id,
        )

        emp = await WorkforceEngine.get_employee(row["employee_id"])
        if emp:
            new_status = EmployeeStatus.IN_MEETING
            await WorkforceEngine.set_employee_status(row["employee_id"], new_status)

        return await AssignmentEngine.get(assignment_id)

    @staticmethod
    async def complete(
        assignment_id: str, output: Optional[AssignmentOutput] = None,
    ) -> Optional[Assignment]:
        """Complete assignment, save output, update employee stats."""
        now = datetime.now(timezone.utc).isoformat()
        row = await fetchrow(
            "SELECT employee_id, actual_start, org_id FROM assignments WHERE id = $1",
            assignment_id,
        )
        if not row:
            return None

        output_id = None
        if output:
            output.id = str(uuid.uuid4())
            output.assignment_id = assignment_id
            output.org_id = row["org_id"]
            output.employee_id = row["employee_id"]
            output.created_at = now
            output_id = output.id

            await execute(
                """INSERT INTO assignment_outputs
                   (id, assignment_id, org_id, employee_id,
                    raw_transcript, clean_transcript, summary,
                    decisions, action_items, risks, key_topics, questions_asked, follow_ups,
                    sentiment_analysis, diagnosis_summary, prescription_draft,
                    recommendations, follow_up_reminders,
                    knowledge_promotion_suggestions, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb,
                           $10::jsonb, $11::jsonb, $12::jsonb, $13::jsonb,
                           $14::jsonb, $15, $16, $17::jsonb, $18::jsonb,
                           $19::jsonb, $20)""",
                output.id, output.assignment_id, output.org_id, output.employee_id,
                output.raw_transcript, output.clean_transcript, output.summary,
                json.dumps(output.decisions), json.dumps(output.action_items),
                json.dumps(output.risks), json.dumps(output.key_topics),
                json.dumps(output.questions_asked), json.dumps(output.follow_ups),
                json.dumps(output.sentiment_analysis),
                output.diagnosis_summary, output.prescription_draft,
                json.dumps(output.recommendations), json.dumps(output.follow_up_reminders),
                json.dumps(output.knowledge_promotion_suggestions),
                now,
            )

        # Calculate duration
        duration = 0
        if row["actual_start"]:
            try:
                start = row["actual_start"]
                if hasattr(start, "timestamp"):
                    duration = int((datetime.now(timezone.utc) - start).total_seconds() / 60)
            except Exception:
                pass

        await execute(
            """UPDATE assignments SET
               status = $1, actual_end = $2, duration_minutes = $3, output_id = $4,
               needs_review = $5, is_completed = TRUE, updated_at = $6
               WHERE id = $7""",
            AssignmentStatus.COMPLETED.value, now, duration, output_id,
            True if output and output.knowledge_promotion_suggestions else False,
            now, assignment_id,
        )

        # Update employee
        emp = await WorkforceEngine.get_employee(row["employee_id"])
        if emp:
            await WorkforceEngine.update_employee(
                row["employee_id"],
                status=EmployeeStatus.AVAILABLE.value,
                current_assignments=max(0, emp.current_assignments - 1),
                completed_assignments=emp.completed_assignments + 1,
            )

        return await AssignmentEngine.get(assignment_id)

    @staticmethod
    async def cancel(assignment_id: str) -> Optional[Assignment]:
        now = datetime.now(timezone.utc).isoformat()
        row = await fetchrow(
            "SELECT employee_id FROM assignments WHERE id = $1", assignment_id,
        )
        if not row:
            return None

        await execute(
            "UPDATE assignments SET status = $1, updated_at = $2 WHERE id = $3",
            AssignmentStatus.CANCELLED.value, now, assignment_id,
        )

        await WorkforceEngine.set_employee_status(
            row["employee_id"], EmployeeStatus.AVAILABLE,
        )

        return await AssignmentEngine.get(assignment_id)

    @staticmethod
    async def needs_review(assignment_id: str) -> Optional[Assignment]:
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            "UPDATE assignments SET status = $1, needs_review = TRUE, updated_at = $2 WHERE id = $3",
            AssignmentStatus.NEEDS_REVIEW.value, now, assignment_id,
        )
        return await AssignmentEngine.get(assignment_id)

    @staticmethod
    def _row_to_assignment(row) -> Assignment:
        def _iso(val):
            return val.isoformat() if hasattr(val, "isoformat") else str(val) if val else ""
        def _safe_json(val):
            if isinstance(val, (list, dict)):
                return val
            if val is None:
                return []
            try:
                return json.loads(val) if isinstance(val, str) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return Assignment(
            id=row["id"], org_id=row["org_id"],
            department_id=row.get("department_id", ""),
            employee_id=row["employee_id"],
            assigned_by=row["assigned_by"],
            assignment_type=AssignmentType(row["assignment_type"]),
            title=row["title"],
            description=row.get("description", ""),
            scheduled_start=_iso(row.get("scheduled_start")) if row.get("scheduled_start") else None,
            scheduled_end=_iso(row.get("scheduled_end")) if row.get("scheduled_end") else None,
            actual_start=_iso(row.get("actual_start")) if row.get("actual_start") else None,
            actual_end=_iso(row.get("actual_end")) if row.get("actual_end") else None,
            duration_minutes=row.get("duration_minutes", 0),
            priority=row.get("priority", "normal"),
            instructions=row.get("instructions", ""),
            status=AssignmentStatus(row.get("status", "scheduled")),
            is_completed=row.get("is_completed", False),
            output_id=str(row["output_id"]) if row.get("output_id") else None,
            needs_review=row.get("needs_review", False),
            patient_name=row.get("patient_name", ""),
            patient_id=row.get("patient_id", ""),
            meeting_link=row.get("meeting_link", ""),
            agenda=row.get("agenda", ""),
            participants=_safe_json(row.get("participants")),
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )
