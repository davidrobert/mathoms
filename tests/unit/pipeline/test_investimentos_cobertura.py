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
        "ano_base": None,
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


def test_presenca_de_linha_no_baseline_nao_e_evidencia_de_medicao() -> None:
    """O ramo que media o CONTÊINER: `bens` é sempre materializado, então isso
    dava `zero_apurado` a qualquer membro e tornava `nao_apurado` inalcançável
    (0/114 no corpus). Só valor lido é medição ([[ADR-394]] §Emenda (c))."""
    c = classificar_cobertura(_obs())
    assert c.status is CoberturaStatus.nao_apurado


def test_sem_fonte_nenhuma_e_nao_apurado() -> None:
    """O caso do r5/r6: nada respondeu, e hoje isso publicava 0,00."""
    c = classificar_cobertura(_obs())
    assert c.status is CoberturaStatus.nao_apurado
    assert c.fonte is None and not c.apurado
    assert c.motivo == "nenhuma fonte devolveu valor para o membro"


# =============================================================================
# Prescrição exige cobertura
# =============================================================================


def test_membro_nao_apurado_suprime_a_prescricao() -> None:
    coberturas = (classificar_cobertura(_obs()),)
    assert motivo_supressao_por_cobertura(coberturas) == "cobertura_incompleta: conjuge"


def test_zero_apurado_nao_suprime() -> None:
    """O modo de falha oposto: se tudo virar ressalva, o sinal some."""
    coberturas = (classificar_cobertura(_obs(posicoes_atribuidas=True)),)
    assert coberturas[0].status is CoberturaStatus.zero_apurado
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


# O fixture anterior era `baseline={"members": <dict>}` — 1 dos 4 shapes que
# `resolve_members` aceita, e o ÚNICO que desvia de `build_members_from_consolidated`,
# que é por onde a produção sempre passa. Era a razão de 22 testes verdes sobre um
# mecanismo inerte: o shape do teste não existe em produção.
def _baseline_consolidado(*, conjuge_inv: list | None = None) -> dict:
    """Shape que o E1.5c realmente emite — sem chave `members`."""
    itens = [{"descricao": "CDB", "proprietario": "david", "valores_31_12": {"2025": 1.0}}]
    for i, inv in enumerate(conjuge_inv or []):
        itens.append(
            {
                "descricao": f"FII{i}",
                "proprietario": "mariana",
                "valores_31_12": {"2025": inv},
            }
        )
    return {"investimentos_consolidados": itens, "patrimonio_por_ano": {"2025": {}}}


def _inputs(totais: dict, *, conjuge_inv: list | None = None) -> PatrimonioInputs:
    return PatrimonioInputs(
        baseline=_baseline_consolidado(conjuge_inv=conjuge_inv),
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


# =============================================================================
# O flip para `null` — e o que cada consumidor faz com ele
# =============================================================================


def test_balde_nao_apurado_publica_null_e_nao_zero(config: PatrimonioConfig) -> None:
    """O eixo da lane: `0,00` afirma sobre o patrimônio da pessoa; `null` não afirma."""
    result = PatrimonioCalculator(config).calculate(_inputs({"david": 943_189.25}))

    assert result["investimentos_conjuge"] is None
    assert result["investimentos_titular"] == 943_189.25


def test_balde_zero_apurado_publica_zero(config: PatrimonioConfig) -> None:
    """Guard anti-vacuidade: sem ele, `null` em tudo passaria neste arquivo."""
    result = PatrimonioCalculator(config).calculate(_inputs({"david": 943_189.25, "mariana": 0.0}))

    assert result["investimentos_conjuge"] == 0.0


def test_titular_nao_absorve_o_valor_do_conjuge_nao_resolvido(config: PatrimonioConfig) -> None:
    """Elo 2 da cadeia: sem este assert, a mutação do slug não prova nada."""
    resolvido = PatrimonioCalculator(config).calculate(
        _inputs({"david": 900_000.0, "mariana": 100_000.0})
    )
    nao_resolvido = PatrimonioCalculator(config).calculate(
        _inputs({"david": 900_000.0, "slug-que-ninguem-canonicaliza": 100_000.0})
    )

    assert resolvido["investimentos_titular"] == 900_000.0
    assert (
        nao_resolvido["investimentos_titular"] == 900_000.0
    ), "o titular NÃO absorve o slug não resolvido (era 1.000.000 antes do 3b)"
    assert nao_resolvido["investimentos_nao_atribuidos"] == 100_000.0
    assert (
        nao_resolvido["bruto"] == resolvido["bruto"]
    ), "o dinheiro sai do titular sem sair do patrimônio — só o dono é incerto"


def test_reserva_conta_membro_nao_apurado_como_zero() -> None:
    """Contrato, não implementação: a reserva não conta dinheiro que ninguém mediu."""
    from pipeline.domain.services.patrimonio_types import MemberIdentity
    from pipeline.domain.services.reserva_liquidez import build_reserva_liquida

    identity = MemberIdentity(
        titular_key="david", conjuge_key="mariana", titular_nome="D", conjuge_nome="M"
    )
    patrimonio = {"investimentos_titular": 100.0, "investimentos_conjuge": None}
    reserva = build_reserva_liquida(patrimonio, None, None, identity=identity)

    assert reserva.componentes(incluir_caixa_me=False, solo=False)["investimentos_conjuge"] == 0


def test_nao_atribuido_vira_categoria_e_a_composicao_segue_fechando(
    config: PatrimonioConfig,
) -> None:
    """P3: sem este assert, o balde podia sumir do donut e a soma quebrar calada."""
    result = PatrimonioCalculator(config).calculate(
        _inputs({"david": 900_000.0, "slug-orfao": 100_000.0})
    )
    categorias = {c["categoria"]: c["valor"] for c in result["composicao"]}

    assert categorias["Investimentos sem titular identificado"] == 100_000.0
    assert round(sum(c["valor"] for c in result["composicao"]), 2) == result["bruto"]
    assert round(sum(c["pct"] for c in result["composicao"]), 2) == 100.0


def test_sem_nao_atribuido_a_categoria_nao_aparece(config: PatrimonioConfig) -> None:
    """Categoria permanente com 0,00 em todo run sadio seria ruído no donut."""
    result = PatrimonioCalculator(config).calculate(_inputs({"david": 900_000.0}))

    assert "Investimentos sem titular identificado" not in {
        c["categoria"] for c in result["composicao"]
    }


# =============================================================================
# Alcançabilidade — o gate que faltava (A40.l69 · ADR-394 §Emenda (c))
#
# O ramo `tem_bens_irpf` media o CONTÊINER: `build_members_from_consolidated`
# materializa `bens` com 4 chaves sempre, logo o predicado era constante `True` e
# `nao_apurado` ficou inalcançável — 0/114 instâncias-membro do corpus, com a
# suíte inteira verde. Enum fechado de estado precisa de cobertura de estados
# MEDIDA: estado que nunca ocorre é código morto ou predicado quebrado, e o
# teste obriga a dizer qual dos dois.
# =============================================================================


def test_os_tres_estados_sao_alcancaveis_pela_fachada(config: PatrimonioConfig) -> None:
    """Cada estado do enum ocorre a partir de um baseline que o produtor emite."""
    alcancados = set()
    for totais, conjuge_inv in (
        ({"david": 943_189.25, "mariana": 110_130.67}, None),  # apurado
        ({"david": 943_189.25, "mariana": 0.0}, None),  # zero_apurado
        ({"david": 943_189.25}, None),  # nao_apurado
    ):
        result = PatrimonioCalculator(config).calculate(_inputs(totais, conjuge_inv=conjuge_inv))
        alcancados |= {c["status"] for c in result["cobertura_investimentos"]}
    assert alcancados == {s.value for s in CoberturaStatus}


def test_frescor_carrega_o_ano_base_do_membro(config: PatrimonioConfig) -> None:
    """`fonte` diz de ONDE; `frescor` diz de QUANDO — a lane pediu os dois."""
    result = PatrimonioCalculator(config).calculate(
        _inputs({"david": 943_189.25, "mariana": 110_130.67})
    )
    por_membro = {c["membro"]: c for c in result["cobertura_investimentos"]}
    assert por_membro["titular"]["frescor"] == "2025"
    assert por_membro["conjuge"]["frescor"] == "2025"
