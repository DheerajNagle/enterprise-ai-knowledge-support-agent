"""
FastAPI Backend Application Package.

Exports the app factory, routers, and request/response models.
"""

from app.api.main import create_app, app
from app.api.routes import router
from app.api.schemas import (
    HealthResponse,
    ChatRequest,
    ChatResponse,
    IngestRequest,
    IngestResponse,
    TicketCreateRequest,
    TicketResponse,
    ToolsListResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
    ErrorResponse,
)

__all__ = [
    "create_app",
    "app",
    "router",
    "HealthResponse",
    "ChatRequest",
    "ChatResponse",
    "IngestRequest",
    "IngestResponse",
    "TicketCreateRequest",
    "TicketResponse",
    "ToolsListResponse",
    "ToolExecuteRequest",
    "ToolExecuteResponse",
    "ErrorResponse",
]
