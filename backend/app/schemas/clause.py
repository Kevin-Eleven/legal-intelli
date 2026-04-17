"""Clause Pydantic schemas."""

import uuid

from pydantic import BaseModel, Field


class ClauseResponse(BaseModel):
    """Individual clause data returned to API consumers."""

    clause_id: uuid.UUID = Field(alias="id")
    contract_id: uuid.UUID
    clause_type: str
    raw_text: str
    page_number: int
    confidence_score: float

    model_config = {"from_attributes": True, "populate_by_name": True}
