"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — all values come from env vars or .env file."""

    DATABASE_URL: str = (
        "postgresql+asyncpg://legaluser:localpassword@localhost:5432/legalintel"
    )
    UPLOAD_DIR: str = "/tmp/uploads"
    LOG_LEVEL: str = "INFO"
    USE_GCP: bool = False

    # Embedding model config (local mode)
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"
    EMBEDDING_BATCH_SIZE: int = 64
    EMBEDDING_DIM: int = 768

    # Segmenter tunables
    MIN_CLAUSE_LENGTH: int = 80
    MAX_CLAUSE_LENGTH: int = 3000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton instance
settings = Settings()
