"""A40.l18 · ADR-357 §2 — `reason_class` é descritivo, derivado do objeto, e o mapa é total."""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.services.pipeline.stage_failure_reason import (
    _REASON_BY_LLM_ERROR,
    StageFailureReason,
    reason_from_exception,
    reason_from_stage_detail,
)
from pipeline.llm.error_classification import LLMError, LLMErrorType, LLMValidationError


def test_mapa_e_funcao_total_sobre_llm_error_type():
    """Membro sem alvo cai em `unknown` e o card mente por omissão."""
    assert set(_REASON_BY_LLM_ERROR) == set(
        LLMErrorType
    ), "todo membro de LLMErrorType precisa de alvo em StageFailureReason"


@pytest.mark.parametrize("error_type", list(LLMErrorType))
def test_toda_exceção_classificada_tem_classe(error_type: LLMErrorType):
    reason = reason_from_exception(LLMError("boom", error_type))
    assert isinstance(reason, StageFailureReason)


def test_validation_e_output_invalido_nao_bug_nosso():
    """`LLMValidationError` é output REJEITADO pelo schema, não defeito de código."""
    # É o modo de falha mais frequente do parecer (reask storm, ADR-292/294).
    # Classificá-lo como `internal_error` diria "bug" ao dono no card.
    exc = LLMValidationError("schema falhou", validation_errors=["campo x"])
    assert reason_from_exception(exc) is StageFailureReason.output_invalid


def test_budget_e_classificado_por_isinstance():
    """`LLMBudgetExceededError` NÃO tem `error_type` — classificador por atributo o perderia."""
    # `budget_exhausted` é justamente o membro cuja copy o cliente não pode
    # confundir com falha técnica transitória.
    from pipeline.llm.call_hooks import LLMBudgetExceededError

    exc = LLMBudgetExceededError("ws-1", Decimal("11.00"), Decimal("10.00"))
    assert not hasattr(exc, "error_type")
    assert reason_from_exception(exc) is StageFailureReason.budget_exhausted


def test_excecao_generica_e_internal_error():
    assert reason_from_exception(RuntimeError("bug")) is StageFailureReason.internal_error


def test_retention_reason_projeta_enforcement():
    """Projeção de `ParecerRetentionReason`, não canal concorrente (ADR-366)."""
    # Derivar em vez de duplicar é o que impede os dois de discordarem — o mesmo
    # argumento com que a §2 rejeitou `{"degraded": True}`.
    detail = {"retention_reason": "dado_insuficiente", "reason": "irrelevante"}
    assert reason_from_stage_detail(detail) is StageFailureReason.enforcement


@pytest.mark.parametrize(
    "declared,expected",
    [
        ("e5_not_found", StageFailureReason.missing_input),
        ("missing_narrativas", StageFailureReason.missing_input),
        ("validation_failed", StageFailureReason.output_invalid),
        ("unknown_mode", StageFailureReason.internal_error),
        ("coisa_nova_nao_mapeada", StageFailureReason.unknown),
    ],
)
def test_motivo_declarado_pelo_stage(declared: str, expected: StageFailureReason):
    assert reason_from_stage_detail({"reason": declared}) is expected


def test_lacuna_de_upstream_nao_e_bug_nosso():
    """`missing_input` existe para não classificar dependência ausente como defeito."""
    assert reason_from_stage_detail({"reason": "e5_not_found"}) is not (
        StageFailureReason.internal_error
    )


def test_detail_ausente_e_unknown():
    assert reason_from_stage_detail(None) is StageFailureReason.unknown
    assert reason_from_stage_detail({}) is StageFailureReason.unknown
