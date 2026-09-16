"""
Application Entrypoint and Gateway Server.

Initializes the FastAPI application from the API factory and exposes the ASGI
application instance for Uvicorn and production deployment.
"""

from app.config import get_settings
from app.api.main import create_app

settings = get_settings()

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
