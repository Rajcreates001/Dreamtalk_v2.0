from __future__ import annotations

import logging
from typing import Optional

from dreamtalk.backend.db.database import fetchrow, fetch
from dreamtalk.workforce.models import (
    MissionControlDashboard, EmployeeStatusSummary, WorkforceSummary,
    Organization, DigitalEmployee, Assignment,
)
from dreamtalk.workforce.engine import WorkforceEngine
from dreamtalk.workforce.assignments import AssignmentEngine
from dreamtalk.workforce.knowledge import OrganizationMemory
from dreamtalk.workforce.performance import PerformanceEngine

logger = logging.getLogger("dreamtalk.workforce.mission_control")


class MissionControl:
    """Aggregate data for the Mission Control dashboard."""

    @staticmethod
    async def get_dashboard(org_id: str) -> MissionControlDashboard:
        org = await WorkforceEngine.get_org(org_id)
        if not org:
            raise ValueError(f"Organization {org_id} not found")

        employees = await WorkforceEngine.get_org_employees(org_id)

        # Employee status breakdown
        status_counts = EmployeeStatusSummary(total=len(employees))
        for emp in employees:
            s = emp.status.value
            if s == "available": status_counts.available += 1
            elif s == "in_meeting": status_counts.in_meeting += 1
            elif s == "in_consultation": status_counts.in_consultation += 1
            elif s == "training": status_counts.training += 1
            elif s == "processing": status_counts.processing += 1
            else: status_counts.offline += 1

        # Active and upcoming assignments
        active = await AssignmentEngine.get_active_assignments(org_id)
        all_assignments = await AssignmentEngine.get_org_assignments(org_id, limit=500)

        # Today's completed
        today_completed = sum(
            1 for a in all_assignments
            if a.is_completed and a.actual_end
        )

        # Summary stats
        org_metrics = await PerformanceEngine.get_org_metrics(org_id)
        summary = WorkforceSummary(
            total_employees=len(employees),
            total_departments=len(await WorkforceEngine.get_org_departments(org_id)),
            active_assignments=len(active),
            pending_reviews=sum(1 for a in all_assignments if a.needs_review),
            pending_knowledge=len(await OrganizationMemory.get_pending_approval(org_id)),
            todays_completed=today_completed,
            avg_rating=float(org_metrics.get("org_avg_rating", 0)),
            utilization_rate=round(
                status_counts.in_meeting / max(len(employees), 1), 2,
            ),
            human_escalations_today=int(org_metrics.get("total_escalations", 0)),
        )

        # Top performers
        sorted_emps = sorted(employees, key=lambda e: e.avg_rating, reverse=True)[:5]

        # Alerts
        alerts = []
        for emp in employees:
            if emp.human_escalations > 5:
                alerts.append({
                    "type": "high_escalations",
                    "employee_id": emp.id,
                    "employee_name": emp.name,
                    "message": f"{emp.name} has {emp.human_escalations} human escalations",
                    "severity": "warning",
                })
        if summary.pending_reviews > 0:
            alerts.append({
                "type": "pending_reviews",
                "count": summary.pending_reviews,
                "message": f"{summary.pending_reviews} assignment(s) pending supervisor review",
                "severity": "info",
            })

        return MissionControlDashboard(
            organization=org,
            employee_status=status_counts,
            summary=summary,
            live_sessions=[a for a in active if a.status.value == "in_progress"],
            upcoming_assignments=[a for a in active if a.status.value == "scheduled"],
            pending_reviews=await PerformanceEngine.get_pending_reviews(org_id, limit=20),
            knowledge_pending_approval=await OrganizationMemory.get_pending_approval(org_id),
            top_performers=sorted_emps,
            alerts=alerts,
            kpi_summary={
                "total_employees": len(employees),
                "avg_rating": summary.avg_rating,
                "utilization": summary.utilization_rate,
                "active_sessions": len(active),
                "total_completed": org_metrics.get("total_completed", 0),
            },
        )
