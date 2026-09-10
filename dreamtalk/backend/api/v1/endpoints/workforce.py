from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from dreamtalk.backend.api.v1.endpoints.auth import get_current_user
from dreamtalk.workforce.models import (
    CreateOrganizationRequest, CreateDepartmentRequest, CreateEmployeeRequest,
    CreateAssignmentRequest, OrgType, AssignmentType, KnowledgeScope,
)
from dreamtalk.workforce.engine import WorkforceEngine
from dreamtalk.workforce.assignments import AssignmentEngine
from dreamtalk.workforce.meetings import MeetingIntelligence
from dreamtalk.workforce.knowledge import OrganizationMemory
from dreamtalk.workforce.performance import PerformanceEngine
from dreamtalk.workforce.mission_control import MissionControl
from dreamtalk.workforce.org_memory import OrgMemory

router = APIRouter(prefix="/api/v1/workforce", tags=["AI Workforce Platform"])


@router.get("/")
async def workforce_root():
    """Workforce API root — lists available endpoints."""
    return {
        "service": "DreamTalk AI Workforce Platform",
        "version": "0.5.0",
        "endpoints": {
            "organizations": "/api/v1/workforce/organizations",
            "departments": "/api/v1/workforce/organizations/{org_id}/departments",
            "employees": "/api/v1/workforce/organizations/{org_id}/employees",
            "assignments": "/api/v1/workforce/assignments",
            "knowledge": "/api/v1/workforce/organizations/{org_id}/knowledge",
            "mission_control": "/api/v1/workforce/organizations/{org_id}/mission-control",
            "memory": "/api/v1/workforce/organizations/{org_id}/memory",
        },
        "auth_required": True,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ORGANIZATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/organizations", status_code=201)
async def create_org(req: CreateOrganizationRequest, current_user: dict = Depends(get_current_user)):
    return (await WorkforceEngine.create_org(current_user["sub"], req)).model_dump()


@router.get("/organizations")
async def list_orgs(current_user: dict = Depends(get_current_user)):
    return [o.model_dump() for o in await WorkforceEngine.get_user_orgs(current_user["sub"])]


@router.get("/organizations/{org_id}")
async def get_org(org_id: str, current_user: dict = Depends(get_current_user)):
    org = await WorkforceEngine.get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org.model_dump()


@router.put("/organizations/{org_id}")
async def update_org(org_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    org = await WorkforceEngine.update_org(org_id, **data)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org.model_dump()


@router.delete("/organizations/{org_id}")
async def delete_org(org_id: str, current_user: dict = Depends(get_current_user)):
    if not await WorkforceEngine.delete_org(org_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"detail": "Organization deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# DEPARTMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/organizations/{org_id}/departments", status_code=201)
async def create_department(org_id: str, req: CreateDepartmentRequest, current_user: dict = Depends(get_current_user)):
    req.org_id = org_id
    return (await WorkforceEngine.create_department(req)).model_dump()


@router.get("/organizations/{org_id}/departments")
async def list_departments(org_id: str, current_user: dict = Depends(get_current_user)):
    return [d.model_dump() for d in await WorkforceEngine.get_org_departments(org_id)]


@router.get("/departments/{dept_id}")
async def get_department(dept_id: str, current_user: dict = Depends(get_current_user)):
    dept = await WorkforceEngine.get_department(dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept.model_dump()


@router.put("/departments/{dept_id}")
async def update_department(dept_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    dept = await WorkforceEngine.update_department(dept_id, **data)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept.model_dump()


@router.delete("/departments/{dept_id}")
async def delete_department(dept_id: str, current_user: dict = Depends(get_current_user)):
    if not await WorkforceEngine.delete_department(dept_id):
        raise HTTPException(status_code=404, detail="Department not found")
    return {"detail": "Department deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# DIGITAL EMPLOYEES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/organizations/{org_id}/employees", status_code=201)
async def create_employee(org_id: str, req: CreateEmployeeRequest, current_user: dict = Depends(get_current_user)):
    req.org_id = org_id
    return (await WorkforceEngine.create_employee(req)).model_dump()


@router.get("/organizations/{org_id}/employees")
async def list_employees(org_id: str, current_user: dict = Depends(get_current_user)):
    return [e.model_dump() for e in await WorkforceEngine.get_org_employees(org_id)]


@router.get("/employees/{emp_id}")
async def get_employee(emp_id: str, current_user: dict = Depends(get_current_user)):
    emp = await WorkforceEngine.get_employee(emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp.model_dump()


@router.put("/employees/{emp_id}")
async def update_employee(emp_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    emp = await WorkforceEngine.update_employee(emp_id, **data)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp.model_dump()


@router.delete("/employees/{emp_id}")
async def delete_employee(emp_id: str, current_user: dict = Depends(get_current_user)):
    if not await WorkforceEngine.delete_employee(emp_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"detail": "Employee deleted"}


@router.get("/departments/{dept_id}/employees")
async def list_dept_employees(dept_id: str, current_user: dict = Depends(get_current_user)):
    return [e.model_dump() for e in await WorkforceEngine.get_dept_employees(dept_id)]


# ═══════════════════════════════════════════════════════════════════════════════
# ASSIGNMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/assignments", status_code=201)
async def create_assignment(req: CreateAssignmentRequest, current_user: dict = Depends(get_current_user)):
    return (await AssignmentEngine.create(current_user["sub"], req)).model_dump()


@router.get("/assignments/{assignment_id}")
async def get_assignment(assignment_id: str, current_user: dict = Depends(get_current_user)):
    a = await AssignmentEngine.get(assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a.model_dump()


@router.get("/organizations/{org_id}/assignments")
async def list_org_assignments(org_id: str, current_user: dict = Depends(get_current_user), limit: int = 100, offset: int = 0):
    return [a.model_dump() for a in await AssignmentEngine.get_org_assignments(org_id, limit, offset)]


@router.get("/organizations/{org_id}/assignments/active")
async def list_active_assignments(org_id: str, current_user: dict = Depends(get_current_user)):
    return [a.model_dump() for a in await AssignmentEngine.get_active_assignments(org_id)]


@router.get("/employees/{emp_id}/assignments")
async def list_employee_assignments(emp_id: str, current_user: dict = Depends(get_current_user), limit: int = 50):
    return [a.model_dump() for a in await AssignmentEngine.get_employee_assignments(emp_id, limit)]


@router.post("/assignments/{assignment_id}/start")
async def start_assignment(assignment_id: str, current_user: dict = Depends(get_current_user)):
    a = await AssignmentEngine.start(assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a.model_dump()


@router.post("/assignments/{assignment_id}/complete")
async def complete_assignment(
    assignment_id: str,
    raw_transcript: str = "",
    current_user: dict = Depends(get_current_user),
):
    a = await AssignmentEngine.get(assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")

    output = None
    if raw_transcript:
        intelligence = MeetingIntelligence()
        output = await intelligence.process_transcript(
            assignment_id=assignment_id,
            org_id=a.org_id,
            employee_id=a.employee_id,
            raw_transcript=raw_transcript,
        )

    result = await AssignmentEngine.complete(assignment_id, output)
    if not result:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return result.model_dump()


@router.post("/assignments/{assignment_id}/cancel")
async def cancel_assignment(assignment_id: str, current_user: dict = Depends(get_current_user)):
    a = await AssignmentEngine.cancel(assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a.model_dump()


# ═══════════════════════════════════════════════════════════════════════════════
# MEETING INTELLIGENCE & OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/assignments/{assignment_id}/process-transcript")
async def process_transcript(
    assignment_id: str,
    raw_transcript: str,
    current_user: dict = Depends(get_current_user),
):
    a = await AssignmentEngine.get(assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    intelligence = MeetingIntelligence()
    output = await intelligence.process_transcript(
        assignment_id=assignment_id,
        org_id=a.org_id,
        employee_id=a.employee_id,
        raw_transcript=raw_transcript,
    )
    return output.model_dump()


# ═══════════════════════════════════════════════════════════════════════════════
# ORGANIZATION KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/organizations/{org_id}/knowledge")
async def list_knowledge(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    approved_only: bool = True,
    limit: int = 100,
    offset: int = 0,
):
    return [k.model_dump() for k in await OrganizationMemory.get_org_knowledge(org_id, approved_only, limit, offset)]


@router.get("/organizations/{org_id}/knowledge/pending")
async def pending_knowledge(org_id: str, current_user: dict = Depends(get_current_user)):
    return [k.model_dump() for k in await OrganizationMemory.get_pending_approval(org_id)]


@router.post("/organizations/{org_id}/knowledge")
async def add_knowledge(
    org_id: str,
    title: str,
    content: str,
    content_type: str = "knowledge",
    current_user: dict = Depends(get_current_user),
):
    entry = await OrganizationMemory.add_entry(
        org_id=org_id, title=title, content=content, content_type=content_type,
        approved_by=current_user["sub"],
    )
    return entry.model_dump()


@router.post("/knowledge/{entry_id}/approve")
async def approve_knowledge(entry_id: str, current_user: dict = Depends(get_current_user)):
    entry = await OrganizationMemory.approve_entry(entry_id, current_user["sub"])
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry.model_dump()


@router.delete("/knowledge/{entry_id}")
async def reject_knowledge(entry_id: str, current_user: dict = Depends(get_current_user)):
    if not await OrganizationMemory.reject_entry(entry_id):
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return {"detail": "Knowledge entry deleted"}


@router.get("/organizations/{org_id}/knowledge/search")
async def search_knowledge(org_id: str, q: str, current_user: dict = Depends(get_current_user)):
    return [k.model_dump() for k in await OrganizationMemory.search_knowledge(org_id, q)]


@router.post("/assignments/{assignment_id}/promote-knowledge")
async def promote_meeting_knowledge(
    assignment_id: str,
    current_user: dict = Depends(get_current_user),
):
    a = await AssignmentEngine.get(assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    entries = await OrganizationMemory.promote_from_meeting(
        assignment_id=assignment_id,
        org_id=a.org_id,
        employee_id=a.employee_id,
        suggestions=[f"Knowledge from {a.title}"],
        transcript_summary="",
    )
    return [e.model_dump() for e in entries]


# ═══════════════════════════════════════════════════════════════════════════════
# SUPERVISOR REVIEWS & PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/assignments/{assignment_id}/review")
async def submit_review(
    assignment_id: str,
    rating: float,
    comments: str = "",
    corrections: list[str] = None,
    promote_to_training: bool = False,
    current_user: dict = Depends(get_current_user),
):
    review = await PerformanceEngine.submit_review(
        assignment_id=assignment_id,
        reviewer_id=current_user["sub"],
        rating=rating,
        comments=comments,
        corrections=corrections,
        promote_to_training=promote_to_training,
    )
    return review.model_dump()


@router.get("/employees/{emp_id}/reviews")
async def employee_reviews(emp_id: str, current_user: dict = Depends(get_current_user), limit: int = 50):
    return [r.model_dump() for r in await PerformanceEngine.get_employee_reviews(emp_id, limit)]


@router.get("/employees/{emp_id}/metrics")
async def employee_metrics(emp_id: str, current_user: dict = Depends(get_current_user)):
    return (await PerformanceEngine.compute_metrics(emp_id)).model_dump()


@router.get("/organizations/{org_id}/metrics")
async def org_metrics(org_id: str, current_user: dict = Depends(get_current_user)):
    return await PerformanceEngine.get_org_metrics(org_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MISSION CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/organizations/{org_id}/mission-control")
async def mission_control(org_id: str, current_user: dict = Depends(get_current_user)):
    try:
        dashboard = await MissionControl.get_dashboard(org_id)
        return dashboard.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ORGANIZATION MEMORY (Two-layer: personal + org shared)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/organizations/{org_id}/memory")
async def add_org_memory(
    org_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Add an organization memory entry (Layer 2 — shared)."""
    mem_id = await OrgMemory.store_org_memory(
        org_id=org_id,
        title=body.get("title", ""),
        content=body.get("content", ""),
        content_type=body.get("content_type", "knowledge"),
        department_id=body.get("department_id"),
        source=body.get("source", "manual"),
        scope=body.get("scope", "organization"),
        tags=body.get("tags"),
        auto_approve=body.get("auto_approve", False),
    )
    return {"id": mem_id, "status": "created"}


@router.get("/organizations/{org_id}/memory")
async def list_org_memory(
    org_id: str,
    department_id: Optional[str] = None,
    approved: bool = True,
    content_type: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """List organization memory entries (Layer 2 — shared)."""
    entries = await OrgMemory.get_org_memories(
        org_id=org_id,
        department_id=department_id,
        only_approved=approved,
        content_type=content_type,
        limit=limit,
    )
    return entries


@router.get("/organizations/{org_id}/memory/search")
async def search_org_memory(
    org_id: str,
    q: str,
    current_user: dict = Depends(get_current_user),
):
    """Search organization memory."""
    results = await OrgMemory.search_org_memory(org_id, q)
    return results


@router.get("/organizations/{org_id}/memory/pending")
async def pending_org_memory(
    org_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get pending organization memory approvals."""
    entries = await OrgMemory.get_pending_approvals(org_id)
    return entries


@router.post("/organizations/{org_id}/memory/{memory_id}/approve")
async def approve_memory(
    org_id: str, memory_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Approve a pending organization memory entry."""
    await OrgMemory.approve(memory_id, current_user["sub"])
    return {"status": "approved"}


@router.post("/organizations/{org_id}/memory/{memory_id}/reject")
async def reject_memory(
    org_id: str, memory_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Reject a pending organization memory entry."""
    await OrgMemory.reject(memory_id)
    return {"status": "rejected"}


@router.delete("/organizations/{org_id}/memory/{memory_id}")
async def delete_org_memory(
    org_id: str, memory_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete an organization memory entry."""
    await OrgMemory.delete(memory_id)
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONAL MEMORY (Layer 1 — per-digital-twin)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/employees/{employee_id}/memory")
async def get_employee_personal_memory(
    employee_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Get personal memory for a digital employee (Layer 1)."""
    from dreamtalk.backend.db.database import fetchrow
    emp = await fetchrow("SELECT twin_id FROM digital_employees WHERE id = $1", employee_id)
    if not emp or not emp["twin_id"]:
        raise HTTPException(status_code=404, detail="Employee or twin not found")
    entries = await OrgMemory.get_personal_memories(emp["twin_id"], limit)
    return entries


@router.get("/employees/{employee_id}/memory/search")
async def search_employee_memory(
    employee_id: str,
    q: str,
    current_user: dict = Depends(get_current_user),
):
    """Search personal memory of a digital employee."""
    from dreamtalk.backend.db.database import fetchrow
    emp = await fetchrow("SELECT twin_id FROM digital_employees WHERE id = $1", employee_id)
    if not emp or not emp["twin_id"]:
        raise HTTPException(status_code=404, detail="Employee or twin not found")
    results = await OrgMemory.search_personal_memory(emp["twin_id"], q)
    return results
