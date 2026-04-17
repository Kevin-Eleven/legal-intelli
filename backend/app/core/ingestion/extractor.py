"""PDF text extraction using PyMuPDF (fitz).

This is the local implementation of BaseExtractor.
Will be replaced by DocumentAIExtractor for GCP production.
"""

import logging

import fitz  # PyMuPDF

from app.core.interfaces import BaseExtractor, PageText

logger = logging.getLogger(__name__)


class PyMuPDFExtractor(BaseExtractor):
    """Extract text from PDFs using PyMuPDF (fitz).

    Handles text-based PDFs directly. For image-based PDFs (scanned),
    logs a warning and returns empty text for those pages — OCR will be
    handled by Document AI in production.
    """

    async def extract(self, source: str) -> list[PageText]:
        """Extract text from a local PDF file.

        Args:
            source: Path to the PDF file on disk.

        Returns:
            List of PageText objects, one per page.
        """
        return extract_text(source)


def extract_text(file_path: str) -> list[PageText]:
    """Extract text from a PDF file page by page.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of PageText with page number, text, and cumulative char offset.
    """
    pages: list[PageText] = []
    char_offset = 0

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.error("Failed to open PDF %s: %s", file_path, exc)
        raise ValueError(f"Cannot open PDF: {file_path}") from exc

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        if not text.strip():
            logger.warning(
                "Page %d of %s has no extractable text (possibly scanned/image)",
                page_num + 1,
                file_path,
            )

        pages.append(
            PageText(
                page_number=page_num + 1,
                text=text,
                char_offset=char_offset,
            )
        )
        char_offset += len(text)

    doc.close()
    logger.info(
        "Extracted %d pages from %s (%d total chars)",
        len(pages),
        file_path,
        char_offset,
    )
    return pages
