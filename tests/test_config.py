"""
Unit tests for configuration validation and environment parsing.
"""

import pytest
from pydantic import ValidationError
from app.config import Settings


def test_default_settings():
    """Verify standard default settings load cleanly."""
    settings = Settings()
    assert settings.APP_NAME == "Enterprise AI Knowledge & Support Agent"
    assert settings.PORT == 8000
    assert settings.QDRANT_URL.startswith("http://")
    assert settings.SIMILARITY_THRESHOLD == 0.72
    assert settings.TOP_K == 5


def test_environment_override():
    """Verify custom settings override defaults."""
    custom = Settings(
        ENVIRONMENT="staging",
        LOG_LEVEL="DEBUG",
        PORT=9000,
        QDRANT_URL="https://custom-qdrant.internal:6333",
        API_KEY="custom-secure-api-key-staging",
        GEMINI_API_KEY="custom-gemini-token-12345",
    )
    assert custom.ENVIRONMENT == "staging"
    assert custom.LOG_LEVEL == "DEBUG"
    assert custom.PORT == 9000
    assert custom.QDRANT_URL == "https://custom-qdrant.internal:6333"
    assert custom.API_KEY == "custom-secure-api-key-staging"
    assert custom.is_gemini_configured() is True


def test_invalid_qdrant_url():
    """Verify that invalid QDRANT_URL scheme raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(QDRANT_URL="ftp://invalid-url.com")
    assert "QDRANT_URL must start with http:// or https://" in str(exc_info.value)


def test_invalid_environment():
    """Verify that invalid ENVIRONMENT raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="unknown_environment")
    assert "ENVIRONMENT must be one of" in str(exc_info.value)


def test_invalid_log_level():
    """Verify that invalid LOG_LEVEL raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(LOG_LEVEL="VERBOSE")
    assert "LOG_LEVEL must be one of" in str(exc_info.value)


def test_production_api_key_validation():
    """Verify that a weak API key in production environment raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            API_KEY="short-key",
        )
    assert "Production API_KEY must be a secure token" in str(exc_info.value)


def test_gemini_configured_flag():
    """Verify placeholder detection in GEMINI_API_KEY."""
    unconfigured = Settings(GEMINI_API_KEY="replace-with-your-key")
    assert unconfigured.is_gemini_configured() is False

    configured = Settings(GEMINI_API_KEY="AIzaSyA_valid_token_test")
    assert configured.is_gemini_configured() is True
