"""
MCP Employee Tools.

Exposes employee directory lookup tools conforming to Model Context Protocol (MCP) v2.
Connects directly to SQLite database via employee CRUD functions.
"""

from typing import Any, Dict, Optional
from app.database.crud import get_employee, get_employee_by_email


def execute_get_employee_info(
    employee_id: Optional[str] = None,
    email: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Business logic for querying employee profile information from SQLite.
    Lookup by employee_id or corporate email.
    Guarantees no internal secrets are exposed.
    """
    clean_emp_id = employee_id.strip() if employee_id else None
    clean_email = email.strip().lower() if email else None

    # 1. Input Validation
    if not clean_emp_id and not clean_email:
        return {
            "success": False,
            "error": "At least one search parameter ('employee_id' or 'email') must be provided.",
        }

    try:
        employee = None
        if clean_emp_id:
            employee = get_employee(clean_emp_id, db_path=db_path)
        elif clean_email:
            employee = get_employee_by_email(clean_email, db_path=db_path)

        if not employee:
            search_param = clean_emp_id or clean_email
            return {
                "success": False,
                "error": f"No active employee found for '{search_param}'.",
            }

        return {
            "success": True,
            "employee": {
                "employee_id": employee.employee_id,
                "name": employee.name,
                "email": employee.email,
                "department": employee.department,
                "role": employee.role,
                "is_active": employee.is_active,
                "created_at": employee.created_at,
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to retrieve employee info: {str(exc)}",
        }
