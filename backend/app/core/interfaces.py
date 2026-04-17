"""Abstract base classes and shared data types for the ingestion pipeline.

All pipeline stages use these interfaces so that local implementations
(PyMuPDF, keyword classifier, sentence-transformers) can be swapped for
GCP services (Document AI, Gemini, Vertex AI) with zero caller changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PageText:
    """Text extracted from a single page of a document."""
    page_number: int
    text: str
    char_offset: int  # cumulative character offset from document start


@dataclass
class RawClause:
    """A raw clause segment extracted from document text."""
    raw_text: str
    page_number: int
    start_char: int
    end_char: int


@dataclass
class ClassificationResult:
    """Result of classifying a clause's type."""
    clause_type: str
    confidence: float
    extracted_parties: list[str] = field(default_factory=list)
    extracted_dates: list[str] = field(default_factory=list)


class BaseExtractor(ABC):
    """Interface for document text extraction.

    Local: PyMuPDFExtractor (uses fitz)
    GCP:   DocumentAIExtractor (uses Document AI)
    """

    @abstractmethod
    async def extract(self, source: str) -> list[PageText]:
        """Extract text from a document source (file path or GCS URI).

        Args:
            source: Local file path or GCS URI to the document.

        Returns:
            List of PageText objects, one per page.
        """
        ...


class BaseClassifier(ABC):
    """Interface for clause classification.

    Local: KeywordClassifier (weighted keyword matching)
    GCP:   GeminiClassifier (Gemini 1.5 Pro structured output)
    """

    @abstractmethod
    async def classify(self, text: str) -> ClassificationResult:
        """Classify a raw clause text into a clause type.

        Args:
            text: The raw text of the clause to classify.

        Returns:
            ClassificationResult with type, confidence, and extracted entities.
        """
        ...


class BaseEmbedder(ABC):
    """Interface for text embedding generation.

    Local: SentenceTransformerEmbedder (all-mpnet-base-v2)
    GCP:   VertexAIEmbedder (text-embedding-005)
    """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each 768-dimensional).
        """
        ...
