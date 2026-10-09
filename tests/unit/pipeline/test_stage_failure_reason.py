"""A40.l18 · ADR-357 §2 — `reason_class` é descritivo, derivado do objeto, e o mapa é total."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.llm.error_classification import LLMError, LLMErrorType, LLMValidationError
from pipeline.stage_failure_reason import (
    _CAPTURABLE,
    _REASON_BY_LLM_ERROR,
    FAILURE_CLASS_KEY,
    StageFailureReason,
    failure_class_detail,
    reason_from_exception,
    reason_from_stage_detail,
)


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


def test_abort_de_schema_e_output_invalido_nao_bug_nosso():
    """O flip `warn→strict` (ADR-284/409) aborta o write com `jsonschema.ValidationError` NUA — sem `error_type`, cairia em `internal_error` e o card acusaria bug nosso por payload rejeitado pelo contrato."""
    import jsonschema

    exc = jsonschema.ValidationError("payload de E3/x viola e3_reconciled.schema.json")
    assert not hasattr(exc, "error_type")
    assert reason_from_exception(exc) is StageFailureReason.output_invalid


# --- ADR-446: a classe atravessa o executor em `detail["failure_class"]` --------------


def _imagem_de_reason_from_exception() -> set[StageFailureReason]:
    import jsonschema

    from pipeline.llm.call_hooks import LLMBudgetExceededError

    excecoes = [LLMError("x", error_type) for error_type in LLMErrorType] + [
        LLMBudgetExceededError("ws-1", Decimal("11.00"), Decimal("10.00")),
        jsonschema.ValidationError("x"),
        RuntimeError("x"),
    ]
    return {reason_from_exception(exc) for exc in excecoes}


def test_o_que_a_captura_afirma_e_a_imagem_do_classificador():
    """O decoder aceita exatamente o que `reason_from_exception` produz — nem mais, nem menos."""
    assert _CAPTURABLE == _imagem_de_reason_from_exception()
    assert StageFailureReason.enforcement not in _CAPTURABLE
    assert StageFailureReason.missing_input not in _CAPTURABLE


def test_builder_grava_so_o_membro_do_enum():
    assert failure_class_detail(StageFailureReason.timeout) == {FAILURE_CLASS_KEY: "timeout"}


@pytest.mark.parametrize(
    "fora_do_contrato",
    ["timeout", StageFailureReason.enforcement, StageFailureReason.missing_input, None],
)
def test_builder_recusa_o_que_nao_e_captura(fora_do_contrato):
    """String solta ou juízo com derivação própria não entra pela chave da captura."""
    with pytest.raises(ValueError, match="capturável"):
        failure_class_detail(fora_do_contrato)


@pytest.mark.parametrize("membro", sorted(_CAPTURABLE, key=lambda m: m.value))
def test_decoder_devolve_a_classe_capturada(membro: StageFailureReason):
    assert reason_from_stage_detail(failure_class_detail(membro)) is membro


@pytest.mark.parametrize("valor", ["enforcement", "missing_input", "coisa_nova", 3, ["timeout"]])
def test_decoder_nao_aceita_valor_que_a_captura_nao_produz(valor):
    """Valor presente e inválido é `unknown` — não cai para o `reason` declarado."""
    detail = {FAILURE_CLASS_KEY: valor, "reason": "e5_not_found"}
    assert reason_from_stage_detail(detail) is StageFailureReason.unknown


def test_precedencia_retencao_captura_declarado():
    """Ordem fixa: o juízo de política vence a captura, que vence o motivo declarado."""
    tudo = {
        "retention_reason": "dado_insuficiente",
        FAILURE_CLASS_KEY: "budget_exhausted",
        "reason": "e5_not_found",
    }
    assert reason_from_stage_detail(tudo) is StageFailureReason.enforcement
    sem_retencao = {k: v for k, v in tudo.items() if k != "retention_reason"}
    assert reason_from_stage_detail(sem_retencao) is StageFailureReason.budget_exhausted
    so_declarado = {"reason": "e5_not_found", FAILURE_CLASS_KEY: None}
    assert reason_from_stage_detail(so_declarado) is StageFailureReason.missing_input


def test_nao_caminha_a_cadeia_da_excecao():
    """Bug levantado dentro de `except LLMError` é bug nosso, não falha do provider."""
    try:
        try:
            raise LLMError("overloaded", LLMErrorType.provider_error)
        except LLMError:
            raise KeyError("campo")  # noqa: B904 — o contexto implícito é o objeto do teste
    except KeyError as exc:
        assert exc.__context__ is not None
        assert reason_from_exception(exc) is StageFailureReason.internal_error
