"""
Application Entrypoint and Foundation REST API.

Provides the initial FastAPI application instance, lifespan handler,
and the foundation GET /health endpoint for readiness testing.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown events."""
    # Startup: logging and resource preparation
    yield
    # Shutdown: clean up connections


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise AI Knowledge & Support Agent REST Gateway",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Foundation health check endpoint.
    Used for liveness probes, container readiness checks, and baseline verification.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "gemini_configured": settings.is_gemini_configured(),
        "qdrant_url": settings.QDRANT_URL,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
