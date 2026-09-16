"""
Automated Tests for Enterprise Model Context Protocol (MCP) Client.

Validates:
- Stdio transport subprocess lifecycle (connection, capability negotiation, disconnection).
- Tool discovery and schema introspection.
- Function declaration generation for Google ADK / Gemini agent integration.
- Typed invocations of search_policy, create_support_ticket, get_ticket_status, get_employee_info.
- Robust error handling for unknown tools, invalid parameters, and missing server executables.
"""

import pytest
from app.database.seed import seed_all
from app.mcp import (
    EnterpriseMCPClient,
    MCPConnectionError,
    MCPToolExecutionError,
)


@pytest.fixture(scope="module", autouse=True)
def ensure_database_seeded():
    """Guarantees enterprise SQLite database has test employees and tickets."""
    seed_all()


# ------------------------------------------------------------------------------
# 1. Connection Lifecycle & Discovery Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_connect_and_disconnect():
    """Verifies stdio subprocess launch, initialization, and clean teardown."""
    client = EnterpriseMCPClient()
    assert not client.is_connected

    await client.connect()
    assert client.is_connected

    # Verify tool discovery cached during connect
    tools = client.get_available_tool_names()
    assert "search_policy" in tools
    assert "create_support_ticket" in tools
    assert "get_ticket_status" in tools
    assert "get_employee_info" in tools

    await client.disconnect()
    assert not client.is_connected


@pytest.mark.asyncio
async def test_client_discover_tools_and_schemas():
    """Verifies tool metadata inspection and agent function declaration conversion."""
    async with EnterpriseMCPClient() as client:
        tools = await client.discover_tools()
        assert len(tools) >= 4

        # Schema inspection
        schema = client.get_tool_schema("create_support_ticket")
        assert schema is not None
        assert "properties" in schema
        assert "employee_id" in schema["properties"]
        assert "title" in schema["properties"]

        # Conversion to agent function declarations
        declarations = client.to_agent_function_declarations()
        assert len(declarations) >= 4
        assert any(d["name"] == "search_policy" for d in declarations)
        assert all("parameters" in d and "description" in d for d in declarations)


# ------------------------------------------------------------------------------
# 2. Tool Execution Tests over stdio Transport
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_search_policy():
    """Verifies search_policy execution over stdio JSON-RPC transport."""
    async with EnterpriseMCPClient() as client:
        result = await client.search_policy(
            query="parental leave policy",
            department="HR",
            top_k=2,
        )
        assert result.get("success") is True
        assert result.get("query") == "parental leave policy"
        assert "results" in result
        assert isinstance(result["results"], list)


@pytest.mark.asyncio
async def test_client_create_support_ticket():
    """Verifies create_support_ticket execution creating record in SQLite."""
    async with EnterpriseMCPClient() as client:
        result = await client.create_support_ticket(
            employee_id="EMP-1001",
            title="External monitor display flicker",
            description="Dell 27-inch 4K monitor randomly blacks out via USB-C dock.",
            category="HARDWARE",
            priority="HIGH",
        )
        assert result.get("success") is True
        assert "ticket" in result
        ticket = result["ticket"]
        assert ticket["employee_id"] == "EMP-1001"
        assert ticket["category"] == "HARDWARE"
        assert ticket["priority"] == "HIGH"
        assert ticket["status"] == "OPEN"
        assert ticket["ticket_id"].startswith("TCK-")


@pytest.mark.asyncio
async def test_client_get_ticket_status():
    """Verifies get_ticket_status querying existing ticket from SQLite."""
    async with EnterpriseMCPClient() as client:
        result = await client.get_ticket_status(ticket_id="TCK-2024-0101")
        assert result.get("success") is True
        assert "ticket" in result
        ticket = result["ticket"]
        assert ticket["ticket_id"] == "TCK-2024-0101"
        assert "status" in ticket
        assert ticket["employee_id"] == "EMP-1001"


@pytest.mark.asyncio
async def test_client_get_employee_info():
    """Verifies get_employee_info directory query by ID and email."""
    async with EnterpriseMCPClient() as client:
        # Lookup by ID
        by_id = await client.get_employee_info(employee_id="EMP-1002")
        assert by_id.get("success") is True
        assert by_id["employee"]["name"] == "David Kim"
        assert by_id["employee"]["department"] == "Engineering"

        # Lookup by Email
        by_email = await client.get_employee_info(email="david.kim@enterprise.internal")
        assert by_email.get("success") is True
        assert by_email["employee"]["employee_id"] == "EMP-1002"


# ------------------------------------------------------------------------------
# 3. Error Handling & Edge Case Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_validation_error_handling():
    """Verifies structured error response when business validation fails on server."""
    async with EnterpriseMCPClient() as client:
        # Non-existent employee
        result = await client.create_support_ticket(
            employee_id="EMP-NONEXISTENT-999",
            title="Valid title",
            description="Valid description",
            category="IT",
            priority="LOW",
        )
        assert result.get("success") is False
        assert "not found" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_client_call_nonexistent_tool():
    """Verifies MCPToolExecutionError when invoking an unknown tool name."""
    async with EnterpriseMCPClient() as client:
        with pytest.raises(MCPToolExecutionError) as exc_info:
            await client.call_tool("nonexistent_fake_tool_xyz")
        assert "not recognized" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_client_connection_failure():
    """Verifies MCPConnectionError when server script does not exist."""
    bad_client = EnterpriseMCPClient(server_args=["scripts/does_not_exist.py"])
    with pytest.raises(MCPConnectionError) as exc_info:
        await bad_client.connect()
    assert "not found" in str(exc_info.value).lower()
