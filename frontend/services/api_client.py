"""
API Client Service for Enterprise Streamlit Frontend.

Provides a robust, synchronous HTTP interface communicating with the FastAPI
backend. Enforces secret protection, structured error wrapping, and timeout
management without running any agent or database logic in the frontend.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger("enterprise_frontend.api_client")


@dataclass
class APIResult:
    """Standardized response container for all frontend API calls."""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


def map_workflow_label(raw_workflow: Optional[str]) -> str:
    """
    Maps backend workflow enum or identifier to canonical UI labels:
    - RAG
    - MCP
    - Direct LLM
    - RAG + MCP
    """
    if not raw_workflow:
        return "Direct LLM"
    
    clean = str(raw_workflow).upper().strip()
    if clean in ("RAG_ONLY", "RAG"):
        return "RAG"
    elif clean in ("TOOL_ONLY", "MCP"):
        return "MCP"
    elif clean in ("HYBRID_RAG_TOOL", "HYBRID", "RAG_TOOL", "RAG + MCP"):
        return "RAG + MCP"
    else:
        # e.g., SAFETY_REFUSAL, DIRECT_LLM, FALLBACK
        return "Direct LLM"


class EnterpriseAPIClient:
    """
    Synchronous HTTP client for FastAPI backend endpoints.
    Protects sensitive credentials and provides graceful failure handling.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str = "dev-insecure-api-key-replace-in-prod",
        timeout_seconds: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout = timeout_seconds

    def __repr__(self) -> str:
        # Never expose raw API key in string representations
        masked_key = f"{self._api_key[:4]}...{self._api_key[-4:]}" if len(self._api_key) > 8 else "***"
        return f"<EnterpriseAPIClient base_url='{self.base_url}' api_key='{masked_key}'>"

    @property
    def headers(self) -> Dict[str, str]:
        """Authenticated request headers."""
        return {
            "X-API-Key": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def check_health(self) -> APIResult:
        """Probe GET /health without requiring auth credentials."""
        url = f"{self.base_url}/health"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url)
                if res.status_code == 200:
                    return APIResult(success=True, status_code=200, data=res.json())
                return APIResult(
                    success=False,
                    status_code=res.status_code,
                    error=f"Health check failed with status {res.status_code}",
                )
        except (httpx.ConnectError, httpx.TimeoutException):
            return APIResult(
                success=False,
                status_code=503,
                error=f"Cannot connect to backend server at {self.base_url}. Ensure FastAPI is running.",
            )
        except Exception as exc:
            return APIResult(
                success=False,
                status_code=500,
                error=f"Unexpected health check error: {str(exc)}",
            )

    def send_chat(
        self,
        message: str,
        user_id: Optional[str] = None,
        department: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> APIResult:
        """Dispatch conversational query to POST /api/chat."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "message": message,
            "user_id": user_id,
            "department": department,
            "conversation_history": conversation_history,
            "filter_criteria": filter_criteria,
            "dry_run": dry_run,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload, headers=self.headers)
                return self._parse_response(res)
        except (httpx.ConnectError, httpx.TimeoutException):
            return APIResult(
                success=False,
                status_code=503,
                error="Cannot connect to API server. Please check backend status in sidebar.",
            )
        except Exception as exc:
            return APIResult(
                success=False,
                status_code=500,
                error=f"Chat request failed: {str(exc)}",
            )

    def upload_and_ingest(
        self,
        file_name: str,
        file_bytes: bytes,
        staging_dir: str = "data/documents",
    ) -> APIResult:
        """
        Saves uploaded file content to staging directory and invokes POST /api/ingest.
        Strictly enforces file extension whitelisting (.pdf, .txt, .md).
        """
        # Validate extension
        suffix = Path(file_name).suffix.lower()
        if suffix not in {".pdf", ".txt", ".md"}:
            return APIResult(
                success=False,
                status_code=400,
                error=f"Unsupported file type '{suffix}'. Allowed types are: .pdf, .txt, .md",
                error_code="UNSUPPORTED_FILE_TYPE",
            )

        # Enforce size limit (10MB)
        if len(file_bytes) > 10 * 1024 * 1024:
            return APIResult(
                success=False,
                status_code=400,
                error=f"File exceeds maximum allowed size of 10MB.",
                error_code="FILE_SIZE_EXCEEDED",
            )

        try:
            out_dir = Path(staging_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_name = Path(file_name).name
            target_path = out_dir / safe_name
            target_path.write_bytes(file_bytes)

            # Call ingestion API
            url = f"{self.base_url}/api/ingest"
            payload = {"file_paths": [str(target_path)]}
            with httpx.Client(timeout=60.0) as client:
                res = client.post(url, json=payload, headers=self.headers)
                return self._parse_response(res)
        except Exception as exc:
            return APIResult(
                success=False,
                status_code=500,
                error=f"Document upload failed: {str(exc)}",
            )

    def create_ticket(
        self,
        employee_id: str,
        title: str,
        description: str,
        category: str = "GENERAL",
        priority: str = "MEDIUM",
    ) -> APIResult:
        """Submit support ticket to POST /api/tickets."""
        url = f"{self.base_url}/api/tickets"
        payload = {
            "employee_id": employee_id,
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload, headers=self.headers)
                return self._parse_response(res)
        except (httpx.ConnectError, httpx.TimeoutException):
            return APIResult(
                success=False,
                status_code=503,
                error="Backend server unavailable.",
            )
        except Exception as exc:
            return APIResult(
                success=False,
                status_code=500,
                error=f"Ticket creation failed: {str(exc)}",
            )

    def get_ticket(self, ticket_id: str) -> APIResult:
        """Lookup ticket status by ID via GET /api/tickets/{ticket_id}."""
        url = f"{self.base_url}/api/tickets/{ticket_id.strip()}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self.headers)
                return self._parse_response(res)
        except (httpx.ConnectError, httpx.TimeoutException):
            return APIResult(
                success=False,
                status_code=503,
                error="Backend server unavailable.",
            )
        except Exception as exc:
            return APIResult(
                success=False,
                status_code=500,
                error=f"Ticket lookup failed: {str(exc)}",
            )

    def list_tools(self) -> APIResult:
        """Query registered tools catalog via GET /api/tools."""
        url = f"{self.base_url}/api/tools"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self.headers)
                return self._parse_response(res)
        except (httpx.ConnectError, httpx.TimeoutException):
            return APIResult(
                success=False,
                status_code=503,
                error="Backend server unavailable.",
            )
        except Exception as exc:
            return APIResult(
                success=False,
                status_code=500,
                error=f"Failed to fetch tools catalog: {str(exc)}",
            )

    def execute_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> APIResult:
        """Directly invoke an operational tool via POST /api/tools/{tool_name}."""
        url = f"{self.base_url}/api/tools/{tool_name}"
        payload = {"arguments": arguments or {}}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload, headers=self.headers)
                return self._parse_response(res)
        except (httpx.ConnectError, httpx.TimeoutException):
            return APIResult(
                success=False,
                status_code=503,
                error="Backend server unavailable.",
            )
        except Exception as exc:
            return APIResult(
                success=False,
                status_code=500,
                error=f"Tool execution failed: {str(exc)}",
            )

    def _parse_response(self, response: httpx.Response) -> APIResult:
        """Normalizes HTTP responses into structured APIResult."""
        try:
            data = response.json()
        except Exception:
            data = None

        if 200 <= response.status_code < 300:
            return APIResult(success=True, status_code=response.status_code, data=data)

        # Extract structured error message if available
        err_msg = f"HTTP {response.status_code}"
        err_code = None
        if isinstance(data, dict):
            if "error" in data and isinstance(data["error"], dict):
                err_msg = data["error"].get("message", err_msg)
                err_code = data["error"].get("code")
            elif "detail" in data:
                if isinstance(data["detail"], dict):
                    err_msg = data["detail"].get("message", str(data["detail"]))
                    err_code = data["detail"].get("code")
                else:
                    err_msg = str(data["detail"])
            elif "message" in data:
                err_msg = str(data["message"])

        return APIResult(
            success=False,
            status_code=response.status_code,
            data=data,
            error=err_msg,
            error_code=err_code,
        )
