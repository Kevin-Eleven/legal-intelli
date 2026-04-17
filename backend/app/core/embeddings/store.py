"""Clause storage — bulk insert with conflict handling and index creation."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clause import Clause, ClauseType

logger = logging.getLogger(__name__)


@dataclass
class ClauseWithEmbedding:
    """A classified clause with its embedding, ready for storage."""
    raw_text: str
    page_number: int
    start_char: int
    end_char: int
    clause_type: str
    confidence_score: float
    embedding: list[float]


async def store_clauses(
    clauses: list[ClauseWithEmbedding],
    contract_id: uuid.UUID,
    session: AsyncSession,
) -> int:
    """Bulk insert clauses with upsert on conflict.

    On conflict (contract_id + start_char), updates the existing row
    instead of creating a duplicate.

    Args:
        clauses: List of classified clauses with embeddings.
        contract_id: UUID of the parent contract.
        session: Async SQLAlchemy session.

    Returns:
        Number of clauses inserted/updated.
    """
    if not clauses:
        logger.warning("No clauses to store for contract %s", contract_id)
        return 0

    values = [
        {
            "id": uuid.uuid4(),
            "contract_id": contract_id,
            "clause_type": clause.clause_type,
            "raw_text": clause.raw_text,
            "page_number": clause.page_number,
            "start_char": clause.start_char,
            "end_char": clause.end_char,
            "embedding": clause.embedding,
            "confidence_score": clause.confidence_score,
        }
        for clause in clauses
    ]

    stmt = pg_insert(Clause).values(values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_clause_position",
        set_={
            "clause_type": stmt.excluded.clause_type,
            "raw_text": stmt.excluded.raw_text,
            "end_char": stmt.excluded.end_char,
            "embedding": stmt.excluded.embedding,
            "confidence_score": stmt.excluded.confidence_score,
        },
    )

    await session.execute(stmt)
    await session.commit()

    logger.info(
        "Stored %d clauses for contract %s", len(clauses), contract_id
    )

    # Ensure IVFFlat index exists (idempotent)
    await _ensure_embedding_index(session)

    return len(clauses)


async def _ensure_embedding_index(session: AsyncSession) -> None:
    """Create the IVFFlat index on the embedding column if it doesn't exist."""
    try:
        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_clause_embedding "
                "ON clauses USING ivfflat (embedding vector_cosine_ops) "
                "WITH (lists = 50)"
            )
        )
        await session.commit()
    except Exception as exc:
        # Index creation may fail if there aren't enough rows for IVFFlat
        # (needs at least lists * 10 rows). This is expected early on.
        logger.debug("IVFFlat index creation skipped: %s", exc)
        await session.rollback()
