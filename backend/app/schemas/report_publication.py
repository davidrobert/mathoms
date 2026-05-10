"""Schemas Pydantic para ``report_publications`` (ADR-187 · ADR-109)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.report_publication import ReportPublication


class ReportPublicationCreate(BaseModel):
    """Body do ``POST /workspaces/{ws}/reports/{period}/publish``."""

    artifact_id: int = Field(
        ...,
        description="ID do PipelineArtifact (E7) que representa o snapshot publicado.",
        gt=0,
    )


class ReportPublicationResponse(BaseModel):
    """Snapshot serializável de uma publicação."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    period_yyyymm: str
    artifact_id: int
    published_at: datetime
    published_by: str
    immutable_hash: str
    unpublished_at: Optional[datetime] = None


class ReportPublicationListResponse(BaseModel):
    items: list[ReportPublicationResponse]


def to_response(publication: ReportPublication) -> ReportPublicationResponse:
    return ReportPublicationResponse.model_validate(publication)
