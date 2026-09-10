from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────

class OrgType(str, Enum):
    HEALTHCARE = "healthcare"
    BUSINESS = "business"
    EDUCATION = "education"
    OTHER = "other"


class EmployeeStatus(str, Enum):
    AVAILABLE = "available"
    IN_MEETING = "in_meeting"
    IN_CONSULTATION = "in_consultation"
    TRAINING = "training"
    PROCESSING = "processing"
    OFFLINE = "offline"


class AssignmentType(str, Enum):
    MEETING = "meeting"
    APPOINTMENT = "appointment"
    CUSTOMER_CALL = "customer_call"
    TRAINING_SESSION = "training_session"
    PRESENTATION = "presentation"
    SUPPORT_TICKET = "support_ticket"
    SALES_DEMO = "sales_demo"
    INTERVIEW = "interview"
    CONSULTATION = "consultation"
    REVIEW = "review"
    CUSTOM = "custom"


class AssignmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NEEDS_REVIEW = "needs_review"


class KnowledgeScope(str, Enum):
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    EMPLOYEE = "employee"


# ─── Organization ────────────────────────────────────────────────────────────

class Organization(BaseModel):
    id: str = ""
    name: str
    org_type: OrgType
    description: str = ""
    industry: str = ""
    size: str = "small"  # small, medium, large, enterprise
    address: str = ""
    website: str = ""
    logo_url: str = ""
    created_by: str = ""
    settings: dict[str, Any] = {}
    created_at: str = ""
    updated_at: str = ""


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    org_type: OrgType = OrgType.BUSINESS
    description: str = ""
    industry: str = ""
    size: str = "small"


class Department(BaseModel):
    id: str = ""
    org_id: str
    name: str
    description: str = ""
    head_employee_id: Optional[str] = None
    parent_department_id: Optional[str] = None
    settings: dict[str, Any] = {}
    employee_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class CreateDepartmentRequest(BaseModel):
    org_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    parent_department_id: Optional[str] = None


# ─── Digital Employee ────────────────────────────────────────────────────────

class DigitalEmployee(BaseModel):
    id: str = ""
    org_id: str
    department_id: str = ""
    twin_id: Optional[str] = None  # link to digital_twin

    # Identity
    name: str
    title: str = ""  # e.g. "Cardiologist", "CEO Clone", "Sales Rep"
    employee_id: str = ""  # internal HR-style ID
    role: str = ""
    level: str = "junior"  # junior, mid, senior, lead, executive

    # Work management
    status: EmployeeStatus = EmployeeStatus.AVAILABLE
    supervisor_id: Optional[str] = None  # another DigitalEmployee or user
    is_active: bool = True

    # Permissions
    can_access_org_knowledge: bool = True
    can_escalate_to_human: bool = True
    max_concurrent_assignments: int = 1
    current_assignments: int = 0

    # Performance tracking
    total_assignments: int = 0
    completed_assignments: int = 0
    avg_rating: float = 0.0
    avg_response_time_seconds: float = 0.0
    human_escalations: int = 0
    knowledge_contributions: int = 0

    # Availability schedule
    availability: dict[str, Any] = {}

    # Version
    employee_version: str = "1.0.0"
    last_trained: Optional[str] = None
    last_deployed: Optional[str] = None

    created_at: str = ""
    updated_at: str = ""


class CreateEmployeeRequest(BaseModel):
    org_id: str
    department_id: str = ""
    name: str = Field(..., min_length=1, max_length=255)
    title: str = ""
    role: str = ""
    level: str = "junior"
    twin_id: Optional[str] = None
    supervisor_id: Optional[str] = None


# ─── Assignment ──────────────────────────────────────────────────────────────

class Assignment(BaseModel):
    id: str = ""
    org_id: str
    department_id: str = ""
    employee_id: str
    assigned_by: str  # user who created this
    assignment_type: AssignmentType
    title: str
    description: str = ""

    # Timing
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    duration_minutes: int = 0

    # Context
    priority: str = "normal"  # low, normal, high, urgent
    instructions: str = ""
    attachment_ids: list[str] = []
    metadata: dict[str, Any] = {}

    # Patient/client info (healthcare)
    patient_name: str = ""
    patient_id: str = ""

    # Meeting info (business)
    meeting_link: str = ""
    agenda: str = ""
    participants: list[str] = []

    # Status
    status: AssignmentStatus = AssignmentStatus.SCHEDULED
    is_completed: bool = False

    # Outputs
    output_id: Optional[str] = None
    needs_review: bool = False
    reviewed_by: Optional[str] = None
    review_rating: Optional[float] = None
    review_notes: str = ""

    created_at: str = ""
    updated_at: str = ""


class CreateAssignmentRequest(BaseModel):
    org_id: str
    department_id: str = ""
    employee_id: str
    assignment_type: AssignmentType = AssignmentType.MEETING
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    priority: str = "normal"
    instructions: str = ""
    agenda: str = ""
    patient_name: str = ""
    patient_id: str = ""
    meeting_link: str = ""
    participants: list[str] = []


# ─── Assignment Output (Conversation Intelligence) ───────────────────────────

class AssignmentOutput(BaseModel):
    id: str = ""
    assignment_id: str
    org_id: str
    employee_id: str

    raw_transcript: str = ""
    clean_transcript: str = ""
    speaker_identification: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []

    summary: str = ""
    decisions: list[str] = []
    action_items: list[str] = []
    risks: list[str] = []
    key_topics: list[str] = []
    questions_asked: list[str] = []
    follow_ups: list[str] = []

    sentiment_analysis: dict[str, float] = {}
    emotion_timeline: list[dict[str, Any]] = []
    performance_metrics: dict[str, Any] = {}

    # Healthcare-specific
    diagnosis_summary: str = ""
    prescription_draft: str = ""
    recommendations: list[str] = []
    follow_up_reminders: list[str] = []
    emr_update: dict[str, Any] = {}

    # Business-specific
    action_items_assigned: list[dict[str, str]] = []
    risks_identified: list[str] = []
    important_decisions: list[str] = []

    knowledge_promotion_suggestions: list[str] = []
    created_at: str = ""


class MeetingIntelligenceResponse(BaseModel):
    output: AssignmentOutput
    stats: dict[str, Any] = {}


# ─── Organization Memory (Shared Knowledge) ─────────────────────────────────

class OrgKnowledgeEntry(BaseModel):
    id: str = ""
    org_id: str
    department_id: str = ""
    source: str = ""  # "meeting", "upload", "manual", "integration"
    source_assignment_id: str = ""
    source_employee_id: str = ""
    title: str
    content: str
    content_type: str = "knowledge"  # policy, protocol, faq, decision, research, sop
    scope: KnowledgeScope = KnowledgeScope.ORGANIZATION
    tags: list[str] = []
    embedding: Optional[list[float]] = None
    approved_by: Optional[str] = None
    is_approved: bool = False
    version: str = "1.0.0"
    created_at: str = ""
    updated_at: str = ""


# ─── Employee Performance ────────────────────────────────────────────────────

class PerformanceMetrics(BaseModel):
    employee_id: str
    org_id: str
    period_start: str
    period_end: str

    assignments_completed: int = 0
    total_duration_minutes: int = 0
    avg_duration_minutes: float = 0.0
    avg_rating: float = 0.0
    rating_count: int = 0
    avg_response_time_seconds: float = 0.0

    human_escalations: int = 0
    escalation_rate: float = 0.0
    corrections_received: int = 0
    knowledge_contributions: int = 0

    sentiment_score: float = 0.0
    accuracy_score: float = 0.0
    knowledge_usage_score: float = 0.0
    learning_score: float = 0.0

    utilization_rate: float = 0.0
    total_kpis: dict[str, float] = {}
    created_at: str = ""


class SupervisorReview(BaseModel):
    id: str = ""
    assignment_id: str
    employee_id: str
    reviewer_id: str  # user or employee id
    rating: float = Field(..., ge=1, le=5)
    comments: str = ""
    corrections: list[str] = []
    knowledge_promoted: bool = False
    promote_to_training: bool = False
    retrain_triggered: bool = False
    created_at: str = ""
    updated_at: str = ""


# ─── Mission Control ─────────────────────────────────────────────────────────

class EmployeeStatusSummary(BaseModel):
    available: int = 0
    in_meeting: int = 0
    in_consultation: int = 0
    training: int = 0
    processing: int = 0
    offline: int = 0
    total: int = 0


class WorkforceSummary(BaseModel):
    total_employees: int
    total_departments: int
    active_assignments: int
    pending_reviews: int
    pending_knowledge: int
    todays_completed: int
    avg_rating: float
    utilization_rate: float
    human_escalations_today: int


class MissionControlDashboard(BaseModel):
    organization: Organization
    employee_status: EmployeeStatusSummary
    summary: WorkforceSummary
    live_sessions: list[Assignment] = []
    upcoming_assignments: list[Assignment] = []
    pending_reviews: list[SupervisorReview] = []
    knowledge_pending_approval: list[OrgKnowledgeEntry] = []
    top_performers: list[DigitalEmployee] = []
    recent_outputs: list[AssignmentOutput] = []
    alerts: list[dict[str, Any]] = []
    kpi_summary: dict[str, float] = {}
