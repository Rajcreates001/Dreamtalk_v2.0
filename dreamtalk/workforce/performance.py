from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.workforce.models import (
    PerformanceMetrics, SupervisorReview, DigitalEmployee,
    Assignment, AssignmentOutput,
)
from dreamtalk.workforce.engine import WorkforceEngine
from dreamtalk.workforce.assignments import AssignmentEngine

logger = logging.getLogger("dreamtalk.workforce.performance")


class PerformanceEngine:
    """Employee KPIs, supervisor reviews, and performance analytics."""

    @staticmethod
    async def submit_review(
        assignment_id: str,
        reviewer_id: str,
        rating: float,
        comments: str = "",
        corrections: list[str] = None,
        promote_to_training: bool = False,
    ) -> SupervisorReview:
        review_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        assignment = await AssignmentEngine.get(assignment_id)
        if not assignment:
            raise ValueError("Assignment not found")

        await execute(
            """INSERT INTO supervisor_reviews
               (id, assignment_id, employee_id, reviewer_id, rating, comments,
                corrections, promote_to_training, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10)""",
            review_id, assignment_id, assignment.employee_id,
            reviewer_id, rating, comments,
            json.dumps(corrections or []),
            promote_to_training, now, now,
        )

        # Update assignment with review
        await execute(
            """UPDATE assignments SET
               reviewed_by = $1, review_rating = $2, review_notes = $3, needs_review = FALSE, updated_at = $4
               WHERE id = $5""",
            reviewer_id, rating, comments, now, assignment_id,
        )

        # Update employee avg rating
        emp = await WorkforceEngine.get_employee(assignment.employee_id)
        if emp:
            total = emp.completed_assignments
            old_total = (total * emp.avg_rating) if total > 0 else 0
            new_avg = (old_total + rating) / (total + 1) if total > 0 else rating
            await WorkforceEngine.update_employee(
                assignment.employee_id,
                avg_rating=round(new_avg, 2),
                human_escalations=emp.human_escalations + (1 if corrections else 0),
            )

        # If corrections and retrain flag, trigger learning pipeline
        if corrections and promote_to_training:
            logger.info("Retrain triggered for employee %s from review %s", assignment.employee_id, review_id)

        return await PerformanceEngine.get_review(review_id)

    @staticmethod
    async def get_review(review_id: str) -> Optional[SupervisorReview]:
        row = await fetchrow("SELECT * FROM supervisor_reviews WHERE id = $1", review_id)
        if not row:
            return None
        return PerformanceEngine._row_to_review(row)

    @staticmethod
    async def get_employee_reviews(employee_id: str, limit: int = 50) -> list[SupervisorReview]:
        rows = await fetch(
            "SELECT * FROM supervisor_reviews WHERE employee_id = $1 ORDER BY created_at DESC LIMIT $2",
            employee_id, limit,
        )
        return [PerformanceEngine._row_to_review(r) for r in rows]

    @staticmethod
    async def get_pending_reviews(org_id: str, limit: int = 50) -> list[SupervisorReview]:
        rows = await fetch(
            """SELECT sr.* FROM supervisor_reviews sr
               JOIN assignments a ON a.id = sr.assignment_id
               WHERE a.org_id = $1 AND a.needs_review = TRUE
               ORDER BY sr.created_at DESC LIMIT $2""",
            org_id, limit,
        )
        return [PerformanceEngine._row_to_review(r) for r in rows]

    @staticmethod
    async def compute_metrics(employee_id: str) -> PerformanceMetrics:
        """Compute performance metrics for an employee."""
        emp = await WorkforceEngine.get_employee(employee_id)
        if not emp:
            raise ValueError("Employee not found")

        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1).isoformat()

        stats = await fetchrow(
            """SELECT
               COUNT(*) AS total_assignments,
               COALESCE(SUM(duration_minutes), 0) AS total_duration,
               COALESCE(AVG(NULLIF(review_rating, 0)), 0) AS avg_rating_val,
               COUNT(*) FILTER (WHERE review_rating IS NOT NULL) AS rating_count
               FROM assignments
               WHERE employee_id = $1 AND is_completed = TRUE
               AND actual_end >= $2""",
            employee_id, period_start,
        )

        reviews = await fetchrow(
            "SELECT COUNT(*) AS corrections_count FROM supervisor_reviews WHERE employee_id = $1",
            employee_id,
        )

        return PerformanceMetrics(
            employee_id=employee_id,
            org_id=emp.org_id,
            period_start=period_start,
            period_end=now.isoformat(),
            assignments_completed=stats["total_assignments"] if stats else 0,
            total_duration_minutes=stats["total_duration"] if stats else 0,
            avg_duration_minutes=round((stats["total_duration"] / stats["total_assignments"]), 1) if stats and stats["total_assignments"] > 0 else 0.0,
            avg_rating=round(float(stats["avg_rating_val"]), 2) if stats else 0.0,
            rating_count=stats["rating_count"] if stats else 0,
            human_escalations=emp.human_escalations,
            escalation_rate=round(emp.human_escalations / max(emp.total_assignments, 1), 3),
            corrections_received=reviews["corrections_count"] if reviews else 0,
            knowledge_contributions=emp.knowledge_contributions,
            utilization_rate=round(emp.current_assignments / max(emp.max_concurrent_assignments, 1), 2),
            total_kpis={
                "assignments_completed": float(stats["total_assignments"]) if stats else 0,
                "avg_rating": float(stats["avg_rating_val"]) if stats else 0.0,
                "human_escalations": float(emp.human_escalations),
            },
        )

    @staticmethod
    async def get_org_metrics(org_id: str) -> dict:
        row = await fetchrow(
            """SELECT
               COUNT(*) AS total_employees,
               COUNT(*) FILTER (WHERE status = 'available') AS available,
               COUNT(*) FILTER (WHERE status IN ('in_meeting', 'in_consultation')) AS busy,
               ROUND(AVG(avg_rating), 2) AS org_avg_rating,
               SUM(completed_assignments) AS total_completed,
               SUM(total_assignments) AS total_assigned,
               SUM(human_escalations) AS total_escalations
               FROM digital_employees WHERE org_id = $1""",
            org_id,
        )
        if not row:
            return {}
        return dict(row)

    @staticmethod
    def _row_to_review(row) -> SupervisorReview:
        def _iso(val):
            return val.isoformat() if hasattr(val, "isoformat") else str(val) if val else ""
        return SupervisorReview(
            id=row["id"],
            assignment_id=row["assignment_id"],
            employee_id=row["employee_id"],
            reviewer_id=row["reviewer_id"],
            rating=float(row["rating"]),
            comments=row.get("comments", ""),
            corrections=json.loads(row["corrections"]) if isinstance(row.get("corrections"), str) else (row.get("corrections") or []),
            promote_to_training=row.get("promote_to_training", False),
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )
