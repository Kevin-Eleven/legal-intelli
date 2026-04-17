"""Contract API routes — upload, list, and clause retrieval."""

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.embeddings.embedder import SentenceTransformerEmbedder
from app.core.embeddings.store import ClauseWithEmbedding, store_clauses
from app.core.ingestion.classifier import KeywordClassifier
from app.core.ingestion.extractor import PyMuPDFExtractor
from app.core.ingestion.segmenter import segment_clauses
from app.core.interfaces import BaseClassifier, BaseEmbedder, BaseExtractor
from app.database import async_session_factory, get_session
from app.models.clause import Clause, ClauseType
from app.models.contract import Contract, ContractStatus, ContractType
from app.schemas.clause import ClauseResponse
from app.schemas.contract import ContractListItem, ContractUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])

# Pipeline component instances (local mode)
_extractor: BaseExtractor = PyMuPDFExtractor()
_classifier: BaseClassifier = KeywordClassifier()
_embedder: BaseEmbedder = SentenceTransformerEmbedder()


async def _run_pipeline(contract_id: uuid.UUID, file_path: str) -> None:
    """Execute the full ingestion pipeline in the background.

    Stages: extract → segment → classify → embed → store
    Updates contract status to INDEXED on success, FAILED on error.
    """
    async with async_session_factory() as session:
        try:
            # Update status to PROCESSING
            contract = await session.get(Contract, contract_id)
            if not contract:
                logger.error("Contract %s not found", contract_id)
                return

            contract.status = ContractStatus.PROCESSING
            await session.commit()

            # Stage 1: Extract text
            logger.info("[%s] Stage 1: Extracting text", contract_id)
            pages = await _extractor.extract(file_path)
            raw_text = "\n".join(p.text for p in pages)

            # Save raw text to contract
            contract.raw_text = raw_text
            await session.commit()

            # Stage 2: Segment into clauses
            logger.info("[%s] Stage 2: Segmenting clauses", contract_id)
            raw_clauses = segment_clauses(pages)

            if not raw_clauses:
                logger.warning("[%s] No clauses found", contract_id)
                contract.status = ContractStatus.INDEXED
                await session.commit()
                return

            # Stage 3: Classify each clause
            logger.info("[%s] Stage 3: Classifying %d clauses", contract_id, len(raw_clauses))
            classifications = []
            for clause in raw_clauses:
                result = await _classifier.classify(clause.raw_text)
                classifications.append(result)

            # Stage 4: Embed all clause texts
            logger.info("[%s] Stage 4: Generating embeddings", contract_id)
            clause_texts = [c.raw_text for c in raw_clauses]
            embeddings = await _embedder.embed(clause_texts)

            # Stage 5: Store clauses with embeddings
            logger.info("[%s] Stage 5: Storing clauses", contract_id)
            clauses_to_store = [
                ClauseWithEmbedding(
                    raw_text=raw_clause.raw_text,
                    page_number=raw_clause.page_number,
                    start_char=raw_clause.start_char,
                    end_char=raw_clause.end_char,
                    clause_type=classification.clause_type,
                    confidence_score=classification.confidence,
                    embedding=embedding,
                )
                for raw_clause, classification, embedding in zip(
                    raw_clauses, classifications, embeddings
                )
            ]

            await store_clauses(clauses_to_store, contract_id, session)

            # Update contract with extracted parties/dates from classifications
            all_parties = []
            for c in classifications:
                all_parties.extend(c.extracted_parties)
            if all_parties:
                contract.parties = list(set(all_parties))

            contract.status = ContractStatus.INDEXED
            await session.commit()

            logger.info(
                "[%s] Pipeline complete — %d clauses indexed",
                contract_id,
                len(clauses_to_store),
            )

        except Exception as exc:
            logger.exception("[%s] Pipeline failed: %s", contract_id, exc)
            try:
                contract = await session.get(Contract, contract_id)
                if contract:
                    contract.status = ContractStatus.FAILED
                    await session.commit()
            except Exception:
                logger.exception("[%s] Failed to update status to FAILED", contract_id)


@router.post("/upload", response_model=ContractUploadResponse)
async def upload_contract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    contract_name: str = Form(...),
    contract_type: str = Form(...),
    session: AsyncSession = Depends(get_session),
) -> ContractUploadResponse:
    """Upload a contract PDF and start the ingestion pipeline.

    The pipeline runs as a background task; this endpoint returns
    immediately with the contract ID and PENDING status.
    """
    # Validate contract type
    try:
        ct = ContractType(contract_type)
    except ValueError:
        valid = [t.value for t in ContractType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid contract_type. Must be one of: {valid}",
        )

    # Validate file type
    if file.content_type and file.content_type != "application/pdf":
        if not (file.filename and file.filename.lower().endswith(".pdf")):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are accepted",
            )

    # Save uploaded file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    file_path = upload_dir / f"{file_id}.pdf"

    content = await file.read()
    file_path.write_bytes(content)

    # Create contract record
    contract = Contract(
        name=contract_name,
        contract_type=ct,
        file_path=str(file_path),
        status=ContractStatus.PENDING,
    )
    session.add(contract)
    await session.commit()
    await session.refresh(contract)

    # Launch pipeline in background
    background_tasks.add_task(_run_pipeline, contract.id, str(file_path))

    return ContractUploadResponse(
        contract_id=contract.id,
        name=contract.name,
        status=contract.status,
        message="Contract uploaded. Processing started in background.",
    )


@router.get("/{contract_id}/clauses", response_model=list[ClauseResponse])
async def get_contract_clauses(
    contract_id: uuid.UUID,
    clause_type: str | None = Query(None, description="Filter by clause type"),
    session: AsyncSession = Depends(get_session),
) -> list[ClauseResponse]:
    """Get all clauses for a specific contract.

    Optionally filter by clause_type (e.g., EXCLUSIVITY, TERMINATION).
    """
    # Verify contract exists
    contract = await session.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Build query
    stmt = select(Clause).where(Clause.contract_id == contract_id)

    if clause_type:
        try:
            ct = ClauseType(clause_type)
        except ValueError:
            valid = [t.value for t in ClauseType]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid clause_type. Must be one of: {valid}",
            )
        stmt = stmt.where(Clause.clause_type == ct)

    stmt = stmt.order_by(Clause.start_char)
    result = await session.execute(stmt)
    clauses = result.scalars().all()

    return [ClauseResponse.model_validate(c) for c in clauses]


@router.get("/", response_model=list[ContractListItem])
async def list_contracts(
    session: AsyncSession = Depends(get_session),
) -> list[ContractListItem]:
    """List all contracts with their status and clause count."""
    stmt = (
        select(
            Contract.id,
            Contract.name,
            Contract.contract_type,
            Contract.status,
            Contract.created_at,
            func.count(Clause.id).label("clause_count"),
        )
        .outerjoin(Clause, Contract.id == Clause.contract_id)
        .group_by(Contract.id)
        .order_by(Contract.created_at.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        ContractListItem(
            contract_id=row.id,
            name=row.name,
            contract_type=row.contract_type,
            status=row.status,
            clause_count=row.clause_count,
            created_at=row.created_at,
        )
        for row in rows
    ]
