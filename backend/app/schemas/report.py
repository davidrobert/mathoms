"""Report request/response schemas."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ReportResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    period: Optional[str] = None
    score: Optional[float] = None
    patrimonio_liquido: Optional[float] = None
    created_at: datetime
    # F11.4a — linhagem: execução do pipeline que gerou o relatório (FK opcional).
    pipeline_run_id: Optional[str] = None
    # F11.4a — agregado: documentos prontos no workspace (IDs truncados p/ payload).
    source_document_count: int = 0
    source_document_ids: list[str] = Field(default_factory=list)
    # ADR-076 / F9 / ADR-131: indica ao frontend se o relatório tem JSON
    # de análise disponível para o render nativo React. ``False`` = relatório
    # legado pré-F9 ou cujo artifact foi removido (run hard-deleted).
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


class ReportTaskSnapshotItem(BaseModel):
    """Item do array ``tasks`` no snapshot/live fallback.

    Campos obrigatórios refletem o schema v1 em
    ``report_tasks_snapshot_service.SNAPSHOT_VERSION``. ``extra="allow"`` evita
    quebras quando a versão do snapshot for incrementada (v2+).
    """

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    number: Optional[int] = None
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    ref: Optional[str] = None
    deadline_kind: Optional[str] = None
    deadline_date: Optional[str] = None
    deadline_label: Optional[str] = None
    parent_task_id: Optional[str] = None


class ReportTasksResponse(BaseModel):
    """Payload do endpoint ``GET /reports/{id}/tasks``.

    Cobre duas variantes (ADR-074 §F8.3):
    - Snapshot imutável (``is_live_fallback=False``) — estado do momento da geração.
    - Fallback live (``is_live_fallback=True``) — relatórios pré-F8.3.

    Ambas compartilham a mesma shape; ``version`` e ``captured_at`` podem ser
    ``None`` no caminho live.
    """

    is_live_fallback: bool
    version: Optional[int] = None
    captured_at: Optional[str] = None
    total: int
    counts_by_status: dict[str, int] = Field(default_factory=dict)
    counts_by_priority: dict[str, int] = Field(default_factory=dict)
    tasks: list[ReportTaskSnapshotItem] = Field(default_factory=list)
