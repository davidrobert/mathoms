"""Cobertura de investimentos por membro — A40.l69 item 3a ([[ADR-394]] §Emenda (b) D7).

O eixo do teste é a distinção que o r5/r6 perdeu: `zero_apurado` (fonte presente,
valor é zero) contra `nao_apurado` (não há fonte para o membro).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.investimentos_cobertura import (
    COBERTURA_ENV,
    CoberturaStatus,
    MembroObservado,
    classificar_cobertura,
    motivo_supressao_da_cobertura,
    motivo_supressao_por_cobertura,
    review_reasons_da_cobertura,
)
from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
)


def _obs(**kw) -> MembroObservado:
    base = {
        "membro": "conjuge",
        "valor_brl": Decimal("0"),
        "posicoes_atribuidas": False,
        "fallback_irpf": False,
        "tem_bens_irpf": False,
    }
    base.update(kw)
    return MembroObservado(**base)


# =============================================================================
# Os 3 estados
# =============================================================================


def test_posicao_atribuida_com_valor_e_apurado() -> None:
    c = classificar_cobertura(_obs(posicoes_atribuidas=True, valor_brl=Decimal("1000")))
    assert c.status is CoberturaStatus.apurado and c.fonte == "posicoes_atuais"


def test_posicao_atribuida_com_zero_e_zero_apurado() -> None:
    """A saída da ressalva: fonte respondeu, e a resposta foi zero."""
    c = classificar_cobertura(_obs(posicoes_atribuidas=True, valor_brl=Decimal("0")))
    assert c.status is CoberturaStatus.zero_apurado
    assert c.apurado, "zero medido não é pendência"


def test_fallback_irpf_e_apurado() -> None:
    c = classificar_cobertura(_obs(fallback_irpf=True, valor_brl=Decimal("188123.73")))
    assert c.status is CoberturaStatus.apurado and c.fonte == "irpf"


def test_sem_posicao_mas_com_bens_no_baseline_e_zero_apurado() -> None:
    """O IRPF do membro existe e não tem investimento — é medida, não ausência."""
    c = classificar_cobertura(_obs(tem_bens_irpf=True))
    assert c.status is CoberturaStatus.zero_apurado and c.fonte == "irpf"


def test_sem_fonte_nenhuma_e_nao_apurado() -> None:
    """O caso do r5/r6: nada respondeu, e hoje isso publicava 0,00."""
    c = classificar_cobertura(_obs())
    assert c.status is CoberturaStatus.nao_apurado
    assert c.fonte is None and not c.apurado
    assert c.motivo == "sem posicao atribuida e sem bens no baseline"


# =============================================================================
# Prescrição exige cobertura
# =============================================================================


def test_membro_nao_apurado_suprime_a_prescricao() -> None:
    coberturas = (classificar_cobertura(_obs()),)
    assert motivo_supressao_por_cobertura(coberturas) == "cobertura_incompleta: conjuge"


def test_zero_apurado_nao_suprime() -> None:
    """O modo de falha oposto: se tudo virar ressalva, o sinal some."""
    coberturas = (classificar_cobertura(_obs(tem_bens_irpf=True)),)
    assert motivo_supressao_por_cobertura(coberturas) is None


def test_motivo_lido_do_artefato() -> None:
    artefato = {
        "cobertura_investimentos": [
            {"membro": "titular", "status": "apurado", "fonte": "posicoes_atuais"},
            {"membro": "conjuge", "status": "nao_apurado", "fonte": None},
        ]
    }
    assert motivo_supressao_da_cobertura(artefato) == "cobertura_incompleta: conjuge"


def test_artefato_legado_sem_o_campo_nao_suprime() -> None:
    assert motivo_supressao_da_cobertura({"bruto": 1_000}) is None


# =============================================================================
# needs_review + kill-switch
# =============================================================================


def test_nao_apurado_projeta_review_reason() -> None:
    artefato = {"cobertura_investimentos": [{"membro": "conjuge", "status": "nao_apurado"}]}
    reasons = review_reasons_da_cobertura(artefato, stage="analyze_finances", artifact_key="a")

    assert len(reasons) == 1
    assert reasons[0]["code"] == "domain.membro_nao_apurado"
    assert reasons[0]["offending_value"] == "membro=conjuge"


def test_apurado_nao_projeta_razao() -> None:
    artefato = {"cobertura_investimentos": [{"membro": "conjuge", "status": "zero_apurado"}]}
    assert review_reasons_da_cobertura(artefato, stage="s", artifact_key="a") == []


def test_kill_switch_desliga_ressalva_e_supressao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(COBERTURA_ENV, "0")
    artefato = {"cobertura_investimentos": [{"membro": "conjuge", "status": "nao_apurado"}]}

    assert review_reasons_da_cobertura(artefato, stage="s", artifact_key="a") == []
    assert motivo_supressao_da_cobertura(artefato) is None


# =============================================================================
# Integração no PatrimonioCalculator
# =============================================================================


@pytest.fixture
def config() -> PatrimonioConfig:
    return PatrimonioConfig(
        members=MemberIdentity(
            titular_key="david",
            conjuge_key="mariana",
            titular_nome="David",
            conjuge_nome="Mariana",
        )
    )


def _inputs(totais: dict, *, conjuge_bens: dict | None = None) -> PatrimonioInputs:
    membros = {"david": {"total_bens": 0, "bens": {"investimentos": [{"valor": 1.0}]}}}
    membros["mariana"] = {"total_bens": 0, "bens": conjuge_bens} if conjuge_bens else {}
    return PatrimonioInputs(
        baseline={"members": membros},
        investimentos_atuais={
            "dados": [{"membro": k, "valor": v} for k, v in totais.items()],
            "total_por_membro": totais,
        },
        caixa_total_brl=0.0,
    )


def _por_membro(result: dict) -> dict:
    return {c["membro"]: c["status"] for c in result["cobertura_investimentos"]}


def test_conjuge_sem_posicao_e_sem_bens_sai_nao_apurado(config: PatrimonioConfig) -> None:
    """O defeito do r5/r6 fica nomeado em vez de publicar 0,00 calado."""
    result = PatrimonioCalculator(config).calculate(_inputs({"david": 943_189.25}))

    assert _por_membro(result) == {"titular": "apurado", "conjuge": "nao_apurado"}


def test_conjuge_com_posicao_zerada_sai_zero_apurado(config: PatrimonioConfig) -> None:
    result = PatrimonioCalculator(config).calculate(_inputs({"david": 943_189.25, "mariana": 0.0}))

    assert _por_membro(result)["conjuge"] == "zero_apurado"


def test_familia_de_um_titular_nao_ressalva_conjuge_inexistente() -> None:
    """Sem `conjuge_key` não há pessoa a cobrir — linha de ressalva seria sobre ninguém."""
    cfg = PatrimonioConfig(
        members=MemberIdentity(
            titular_key="joao", conjuge_key="", titular_nome="João", conjuge_nome=""
        )
    )
    result = PatrimonioCalculator(cfg).calculate(_inputs({"joao": 100.0}))

    assert [c["membro"] for c in result["cobertura_investimentos"]] == ["titular"]


# =============================================================================
# Wiring — as duas pontas que a mutação mostrou descobertas
# =============================================================================

_ARTEFATO_SEM_COBERTURA = {
    "bruto": 1_000_000,
    "liquido": 800_000,
    "cobertura_investimentos": [{"membro": "conjuge", "status": "nao_apurado", "fonte": None}],
}


def _derived_com_patrimonio(patrimonio: dict) -> dict:
    from pipeline.domain.services.e5_serialization import build_e5_output
    from tests.unit.pipeline.test_e5_serialization import _inputs

    out = build_e5_output(
        _inputs(
            patrimonio=patrimonio,
            goals={"if_meta": 5_000_000, "alocacao_alvo": {"rf_pos_pct": 40, "acoes_br_pct": 60}},
            investimentos_classes={"tabela_classes": [{"categoria": "Renda Fixa", "valor": 1000}]},
        )
    )
    return out["goals"]["alocacao_alvo"]["derived"]


def test_cobertura_incompleta_suprime_a_prescricao_no_payload_e5() -> None:
    """N7: sem esta asserção, `e5_serialization` podia ignorar a cobertura calado."""
    derived = _derived_com_patrimonio(_ARTEFATO_SEM_COBERTURA)

    assert derived["next_aporte_classe"] is None
    assert derived["desvio_max_pct"] is None
    assert derived["motivo_supressao"] == "cobertura_incompleta: conjuge"
    assert derived["comparaveis"], "descrição admite ressalva — a tabela publica"


def test_cobertura_completa_publica_a_prescricao() -> None:
    """Guard anti-vacuidade do teste acima."""
    patrimonio = {
        **_ARTEFATO_SEM_COBERTURA,
        "cobertura_investimentos": [{"membro": "conjuge", "status": "zero_apurado"}],
    }

    assert _derived_com_patrimonio(patrimonio)["motivo_supressao"] is None


def test_membro_nao_apurado_pausa_o_stage_em_needs_review() -> None:
    """N8: sem esta asserção, o bloco `validation` podia ignorar a cobertura calado."""
    from scripts.analyze_finances import _e5_build_result_dict

    legacy = {
        "score": {"valor": 7.0, "classificacao": "Bom"},
        "patrimonio": _ARTEFATO_SEM_COBERTURA,
        "goals": {},
    }
    result = _e5_build_result_dict(legacy, [])

    assert result["validation"]["valid"] is False
    assert result["validation"]["review_reasons"][0]["code"] == "domain.membro_nao_apurado"
    assert result["patrimonio_bruto"] == 1_000_000, "pausa, não aborto — o artefato saiu"
