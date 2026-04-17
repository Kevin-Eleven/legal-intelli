"""Embeddings generation and storage."""

from app.core.embeddings.embedder import SentenceTransformerEmbedder
from app.core.embeddings.store import store_clauses

__all__ = ["SentenceTransformerEmbedder", "store_clauses"]
