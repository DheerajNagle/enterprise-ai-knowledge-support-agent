"""
Integration Tests for FastAPI REST Gateway.

Verifies:
1. Foundation and Subsystem Health Probes (GET /health, GET /api/health)
2. API Key Authentication & Bearer Header Security (401 Unauthorized)
3. Request ID Tracing and Latency Headers (X-Request-ID, X-Process-Time-Ms)
4. Request and Response Validation & Structured Error Envelopes (422, 400, 404)
5. Agent Chat Orchestration (POST /api/chat)
6. Document Knowledge Base Ingestion (POST /api/ingest)
7. Support Ticket Lifecycle (POST /api/tickets, GET /api/tickets/{ticket_id})
8. MCP Tools Discovery & Direct Execution (GET /api/tools, POST /api/tools/{tool_name})
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.config import get_settings
from app.agent import RootAgent, AgentService
from app.api.dependencies import get_agent_service_dep
from app.mcp import EnterpriseMCPClient

settings = get_settings()
VALID_API_KEY = settings.API_KEY


@pytest.fixture
def auth_headers():
    """Provides valid API Key header for protected routes."""
    return {"X-API-Key": VALID_API_KEY}


@pytest_asyncio.fixture
async def live_agent_service():
    """Initializes a live RootAgent orchestrator connected to MCP client for API tests."""
    mcp_client = EnterpriseMCPClient()
    await mcp_client.connect()
    try:
        agent = RootAgent(mcp_client=mcp_client)
        service = AgentService(mcp_client=mcp_client, root_agent=agent)
        app.dependency_overrides[get_agent_service_dep] = lambda: service
        yield service
    finally:
        app.dependency_overrides.pop(get_agent_service_dep, None)
        await mcp_client.disconnect()


# ==============================================================================
# 1. Health Probe Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify that GET /health returns 200 OK with component health status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["app"] == settings.APP_NAME
    assert data["version"] == settings.APP_VERSION
    assert "components" in data
    assert "database" in data["components"]
    assert "vector_store" in data["components"]


# ==============================================================================
# 2. Authentication & Authorization Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_auth_missing_api_key():
    """Verify that accessing protected routes without API key returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tools")

    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_invalid_api_key():
    """Verify that providing an incorrect API key returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tools", headers={"X-API-Key": "completely-invalid-key"})

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_bearer_token_support():
    """Verify that 'Authorization: Bearer <key>' is accepted as an alternative to X-API-Key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/tools",
            headers={"Authorization": f"Bearer {VALID_API_KEY}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "tools" in data


# ==============================================================================
# 3. Request Tracing & Middleware Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_request_id_generation_and_propagation():
    """Verify that responses include unique X-Request-ID and X-Process-Time-Ms headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers
    assert response.headers["X-Request-ID"].startswith("req-")


@pytest.mark.asyncio
async def test_custom_request_id_echo():
    """Verify that client-provided X-Request-ID is preserved and echoed back."""
    custom_id = "custom-trace-uuid-9999"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": custom_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


# ==============================================================================
# 4. Request Validation & Error Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_validation_error_structured_response(auth_headers):
    """Verify that 422 Unprocessable Entity returns standardized structured error JSON."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send empty message violating min_length=1
        response = await client.post(
            "/api/chat",
            json={"message": ""},
            headers=auth_headers,
        )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert "request_id" in data


# ==============================================================================
# 5. Chat Endpoint & Agent Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_chat_endpoint_rag_inquiry(auth_headers, live_agent_service):
    """Verify that POST /api/chat dispatches knowledge inquiry through RootAgent."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"message": "What is the remote work policy on core working hours?"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["workflow"] == "RAG_ONLY"
    assert len(data["response"]) > 0
    assert "request_id" in data
    assert isinstance(data["retrieved_knowledge"], list)
    assert data["grounded"] is True


@pytest.mark.asyncio
async def test_chat_endpoint_tool_inquiry(auth_headers, live_agent_service):
    """Verify that POST /api/chat routes operational request to tool execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"message": "Create a ticket because my keyboard keys are sticking"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["workflow"] == "TOOL_ONLY"
    assert len(data["tool_results"]) > 0
    assert data["tool_results"][0]["tool_name"] == "create_support_ticket"


# ==============================================================================
# 6. Document Ingestion Endpoint
# ==============================================================================

@pytest.mark.asyncio
async def test_ingest_endpoint_valid_file(auth_headers):
    """Verify that POST /api/ingest successfully indexes an existing policy file."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/ingest",
            json={"file_paths": ["data/documents/remote_work_policy.md"]},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("success", "partial")
    assert data["files_processed"] == 1
    assert data["chunks_created"] > 0


@pytest.mark.asyncio
async def test_ingest_endpoint_nonexistent_file(auth_headers):
    """Verify that POST /api/ingest returns 400 Bad Request for nonexistent file."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/ingest",
            json={"file_paths": ["nonexistent/fake_policy_file.md"]},
            headers=auth_headers,
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "FILE_NOT_FOUND"


# ==============================================================================
# 7. Support Tickets Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_create_and_get_ticket_lifecycle(auth_headers):
    """Verify POST /api/tickets creates a ticket and GET /api/tickets/{id} retrieves it."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create ticket for valid seeded employee
        create_payload = {
            "employee_id": "EMP-1001",
            "title": "Monitor flickering over HDMI connection",
            "description": "The external monitor blinks black every few minutes while working.",
            "category": "Hardware",
            "priority": "HIGH",
        }
        create_res = await client.post(
            "/api/tickets",
            json=create_payload,
            headers=auth_headers,
        )

        assert create_res.status_code == 201
        created_data = create_res.json()
        ticket_id = created_data["ticket_id"]
        assert ticket_id.startswith("TCK-")
        assert created_data["title"] == create_payload["title"]
        assert created_data["status"] == "OPEN"

        # Retrieve ticket by ID
        get_res = await client.get(
            f"/api/tickets/{ticket_id}",
            headers=auth_headers,
        )
        assert get_res.status_code == 200
        retrieved_data = get_res.json()
        assert retrieved_data["ticket_id"] == ticket_id
        assert retrieved_data["employee_id"] == "EMP-1001"


@pytest.mark.asyncio
async def test_create_ticket_invalid_employee(auth_headers):
    """Verify POST /api/tickets returns 400 when employee_id is nonexistent."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tickets",
            json={
                "employee_id": "EMP-NONEXISTENT-9999",
                "title": "Invalid employee test ticket",
                "description": "Should fail because employee does not exist in SQLite.",
                "category": "General",
                "priority": "LOW",
            },
            headers=auth_headers,
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_EMPLOYEE"


@pytest.mark.asyncio
async def test_get_ticket_not_found(auth_headers):
    """Verify GET /api/tickets/{ticket_id} returns 404 for nonexistent ticket."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/tickets/TCK-NONEXISTENT-9999",
            headers=auth_headers,
        )

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "TICKET_NOT_FOUND"


# ==============================================================================
# 8. MCP Tools Discovery & Execution
# ==============================================================================

@pytest.mark.asyncio
async def test_list_tools_endpoint(auth_headers):
    """Verify GET /api/tools returns the registered MCP tool definitions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tools", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert data["count"] > 0
    tool_names = [t["name"] for t in data["tools"]]
    assert "search_policy" in tool_names
    assert "create_support_ticket" in tool_names
    assert "get_ticket_status" in tool_names
    assert "get_employee_info" in tool_names


@pytest.mark.asyncio
async def test_execute_tool_endpoint_success(auth_headers):
    """Verify POST /api/tools/{tool_name} executes a tool directly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tools/get_employee_info",
            json={"arguments": {"email": "sarah.jenkins@enterprise.internal"}},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["tool_name"] == "get_employee_info"
    assert data["success"] is True
    assert "result" in data
    assert data["result"]["employee"]["employee_id"] == "EMP-1001"


@pytest.mark.asyncio
async def test_execute_tool_endpoint_not_found(auth_headers):
    """Verify POST /api/tools/{tool_name} returns 404 for unrecognized tool."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tools/nonexistent_fake_tool",
            json={"arguments": {}},
            headers=auth_headers,
        )

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "TOOL_NOT_FOUND"
