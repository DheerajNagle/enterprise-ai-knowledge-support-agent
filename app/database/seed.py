"""
Database Seeding Script for Synthetic Enterprise Data.

Populates the SQLite database with realistic synthetic employees
and enterprise support tickets. No real personal data is used.
"""

from typing import Optional
from app.database.connection import DatabaseManager, init_db
from app.database.crud import (
    create_employee,
    create_ticket,
    get_employee,
    get_ticket,
    update_ticket_status,
)
from app.database.models import EmployeeCreate, TicketCreate

SYNTHETIC_EMPLOYEES = [
    {
        "employee_id": "EMP-1001",
        "name": "Sarah Jenkins",
        "email": "sarah.jenkins@enterprise.internal",
        "department": "Engineering",
        "role": "Staff Software Engineer",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1002",
        "name": "David Kim",
        "email": "david.kim@enterprise.internal",
        "department": "Engineering",
        "role": "Senior DevOps Engineer",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1003",
        "name": "Elena Rodriguez",
        "email": "elena.rodriguez@enterprise.internal",
        "department": "Product",
        "role": "Principal Product Manager",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1004",
        "name": "Marcus Vance",
        "email": "marcus.vance@enterprise.internal",
        "department": "IT Support",
        "role": "Lead Systems Administrator",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1005",
        "name": "Amina Patel",
        "email": "amina.patel@enterprise.internal",
        "department": "HR/People Operations",
        "role": "Senior HR Specialist",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1006",
        "name": "Liam O'Connor",
        "email": "liam.oconnor@enterprise.internal",
        "department": "Finance",
        "role": "Senior Financial Analyst",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1007",
        "name": "Chloe Dubois",
        "email": "chloe.dubois@enterprise.internal",
        "department": "Marketing",
        "role": "Content Strategy Lead",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1008",
        "name": "Rajesh Kulkarni",
        "email": "rajesh.kulkarni@enterprise.internal",
        "department": "Cybersecurity",
        "role": "SOC Lead Analyst",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1009",
        "name": "Hannah Becker",
        "email": "hannah.becker@enterprise.internal",
        "department": "Sales",
        "role": "Enterprise Account Executive",
        "is_active": True,
    },
    {
        "employee_id": "EMP-1010",
        "name": "Jordan Taylor",
        "email": "jordan.taylor@enterprise.internal",
        "department": "Legal & Compliance",
        "role": "Corporate Legal Counsel",
        "is_active": True,
    },
]

SYNTHETIC_TICKETS = [
    {
        "ticket_id": "TCK-2024-0101",
        "employee_id": "EMP-1001",
        "title": "GlobalProtect VPN Gateway 502 Error from Home Network",
        "description": "Unable to connect to vpn-us-east.enterprise.internal. Receiving error 502 Bad Gateway after entering Okta push verification.",
        "category": "Network/VPN",
        "priority": "HIGH",
        "initial_status": "OPEN",
    },
    {
        "ticket_id": "TCK-2024-0102",
        "employee_id": "EMP-1002",
        "title": "Production Bastion Full-Tunnel VPN Profile Provisioning",
        "description": "Need Corp-Privileged-Full profile assigned to my user identity to conduct upcoming database migration this Saturday.",
        "category": "Network/VPN",
        "priority": "CRITICAL",
        "initial_status": "IN_PROGRESS",
    },
    {
        "ticket_id": "TCK-2024-0103",
        "employee_id": "EMP-1003",
        "title": "MacBook Pro 36-Month Hardware Refresh Eligibility",
        "description": "My 2021 MacBook Pro 16 has reached 36 months of deployment. Requesting eligibility verification and link to pick new M-series model.",
        "category": "Hardware",
        "priority": "MEDIUM",
        "initial_status": "IN_PROGRESS",
    },
    {
        "ticket_id": "TCK-2024-0104",
        "employee_id": "EMP-1006",
        "title": "Expensify Missing Receipt Approval for Client Dinner Over $25",
        "description": "Lost itemized paper receipt for client dinner ($64.50). Only have credit card authorization slip. Need exception waiver.",
        "category": "Finance/Accounting",
        "priority": "LOW",
        "initial_status": "OPEN",
    },
    {
        "ticket_id": "TCK-2024-0105",
        "employee_id": "EMP-1007",
        "title": "One-Time Home Office Setup Stipend Question",
        "description": "I bought a sit-stand motorized desk ($520) and an ergonomic chair ($210). Can I submit both receipts under the $750 allowance?",
        "category": "HR/Benefits",
        "priority": "LOW",
        "initial_status": "RESOLVED",
        "resolution_notes": "Confirmed. Both receipts submitted under Expensify category 'Home Office Setup (One-Time)' and approved.",
    },
    {
        "ticket_id": "TCK-2024-0106",
        "employee_id": "EMP-1009",
        "title": "International Remote Work Notification - 10 Days in Canada",
        "description": "Requesting formal approval to work remotely from Toronto, Canada for 10 business days in August. Manager has endorsed.",
        "category": "HR/Benefits",
        "priority": "LOW",
        "initial_status": "OPEN",
    },
    {
        "ticket_id": "TCK-2024-0107",
        "employee_id": "EMP-1001",
        "title": "Keyboard Liquid Spill on Laptop - Requesting Loaner",
        "description": "Accidentally spilled tea on my MacBook keyboard. Keys are sticking and trackpad is unresponsive. Requesting expedited loaner dispatch.",
        "category": "Hardware",
        "priority": "HIGH",
        "initial_status": "IN_PROGRESS",
    },
    {
        "ticket_id": "TCK-2024-0108",
        "employee_id": "EMP-1010",
        "title": "Okta Verify Number Matching Challenge Failure After Phone Upgrade",
        "description": "Transferred to a new phone and Okta Verify notifications are no longer prompting. Locked out of SSO.",
        "category": "Access/Identity",
        "priority": "HIGH",
        "initial_status": "RESOLVED",
        "resolution_notes": "Identity verified via video challenge. Issued temporary bypass token and re-enrolled new mobile device.",
    },
    {
        "ticket_id": "TCK-2024-0109",
        "employee_id": "EMP-1002",
        "title": "CrowdStrike Falcon Sensor Out of Date - Quarantined VLAN",
        "description": "Device health posture failed during VPN check: CS_SENSOR reporting out-of-date baseline.",
        "category": "Network/VPN",
        "priority": "HIGH",
        "initial_status": "RESOLVED",
        "resolution_notes": "Forced falconctl update daemon remotely; sensor updated to v7.14 and host restored to compliant state.",
    },
    {
        "ticket_id": "TCK-2024-0110",
        "employee_id": "EMP-1003",
        "title": "Suspicious Phishing Email Forwarded - Executive Impersonation",
        "description": "Received email purportedly from the CEO requesting urgent iTunes gift cards. Forwarded raw headers to phishing@enterprise.internal.",
        "category": "Access/Identity",
        "priority": "MEDIUM",
        "initial_status": "CLOSED",
        "resolution_notes": "Sender domain blocked across Proofpoint mail gateways and threat intelligence indicators updated.",
    },
    {
        "ticket_id": "TCK-2024-0111",
        "employee_id": "EMP-1005",
        "title": "Annual Leave Rollover Policy Clarification for Q1",
        "description": "Inquiring whether my 4 rolled-over PTO days must be completely taken before March 31 or if they can be scheduled for summer.",
        "category": "HR/Benefits",
        "priority": "LOW",
        "initial_status": "RESOLVED",
        "resolution_notes": "Informed employee of Section 2.1 rollover cap: rolled-over days expire on March 31 without cash payout.",
    },
    {
        "ticket_id": "TCK-2024-0112",
        "employee_id": "EMP-1008",
        "title": "Temporary 14-Day USB Mass Storage Exemption for Hardware Firmware Flashing",
        "description": "Security testing team requires USB mass storage write capability on dedicated test bench machine for firmware forensic analysis.",
        "category": "Access/Identity",
        "priority": "MEDIUM",
        "initial_status": "OPEN",
    },
]


def seed_employees(db_path: Optional[str] = None) -> int:
    """Seeds synthetic employees into the database if not already present."""
    count = 0
    for emp_data in SYNTHETIC_EMPLOYEES:
        existing = get_employee(emp_data["employee_id"], db_path=db_path)
        if not existing:
            create_employee(EmployeeCreate(**emp_data), db_path=db_path)
            count += 1
    return count


def seed_tickets(db_path: Optional[str] = None) -> int:
    """Seeds synthetic support tickets into the database if not already present."""
    count = 0
    for tck_data in SYNTHETIC_TICKETS:
        existing = get_ticket(tck_data["ticket_id"], db_path=db_path)
        if not existing:
            ticket = create_ticket(
                TicketCreate(
                    employee_id=tck_data["employee_id"],
                    title=tck_data["title"],
                    description=tck_data["description"],
                    category=tck_data["category"],
                    priority=tck_data["priority"],
                ),
                ticket_id=tck_data["ticket_id"],
                db_path=db_path,
            )
            # Apply initial status and resolution notes if not OPEN
            if tck_data.get("initial_status") != "OPEN":
                update_ticket_status(
                    ticket_id=ticket.ticket_id,
                    new_status=tck_data["initial_status"],
                    resolution_notes=tck_data.get("resolution_notes"),
                    db_path=db_path,
                )
            count += 1
    return count


def seed_all(db_path: Optional[str] = None, reset: bool = False) -> dict:
    """
    Initializes database schema and populates all synthetic seed records.
    If reset is True, drops existing tables first.
    """
    manager = DatabaseManager(db_path)
    if reset:
        with manager.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS support_tickets;")
            cur.execute("DROP TABLE IF EXISTS employees;")

    init_db(db_path=db_path)
    emp_count = seed_employees(db_path=db_path)
    tck_count = seed_tickets(db_path=db_path)

    return {
        "status": "success",
        "employees_seeded": emp_count,
        "tickets_seeded": tck_count,
    }


if __name__ == "__main__":
    result = seed_all(reset=True)
    print(f"Database seeded successfully: {result}")
