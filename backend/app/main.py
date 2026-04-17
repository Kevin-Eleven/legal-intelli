"""Legal Intelligence API — FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.contracts import router as contracts_router
from app.config import settings
from app.database import init_pgvector

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Set up structured logging for the application."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown tasks."""
    _configure_logging()

    # 1. Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", upload_dir)

    # 2. Enable pgvector extension
    await init_pgvector()

    # 3. Run Alembic migrations programmatically
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

        # Run in a thread to avoid blocking the event loop
        import asyncio
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        logger.info("Database migrations applied")
    except Exception as exc:
        logger.warning("Alembic migration skipped: %s", exc)

    # 4. Eagerly load the embedding model
    if not settings.USE_GCP:
        from app.core.embeddings.embedder import SentenceTransformerEmbedder
        SentenceTransformerEmbedder.load_model()

    mode = "GCP" if settings.USE_GCP else "local"
    logger.info("Legal Intel API ready — %s mode", mode)

    yield

    logger.info("Legal Intel API shutting down")


app = FastAPI(
    title="Legal Intelligence API",
    description="Contract ingestion and clause indexing pipeline for sports organizations",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(contracts_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "mode": "gcp" if settings.USE_GCP else "local"}
