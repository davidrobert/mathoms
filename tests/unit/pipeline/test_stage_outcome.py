"""ADR-357 §1/§2 · A40.l18 — disposição de stage a partir de (retorno, criticality)."""

from __future__ import annotations

import inspect

import pytest

from pipeline.stage_outcome import (
    DEGRADABLE,
    REQUIRED,
    StageOutcome,
    commits_artifacts_on_degrade,
    resolve_stage_outcome,
    stage_criticality,
)
from pipeline.stage_spec import FULL_ORDER, STAGE_REGISTRY

_TAIL = ("generate_narratives", "validate_cross", "review_finances_holistic")


def test_cauda_e_exatamente_os_tres_degradaveis() -> None:
    cutoff = FULL_ORDER.index("analyze_finances")
    assert tuple(FULL_ORDER[cutoff + 1 :]) == _TAIL
    assert {s for s in FULL_ORDER if stage_criticality(s) == DEGRADABLE} == set(_TAIL)


@pytest.mark.parametrize("stage", FULL_ORDER[: FULL_ORDER.index("analyze_finances") + 1])
def test_cabeca_e_required(stage: str) -> None:
    assert stage_criticality(stage) == REQUIRED


def test_nao_entrega_em_required_falha_o_run() -> None:
    assert resolve_stage_outcome("analyze_finances", delivered=False) is StageOutcome.failed


@pytest.mark.parametrize("stage", _TAIL)
def test_nao_entrega_em_degradavel_degrada(stage: str) -> None:
    assert resolve_stage_outcome(stage, delivered=False) is StageOutcome.degraded


@pytest.mark.parametrize("stage", ("analyze_finances", *_TAIL))
def test_entrega_completa_independente_da_criticidade(stage: str) -> None:
    assert resolve_stage_outcome(stage, delivered=True) is StageOutcome.completed


def test_skip_declarado_e_entrega() -> None:
    outcome = resolve_stage_outcome("extract_members", delivered=True, declared_skip=True)
    assert outcome is StageOutcome.skipped
    assert outcome.delivered


@pytest.mark.parametrize(
    "legacy,descritivo",
    [
        ("E6-parecer", "review_finances_holistic"),
        ("E5.N", "generate_narratives"),
        ("E7-crossval", "validate_cross"),
    ],
)
def test_nome_legado_resolve_para_a_mesma_criticidade(legacy: str, descritivo: str) -> None:
    # O loop recebe `stage_name` cru e nomes legados ainda circulam pelo sistema.
    # Sem `resolve_stage_name`, o lookup devolve None, cai no default `required` e
    # a degradação simplesmente não acontece — fail-closed, portanto invisível
    # num teste feliz que só usa nomes descritivos.
    assert stage_criticality(legacy) == stage_criticality(descritivo) == DEGRADABLE
    assert resolve_stage_outcome(legacy, delivered=False) is StageOutcome.degraded


def test_stage_desconhecido_e_fail_closed() -> None:
    # A rota `"No runner found for X"` do orquestrador constrói StageResult para
    # um stage fora do registry: nunca deve ganhar licença de degradar.
    assert stage_criticality("stage_que_nao_existe") == REQUIRED
    assert resolve_stage_outcome("stage_que_nao_existe", delivered=False) is StageOutcome.failed
    assert commits_artifacts_on_degrade("stage_que_nao_existe") is False


def test_erro_nao_entra_na_assinatura_da_disposicao() -> None:
    # ADR-357 §2 proíbe `result.error` como discriminador: `error is None`
    # significa "nenhuma exceção cruzou a fronteira do runner", não "o stage
    # declarou". Travar a ASSINATURA é o que impede a reintrodução — um teste de
    # comportamento passaria mesmo com o parâmetro presente e ignorado.
    params = set(inspect.signature(resolve_stage_outcome).parameters)
    assert params == {"stage", "delivered", "declared_skip"}


def test_politica_de_commit_e_declarada_por_stage() -> None:
    # `generate_narratives` escreve na chave do E5, não na própria: commitar em
    # degradação alcança o deliverable. `StageSpec.writes` NÃO serve de
    # discriminador aqui — ele declara chave própria para os dois.
    assert STAGE_REGISTRY["generate_narratives"].writes == ("generate_narratives",)
    assert commits_artifacts_on_degrade("generate_narratives") is False
    assert commits_artifacts_on_degrade("review_finances_holistic") is True
    assert commits_artifacts_on_degrade("validate_cross") is True
