"""
Application Configuration Module.

Loads environment variables, validates settings, and enforces security
controls using Pydantic v2 and pydantic-settings. Secrets are never hard-coded.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Core Application Settings.
    Reads from environment variables and an optional .env file.
    """

    # Service Metadata
    APP_NAME: str = Field(
        default="Enterprise AI Knowledge & Support Agent",
        description="Name of the service",
    )
    APP_VERSION: str = Field(
        default="0.1.0",
        description="Semantic application version",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Deployment environment (development, staging, production, test)",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host address",
    )
    PORT: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server listening port",
    )

    # API Security Credentials
    API_KEY: str = Field(
        default="dev-insecure-api-key-replace-in-prod",
        description="Master API authentication key for API Gateway",
    )

    # Google Gemini / LLM Credentials
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key for LLM generation and embeddings",
    )

    # Qdrant Vector Database
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="URL for Qdrant vector database instance",
    )
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional API key for Qdrant Cloud or protected instance",
    )
    QDRANT_COLLECTION_NAME: str = Field(
        default="enterprise_knowledge_base",
        description="Default Qdrant collection name",
    )

    # Model Parameters & Vector Tuning
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-004",
        description="Embedding model name",
    )
    EMBEDDING_DIMENSION: int = Field(
        default=768,
        description="Dimension size for vector embeddings",
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.72,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for RAG retrieval",
    )
    TOP_K: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of chunks to retrieve per search",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("QDRANT_URL")
    @classmethod
    def validate_qdrant_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("QDRANT_URL cannot be empty.")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("QDRANT_URL must start with http:// or https://")
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got '{v}'")
        return v_lower

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return v_upper

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        v_clean = v.strip()
        if env == "production" and (len(v_clean) < 16 or "dev" in v_clean.lower()):
            raise ValueError(
                "Production API_KEY must be a secure token with at least 16 characters."
            )
        return v_clean

    def is_gemini_configured(self) -> bool:
        """Returns True if a non-placeholder GEMINI_API_KEY is configured."""
        key = self.GEMINI_API_KEY.strip()
        return bool(key and not key.startswith("replace-with"))

    def is_qdrant_cloud(self) -> bool:
        """Returns True if connecting to Qdrant Cloud or requiring API key."""
        return bool(self.QDRANT_API_KEY and self.QDRANT_API_KEY.strip())


@lru_cache()
def get_settings() -> Settings:
    """Returns cached Settings instance."""
    return Settings()
