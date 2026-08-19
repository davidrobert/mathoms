"""Boundary de `review_reasons` (ADR-404): normaliza o payload do produtor ao
contrato de coluna ANTES do INSERT. Degrada o campo, depois a row, nunca o run.

As três munições medidas contra `origin/main` (run `140ac8d7`, §r7) são de
**tipo**, não de largura: `dict` em coluna `Text` (o driver recusa o bind),
entrada `str` no lugar de objeto (`AttributeError`) e `occurrence_count`
não-numérico (`ValueError`). Por isso o contrato é um DTO e não só um `_fit`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from backend.app.core.logging import get_logger
from backend.app.models.review_reason import ReviewReason
from pipeline.domain.review_reason import redact_pii

logger = get_logger("pipeline.diagnostics")


def _column_limit(name: str) -> int:
    """Largura declarada da coluna — derivada do model, não transcrita.
    Número mágico aqui dessincroniza no próximo `alter column` (RV6-11)."""
    length = getattr(ReviewReason.__table__.c[name].type, "length", None)
    if length is None:  # pragma: no cover — só se a coluna virar Text/Integer
        raise ValueError(f"coluna sem largura declarada: review_reasons.{name}")
    return int(length)


# Larguras derivadas do model. `stage` NÃO entra: o valor é do orquestrador
# (nome de `STAGE_REGISTRY`), nunca do produtor — truncá-lo esconderia bug nosso.
CLIPPED_COLUMNS = ("code", "artifact_key")
_DOCUMENT_ID_MAX = _column_limit("document_id")

# `offending_value`/`expected`/`message` são `Text` (sem largura declarada). O
# teto sanitário existe porque row de diagnóstico não é dump: um produtor que
# serialize o extrato inteiro na mensagem inflaria a tabela.
_TEXT_MAX = 4096
_TRUNCATION_MARK = "…[truncado]"


def clip(value: str, limit: int) -> str:
    """Trunca preservando a CABEÇA: em `artifact_key` o prefixo é o
    `content_hash[:12]` (ADR-084) que resolve a identidade do documento."""
    if len(value) <= limit:
        return value
    return value[: limit - len(_TRUNCATION_MARK)] + _TRUNCATION_MARK


def _as_text(value: Any) -> str:
    """Coage qualquer valor a texto redigido — `dict`/`list` em coluna `Text`
    levanta no bind do driver (`type 'dict' is not supported`) e mataria o run."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return redact_pii(text)


class ReviewReasonRow(BaseModel):
    """Contrato de uma row de `review_reasons` na fronteira produtor → DB."""

    model_config = ConfigDict(frozen=True)

    code: str
    stage: str
    artifact_key: str = ""
    document_id: str | None = None
    offending_value: str = ""
    expected: str = ""
    message: str = ""
    occurrence_count: int = 1

    @field_validator("code", "stage", "artifact_key", mode="before")
    @classmethod
    def _identity_text(cls, value: Any) -> str:
        return "" if value is None else str(value)

    @field_validator("offending_value", "expected", "message", mode="before")
    @classmethod
    def _free_text(cls, value: Any) -> str:
        return clip(_as_text(value), _TEXT_MAX)

    @field_validator("document_id", mode="before")
    @classmethod
    def _document_id(cls, value: Any) -> str | None:
        """Id que não cabe na coluna também não resolveria a FK (ADR-371)."""
        if value is None or not isinstance(value, str) or len(value) > _DOCUMENT_ID_MAX:
            return None
        return value or None

    @field_validator("occurrence_count", mode="before")
    @classmethod
    def _occurrence(cls, value: Any) -> int:
        try:
            count = int(value)
        except (TypeError, ValueError):
            return 1
        return count if count >= 1 else 1


def _fit_column(field: str, value: str, *, stage_name: str) -> str:
    limit = _column_limit(field)
    if len(value) <= limit:
        return value
    logger.warning(
        "review_reason acima da largura da coluna — truncado",
        extra={
            "event": "mathoms.pipeline.review_reason_field_clipped",
            "stage": stage_name,
            "field": field,
            "length": len(value),
            "declared_limit": limit,
        },
    )
    return clip(value, limit)


def _fit_columns(row: ReviewReasonRow, *, stage_name: str) -> dict[str, Any]:
    """Row ajustada às larguras declaradas no model. O SQLite ignora
    `VARCHAR(n)`; o Postgres levanta `22001` — o ajuste é aqui, não no dialeto."""
    data = row.model_dump()
    for field in CLIPPED_COLUMNS:
        data[field] = _fit_column(field, data[field], stage_name=stage_name)
    return data


def _reject(reason: str, event: str, stage_name: str, **fields: Any) -> None:
    logger.warning(reason, extra={"event": event, "stage": stage_name, **fields})


def _build_row(payload: dict, *, stage_name: str) -> ReviewReasonRow | None:
    """DTO a partir do payload, ou None se nem coagido ele fecha o contrato."""
    try:
        # `stage` é do ORQUESTRADOR: o produtor não escolhe em que stage a razão
        # dele foi emitida, e deixá-lo escolher reabriria a munição de largura.
        return ReviewReasonRow(**{**payload, "stage": stage_name})
    except Exception as exc:  # noqa: BLE001 — boundary não propaga; ver ADR-404
        # Sem `exc_info`: `ValidationError` ecoa o input, que pode carregar PII.
        _reject(
            "review_reason descartado — payload inválido",
            "mathoms.pipeline.review_reason_invalid_payload",
            stage_name,
            exc_type=type(exc).__name__,
            fields=sorted(str(k) for k in payload),
        )
        return None


def _normalize_one(payload: Any, *, stage_name: str) -> dict[str, Any] | None:
    """Payload do produtor → dict que cabe nas colunas; None = insalvável."""
    if not isinstance(payload, dict):
        _reject(
            "review_reason descartado — entrada não é objeto",
            "mathoms.pipeline.review_reason_not_an_object",
            stage_name,
            got_type=type(payload).__name__,
        )
        return None
    row = _build_row(payload, stage_name=stage_name)
    if row is not None and not row.code:
        _reject(
            "review_reason descartado — sem `code`",
            "mathoms.pipeline.review_reason_missing_code",
            stage_name,
        )
        return None
    return None if row is None else _fit_columns(row, stage_name=stage_name)


def sanitize_review_reasons(raw: Any, *, stage_name: str) -> list[dict[str, Any]]:
    """Lista de payloads do produtor → lista normalizada. Nunca levanta."""
    if not raw:
        return []
    if not isinstance(raw, list):
        _reject(
            "validation.review_reasons ignorado — esperado list",
            "mathoms.pipeline.review_reasons_not_a_list",
            stage_name,
            got_type=type(raw).__name__,
        )
        return []
    normalized = [_normalize_one(p, stage_name=stage_name) for p in raw]
    return [row for row in normalized if row is not None]


__all__ = ["CLIPPED_COLUMNS", "ReviewReasonRow", "clip", "sanitize_review_reasons"]
