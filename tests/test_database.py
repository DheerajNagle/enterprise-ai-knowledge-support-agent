"""
Unit and Integration Tests for Database Initialization, Schema, and CRUD Operations.
"""

import os
import pytest
from app.database.connection import DatabaseManager, init_db
from app.database.crud import (
    create_employee,
    get_employee,
    get_employee_by_email,
    list_employees,
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_status,
    delete_ticket,
)
from app.database.models import EmployeeCreate, TicketCreate, TicketStatus, TicketPriority
from app.database.seed import seed_all


@pytest.fixture
def temp_db(tmp_path):
    """Provides a fresh, isolated temporary SQLite database path for each test."""
    db_file = str(tmp_path / "test_enterprise.db")
    init_db(db_path=db_file)
    return db_file


def test_database_initialization(temp_db):
    """Verify that tables and indexes are created properly upon initialization."""
    manager = DatabaseManager(temp_db)
    with manager.cursor() as cur:
        # Check tables existence
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('employees', 'support_tickets');"
        )
        tables = {row["name"] for row in cur.fetchall()}
        assert "employees" in tables
        assert "support_tickets" in tables

        # Check indexes existence
        cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indices = {row["name"] for row in cur.fetchall()}
        assert "idx_tickets_employee" in indices
        assert "idx_tickets_status" in indices
        assert "idx_tickets_category" in indices


def test_employee_creation_and_lookup(temp_db):
    """Verify creating and retrieving an employee record."""
    new_emp = EmployeeCreate(
        employee_id="EMP-9999",
        name="Test Employee",
        email="test.employee@enterprise.internal",
        department="Quality Assurance",
        role="Automation Engineer",
        is_active=True,
    )
    created = create_employee(new_emp, db_path=temp_db)
    assert created.employee_id == "EMP-9999"
    assert created.name == "Test Employee"

    # Lookup by ID
    found_by_id = get_employee("EMP-9999", db_path=temp_db)
    assert found_by_id is not None
    assert found_by_id.email == "test.employee@enterprise.internal"

    # Lookup by Email
    found_by_email = get_employee_by_email(
        "test.employee@enterprise.internal", db_path=temp_db
    )
    assert found_by_email is not None
    assert found_by_email.employee_id == "EMP-9999"

    # Lookup non-existent
    assert get_employee("EMP-0000", db_path=temp_db) is None


def test_ticket_creation(temp_db):
    """Verify creating a support ticket for an existing employee."""
    # Create employee first
    emp = create_employee(
        EmployeeCreate(
            employee_id="EMP-5001",
            name="Alice Smith",
            email="alice.smith@enterprise.internal",
            department="Engineering",
            role="Backend Developer",
        ),
        db_path=temp_db,
    )

    # Create ticket
    ticket_data = TicketCreate(
        employee_id=emp.employee_id,
        title="Laptop Battery Depleting Rapidly",
        description="The battery health indicator reports degraded capacity under heavy compilation workloads.",
        category="Hardware",
        priority=TicketPriority.MEDIUM.value,
    )
    ticket = create_ticket(ticket_data, db_path=temp_db)

    assert ticket.ticket_id.startswith("TCK-")
    assert ticket.employee_id == "EMP-5001"
    assert ticket.title == "Laptop Battery Depleting Rapidly"
    assert ticket.category == "Hardware"
    assert ticket.priority == "MEDIUM"
    assert ticket.status == "OPEN"
    assert ticket.resolution_notes is None
    assert ticket.created_at is not None
    assert ticket.updated_at is not None


def test_ticket_creation_nonexistent_employee_fails(temp_db):
    """Verify that creating a ticket for a non-existent employee raises ValueError."""
    ticket_data = TicketCreate(
        employee_id="EMP-NONEXISTENT",
        title="Invalid Employee Test",
        description="This ticket should fail validation because employee does not exist.",
        category="General",
        priority="LOW",
    )
    with pytest.raises(ValueError) as exc_info:
        create_ticket(ticket_data, db_path=temp_db)

    assert "Cannot create ticket: Employee ID 'EMP-NONEXISTENT' not found" in str(
        exc_info.value
    )


def test_ticket_lookup(temp_db):
    """Verify ticket lookup by ID and filtering by status, category, and employee."""
    # Seed data
    seed_all(db_path=temp_db)

    # Lookup existing ticket by ID
    ticket = get_ticket("TCK-2024-0101", db_path=temp_db)
    assert ticket is not None
    assert ticket.ticket_id == "TCK-2024-0101"
    assert ticket.employee_id == "EMP-1001"
    assert "VPN Gateway 502" in ticket.title

    # Lookup non-existent ticket
    assert get_ticket("TCK-DOES-NOT-EXIST", db_path=temp_db) is None

    # Filter by status OPEN
    open_tickets = list_tickets(status="OPEN", db_path=temp_db)
    assert len(open_tickets) > 0
    assert all(t.status == "OPEN" for t in open_tickets)

    # Filter by category Network/VPN
    vpn_tickets = list_tickets(category="Network/VPN", db_path=temp_db)
    assert len(vpn_tickets) > 0
    assert all(t.category == "Network/VPN" for t in vpn_tickets)

    # Filter by employee EMP-1001
    emp_tickets = list_tickets(employee_id="EMP-1001", db_path=temp_db)
    assert len(emp_tickets) >= 2
    assert all(t.employee_id == "EMP-1001" for t in emp_tickets)


def test_ticket_status_update(temp_db):
    """Verify updating ticket status and resolution notes."""
    seed_all(db_path=temp_db)

    ticket_id = "TCK-2024-0101"
    # Update to IN_PROGRESS
    updated = update_ticket_status(
        ticket_id=ticket_id,
        new_status="IN_PROGRESS",
        db_path=temp_db,
    )
    assert updated is not None
    assert updated.status == "IN_PROGRESS"

    # Update to RESOLVED with notes
    resolved = update_ticket_status(
        ticket_id=ticket_id,
        new_status="RESOLVED",
        resolution_notes="Flushed DNS cache and switched gateway to vpn-us-west. Tunnel restored.",
        db_path=temp_db,
    )
    assert resolved is not None
    assert resolved.status == "RESOLVED"
    assert "Flushed DNS cache" in resolved.resolution_notes

    # Updating non-existent ticket returns None
    assert (
        update_ticket_status(
            ticket_id="TCK-9999-FAKE",
            new_status="RESOLVED",
            db_path=temp_db,
        )
        is None
    )


def test_ticket_deletion(temp_db):
    """Verify deleting a ticket."""
    seed_all(db_path=temp_db)
    ticket_id = "TCK-2024-0104"

    assert get_ticket(ticket_id, db_path=temp_db) is not None
    assert delete_ticket(ticket_id, db_path=temp_db) is True
    assert get_ticket(ticket_id, db_path=temp_db) is None
    # Second delete returns False
    assert delete_ticket(ticket_id, db_path=temp_db) is False


def test_seed_functionality(temp_db):
    """Verify seed_all populates employees and tickets accurately."""
    result = seed_all(db_path=temp_db, reset=True)
    assert result["status"] == "success"
    assert result["employees_seeded"] == 10
    assert result["tickets_seeded"] == 12

    employees = list_employees(db_path=temp_db)
    assert len(employees) == 10

    tickets = list_tickets(db_path=temp_db)
    assert len(tickets) == 12
