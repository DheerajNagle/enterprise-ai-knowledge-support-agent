"""
Data Models and Enums for SQLite Database.

Defines Pydantic v2 schemas and enumerations representing employees
and support tickets in the enterprise domain.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCategory(str, Enum):
    HARDWARE = "Hardware"
    NETWORK_VPN = "Network/VPN"
    ACCESS_IDENTITY = "Access/Identity"
    SOFTWARE = "Software"
    HR_BENEFITS = "HR/Benefits"
    FINANCE_ACCOUNTING = "Finance/Accounting"
    GENERAL = "General"


def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ==============================================================================
# Employee Models
# ==============================================================================


class EmployeeBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full employee name")
    email: str = Field(
        ...,
        pattern=r"^[\w\.\+-]+@[\w\.-]+\.\w+$",
        description="Corporate email address",
    )
    department: str = Field(..., min_length=2, max_length=100, description="Department name")
    role: str = Field(..., min_length=2, max_length=100, description="Job title / role")
    is_active: bool = Field(default=True, description="Whether employee is currently active")


class EmployeeCreate(EmployeeBase):
    employee_id: Optional[str] = Field(
        default=None,
        description="Unique employee ID (e.g. EMP-1001). Auto-generated if omitted.",
    )


class Employee(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str = Field(..., description="Unique employee identifier")
    created_at: str = Field(default_factory=utc_now_iso, description="Record creation timestamp")


# ==============================================================================
# Support Ticket Models
# ==============================================================================


class TicketBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=250, description="Summary title of ticket")
    description: str = Field(..., min_length=10, max_length=5000, description="Detailed problem description")
    category: str = Field(default=TicketCategory.GENERAL.value, description="Ticket category")
    priority: str = Field(default=TicketPriority.MEDIUM.value, description="Urgency priority level")


class TicketCreate(TicketBase):
    employee_id: str = Field(..., min_length=3, max_length=50, description="Associated employee ID")


class TicketUpdate(BaseModel):
    status: Optional[str] = Field(default=None, description="Updated ticket status")
    priority: Optional[str] = Field(default=None, description="Updated ticket priority")
    resolution_notes: Optional[str] = Field(default=None, description="Technician resolution summary")


class SupportTicket(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str = Field(..., description="Unique ticket identifier (e.g. TCK-2024-001)")
    employee_id: str = Field(..., description="Associated employee ID")
    status: str = Field(default=TicketStatus.OPEN.value, description="Current resolution status")
    resolution_notes: Optional[str] = Field(default=None, description="Resolution notes if resolved")
    created_at: str = Field(default_factory=utc_now_iso, description="Ticket creation timestamp")
    updated_at: str = Field(default_factory=utc_now_iso, description="Last update timestamp")
