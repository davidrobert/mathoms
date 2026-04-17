"""Report request/response schemas."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer


class ReportResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    period: Optional[str] = None
    size_bytes: Optional[int] = None
    score: Optional[float] = None
    patrimonio_liquido: Optional[float] = None
    created_at: datetime
    # F11.4a — linhagem: execução do pipeline que gerou o relatório (FK opcional).
    pipeline_run_id: Optional[str] = None
    # F11.4a — agregado: documentos prontos no workspace (IDs truncados p/ payload).
    source_document_count: int = 0
    source_document_ids: list[str] = Field(default_factory=list)
    # ADR-076 / F9: indica ao frontend se o relatório tem JSON de análise
    # disponível para o render nativo React. False = apenas HTML (legado pré-F9),
    # usar download do standalone HTML em vez do view nativo.
    has_analysis_data: bool = False
    # F11.6b — snapshot de premissas (metas + hash goals.json) na geração.
    premissas_snapshot: Optional[dict] = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    @classmethod
    def _serialize_created_at(cls, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int


class ReportAnalysisResponse(BaseModel):
    """Payload do endpoint GET /reports/{id}/data (F9 · F0.4).

    Serve o snapshot E5 JSON que alimenta o render nativo do relatório.
    Esquema frouxo nesta fase (E5 tem 24 chaves top-level; tipar
    incrementalmente conforme as seções migram para React — fases 2.A-2.H).
    """

    data: dict[str, Any]
