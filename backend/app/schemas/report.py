"""Report request/response schemas."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from backend.app.schemas.money import MoneyBRL
from backend.app.services.report_run_outcome import ReportRunOutcome


class ReportResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    period: Optional[str] = None
    score: Optional[float] = None
    # ADR-283 follow-up 2: Decimal em memória, number no wire (convenção
    # MoneyBRL/A6g.3b) — wire-string foi avaliado e rejeitado (campo NULL em
    # prod; cálculo de meta IF lê o DB direto, nunca o wire).
    patrimonio_liquido: Optional[MoneyBRL] = None
    created_at: datetime
    # F11.4a — linhagem: execução do pipeline que gerou o relatório (FK opcional).
    pipeline_run_id: Optional[str] = None
    # F11.4a — agregado: documentos prontos no workspace (IDs truncados p/ payload).
    source_document_count: int = 0
    source_document_ids: list[str] = Field(default_factory=list)
    # Documentos efetivamente consumidos pela run que gerou o relatório.
    # Diferente de ``source_document_count`` (snapshot atual do workspace, mutável):
    # esta métrica reflete autoria real e é imutável após a geração.
    consumed_document_count: int = 0
    consumed_document_ids: list[str] = Field(default_factory=list)
    # ADR-076 / F9 / ADR-131: indica ao frontend se o relatório tem JSON
    # de análise disponível para o render nativo React. ``False`` = relatório
    # legado pré-F9 ou cujo artifact foi removido (run hard-deleted).
    has_analysis_data: bool = False
    # F11.6b — snapshot de premissas (metas + hash goals.json) na geração.
    premissas_snapshot: Optional[dict] = None
    # v2.F.3a — sobrenome da família para a capa do relatório (cover identity).
    # Lido de ``Workspace.family_surname``; ``None`` quando não definido.
    workspace_family_surname: Optional[str] = None
    # A40.l18 · ADR-357 — desfecho do run, com polaridade POSITIVA: só
    # ``complete`` autoriza o relatório a afirmar "sem pendências". OBRIGATÓRIO
    # de propósito: campo opcional que chegue ``undefined`` (rollout, cache de
    # cliente antigo, fixture velha) faria a supressão sumir em silêncio.
    run_outcome: ReportRunOutcome

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


class ConsumoPontuaisItem(BaseModel):
    """Gasto pontual ≥ threshold após filtro de transferências internas."""

    data: str
    descricao: str
    valor: MoneyBRL
    banco: str
    categoria: str
    tipo_conta: Optional[str] = None
    titular: Optional[str] = None
    transaction_hash: str


class ConsumoPontuaisResponse(BaseModel):
    """Resposta do endpoint ``GET /reports/consumo-pontuais`` (ordenada desc)."""

    period: str
    date_from: str
    date_to: str
    items: list[ConsumoPontuaisItem]
    total: int
    total_valor: MoneyBRL


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
