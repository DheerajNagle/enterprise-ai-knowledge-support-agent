"""
FastAPI Application Factory & Core Server Configuration.

Configures the FastAPI application instance with:
- Structured logging & request tracing middleware (X-Request-ID)
- Global exception handlers for standard JSON error contracts
- Lifespan management for background resources and MCP client lifecycle
- Route registration for all API endpoints
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.api.routes import router
from app.agent.service import get_agent_service

logger = logging.getLogger("enterprise_agent.api")


# ==============================================================================
# Request Tracing & Performance Middleware
# ==============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Attaches a unique X-Request-ID to each incoming request state and echoes
    it back in the outgoing HTTP response headers for end-to-end auditability.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = req_id

        start_time = time.time()
        response = await call_next(request)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)

        logger.info(
            "[%s] %s %s -> %d (%.2f ms)",
            req_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


# ==============================================================================
# Application Lifespan Context
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown lifecycle events.
    Guarantees clean connection teardown and prevents orphaned subprocesses.
    """
    settings = get_settings()
    logger.info("Initializing %s v%s (%s environment)...", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    yield

    # Clean shutdown
    logger.info("Shutting down %s...", settings.APP_NAME)
    agent_service = get_agent_service()
    if agent_service.is_mcp_connected:
        try:
            await agent_service.stop()
        except Exception as exc:
            logger.warning("Error stopping Agent Service: %s", exc)


# ==============================================================================
# Application Factory
# ==============================================================================

def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise AI Knowledge & Support Agent REST Gateway",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and tracing middleware
    app.add_middleware(RequestIDMiddleware)

    # --------------------------------------------------------------------------
    # Global Structured Exception Handlers
    # --------------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", None)
        logger.warning("[%s] Request validation error: %s", req_id, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed. Please review the supplied parameters.",
                    "details": exc.errors(),
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = getattr(request.state, "request_id", None)
        if isinstance(exc.detail, dict):
            error_code = exc.detail.get("code", "HTTP_ERROR")
            error_msg = exc.detail.get("message", "An error occurred.")
            details = exc.detail.get("details", None)
        else:
            error_code = "HTTP_ERROR"
            error_msg = str(exc.detail)
            details = None

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": error_msg,
                    "details": details,
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        req_id = getattr(request.state, "request_id", None)
        logger.warning("[%s] Value error: %s", req_id, exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": str(exc),
                    "details": None,
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", None)
        logger.error("[%s] Unhandled server exception: %s", req_id, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please contact support.",
                    "details": None,
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    # Register API endpoints
    app.include_router(router)

    return app


app = create_app()
