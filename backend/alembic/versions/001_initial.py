"""Initial tables — contracts and clauses with pgvector

Revision ID: 001_initial
Revises:
Create Date: 2026-04-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create contract_type_enum
    contract_type_enum = sa.Enum(
        "PLAYER", "SPONSORSHIP", "BROADCAST", "VENUE", "PARTNERSHIP", "OTHER",
        name="contract_type_enum",
    )
    contract_type_enum.create(op.get_bind(), checkfirst=True)

    # Create contract_status_enum
    contract_status_enum = sa.Enum(
        "PENDING", "PROCESSING", "INDEXED", "FAILED",
        name="contract_status_enum",
    )
    contract_status_enum.create(op.get_bind(), checkfirst=True)

    # Create clause_type_enum
    clause_type_enum = sa.Enum(
        "EXCLUSIVITY", "INDEMNITY", "TERMINATION", "GOVERNING_LAW", "RENEWAL",
        "PAYMENT", "IP_OWNERSHIP", "LIABILITY_CAP", "CONFIDENTIALITY", "OTHER",
        name="clause_type_enum",
    )
    clause_type_enum.create(op.get_bind(), checkfirst=True)

    # contracts table
    op.create_table(
        "contracts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column(
            "contract_type",
            sa.Enum(
                "PLAYER", "SPONSORSHIP", "BROADCAST", "VENUE", "PARTNERSHIP", "OTHER",
                name="contract_type_enum",
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("parties", sa.ARRAY(sa.String), server_default="{}"),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True),
        sa.Column("raw_text", sa.Text, server_default=""),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "PROCESSING", "INDEXED", "FAILED",
                name="contract_status_enum",
                create_constraint=True,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # clauses table
    op.create_table(
        "clauses",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "contract_id",
            sa.UUID(),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "clause_type",
            sa.Enum(
                "EXCLUSIVITY", "INDEMNITY", "TERMINATION", "GOVERNING_LAW",
                "RENEWAL", "PAYMENT", "IP_OWNERSHIP", "LIABILITY_CAP",
                "CONFIDENTIALITY", "OTHER",
                name="clause_type_enum",
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("start_char", sa.Integer, nullable=False),
        sa.Column("end_char", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("confidence_score", sa.Float, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("contract_id", "start_char", name="uq_clause_position"),
    )

    # IVFFlat index for approximate nearest-neighbor search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_clause_embedding "
        "ON clauses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_clause_embedding")
    op.drop_table("clauses")
    op.drop_table("contracts")
    sa.Enum(name="clause_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="contract_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="contract_type_enum").drop(op.get_bind(), checkfirst=True)
