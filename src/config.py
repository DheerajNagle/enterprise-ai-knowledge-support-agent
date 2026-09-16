import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Enterprise AI Knowledge Support Agent"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    # Retrieval Settings
    embedding_model: str = "text-embedding-3-small"
    vector_store_type: str = "chroma"
    chroma_persist_dir: str = "./data/chroma_db"
    top_k_results: int = 5

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
