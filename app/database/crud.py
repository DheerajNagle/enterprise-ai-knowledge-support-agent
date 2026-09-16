"""
CRUD Operations for Employees and Support Tickets.

Provides transactional functions for inserting, querying, updating,
and deleting records in the SQLite database.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from app.database.connection import DatabaseManager
from app.database.models import (
    Employee,
    EmployeeCreate,
    SupportTicket,
    TicketCreate,
    TicketUpdate,
    utc_now_iso,
)


def _generate_ticket_id() -> str:
    """Generates a human-friendly ticket ID: TCK-2024-XXXX."""
    short_uuid = uuid.uuid4().hex[:6].upper()
    year = datetime.now(timezone.utc).year
    return f"TCK-{year}-{short_uuid}"


def _generate_employee_id() -> str:
    """Generates a unique employee ID: EMP-XXXX."""
    short_uuid = uuid.uuid4().hex[:4].upper()
    return f"EMP-{short_uuid}"


# ==============================================================================
# Employee Operations
# ==============================================================================


def create_employee(
    employee_data: EmployeeCreate, db_path: Optional[str] = None
) -> Employee:
    """Creates a new employee record."""
    manager = DatabaseManager(db_path)
    emp_id = employee_data.employee_id or _generate_employee_id()
    now = utc_now_iso()

    sql = """
    INSERT INTO employees (employee_id, name, email, department, role, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with manager.cursor() as cur:
        cur.execute(
            sql,
            (
                emp_id,
                employee_data.name,
                employee_data.email,
                employee_data.department,
                employee_data.role,
                1 if employee_data.is_active else 0,
                now,
            ),
        )

    return Employee(
        employee_id=emp_id,
        name=employee_data.name,
        email=employee_data.email,
        department=employee_data.department,
        role=employee_data.role,
        is_active=employee_data.is_active,
        created_at=now,
    )


def get_employee(
    employee_id: str, db_path: Optional[str] = None
) -> Optional[Employee]:
    """Retrieves an employee by their unique ID."""
    manager = DatabaseManager(db_path)
    sql = "SELECT * FROM employees WHERE employee_id = ?"
    with manager.cursor() as cur:
        cur.execute(sql, (employee_id,))
        row = cur.fetchone()
        if not row:
            return None
        return Employee(
            employee_id=row["employee_id"],
            name=row["name"],
            email=row["email"],
            department=row["department"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )


def get_employee_by_email(
    email: str, db_path: Optional[str] = None
) -> Optional[Employee]:
    """Retrieves an employee by corporate email."""
    manager = DatabaseManager(db_path)
    sql = "SELECT * FROM employees WHERE email = ?"
    with manager.cursor() as cur:
        cur.execute(sql, (email.strip().lower(),))
        row = cur.fetchone()
        if not row:
            return None
        return Employee(
            employee_id=row["employee_id"],
            name=row["name"],
            email=row["email"],
            department=row["department"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )


def list_employees(
    department: Optional[str] = None,
    active_only: bool = True,
    db_path: Optional[str] = None,
) -> List[Employee]:
    """Lists employees with optional department filter."""
    manager = DatabaseManager(db_path)
    clauses = []
    params = []

    if department:
        clauses.append("department = ?")
        params.append(department)
    if active_only:
        clauses.append("is_active = 1")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM employees {where} ORDER BY name ASC"

    with manager.cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        return [
            Employee(
                employee_id=row["employee_id"],
                name=row["name"],
                email=row["email"],
                department=row["department"],
                role=row["role"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]


# ==============================================================================
# Support Ticket Operations
# ==============================================================================


def create_ticket(
    ticket_data: TicketCreate,
    ticket_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> SupportTicket:
    """Creates a new support ticket."""
    manager = DatabaseManager(db_path)
    t_id = ticket_id or _generate_ticket_id()
    now = utc_now_iso()

    # Validate employee exists
    employee = get_employee(ticket_data.employee_id, db_path=db_path)
    if not employee:
        raise ValueError(
            f"Cannot create ticket: Employee ID '{ticket_data.employee_id}' not found."
        )

    sql = """
    INSERT INTO support_tickets (
        ticket_id, employee_id, title, description, category, priority,
        status, resolution_notes, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with manager.cursor() as cur:
        cur.execute(
            sql,
            (
                t_id,
                ticket_data.employee_id,
                ticket_data.title,
                ticket_data.description,
                ticket_data.category,
                ticket_data.priority,
                "OPEN",
                None,
                now,
                now,
            ),
        )

    return SupportTicket(
        ticket_id=t_id,
        employee_id=ticket_data.employee_id,
        title=ticket_data.title,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority,
        status="OPEN",
        resolution_notes=None,
        created_at=now,
        updated_at=now,
    )


def get_ticket(
    ticket_id: str, db_path: Optional[str] = None
) -> Optional[SupportTicket]:
    """Retrieves a single ticket by its ticket_id."""
    manager = DatabaseManager(db_path)
    sql = "SELECT * FROM support_tickets WHERE ticket_id = ?"
    with manager.cursor() as cur:
        cur.execute(sql, (ticket_id,))
        row = cur.fetchone()
        if not row:
            return None
        return SupportTicket(
            ticket_id=row["ticket_id"],
            employee_id=row["employee_id"],
            title=row["title"],
            description=row["description"],
            category=row["category"],
            priority=row["priority"],
            status=row["status"],
            resolution_notes=row["resolution_notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def list_tickets(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
) -> List[SupportTicket]:
    """Queries tickets matching filtering criteria."""
    manager = DatabaseManager(db_path)
    clauses = []
    params = []

    if employee_id:
        clauses.append("employee_id = ?")
        params.append(employee_id)
    if status:
        clauses.append("status = ?")
        params.append(status.upper())
    if category:
        clauses.append("category = ?")
        params.append(category)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM support_tickets {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with manager.cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        return [
            SupportTicket(
                ticket_id=row["ticket_id"],
                employee_id=row["employee_id"],
                title=row["title"],
                description=row["description"],
                category=row["category"],
                priority=row["priority"],
                status=row["status"],
                resolution_notes=row["resolution_notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


def update_ticket_status(
    ticket_id: str,
    new_status: str,
    resolution_notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[SupportTicket]:
    """Updates the status and optional resolution notes of an existing ticket."""
    manager = DatabaseManager(db_path)
    now = utc_now_iso()
    status_upper = new_status.upper()

    sql = """
    UPDATE support_tickets
    SET status = ?, resolution_notes = COALESCE(?, resolution_notes), updated_at = ?
    WHERE ticket_id = ?
    """
    with manager.cursor() as cur:
        cur.execute(sql, (status_upper, resolution_notes, now, ticket_id))
        if cur.rowcount == 0:
            return None

    return get_ticket(ticket_id, db_path=db_path)


def delete_ticket(ticket_id: str, db_path: Optional[str] = None) -> bool:
    """Deletes a ticket by ID."""
    manager = DatabaseManager(db_path)
    sql = "DELETE FROM support_tickets WHERE ticket_id = ?"
    with manager.cursor() as cur:
        cur.execute(sql, (ticket_id,))
        return cur.rowcount > 0
