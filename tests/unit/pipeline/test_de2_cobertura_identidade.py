"""DE-2 braço 2 — cobertura de identidade de instituição por membro ([[ADR-405]]).

Medido no §r7: as instituições distintas do titular caíram de 18 para 16 com as
posições constantes. A causa não é a contagem — é posição com valor cuja
identidade de instituição não chegou. Esse item classifica num balde NOMEADO,
então `nao_classificado_pct` é cego a ele: os dois braços são disjuntos.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.classificacao_review_reasons import (
    GATE_ENV,
    ITEM_MIN_PCT,
    review_reasons_da_classificacao,
)
from pipeline.domain.services.instituicoes_por_membro_analyzer import (
    InstituicoesPorMembroAnalyzer,
)
from pipeline.domain.services.investimentos_classes_analyzer import InvestimentosClassesAnalyzer

CODE = "domain.instituicao_ausente"


def _inv(valor: Decimal, inv_id: str, instituicao: str | None) -> dict:
    entry = {
        "descricao": "cdb prefixado sintetico",
        "valor_31_12_ano_base": float(valor),
        "investment_id": inv_id,
    }
    if instituicao is not None:
        entry["instituicao"] = instituicao
    return entry


def _bens(*investimentos: dict) -> dict:
    return {"investimentos": list(investimentos)}


def _payload(*investimentos: dict) -> dict:
    """Payload `investimentos` do E5 como `_e5_extract_legacy_dicts` o monta."""
    bens = _bens(*investimentos)
    payload = InvestimentosClassesAnalyzer().analyze([bens]).to_legacy_dict()
    payload.update(InstituicoesPorMembroAnalyzer().analyze([("titular", bens)]).to_legacy_dict())
    return payload


def _reasons(payload: dict) -> list[dict]:
    return review_reasons_da_classificacao(
        payload, stage="analyze_finances", artifact_key="analise_financeira"
    )


@pytest.fixture()
def gate_ligado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GATE_ENV, raising=False)


# =============================================================================
# O analyzer publica o denominador que faltava
# =============================================================================


def test_publica_n_posicoes_ao_lado_das_instituicoes() -> None:
    """Sem `n_posicoes` a queda 18→16 é incomparável: não dá para saber se
    caiu porque o corpus encolheu ou porque a identidade se perdeu."""
    result = InstituicoesPorMembroAnalyzer().analyze(
        [("titular", _bens(_inv(Decimal("10"), "a", "alfa"), _inv(Decimal("20"), "b", "beta")))]
    )
    linha = result.to_legacy_dict()["instituicoes_por_membro"][0]
    assert linha["n_posicoes"] == 2
    assert sorted(linha["instituicoes"]) == ["Alfa", "Beta"]
    assert linha["posicoes_sem_identidade"] == []


def test_posicao_sem_identidade_e_listada_com_locator_e_valor() -> None:
    result = InstituicoesPorMembroAnalyzer().analyze(
        [("titular", _bens(_inv(Decimal("10"), "a", "alfa"), _inv(Decimal("20"), "b", None)))]
    )
    linha = result.to_legacy_dict()["instituicoes_por_membro"][0]
    assert linha["n_posicoes"] == 2 and linha["instituicoes"] == ["Alfa"]
    assert linha["posicoes_sem_identidade"] == [{"locator": "b", "valor": 20.0}]


def test_posicao_sem_valor_nao_entra_na_lista() -> None:
    """Posição zerada não é lacuna de identidade — é posição encerrada."""
    result = InstituicoesPorMembroAnalyzer().analyze(
        [("titular", _bens(_inv(Decimal("10"), "a", "alfa"), _inv(Decimal("0"), "b", None)))]
    )
    linha = result.to_legacy_dict()["instituicoes_por_membro"][0]
    assert linha["n_posicoes"] == 2 and linha["posicoes_sem_identidade"] == []


# =============================================================================
# O gate: material sem identidade retém; imaterial não
# =============================================================================


def test_posicao_material_sem_identidade_vira_razao(gate_ligado: None) -> None:
    payload = _payload(
        _inv(Decimal("97000"), "id-ok", "alfa"), _inv(Decimal("3000"), "id-orfa", None)
    )
    reasons = [r for r in _reasons(payload) if r["code"] == CODE]
    assert len(reasons) == 1
    assert "id-orfa" in reasons[0]["offending_value"]
    assert "3.00%" in reasons[0]["offending_value"]


def test_posicao_imaterial_sem_identidade_nao_vira_razao(gate_ligado: None) -> None:
    payload = _payload(
        _inv(Decimal("99900"), "id-ok", "alfa"), _inv(Decimal("100"), "id-orfa", None)
    )
    assert 100.0 / 100_000.0 * 100 < ITEM_MIN_PCT
    assert [r for r in _reasons(payload) if r["code"] == CODE] == []


def test_orfa_classificada_e_invisivel_ao_braco_da_classe(gate_ligado: None) -> None:
    """O disjunto medido no r7: o item some das instituições e continua num
    balde nomeado, então `nao_classificado_pct` fica em zero."""
    payload = _payload(
        _inv(Decimal("97000"), "id-ok", "alfa"), _inv(Decimal("3000"), "id-orfa", None)
    )
    assert payload["nao_classificado_pct"] == 0.0
    assert payload["nao_classificado_itens"] == []
    assert [r["code"] for r in _reasons(payload)] == [CODE]


def test_kill_switch_desliga_o_braco_de_identidade(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GATE_ENV, "0")
    payload = _payload(
        _inv(Decimal("97000"), "id-ok", "alfa"), _inv(Decimal("3000"), "id-orfa", None)
    )
    assert _reasons(payload) == []


def test_razao_nao_carrega_nome_de_membro_nem_brl(gate_ligado: None) -> None:
    payload = _payload(
        _inv(Decimal("97000"), "id-ok", "alfa"), _inv(Decimal("3000"), "id-orfa", None)
    )
    for reason in _reasons(payload):
        blob = f"{reason['offending_value']} {reason['message']} {reason['expected']}"
        assert "titular" not in blob.lower()
        assert "3000" not in blob and "3.000" not in blob
