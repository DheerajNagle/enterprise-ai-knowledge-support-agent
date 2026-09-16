"""
Enterprise Database Package.

Provides SQLite connection management, data models, CRUD utilities,
and seed data generators for internal employees and support tickets.
"""

from app.database.models import (
    Employee,
    EmployeeCreate,
    SupportTicket,
    TicketCreate,
    TicketUpdate,
    TicketPriority,
    TicketStatus,
    TicketCategory,
)
from app.database.connection import DatabaseManager, get_db_connection, init_db

__all__ = [
    "Employee",
    "EmployeeCreate",
    "SupportTicket",
    "TicketCreate",
    "TicketUpdate",
    "TicketPriority",
    "TicketStatus",
    "TicketCategory",
    "DatabaseManager",
    "get_db_connection",
    "init_db",
]
