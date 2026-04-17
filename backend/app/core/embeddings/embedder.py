"""Sentence-transformer embedder.

Local implementation of BaseEmbedder using all-mpnet-base-v2.
Will be replaced by VertexAIEmbedder for GCP production.
"""

import logging
from typing import ClassVar

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.interfaces import BaseEmbedder

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedder(BaseEmbedder):
    """Generate embeddings using a local sentence-transformers model.

    Uses a singleton pattern: the model is loaded once and shared
    across all calls. First load downloads ~420MB.
    """

    _instance: ClassVar["SentenceTransformerEmbedder | None"] = None
    _model: ClassVar[SentenceTransformer | None] = None

    def __new__(cls) -> "SentenceTransformerEmbedder":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load_model(cls) -> None:
        """Eagerly load the model into memory (call at startup)."""
        if cls._model is None:
            logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Get the loaded model, loading it if necessary."""
        if cls._model is None:
            cls.load_model()
        return cls._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate 768-dimensional embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of float vectors, each 768-dimensional.
        """
        return embed_clauses(texts)


def embed_clauses(texts: list[str]) -> list[list[float]]:
    """Generate embeddings in batches.

    Args:
        texts: List of clause texts to embed.

    Returns:
        List of 768-dim float vectors.
    """
    if not texts:
        return []

    model = SentenceTransformerEmbedder.get_model()
    batch_size = settings.EMBEDDING_BATCH_SIZE
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.extend(embeddings.tolist())

    logger.info("Generated %d embeddings", len(all_embeddings))
    return all_embeddings
