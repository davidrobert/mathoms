"""Pydantic schemas for Pipeline execution endpoints."""

from datetime import datetime, timezone
from typing import Literal, Optional, Union

from pydantic import BaseModel, computed_field, field_serializer, field_validator

from backend.app.models.pipeline_run import PipelineRunStatus, PipelineStageStatus
from backend.app.models.stage_review import StageReviewStatus

# ADR-165: context aceita primitivos serializáveis em JSON. Todos os codes
# atuais (e16.*) usam apenas str/int/float/bool/None — ver
# `pipeline/llm/validators.py`. Nested dict não é permitido no boundary.
ValidationContextValue = Union[str, int, float, bool, None]


def _valid_from_stages() -> frozenset[str]:
    """Keys do FROM_MAP — fonte única (descritivos pós-F9.2 + aliases legados)."""
    # O set hardcoded legado (E0..E7) rejeitava ``failed_at_stage`` descritivo
    # (ex.: ``review_finances_holistic``), quebrando o botão "Reprocessar a
    # partir de <stage>" da UI para todo run pós-F9.2 (incidente 2026-06-12).
    from pipeline.orchestrator import FROM_MAP

    return frozenset(FROM_MAP)


class PipelineRunRequest(BaseModel):
    from_stage: Optional[str] = None
    skip_llm: bool = True
    stop_on_error: bool = True
    incremental: bool = False

    @field_validator("from_stage")
    @classmethod
    def validate_from_stage(cls, v: Optional[str] = None) -> Optional[str]:
        if v is not None and v not in _valid_from_stages():
            raise ValueError(f"from_stage inválido: {v}. Válidos: {sorted(_valid_from_stages())}")
        return v


class PipelineStageLogResponse(BaseModel):
    id: str
    stage: str
    status: PipelineStageStatus
    output_summary: Optional[dict] = None
    errors: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("started_at", "completed_at")
    @classmethod
    def _serialize_dt_utc(cls, v: datetime | None) -> str | None:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class ValidationIssueDTO(BaseModel):
    """ADR-165 onda 2: representação API de `pipeline.llm.validators.ValidationIssue`.
    Issues projetadas de ReviewReason (ADR-272/ADR-308) carregam em ``context`` as
    chaves ``artifact_key``/``document_id``/``offending_value``/``expected`` e, quando
    o documento de origem é resolvido, a identidade legível (A32.l6):
    ``doc_bank_code``, ``doc_type``, ``doc_e0_type``, ``doc_period``."""

    code: str
    severity: Literal["error", "warning"]
    path: Optional[str] = None
    context: dict[str, ValidationContextValue] = {}
    legacy_message: str = ""


def _summarize_issues(issues: list[ValidationIssueDTO]) -> str:
    """Frase curta derivada de issues (ADR-165 D4) — fallback para clientes não-onda3."""
    if not issues:
        return ""
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    if len(errors) == 1 and not warnings:
        return errors[0].legacy_message or errors[0].code
    if not errors and len(warnings) == 1:
        return warnings[0].legacy_message or warnings[0].code
    parts = []
    if errors:
        parts.append(f"{len(errors)} erro(s)")
    if warnings:
        parts.append(f"{len(warnings)} aviso(s)")
    return " + ".join(parts) + " na revisão"


class StageReviewResponse(BaseModel):
    id: str
    pipeline_run_id: str
    stage: str
    status: StageReviewStatus
    original_output_json: Optional[dict] = None
    edited_output_json: Optional[dict] = None
    validation_errors: Optional[str] = None
    validation_issues: Optional[list[ValidationIssueDTO]] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> str:
        """Frase curta derivada (ADR-165 D4) — não persistida; recomputada por GET."""
        return _summarize_issues(self.validation_issues or [])


class StageReviewActionRequest(BaseModel):
    action: str  # "approve" or "edit"
    edited_output_json: Optional[dict] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "edit"):
            raise ValueError("action must be 'approve' or 'edit'")
        return v


class PipelineRunResponse(BaseModel):
    id: str
    workspace_id: str
    status: PipelineRunStatus
    current_stage: Optional[str] = None
    failed_at_stage: Optional[str] = None
    # A40.l27 — coluna write-only desde 2026-05: a ADR-172 decidiu "UI consome
    # `failure_reason` e mostra mensagem honesta" e o campo nunca saiu do DB. A ADR-359
    # acrescentou 3 valores ao vocabulário, e sem read path os 4 são legíveis só por SQL —
    # a distinção que eles compram não chega a operador nem a usuário.
    failure_reason: Optional[str] = None
    paused_at_stage: Optional[str] = None
    tier_at_run: str = "free"
    total_documents: Optional[int] = None
    incremental: bool = False
    celery_task_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    stage_logs: list[PipelineStageLogResponse] = []
    report_id: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_serializer("started_at", "completed_at")
    @classmethod
    def _serialize_dt_utc(cls, v: datetime | None) -> str | None:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class PipelineRunListResponse(BaseModel):
    runs: list[PipelineRunResponse]
    total: int


class NewDocCountResponse(BaseModel):
    """Resposta de ``GET /pipeline/new-doc-count`` — docs nunca processados."""

    new_count: int


class RunActionResponse(BaseModel):
    """Resposta genérica de ações no run (cancel/resume)."""

    detail: str
    run_id: str
