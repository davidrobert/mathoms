"""Pydantic schemas for PasswordVault endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class VaultCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=500)


class VaultResponse(BaseModel):
    id: str
    label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VaultListResponse(BaseModel):
    passwords: list[VaultResponse]
    total: int
