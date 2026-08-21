"""DE-2 / RV7-04 — gate por ITEM da catch-all ([[ADR-405]]).

O eixo é a cegueira POR CONSTRUÇÃO que o §r7 denuncia: migração entre baldes
preserva Σ, então todo check de conservação passa. Os testes de replay abaixo
afirmam Σ **inalterado** e o gate disparando no mesmo cenário — é esse verde
que eles existem para matar.

Valores sintéticos. Carteira financeira = 100.000; imóvel = 900.000 (a razão
9:1 existe para que trocar o denominador de `total_financeiro` por `total`
inverta o veredito — sem ela a base do percentual seria indistinguível).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.asset_classifier import AssetAuthority, classify_asset_outcome
from pipeline.domain.services.classificacao_review_reasons import (
    AGREGADO_MIN_PCT,
    GATE_ENV,
    ITEM_MIN_PCT,
    MAX_RAZOES_POR_CODE,
    review_reasons_da_classificacao,
)
from pipeline.domain.services.investimentos_classes_analyzer import InvestimentosClassesAnalyzer

DESC_KEYWORD = "tesouro selic sintetico"
DESC_MIGRADO = "produto estruturado indice sintetico"
DESC_IMATERIAL = "residual nao mapeado"


def _inv(desc: str, valor: Decimal, inv_id: str, *, instituicao: str = "inst-sintetica") -> dict:
    return {
        "descricao": desc,
        "valor_31_12_ano_base": float(valor),
        "investment_id": inv_id,
        "instituicao": instituicao,
    }


def _carteira(desc_p3: str) -> list[dict]:
    """Carteira de 100.000 + imóvel de 900.000. `desc_p3` decide se P3 migra."""
    return [
        {
            "investimentos": [
                _inv("cdb prefixado sintetico", Decimal("80000"), "id-p1"),
                _inv("fundo de investimento sintetico", Decimal("18490"), "id-p2"),
                _inv(desc_p3, Decimal("1300"), "id-p3"),
                _inv(DESC_IMATERIAL, Decimal("200"), "id-p4"),
                _inv("", Decimal("10"), "id-p5"),
            ],
            "imoveis": [{"valor_31_12_ano_base": 900_000.0, "property_id": "prop-inv"}],
        }
    ]


def _reasons(payload: dict) -> list[dict]:
    return review_reasons_da_classificacao(
        payload, stage="analyze_finances", artifact_key="analise_financeira"
    )


def _codes(reasons: list[dict]) -> list[str]:
    return sorted(r["code"] for r in reasons)


@pytest.fixture()
def gate_ligado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GATE_ENV, raising=False)


# =============================================================================
# A fixture exercita o mecanismo que nomeia (senão o teste envelhece calado)
# =============================================================================


def test_fixture_produz_as_autoridades_que_o_gate_le() -> None:
    assert classify_asset_outcome("", DESC_KEYWORD).autoridade is AssetAuthority.KEYWORD
    assert classify_asset_outcome("", DESC_MIGRADO).autoridade is AssetAuthority.SEM_MATCH
    assert classify_asset_outcome("", DESC_IMATERIAL).autoridade is AssetAuthority.SEM_MATCH
    assert classify_asset_outcome("", "").autoridade is AssetAuthority.SEM_HAYSTACK


# =============================================================================
# Replay do §r7: migração preserva Σ e os CV ficam cegos — o gate não
# =============================================================================


def test_migracao_para_catch_all_preserva_soma_e_dispara_o_gate(gate_ligado: None) -> None:
    analyzer = InvestimentosClassesAnalyzer()
    antes = analyzer.analyze(_carteira(DESC_KEYWORD)).to_legacy_dict()
    depois = analyzer.analyze(_carteira(DESC_MIGRADO)).to_legacy_dict()

    # A cegueira por construção: os três agregados que os CV comparam não mudam.
    assert antes["total"] == depois["total"]
    assert antes["total_financeiro"] == depois["total_financeiro"]
    assert antes["total_imoveis_investimento"] == depois["total_imoveis_investimento"]

    # E o balde nomeado perde exatamente o que a catch-all ganha.
    def _classe(payload: dict, nome: str) -> float:
        return next((c["valor"] for c in payload["tabela_classes"] if c["categoria"] == nome), 0.0)

    assert _classe(antes, "Renda Fixa") - _classe(depois, "Renda Fixa") == 1_300.0
    assert _classe(depois, "Outros") - _classe(antes, "Outros") == 1_300.0

    assert "domain.ativo_nao_classificado" in _codes(_reasons(depois))


def test_item_migrado_e_nomeado_pelo_locator(gate_ligado: None) -> None:
    reasons = _reasons(
        InvestimentosClassesAnalyzer().analyze(_carteira(DESC_MIGRADO)).to_legacy_dict()
    )
    por_item = [
        r
        for r in reasons
        if r["code"] == "domain.ativo_nao_classificado" and "id-p3" in r["offending_value"]
    ]
    assert len(por_item) == 1
    assert "1.30%" in por_item[0]["offending_value"]


def test_sensor_de_nivel_legado_nao_ve_o_caso(gate_ligado: None) -> None:
    """O 5% de `OUTROS_EXCESSIVO_THRESHOLD_PCT` é o verde que o DE-2 acusa."""
    depois = InvestimentosClassesAnalyzer().analyze(_carteira(DESC_MIGRADO))
    outros_pct = next(c.pct for c in depois.tabela_classes if c.categoria == "Outros")
    assert outros_pct < 5.0
    assert depois.warnings == ()
    assert _reasons(depois.to_legacy_dict()) != []


# =============================================================================
# Limiares: por item, por agregado, e a base do percentual
# =============================================================================


def test_item_imaterial_nao_vira_razao_por_item(gate_ligado: None) -> None:
    payload = InvestimentosClassesAnalyzer().analyze(_carteira(DESC_MIGRADO)).to_legacy_dict()
    nomeados = [r["offending_value"] for r in _reasons(payload)]
    assert not any("id-p4" in v for v in nomeados)


# 1.300 é 1,30% da carteira financeira e 0,13% do total investido. Com o
# denominador errado (`total`, que inclui imóvel) o item cai abaixo de
# `ITEM_MIN_PCT` e o gate volta a ficar cego — é a mutação M2.
def test_limiar_do_item_e_lido_da_carteira_financeira(gate_ligado: None) -> None:
    """O peso do item é medido sobre a carteira financeira, não sobre o total."""
    payload = InvestimentosClassesAnalyzer().analyze(_carteira(DESC_MIGRADO)).to_legacy_dict()
    pct_financeiro = 1_300.0 / payload["total_financeiro"] * 100
    pct_total = 1_300.0 / payload["total"] * 100
    assert pct_total < ITEM_MIN_PCT < pct_financeiro
    assert any("id-p3" in r["offending_value"] for r in _reasons(payload))


def test_agregado_dispara_sem_nenhum_item_material(gate_ligado: None) -> None:
    """Morte por mil cortes: 4 itens de 0,3% cada — nenhum material, Σ = 1,2%."""
    bens = [{"investimentos": [_inv(DESC_IMATERIAL, Decimal("300"), f"id-{i}") for i in range(4)]}]
    bens[0]["investimentos"].append(_inv("cdb prefixado sintetico", Decimal("98800"), "id-rf"))
    payload = InvestimentosClassesAnalyzer().analyze(bens).to_legacy_dict()
    assert payload["nao_classificado_pct"] > AGREGADO_MIN_PCT
    reasons = _reasons(payload)
    assert [r["code"] for r in reasons] == ["domain.ativo_nao_classificado"]
    assert "carteira" in reasons[0]["offending_value"]


def test_carteira_limpa_nao_emite_razao(gate_ligado: None) -> None:
    bens = [{"investimentos": [_inv("cdb prefixado sintetico", Decimal("100000"), "id-rf")]}]
    payload = InvestimentosClassesAnalyzer().analyze(bens).to_legacy_dict()
    assert payload["nao_classificado_pct"] == 0.0
    assert _reasons(payload) == []


# =============================================================================
# `sem_haystack` é violação de contrato do produtor — nunca escala por limiar
# =============================================================================


def test_sem_haystack_vira_razao_mesmo_sendo_irrisorio(gate_ligado: None) -> None:
    """P5 vale 0,01% da carteira. Sob qualquer limiar de materialidade ele
    sumiria — e é justamente o item que denuncia bug a montante (M3)."""
    payload = InvestimentosClassesAnalyzer().analyze(_carteira(DESC_KEYWORD)).to_legacy_dict()
    sem_haystack = [r for r in _reasons(payload) if r["code"] == "domain.ativo_sem_haystack"]
    assert len(sem_haystack) == 1
    assert "id-p5" in sem_haystack[0]["offending_value"]
    assert "0.01%" in sem_haystack[0]["offending_value"]


# =============================================================================
# Cap de cardinalidade ([[ADR-272]]) e kill-switch
# =============================================================================


def test_cap_preserva_a_contagem_total_em_occurrence_count(gate_ligado: None) -> None:
    n = MAX_RAZOES_POR_CODE + 3
    bens = [{"investimentos": [_inv(DESC_MIGRADO, Decimal("1000"), f"id-{i}") for i in range(n)]}]
    bens[0]["investimentos"].append(_inv("cdb prefixado sintetico", Decimal("90000"), "id-rf"))
    reasons = [
        r
        for r in _reasons(InvestimentosClassesAnalyzer().analyze(bens).to_legacy_dict())
        if r["code"] == "domain.ativo_nao_classificado" and "carteira" not in r["offending_value"]
    ]
    assert len(reasons) == MAX_RAZOES_POR_CODE
    assert sum(r["occurrence_count"] for r in reasons) == n


def test_kill_switch_desliga_o_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GATE_ENV, "0")
    payload = InvestimentosClassesAnalyzer().analyze(_carteira(DESC_MIGRADO)).to_legacy_dict()
    assert payload["nao_classificado_itens"] != []
    assert _reasons(payload) == []


def test_payload_legado_sem_o_campo_nao_quebra(gate_ligado: None) -> None:
    assert _reasons({"tabela_classes": [], "total": 0}) == []
    assert _reasons({}) == []


# =============================================================================
# PII: a razão nunca carrega descrição, instituição nem valor em BRL
# =============================================================================


# `redact_pii` mascara `\d+,\d{2}`: percentual escrito em pt-BR virava "R$ ***".
# O `__post_init__` redige `offending_value`, então formatar o peso com vírgula
# apagaria calado o único número acionável da razão.
def test_percentual_sobrevive_a_redacao_monetaria(gate_ligado: None) -> None:
    """O peso na carteira sobrevive à redação do construtor."""
    payload = InvestimentosClassesAnalyzer().analyze(_carteira(DESC_MIGRADO)).to_legacy_dict()
    for reason in _reasons(payload):
        assert "R$ ***" not in reason["offending_value"]
        assert "%" in reason["offending_value"]


def test_razao_nao_carrega_descricao_instituicao_nem_brl(gate_ligado: None) -> None:
    payload = InvestimentosClassesAnalyzer().analyze(_carteira(DESC_MIGRADO)).to_legacy_dict()
    for reason in _reasons(payload):
        blob = f"{reason['offending_value']} {reason['message']} {reason['expected']}"
        assert DESC_MIGRADO not in blob
        assert "inst-sintetica" not in blob
        assert "1300" not in blob and "1.300" not in blob
