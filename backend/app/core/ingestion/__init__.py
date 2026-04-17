"""Ingestion pipeline — text extraction, segmentation, classification."""

from app.core.ingestion.extractor import PyMuPDFExtractor
from app.core.ingestion.segmenter import segment_clauses
from app.core.ingestion.classifier import KeywordClassifier

__all__ = ["PyMuPDFExtractor", "segment_clauses", "KeywordClassifier"]
