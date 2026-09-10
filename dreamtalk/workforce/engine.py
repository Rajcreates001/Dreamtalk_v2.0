from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.workforce.models import (
    Organization, CreateOrganizationRequest,
    Department, CreateDepartmentRequest,
    DigitalEmployee, CreateEmployeeRequest, EmployeeStatus,
    OrgType,
)

logger = logging.getLogger("dreamtalk.workforce")


class WorkforceEngine:
    """Core CRUD for organizations, departments, and digital employees."""

    # ─── Organizations ───────────────────────────────────────────────────────

    @staticmethod
    async def create_org(user_id: str, req: CreateOrganizationRequest) -> Organization:
        org_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            """INSERT INTO organizations
               (id, name, org_type, description, industry, size, created_by, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
            org_id, req.name, req.org_type.value, req.description,
            req.industry, req.size, user_id, now, now,
        )
        return await WorkforceEngine.get_org(org_id)

    @staticmethod
    async def get_org(org_id: str) -> Optional[Organization]:
        row = await fetchrow("SELECT * FROM organizations WHERE id = $1", org_id)
        if not row:
            return None
        return WorkforceEngine._row_to_org(row)

    @staticmethod
    async def get_user_orgs(user_id: str) -> list[Organization]:
        rows = await fetch(
            "SELECT * FROM organizations WHERE created_by = $1 ORDER BY created_at DESC",
            user_id,
        )
        return [WorkforceEngine._row_to_org(r) for r in rows]

    @staticmethod
    async def list_orgs() -> list[Organization]:
        rows = await fetch("SELECT * FROM organizations ORDER BY name")
        return [WorkforceEngine._row_to_org(r) for r in rows]

    @staticmethod
    async def update_org(org_id: str, **kwargs) -> Optional[Organization]:
        fields = []
        values = []
        idx = 1
        for key, val in kwargs.items():
            if val is not None:
                fields.append(f"{key} = ${idx}")
                values.append(val)
                idx += 1
        if not fields:
            return await WorkforceEngine.get_org(org_id)
        fields.append(f"updated_at = ${idx}")
        values.append(datetime.now(timezone.utc).isoformat())
        idx += 1
        values.append(org_id)
        await execute(
            f"UPDATE organizations SET {', '.join(fields)} WHERE id = ${idx}",
            *values,
        )
        return await WorkforceEngine.get_org(org_id)

    @staticmethod
    async def delete_org(org_id: str) -> bool:
        r = await fetchrow("SELECT id FROM organizations WHERE id = $1", org_id)
        if not r:
            return False
        await execute("DELETE FROM organizations WHERE id = $1", org_id)
        return True

    # ─── Departments ─────────────────────────────────────────────────────────

    @staticmethod
    async def create_department(req: CreateDepartmentRequest) -> Department:
        dept_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            """INSERT INTO departments
               (id, org_id, name, description, parent_department_id, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            dept_id, req.org_id, req.name, req.description,
            req.parent_department_id, now, now,
        )
        return await WorkforceEngine.get_department(dept_id)

    @staticmethod
    async def get_department(dept_id: str) -> Optional[Department]:
        row = await fetchrow("SELECT * FROM departments WHERE id = $1", dept_id)
        if not row:
            return None
        return WorkforceEngine._row_to_dept(row)

    @staticmethod
    async def get_org_departments(org_id: str) -> list[Department]:
        rows = await fetch(
            "SELECT * FROM departments WHERE org_id = $1 ORDER BY name",
            org_id,
        )
        return [WorkforceEngine._row_to_dept(r) for r in rows]

    @staticmethod
    async def update_department(dept_id: str, **kwargs) -> Optional[Department]:
        fields = []
        values = []
        idx = 1
        for key, val in kwargs.items():
            if val is not None:
                fields.append(f"{key} = ${idx}")
                values.append(val)
                idx += 1
        if not fields:
            return await WorkforceEngine.get_department(dept_id)
        fields.append(f"updated_at = ${idx}")
        values.append(datetime.now(timezone.utc).isoformat())
        idx += 1
        values.append(dept_id)
        await execute(
            f"UPDATE departments SET {', '.join(fields)} WHERE id = ${idx}",
            *values,
        )
        return await WorkforceEngine.get_department(dept_id)

    @staticmethod
    async def delete_department(dept_id: str) -> bool:
        r = await fetchrow("SELECT id FROM departments WHERE id = $1", dept_id)
        if not r:
            return False
        await execute("DELETE FROM departments WHERE id = $1", dept_id)
        return True

    # ─── Digital Employees ───────────────────────────────────────────────────

    @staticmethod
    async def create_employee(req: CreateEmployeeRequest) -> DigitalEmployee:
        emp_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            """INSERT INTO digital_employees
               (id, org_id, department_id, twin_id, name, title, role, level,
                supervisor_id, status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
            emp_id, req.org_id, req.department_id, req.twin_id,
            req.name, req.title, req.role, req.level,
            req.supervisor_id, EmployeeStatus.AVAILABLE.value, now, now,
        )
        await WorkforceEngine._update_dept_count(req.department_id)
        return await WorkforceEngine.get_employee(emp_id)

    @staticmethod
    async def get_employee(emp_id: str) -> Optional[DigitalEmployee]:
        row = await fetchrow("SELECT * FROM digital_employees WHERE id = $1", emp_id)
        if not row:
            return None
        return WorkforceEngine._row_to_employee(row)

    @staticmethod
    async def get_org_employees(org_id: str) -> list[DigitalEmployee]:
        rows = await fetch(
            "SELECT * FROM digital_employees WHERE org_id = $1 AND is_active = TRUE ORDER BY name",
            org_id,
        )
        return [WorkforceEngine._row_to_employee(r) for r in rows]

    @staticmethod
    async def get_dept_employees(dept_id: str) -> list[DigitalEmployee]:
        rows = await fetch(
            "SELECT * FROM digital_employees WHERE department_id = $1 AND is_active = TRUE ORDER BY name",
            dept_id,
        )
        return [WorkforceEngine._row_to_employee(r) for r in rows]

    @staticmethod
    async def update_employee(emp_id: str, **kwargs) -> Optional[DigitalEmployee]:
        fields = []
        values = []
        idx = 1
        for key, val in kwargs.items():
            if val is not None:
                fields.append(f"{key} = ${idx}")
                values.append(val)
                idx += 1
        if not fields:
            return await WorkforceEngine.get_employee(emp_id)
        fields.append(f"updated_at = ${idx}")
        values.append(datetime.now(timezone.utc).isoformat())
        idx += 1
        values.append(emp_id)
        await execute(
            f"UPDATE digital_employees SET {', '.join(fields)} WHERE id = ${idx}",
            *values,
        )
        return await WorkforceEngine.get_employee(emp_id)

    @staticmethod
    async def set_employee_status(emp_id: str, status: EmployeeStatus) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            "UPDATE digital_employees SET status = $1, updated_at = $2 WHERE id = $3",
            status.value, now, emp_id,
        )

    @staticmethod
    async def delete_employee(emp_id: str) -> bool:
        row = await fetchrow("SELECT department_id FROM digital_employees WHERE id = $1", emp_id)
        if not row:
            return False
        dept_id = row["department_id"]
        await execute("DELETE FROM digital_employees WHERE id = $1", emp_id)
        await WorkforceEngine._update_dept_count(dept_id)
        return True

    @staticmethod
    async def get_employees_by_status(org_id: str, status: EmployeeStatus) -> list[DigitalEmployee]:
        rows = await fetch(
            "SELECT * FROM digital_employees WHERE org_id = $1 AND status = $2 AND is_active = TRUE",
            org_id, status.value,
        )
        return [WorkforceEngine._row_to_employee(r) for r in rows]

    @staticmethod
    async def _update_dept_count(dept_id: str) -> None:
        if not dept_id:
            return
        count = await fetchval(
            "SELECT COUNT(*) FROM digital_employees WHERE department_id = $1 AND is_active = TRUE",
            dept_id,
        )
        await execute(
            "UPDATE departments SET employee_count = $1 WHERE id = $2",
            count, dept_id,
        )

    # ─── Row converters ──────────────────────────────────────────────────────

    @staticmethod
    def _row_to_org(row) -> Organization:
        def _iso(val):
            return val.isoformat() if hasattr(val, "isoformat") else str(val) if val else ""
        return Organization(
            id=row["id"], name=row["name"],
            org_type=OrgType(row["org_type"]),
            description=row.get("description", ""),
            industry=row.get("industry", ""),
            size=row.get("size", "small"),
            created_by=row.get("created_by", ""),
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )

    @staticmethod
    def _row_to_dept(row) -> Department:
        def _iso(val):
            return val.isoformat() if hasattr(val, "isoformat") else str(val) if val else ""
        return Department(
            id=row["id"], org_id=row["org_id"], name=row["name"],
            description=row.get("description", ""),
            parent_department_id=str(row["parent_department_id"]) if row.get("parent_department_id") else None,
            employee_count=row.get("employee_count", 0),
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )

    @staticmethod
    def _row_to_employee(row) -> DigitalEmployee:
        def _iso(val):
            return val.isoformat() if hasattr(val, "isoformat") else str(val) if val else ""
        return DigitalEmployee(
            id=row["id"], org_id=row["org_id"],
            department_id=row.get("department_id", ""),
            twin_id=str(row["twin_id"]) if row.get("twin_id") else None,
            name=row["name"], title=row.get("title", ""),
            employee_id=row.get("employee_id", ""),
            role=row.get("role", ""), level=row.get("level", "junior"),
            status=EmployeeStatus(row.get("status", "available")),
            supervisor_id=str(row["supervisor_id"]) if row.get("supervisor_id") else None,
            is_active=row.get("is_active", True),
            current_assignments=row.get("current_assignments", 0),
            total_assignments=row.get("total_assignments", 0),
            completed_assignments=row.get("completed_assignments", 0),
            avg_rating=row.get("avg_rating", 0.0),
            employee_version=row.get("employee_version", "1.0.0"),
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )


async def fetchval(sql: str, *args):
    from dreamtalk.backend.db.database import fetchval as _fv
    return await _fv(sql, *args)
