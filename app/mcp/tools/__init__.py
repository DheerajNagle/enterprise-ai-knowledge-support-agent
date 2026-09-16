"""
MCP Tools Registration.

Binds enterprise tools to an MCPServer instance conforming to Model Context Protocol (MCP) v2.
"""

from typing import Any, Dict, Optional
from mcp.server.mcpserver import MCPServer
from app.mcp.tools.policy_tools import execute_search_policy
from app.mcp.tools.ticket_tools import (
    execute_create_support_ticket,
    execute_get_ticket_status,
)
from app.mcp.tools.employee_tools import execute_get_employee_info


def register_all_tools(server: MCPServer) -> None:
    """
    Registers all enterprise tools with the provided MCPServer instance.
    Enforces typed schemas, comprehensive docstrings, and structured output.
    """

    @server.tool(
        name="search_policy",
        description=(
            "Search enterprise policy documents and knowledge base using semantic vector retrieval. "
            "Returns relevant policy excerpts, document filenames, section titles, page numbers, "
            "and relevance scores. Optional department filter narrows search."
        ),
    )
    def search_policy(
        query: str,
        department: Optional[str] = None,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Args:
            query: The natural language search query (e.g. 'parental leave duration').
            department: Optional organizational department filter (e.g. 'HR', 'IT', 'Finance').
            top_k: Number of relevant chunks to retrieve (between 1 and 10, default 3).
        """
        return execute_search_policy(query=query, department=department, top_k=top_k)

    @server.tool(
        name="create_support_ticket",
        description=(
            "Create a new internal support ticket in the enterprise database. "
            "Validates employee existence, category, and priority before transactional persistence. "
            "Returns the created ticket record and generated ticket ID."
        ),
    )
    def create_support_ticket(
        employee_id: str,
        title: str,
        description: str,
        category: str,
        priority: str = "MEDIUM",
    ) -> Dict[str, Any]:
        """
        Args:
            employee_id: The ID of the employee opening the ticket (e.g. 'EMP-1001').
            title: Concise summary of the issue.
            description: Detailed explanation of the support request or incident.
            category: One of ['IT', 'HR', 'FACILITIES', 'FINANCE', 'SECURITY', 'HARDWARE', 'GENERAL'].
            priority: One of ['LOW', 'MEDIUM', 'HIGH', 'URGENT'] (default 'MEDIUM').
        """
        return execute_create_support_ticket(
            employee_id=employee_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
        )

    @server.tool(
        name="get_ticket_status",
        description=(
            "Retrieve current status, priority, resolution notes, and timeline of an "
            "enterprise support ticket by ticket ID (e.g. 'TCK-2024-001' or 'TCK-2024-XXXX')."
        ),
    )
    def get_ticket_status(ticket_id: str) -> Dict[str, Any]:
        """
        Args:
            ticket_id: Unique support ticket identifier.
        """
        return execute_get_ticket_status(ticket_id=ticket_id)

    @server.tool(
        name="get_employee_info",
        description=(
            "Look up employee directory profile by employee ID or corporate email address. "
            "Returns employee name, corporate email, department, role, and active status. "
            "Does not expose passwords or sensitive credentials."
        ),
    )
    def get_employee_info(
        employee_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Args:
            employee_id: Optional unique employee ID (e.g. 'EMP-1001').
            email: Optional corporate email address (e.g. 'john.doe@company.com').
        """
        return execute_get_employee_info(employee_id=employee_id, email=email)


__all__ = [
    "register_all_tools",
    "execute_search_policy",
    "execute_create_support_ticket",
    "execute_get_ticket_status",
    "execute_get_employee_info",
]
