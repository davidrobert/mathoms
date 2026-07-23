"""ReviewReason — razão estruturada de needs_review (ADR-272), Python puro."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

# CPF formatado (123.456.789-01) e cru (11 dígitos isolados).
_CPF_FORMATTED_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CPF_RAW_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
# Valor monetário BRL: 1.234,56 / 1234,56 / R$ 1.234,56 / 1234.56 (ponto decimal).
_MONEY_RE = re.compile(
    r"(?:R\$\s*)?\d{1,3}(?:\.\d{3})+(?:,\d{2})?|(?:R\$\s*)?\d+,\d{2}|(?:R\$\s*)\d+(?:\.\d{2})?"
)

_CPF_MASK = "***.***.***-**"
_MONEY_MASK = "R$ ***"


class ReviewReasonCode(str, enum.Enum):
    """Vocabulário namespaced por origem (ADR-272); code novo = membro aqui + JSON Schema."""

    extract_low_confidence = "extract.low_confidence"
    extract_llm_fallback = "extract.llm_fallback"
    extract_missing_required_field = "extract.missing_required_field"
    extract_incomplete_conservation = "extract.incomplete_conservation"
    extract_empty_result = "extract.empty_result"
    extract_investment_sum_mismatch = "extract.investment_sum_mismatch"
    dedup_possible_duplicate = "dedup.possible_duplicate"
    dedup_sentinel_period = "dedup.sentinel_period"
    domain_validation_conflict = "domain.validation_conflict"
    domain_balance_gap = "domain.balance_gap"
    domain_temporal_gap = "domain.temporal_gap"
    domain_anachronic_transaction = "domain.anachronic_transaction"
    domain_baseline_divergence = "domain.baseline_divergence"


# Codes que pausam o run em needs_review (gate A28.l8). Os demais são
# informativos: aparecem na review/fila mas não bloqueiam o pipeline —
# saldo gap em série histórica é o caso comum e não pode virar pausa
# recorrente (ADR-308 §4).
BLOCKING_CODES: frozenset[ReviewReasonCode] = frozenset(
    {
        ReviewReasonCode.extract_missing_required_field,
        ReviewReasonCode.dedup_sentinel_period,
    }
)


def redact_pii(text: str) -> str:
    """Mascara CPF (formatado e cru) e valor monetário BRL em texto livre; idempotente."""
    if not text:
        return text
    out = _CPF_FORMATTED_RE.sub(_CPF_MASK, text)
    out = _MONEY_RE.sub(_MONEY_MASK, out)
    out = _CPF_RAW_RE.sub(_CPF_MASK, out)
    return out


def _redact_value(value: Any) -> Any:
    """Redige um valor de contexto recursivamente (str, dict ou list de str)."""
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return redact_context(value)
    if isinstance(value, list):
        return [redact_pii(i) if isinstance(i, str) else i for i in value]
    return value


def redact_context(context: dict[str, Any]) -> dict[str, Any]:
    """Redige recursivamente um dict de contexto (pode conter trecho de extrato)."""
    return {k: _redact_value(v) for k, v in context.items()}


@dataclass(frozen=True)
class ReviewReason:
    """Razão estruturada de needs_review (ADR-272), redigida no construtor."""

    code: ReviewReasonCode
    stage: str
    artifact_key: str
    document_id: str | None
    offending_value: str
    expected: str
    message: str
    occurrence_count: int = 1

    def __post_init__(self) -> None:
        # Defesa em profundidade: message só carrega IDs/contadores/enums por
        # contrato — redigir é no-op quando respeitado, rede de segurança quando não.
        object.__setattr__(self, "offending_value", redact_pii(self.offending_value))
        object.__setattr__(self, "message", redact_pii(self.message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "stage": self.stage,
            "artifact_key": self.artifact_key,
            "document_id": self.document_id,
            "offending_value": self.offending_value,
            "expected": self.expected,
            "message": self.message,
            "occurrence_count": self.occurrence_count,
        }


@runtime_checkable
class ToReviewReason(Protocol):
    """Produtores (ValidationIssue, warnings de domínio) projetam para ReviewReason (ADR-272)."""

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None: ...


__all__ = [
    "BLOCKING_CODES",
    "ReviewReason",
    "ReviewReasonCode",
    "ToReviewReason",
    "redact_pii",
    "redact_context",
]
