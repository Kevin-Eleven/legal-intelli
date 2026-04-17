"""Contract ORM model."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ContractType(str, enum.Enum):
    """Types of contracts managed by the system."""
    PLAYER = "PLAYER"
    SPONSORSHIP = "SPONSORSHIP"
    BROADCAST = "BROADCAST"
    VENUE = "VENUE"
    PARTNERSHIP = "PARTNERSHIP"
    OTHER = "OTHER"


class ContractStatus(str, enum.Enum):
    """Processing status of a contract."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class Contract(Base):
    """A legal contract document uploaded to the system."""

    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    contract_type: Mapped[str] = mapped_column(
        Enum(ContractType, name="contract_type_enum", create_constraint=True),
        nullable=False,
    )
    parties: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    effective_date: Mapped[date | None] = mapped_column(nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(ContractStatus, name="contract_status_enum", create_constraint=True),
        default=ContractStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    clauses: Mapped[list["Clause"]] = relationship(
        "Clause", back_populates="contract", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Contract {self.name} ({self.status})>"
