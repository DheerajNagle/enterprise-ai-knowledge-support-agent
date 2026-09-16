"""
Automated Tests for Enterprise Model Context Protocol (MCP) Server.

Validates:
- MCP Server tool advertisement via official MCP SDK v2 ClientSession.
- Live tool execution over MCP memory transport.
- Tool input validation, error handling, and structured JSON-RPC responses.
- Integration with live SQLite database and policy retriever.
"""

import asyncio
import json
from contextlib import asynccontextmanager
import pytest
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams
from app.database.seed import seed_all
from app.mcp.server import create_mcp_server


@pytest.fixture(scope="module", autouse=True)
def ensure_database_seeded():
    """Guarantees enterprise SQLite database has test employees and tickets."""
    seed_all()


@asynccontextmanager
async def create_test_session():
    """
    Spawns an in-memory client-server session using the official MCP Python SDK v2.
    Runs the real MCPServer instance and yields an initialized ClientSession.
    Guarantees cancel scopes and task groups open and close within the same asyncio task.
    """
    server = create_mcp_server()

    async with create_client_server_memory_streams() as (
        (client_read, client_write),
        (server_read, server_write),
    ):
        server_task = asyncio.create_task(
            server._lowlevel_server.run(
                server_read,
                server_write,
                server._lowlevel_server.create_initialization_options(),
            )
        )

        async with ClientSession(client_read, client_write) as session:
            init_result = await session.initialize()
            assert init_result.server_info.name == "enterprise-knowledge-agent"
            yield session

        # Cleanly terminate server task upon exit
        server_task.cancel()
        try:
            await server_task
        except (asyncio.CancelledError, Exception):
            pass


# ------------------------------------------------------------------------------
# 1. Tool Discovery & Schema Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_list_tools():
    """Verifies that the MCP server advertises all 4 required enterprise tools."""
    async with create_test_session() as session:
        tools_list = await session.list_tools()
        tool_names = [t.name for t in tools_list.tools]

        assert "search_policy" in tool_names
        assert "create_support_ticket" in tool_names
        assert "get_ticket_status" in tool_names
        assert "get_employee_info" in tool_names

        # Verify tool descriptions and input schemas are properly populated
        for tool in tools_list.tools:
            assert tool.description and len(tool.description) > 10
            assert tool.input_schema is not None
            assert "properties" in tool.input_schema


# ------------------------------------------------------------------------------
# 2. search_policy Tool Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_search_policy_success():
    """Verifies search_policy execution returning structured policy matches."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "search_policy",
            {"query": "parental leave and time off", "top_k": 2},
        )
        assert not result.is_error
        payload = json.loads(result.content[0].text)

        assert payload["success"] is True
        assert payload["query"] == "parental leave and time off"
        assert "results" in payload
        assert isinstance(payload["results"], list)


@pytest.mark.asyncio
async def test_mcp_search_policy_empty_query():
    """Verifies search_policy input validation for empty queries."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "search_policy",
            {"query": "   "},
        )
        payload = json.loads(result.content[0].text)

        assert payload["success"] is False
        assert "cannot be empty" in payload["error"].lower()


# ------------------------------------------------------------------------------
# 3. create_support_ticket Tool Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_create_support_ticket_success():
    """Verifies ticket creation for a valid employee in SQLite."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "create_support_ticket",
            {
                "employee_id": "EMP-1001",
                "title": "VPN connection times out",
                "description": "Unable to connect to gateway-us-east from home network.",
                "category": "IT",
                "priority": "HIGH",
            },
        )
        assert not result.is_error
        payload = json.loads(result.content[0].text)

        assert payload["success"] is True
        assert "ticket" in payload
        ticket = payload["ticket"]
        assert ticket["employee_id"] == "EMP-1001"
        assert ticket["title"] == "VPN connection times out"
        assert ticket["category"] == "IT"
        assert ticket["priority"] == "HIGH"
        assert ticket["status"] == "OPEN"
        assert ticket["ticket_id"].startswith("TCK-")


@pytest.mark.asyncio
async def test_mcp_create_support_ticket_invalid_employee():
    """Verifies ticket creation rejects non-existent employee IDs."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "create_support_ticket",
            {
                "employee_id": "EMP-NONEXISTENT",
                "title": "Laptop broken",
                "description": "Screen cracked",
                "category": "HARDWARE",
                "priority": "MEDIUM",
            },
        )
        payload = json.loads(result.content[0].text)

        assert payload["success"] is False
        assert "not found" in payload["error"].lower()


@pytest.mark.asyncio
async def test_mcp_create_support_ticket_invalid_category():
    """Verifies ticket creation rejects invalid categories."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "create_support_ticket",
            {
                "employee_id": "EMP-1001",
                "title": "General inquiry",
                "description": "Need assistance",
                "category": "INVALID_CAT",
                "priority": "LOW",
            },
        )
        payload = json.loads(result.content[0].text)

        assert payload["success"] is False
        assert "invalid category" in payload["error"].lower()


# ------------------------------------------------------------------------------
# 4. get_ticket_status Tool Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_get_ticket_status_existing():
    """Verifies querying existing ticket status from SQLite."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "get_ticket_status",
            {"ticket_id": "TCK-2024-0101"},
        )
        assert not result.is_error
        payload = json.loads(result.content[0].text)

        assert payload["success"] is True
        assert "ticket" in payload
        assert payload["ticket"]["ticket_id"] == "TCK-2024-0101"
        assert "status" in payload["ticket"]


@pytest.mark.asyncio
async def test_mcp_get_ticket_status_nonexistent():
    """Verifies querying an unknown ticket returns a clean error."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "get_ticket_status",
            {"ticket_id": "TCK-9999-NOTFOUND"},
        )
        payload = json.loads(result.content[0].text)

        assert payload["success"] is False
        assert "not found" in payload["error"].lower()


# ------------------------------------------------------------------------------
# 5. get_employee_info Tool Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_get_employee_info_by_id():
    """Verifies employee directory lookup by ID without exposing sensitive secrets."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "get_employee_info",
            {"employee_id": "EMP-1001"},
        )
        assert not result.is_error
        payload = json.loads(result.content[0].text)

        assert payload["success"] is True
        emp = payload["employee"]
        assert emp["employee_id"] == "EMP-1001"
        assert emp["name"] == "Sarah Jenkins"
        assert emp["email"] == "sarah.jenkins@enterprise.internal"
        assert emp["department"] == "Engineering"
        # Verify no secrets or password keys exist
        assert "password" not in emp
        assert "token" not in emp


@pytest.mark.asyncio
async def test_mcp_get_employee_info_by_email():
    """Verifies employee directory lookup by corporate email."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "get_employee_info",
            {"email": "david.kim@enterprise.internal"},
        )
        assert not result.is_error
        payload = json.loads(result.content[0].text)

        assert payload["success"] is True
        assert payload["employee"]["employee_id"] == "EMP-1002"
        assert payload["employee"]["name"] == "David Kim"


@pytest.mark.asyncio
async def test_mcp_get_employee_info_missing_parameters():
    """Verifies that calling get_employee_info without parameters fails cleanly."""
    async with create_test_session() as session:
        result = await session.call_tool(
            "get_employee_info",
            {},
        )
        payload = json.loads(result.content[0].text)

        assert payload["success"] is False
        assert "at least one" in payload["error"].lower()
