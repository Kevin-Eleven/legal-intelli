"""Shared test fixtures — synthetic PDF generation and async DB setup."""

import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure we generate the sample PDF before any test collection
SAMPLE_PDF_PATH = Path(__file__).parent / "sample_contract.pdf"


def _generate_sample_pdf(output_path: Path) -> None:
    """Generate a synthetic contract PDF with clearly labeled clauses.

    Contains three sections:
      1. An EXCLUSIVITY clause
      2. A TERMINATION clause
      3. A GOVERNING LAW clause
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()

    heading_style = ParagraphStyle(
        "ContractHeading",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceAfter=8,
        spaceBefore=16,
    )
    body_style = ParagraphStyle(
        "ContractBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    elements = []

    # Title
    elements.append(Paragraph("SPONSORSHIP AGREEMENT", heading_style))
    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(
            "This Sponsorship Agreement (the \"Agreement\") is entered into as of "
            "January 15, 2026, by and between Apex Sports League, Inc. (\"League\") "
            "and GlobalBrand Corporation (\"Sponsor\").",
            body_style,
        )
    )
    elements.append(Spacer(1, 20))

    # Section 1 — Exclusivity
    elements.append(Paragraph("Section 1. EXCLUSIVITY", section_style))
    elements.append(
        Paragraph(
            "1.1 The Sponsor shall have the exclusive right to be the sole and "
            "exclusive provider of branded athletic apparel for all League events. "
            "The League hereby grants Sponsor exclusivity within the sports apparel "
            "category during the term of this Agreement. No other supplier shall be "
            "permitted to provide competing products at League-sanctioned events. "
            "This exclusive right extends to all broadcasting, merchandising, and "
            "promotional activities conducted by or on behalf of the League.",
            body_style,
        )
    )
    elements.append(Spacer(1, 12))

    # Section 2 — Termination
    elements.append(Paragraph("Section 2. TERMINATION", section_style))
    elements.append(
        Paragraph(
            "2.1 Either party may terminate this Agreement upon ninety (90) days "
            "prior written notice to the other party. In the event of a material "
            "breach, the non-breaching party shall have the right to terminate this "
            "Agreement immediately upon delivery of written notice specifying the "
            "nature of the breach. The notice period for termination without cause "
            "shall commence on the date of receipt of the written termination notice. "
            "Upon termination, all rights granted hereunder shall immediately revert "
            "to the granting party. Any obligations that by their nature extend "
            "beyond the end of term shall survive termination.",
            body_style,
        )
    )
    elements.append(Spacer(1, 12))

    # Section 3 — Governing Law
    elements.append(Paragraph("Section 3. GOVERNING LAW", section_style))
    elements.append(
        Paragraph(
            "3.1 This Agreement shall be governed by and construed in accordance "
            "with the laws of the State of New York, without regard to its conflict "
            "of laws principles. Any disputes arising out of or in connection with "
            "this Agreement shall be submitted to the exclusive jurisdiction of the "
            "courts of New York County, New York. The parties hereby consent to the "
            "personal jurisdiction of such courts and waive any objection to venue "
            "in such jurisdiction.",
            body_style,
        )
    )
    elements.append(Spacer(1, 12))

    # Section 4 — Payment
    elements.append(Paragraph("Section 4. PAYMENT TERMS", section_style))
    elements.append(
        Paragraph(
            "4.1 Sponsor shall pay the League a total sponsorship fee of Five Million "
            "Dollars ($5,000,000.00) per season, payable in four equal quarterly "
            "installments. Each payment shall be due within thirty (30) days of the "
            "invoice date. Late payments shall bear interest at a rate of 1.5% per month. "
            "The compensation includes all rights granted under this Agreement.",
            body_style,
        )
    )

    doc.build(elements)


# Generate sample PDF if it doesn't exist
if not SAMPLE_PDF_PATH.exists():
    _generate_sample_pdf(SAMPLE_PDF_PATH)


@pytest.fixture(scope="session")
def sample_pdf_path() -> Path:
    """Path to the synthetic sample contract PDF."""
    if not SAMPLE_PDF_PATH.exists():
        _generate_sample_pdf(SAMPLE_PDF_PATH)
    return SAMPLE_PDF_PATH


@pytest.fixture
def tmp_pdf_path(sample_pdf_path: Path, tmp_path: Path) -> Path:
    """Copy the sample PDF to a temp directory for tests that modify it."""
    import shutil
    dest = tmp_path / "test_contract.pdf"
    shutil.copy2(sample_pdf_path, dest)
    return dest


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for testing FastAPI endpoints.

    Uses a test-specific database URL if set, otherwise falls back
    to the default. Skips model loading for faster test execution.
    """
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
