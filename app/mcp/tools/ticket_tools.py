"""
MCP Support Ticket Tools.

Exposes ticket creation and status tracking tools conforming to Model Context Protocol (MCP) v2.
Connects directly to SQLite database via transactional CRUD functions.
"""

from typing import Any, Dict, Optional
from app.database.crud import create_ticket, get_employee, get_ticket
from app.database.models import TicketCreate

ALLOWED_CATEGORIES = {"IT", "HR", "FACILITIES", "FINANCE", "SECURITY", "HARDWARE", "GENERAL"}
ALLOWED_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}


def execute_create_support_ticket(
    employee_id: str,
    title: str,
    description: str,
    category: str,
    priority: str = "MEDIUM",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Business logic for creating an enterprise support ticket in SQLite.
    Validates employee identity, title, description, category, and priority.
    """
    # 1. Input Validation
    emp_id = (employee_id or "").strip()
    clean_title = (title or "").strip()
    clean_desc = (description or "").strip()
    cat_upper = (category or "").strip().upper()
    prio_upper = (priority or "MEDIUM").strip().upper()

    if not emp_id:
        return {"success": False, "error": "employee_id must be provided."}
    if not clean_title:
        return {"success": False, "error": "title cannot be empty."}
    if not clean_desc:
        return {"success": False, "error": "description cannot be empty."}
    if cat_upper not in ALLOWED_CATEGORIES:
        return {
            "success": False,
            "error": f"Invalid category '{category}'. Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}",
        }
    if prio_upper not in ALLOWED_PRIORITIES:
        return {
            "success": False,
            "error": f"Invalid priority '{priority}'. Allowed priorities: {', '.join(sorted(ALLOWED_PRIORITIES))}",
        }

    # 2. Verify Employee Exists in SQLite
    try:
        employee = get_employee(emp_id, db_path=db_path)
        if not employee:
            return {
                "success": False,
                "error": f"Employee ID '{emp_id}' not found in the employee directory.",
            }

        # 3. Create Ticket Record
        ticket_data = TicketCreate(
            employee_id=emp_id,
            title=clean_title,
            description=clean_desc,
            category=cat_upper,
            priority=prio_upper,
        )
        created = create_ticket(ticket_data, db_path=db_path)

        return {
            "success": True,
            "message": f"Ticket {created.ticket_id} created successfully.",
            "ticket": {
                "ticket_id": created.ticket_id,
                "employee_id": created.employee_id,
                "employee_name": employee.name,
                "title": created.title,
                "description": created.description,
                "category": created.category,
                "priority": created.priority,
                "status": created.status,
                "created_at": created.created_at,
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to create support ticket: {str(exc)}",
        }


def execute_get_ticket_status(
    ticket_id: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Business logic for querying support ticket status from SQLite.
    """
    clean_id = (ticket_id or "").strip()
    if not clean_id:
        return {"success": False, "error": "ticket_id must be provided."}

    try:
        ticket = get_ticket(clean_id, db_path=db_path)
        if not ticket:
            return {
                "success": False,
                "error": f"Support ticket '{clean_id}' not found.",
            }

        # Fetch employee name if available for richer response
        employee_name = "Unknown"
        emp = get_employee(ticket.employee_id, db_path=db_path)
        if emp:
            employee_name = emp.name

        return {
            "success": True,
            "ticket": {
                "ticket_id": ticket.ticket_id,
                "employee_id": ticket.employee_id,
                "employee_name": employee_name,
                "title": ticket.title,
                "description": ticket.description,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "resolution_notes": ticket.resolution_notes,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to retrieve ticket status: {str(exc)}",
        }
