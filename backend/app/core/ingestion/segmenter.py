"""Clause segmentation — splits extracted text into individual clauses.

Two-pass approach:
  Pass 1: Structural split using regex patterns for numbered sections,
           article/section headings, and ALL-CAPS headings.
  Pass 2: Merge short fragments (under MIN_CLAUSE_LENGTH) with the next
           segment; split oversized segments (over MAX_CLAUSE_LENGTH).
"""

import logging
import re

from app.config import settings
from app.core.interfaces import PageText, RawClause

logger = logging.getLogger(__name__)

# Patterns that indicate a new clause/section boundary
SECTION_PATTERNS = [
    re.compile(r"^\d+\.\d*\s", re.MULTILINE),          # "1. " or "1.1 "
    re.compile(
        r"^(Article|Section|Clause)\s+\d+", re.MULTILINE | re.IGNORECASE
    ),                                                    # "Article 1", "Section 2"
    re.compile(r"^[A-Z][A-Z\s]{3,30}\n", re.MULTILINE),  # ALL CAPS heading lines
]


def segment_clauses(pages: list[PageText]) -> list[RawClause]:
    """Segment extracted pages into individual clause fragments.

    Args:
        pages: List of PageText objects from the extractor.

    Returns:
        List of RawClause objects with positional metadata.
    """
    # Concatenate all page text, track page boundaries
    full_text = ""
    page_boundaries: list[tuple[int, int, int]] = []  # (start, end, page_num)

    for page in pages:
        start = len(full_text)
        full_text += page.text
        end = len(full_text)
        page_boundaries.append((start, end, page.page_number))

    if not full_text.strip():
        logger.warning("No text to segment")
        return []

    # Pass 1: Find all split points
    split_points: set[int] = {0}
    for pattern in SECTION_PATTERNS:
        for match in pattern.finditer(full_text):
            split_points.add(match.start())
    split_points.add(len(full_text))

    sorted_points = sorted(split_points)

    # Extract raw segments
    raw_segments: list[tuple[int, int, str]] = []
    for i in range(len(sorted_points) - 1):
        start = sorted_points[i]
        end = sorted_points[i + 1]
        text = full_text[start:end].strip()
        if text:
            raw_segments.append((start, end, text))

    # Pass 2: Merge short fragments, split oversized ones
    merged = _merge_short_segments(raw_segments, settings.MIN_CLAUSE_LENGTH)
    final_segments = _split_long_segments(merged, settings.MAX_CLAUSE_LENGTH)

    # Convert to RawClause with page numbers
    clauses: list[RawClause] = []
    for start, end, text in final_segments:
        page_num = _find_page_number(start, page_boundaries)
        clauses.append(
            RawClause(
                raw_text=text,
                page_number=page_num,
                start_char=start,
                end_char=end,
            )
        )

    logger.info("Segmented text into %d clauses", len(clauses))
    return clauses


def _merge_short_segments(
    segments: list[tuple[int, int, str]],
    min_length: int,
) -> list[tuple[int, int, str]]:
    """Merge segments shorter than min_length with the next segment."""
    if not segments:
        return []

    merged: list[tuple[int, int, str]] = []
    buffer_start, buffer_end, buffer_text = segments[0]

    for i in range(1, len(segments)):
        start, end, text = segments[i]
        if len(buffer_text) < min_length:
            # Merge with current segment
            buffer_end = end
            buffer_text = buffer_text + "\n" + text
        else:
            merged.append((buffer_start, buffer_end, buffer_text))
            buffer_start, buffer_end, buffer_text = start, end, text

    # Don't forget the last buffer
    if buffer_text:
        merged.append((buffer_start, buffer_end, buffer_text))

    return merged


def _split_long_segments(
    segments: list[tuple[int, int, str]],
    max_length: int,
) -> list[tuple[int, int, str]]:
    """Split segments exceeding max_length at sentence boundaries."""
    result: list[tuple[int, int, str]] = []

    for start, end, text in segments:
        if len(text) <= max_length:
            result.append((start, end, text))
            continue

        # Split at sentence boundaries (period + space/newline)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunk_text = ""
        chunk_start = start

        for sentence in sentences:
            if len(chunk_text) + len(sentence) > max_length and chunk_text:
                chunk_end = chunk_start + len(chunk_text)
                result.append((chunk_start, chunk_end, chunk_text.strip()))
                chunk_start = chunk_end
                chunk_text = sentence
            else:
                chunk_text = (chunk_text + " " + sentence).strip() if chunk_text else sentence

        if chunk_text.strip():
            result.append((chunk_start, chunk_start + len(chunk_text), chunk_text.strip()))

    return result


def _find_page_number(
    char_pos: int,
    page_boundaries: list[tuple[int, int, int]],
) -> int:
    """Determine which page a character position falls on."""
    for start, end, page_num in page_boundaries:
        if start <= char_pos < end:
            return page_num
    # Default to last page if beyond boundaries
    return page_boundaries[-1][2] if page_boundaries else 1
