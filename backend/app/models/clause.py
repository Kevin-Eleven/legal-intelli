"""Clause ORM model with pgvector embedding column."""

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClauseType(str, enum.Enum):
    """Types of legal clauses extracted from contracts."""
    EXCLUSIVITY = "EXCLUSIVITY"
    INDEMNITY = "INDEMNITY"
    TERMINATION = "TERMINATION"
    GOVERNING_LAW = "GOVERNING_LAW"
    RENEWAL = "RENEWAL"
    PAYMENT = "PAYMENT"
    IP_OWNERSHIP = "IP_OWNERSHIP"
    LIABILITY_CAP = "LIABILITY_CAP"
    CONFIDENTIALITY = "CONFIDENTIALITY"
    OTHER = "OTHER"


class Clause(Base):
    """An individual clause extracted from a contract document."""

    __tablename__ = "clauses"
    __table_args__ = (
        UniqueConstraint("contract_id", "start_char", name="uq_clause_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    clause_type: Mapped[str] = mapped_column(
        Enum(ClauseType, name="clause_type_enum", create_constraint=True),
        nullable=False,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_char: Mapped[int] = mapped_column(Integer, nullable=False)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(768), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    contract: Mapped["Contract"] = relationship("Contract", back_populates="clauses")

    def __repr__(self) -> str:
        return f"<Clause {self.clause_type} contract={self.contract_id}>"
