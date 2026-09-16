"""
FastAPI Dependency Injection Providers.

Provides centralized dependencies for authentication, database access,
agent service lifecycle, and document ingestion.
"""

from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.config import get_settings
from app.database.connection import DatabaseManager
from app.agent.service import AgentService, get_agent_service
from app.rag.ingestion import DocumentIngestionPipeline

from app.security.auth import APIKeyAuthenticator

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    Validates API key from either the 'X-API-Key' header or 'Authorization: Bearer <key>'.
    Enforces security boundaries on all protected API routes using constant-time comparison.
    """
    settings = get_settings()
    expected_key = settings.API_KEY.strip()

    provided_key = x_api_key or APIKeyAuthenticator.extract_bearer_token(authorization)

    if not APIKeyAuthenticator.verify(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing API key. Provide a valid 'X-API-Key' header.",
            },
        )

    return provided_key


def get_db() -> DatabaseManager:
    """Provides a DatabaseManager instance for SQLite operations."""
    return DatabaseManager()


def get_agent_service_dep() -> AgentService:
    """Provides the singleton AgentService instance."""
    return get_agent_service()


def get_ingestion_pipeline() -> DocumentIngestionPipeline:
    """Provides DocumentIngestionPipeline instance for knowledge base indexing."""
    return DocumentIngestionPipeline()
