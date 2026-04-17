"""Contract Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContractUploadResponse(BaseModel):
    """Response returned immediately after uploading a contract."""

    contract_id: uuid.UUID
    name: str
    status: str
    message: str

    model_config = {"from_attributes": True}


class ContractListItem(BaseModel):
    """Summary of a contract for list views."""

    contract_id: uuid.UUID = Field(alias="id")
    name: str
    contract_type: str
    status: str
    clause_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
