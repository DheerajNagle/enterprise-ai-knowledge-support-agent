"""
Unit and Integration Tests for Streamlit Frontend Services & Components.

Tests the EnterpriseAPIClient, workflow label mappings, file validation,
secret protection, and interaction with the FastAPI backend.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from frontend.services.api_client import EnterpriseAPIClient, APIResult, map_workflow_label


# ==============================================================================
# 1. Workflow Label Mapping Tests
# ==============================================================================

def test_map_workflow_label_rag():
    assert map_workflow_label("RAG_ONLY") == "RAG"
    assert map_workflow_label("rag") == "RAG"


def test_map_workflow_label_mcp():
    assert map_workflow_label("TOOL_ONLY") == "MCP"
    assert map_workflow_label("mcp") == "MCP"


def test_map_workflow_label_hybrid():
    assert map_workflow_label("HYBRID_RAG_TOOL") == "RAG + MCP"
    assert map_workflow_label("hybrid") == "RAG + MCP"
    assert map_workflow_label("RAG + MCP") == "RAG + MCP"


def test_map_workflow_label_direct_llm():
    assert map_workflow_label("SAFETY_REFUSAL") == "Direct LLM"
    assert map_workflow_label("DIRECT_LLM") == "Direct LLM"
    assert map_workflow_label("unknown") == "Direct LLM"
    assert map_workflow_label(None) == "Direct LLM"


# ==============================================================================
# 2. Secret Protection & Client Representation
# ==============================================================================

def test_client_repr_masks_secret():
    secret_key = "sk-live-super-secret-enterprise-key-12345"
    client = EnterpriseAPIClient(base_url="http://localhost:8000", api_key=secret_key)
    repr_str = repr(client)
    
    assert secret_key not in repr_str
    assert "sk-l...2345" in repr_str
    assert "http://localhost:8000" in repr_str


def test_client_headers_contain_api_key():
    client = EnterpriseAPIClient(base_url="http://localhost:8000", api_key="test-key-xyz")
    headers = client.headers
    assert headers["X-API-Key"] == "test-key-xyz"
    assert headers["Content-Type"] == "application/json"


# ==============================================================================
# 3. File Validation in Frontend Client
# ==============================================================================

def test_upload_and_ingest_rejects_unauthorized_extensions():
    client = EnterpriseAPIClient()
    unauthorized = ["malicious.exe", "script.py", "exploit.sh", "doc.docx", "data.json"]
    
    for filename in unauthorized:
        res = client.upload_and_ingest(filename, b"dummy content")
        assert not res.success
        assert res.status_code == 400
        assert res.error_code == "UNSUPPORTED_FILE_TYPE"
        assert "Allowed types are: .pdf, .txt, .md" in res.error


def test_upload_and_ingest_rejects_oversized_files():
    client = EnterpriseAPIClient()
    oversized_bytes = b"x" * (10 * 1024 * 1024 + 1)
    res = client.upload_and_ingest("large.txt", oversized_bytes)
    assert not res.success
    assert res.status_code == 400
    assert res.error_code == "FILE_SIZE_EXCEEDED"


# ==============================================================================
# 4. Error Handling on Network / Server Failure
# ==============================================================================

def test_client_health_check_connection_error():
    # Use invalid port to trigger ConnectError
    client = EnterpriseAPIClient(base_url="http://127.0.0.1:59999", timeout_seconds=1.0)
    res = client.check_health()
    assert not res.success
    assert res.status_code == 503
    assert "Cannot connect to backend server" in res.error


def test_client_send_chat_connection_error():
    client = EnterpriseAPIClient(base_url="http://127.0.0.1:59999", timeout_seconds=1.0)
    res = client.send_chat("Hello")
    assert not res.success
    assert res.status_code == 503
    assert "Cannot connect to API server" in res.error


# ==============================================================================
# 5. Integration with FastAPI Application Endpoints
# ==============================================================================

@pytest.fixture
def fastapi_app():
    return create_app()


@pytest.fixture
def app_client(fastapi_app):
    return TestClient(fastapi_app)


def test_frontend_health_check_with_live_app(app_client):
    """Test health check parsing against FastAPI app."""
    # We patch httpx.Client in EnterpriseAPIClient to route to TestClient
    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_instance
        
        # Setup simulated healthy response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "app": "Enterprise AI Knowledge & Support Agent",
            "version": "0.1.0",
            "environment": "test",
            "components": {
                "database": {"status": "healthy"},
                "vector_store": {"status": "healthy"},
                "mcp_client": {"status": "healthy"},
                "gemini_llm": {"status": "offline_fallback"},
            }
        }
        mock_instance.get.return_value = mock_response
        
        client = EnterpriseAPIClient(base_url="http://127.0.0.1:8000")
        res = client.check_health()
        assert res.success
        assert res.status_code == 200
        assert res.data["status"] == "healthy"
        assert "database" in res.data["components"]


def test_frontend_ticket_lifecycle(fastapi_app, app_client):
    """Test creating and retrieving support tickets through frontend client."""
    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_instance
        
        # 1. Test create ticket success
        mock_create_resp = MagicMock()
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {
            "ticket_id": "TCK-2026-999999",
            "employee_id": "EMP-001",
            "title": "Need second monitor",
            "description": "Ergonomic hardware request",
            "category": "HARDWARE",
            "priority": "MEDIUM",
            "status": "OPEN",
            "created_at": "2026-09-16T12:00:00Z",
            "updated_at": "2026-09-16T12:00:00Z",
        }
        mock_instance.post.return_value = mock_create_resp

        client = EnterpriseAPIClient()
        res_create = client.create_ticket(
            employee_id="EMP-001",
            title="Need second monitor",
            description="Ergonomic hardware request",
            category="HARDWARE",
            priority="MEDIUM",
        )
        assert res_create.success
        assert res_create.data["ticket_id"] == "TCK-2026-999999"

        # 2. Test get ticket success
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = mock_create_resp.json.return_value
        mock_instance.get.return_value = mock_get_resp

        res_get = client.get_ticket("TCK-2026-999999")
        assert res_get.success
        assert res_get.data["status"] == "OPEN"


def test_frontend_chat_dispatch(fastapi_app):
    """Test chat dispatch and parsing."""
    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_instance
        
        mock_chat_resp = MagicMock()
        mock_chat_resp.status_code = 200
        mock_chat_resp.json.return_value = {
            "request_id": "req-123456",
            "workflow": "RAG_ONLY",
            "response": "Employees are eligible for remote work after 90 days.",
            "retrieved_knowledge": [
                {
                    "filename": "remote_work_policy.md",
                    "section": "Eligibility",
                    "page_number": 1,
                    "chunk_text": "Full-time employees may request remote work after 90 days.",
                    "relevance_score": 0.88,
                    "citation": "[Source: remote_work_policy.md, Section: Eligibility]",
                }
            ],
            "tool_results": [],
            "grounded": True,
            "confidence_score": 0.95,
        }
        mock_instance.post.return_value = mock_chat_resp

        client = EnterpriseAPIClient()
        chat_res = client.send_chat(
            message="What is the remote work eligibility?",
            user_id="EMP-001",
            department="Engineering",
        )

        assert chat_res.success
        assert map_workflow_label(chat_res.data["workflow"]) == "RAG"
        assert len(chat_res.data["retrieved_knowledge"]) == 1
        assert chat_res.data["retrieved_knowledge"][0]["filename"] == "remote_work_policy.md"


def test_frontend_document_upload(tmp_path):
    """Test document upload and ingestion through EnterpriseAPIClient."""
    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_instance

        mock_ingest_resp = MagicMock()
        mock_ingest_resp.status_code = 200
        mock_ingest_resp.json.return_value = {
            "status": "success",
            "files_processed": 1,
            "documents_loaded": 1,
            "chunks_created": 4,
            "vectors_upserted": 4,
            "total_vectors_in_collection": 42,
            "elapsed_seconds": 1.25,
            "details": [{"file": "security_policy.md", "status": "success"}],
        }
        mock_instance.post.return_value = mock_ingest_resp

        client = EnterpriseAPIClient()
        test_file = "security_policy.md"
        test_bytes = b"# Security Policy\nEmployees must use MFA."
        staging_dir = str(tmp_path / "documents")

        res = client.upload_and_ingest(test_file, test_bytes, staging_dir=staging_dir)
        assert res.success
        assert res.data["chunks_created"] == 4
        assert res.data["vectors_upserted"] == 4

        # Verify file was written to staging_dir
        saved_file = Path(staging_dir) / test_file
        assert saved_file.exists()
        assert saved_file.read_bytes() == test_bytes


def test_frontend_tools_interaction():
    """Test listing and executing MCP tools through the frontend client."""
    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_instance

        # 1. List tools
        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "tools": [
                {
                    "name": "create_ticket",
                    "description": "Create support ticket",
                    "input_schema": {"type": "object"},
                }
            ],
            "count": 1,
        }
        mock_instance.get.return_value = mock_list_resp

        client = EnterpriseAPIClient()
        res_list = client.list_tools()
        assert res_list.success
        assert res_list.data["count"] == 1
        assert res_list.data["tools"][0]["name"] == "create_ticket"

        # 2. Execute tool
        mock_exec_resp = MagicMock()
        mock_exec_resp.status_code = 200
        mock_exec_resp.json.return_value = {
            "tool_name": "create_ticket",
            "success": True,
            "result": {"ticket_id": "TCK-12345"},
            "execution_time_seconds": 0.05,
        }
        mock_instance.post.return_value = mock_exec_resp

        res_exec = client.execute_tool("create_ticket", {"title": "Test"})
        assert res_exec.success
        assert res_exec.data["result"]["ticket_id"] == "TCK-12345"


def test_error_normalization_variants():
    """Test parsing varied error envelopes from backend."""
    client = EnterpriseAPIClient()

    # 1. RFC style error object
    resp1 = MagicMock()
    resp1.status_code = 400
    resp1.json.return_value = {"error": {"code": "BAD_INPUT", "message": "Invalid field value"}}
    parsed1 = client._parse_response(resp1)
    assert not parsed1.success
    assert parsed1.status_code == 400
    assert parsed1.error == "Invalid field value"
    assert parsed1.error_code == "BAD_INPUT"

    # 2. FastAPI detail dict
    resp2 = MagicMock()
    resp2.status_code = 404
    resp2.json.return_value = {"detail": {"code": "NOT_FOUND", "message": "Item missing"}}
    parsed2 = client._parse_response(resp2)
    assert not parsed2.success
    assert parsed2.status_code == 404
    assert parsed2.error == "Item missing"
    assert parsed2.error_code == "NOT_FOUND"

    # 3. FastAPI detail string
    resp3 = MagicMock()
    resp3.status_code = 401
    resp3.json.return_value = {"detail": "Invalid or missing API key"}
    parsed3 = client._parse_response(resp3)
    assert not parsed3.success
    assert parsed3.status_code == 401
    assert parsed3.error == "Invalid or missing API key"

    # 4. Non-JSON response
    resp4 = MagicMock()
    resp4.status_code = 502
    resp4.json.side_effect = ValueError("Not JSON")
    parsed4 = client._parse_response(resp4)
    assert not parsed4.success
    assert parsed4.status_code == 502
    assert parsed4.error == "HTTP 502"


def test_render_workflow_pill():
    """Verify HTML pill rendering for workflows."""
    from frontend.components.chat import render_workflow_pill

    rag_pill = render_workflow_pill("RAG")
    assert "workflow-rag" in rag_pill
    assert "Workflow: RAG" in rag_pill

    mcp_pill = render_workflow_pill("MCP")
    assert "workflow-mcp" in mcp_pill
    assert "Workflow: MCP" in mcp_pill

    hybrid_pill = render_workflow_pill("RAG + MCP")
    assert "workflow-hybrid" in hybrid_pill
    assert "Workflow: RAG + MCP" in hybrid_pill

    direct_pill = render_workflow_pill("Direct LLM")
    assert "workflow-direct" in direct_pill
    assert "Workflow: Direct LLM" in direct_pill


def test_all_components_importable():
    """Verify all UI components and entry point can be imported cleanly."""
    import frontend.components as fc
    assert hasattr(fc, "apply_custom_styles")
    assert hasattr(fc, "render_sidebar")
    assert hasattr(fc, "render_chat_view")
    assert hasattr(fc, "render_rag_sources")
    assert hasattr(fc, "render_tool_executions")
    assert hasattr(fc, "render_tickets_view")
    assert hasattr(fc, "render_documents_view")
    assert hasattr(fc, "render_tools_explorer_view")
