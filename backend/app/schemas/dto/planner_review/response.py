"""Response DTOs do aggregate ``PlannerReview`` (ADR-199) — stub do Ato 3 com ``content`` dict aberto; Ato 4 substitui por Pydantic tipado derivado do JSON Schema."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PlannerReviewResponse(BaseModel):
    """Parecer planejador — shape de resposta do endpoint stub (tier filtering vem no Ato 5)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    pipeline_run_id: str
    status: str
    persona_hash: str
    manifest_version: str
    schema_version: str
    model_id: str
    tier_at_generation: str
    items_shown_count: int
    items_gated_count: int
    cost_usd_cents: int
    created_at: datetime
    published_at: Optional[datetime] = None
    superseded_at: Optional[datetime] = None
    supersedes_id: Optional[str] = None
    superseded_by_id: Optional[str] = None
    immutable_hash: Optional[str] = None

    # Conteúdo do parecer (vem de pipeline_artifact.content_json). No Ato 3, dict
    # aberto; Ato 4 substitui por shape tipado derivado do JSON Schema.
    content: dict
