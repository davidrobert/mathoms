"""Guarda de sinal dos baldes patrimoniais — A40.l67 item 1d ([[ADR-394]] §Emenda 2026-08-18).

Cobre o serviço puro, o efeito no ``PatrimonioCalculator`` (a montante das duas
somas) e o kill-switch de três estados.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.carteira_por_papel import build_carteira_por_papel
from pipeline.domain.services.conversao_me import identity_native_brl
from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_sign_guard import (
    SIGN_GUARD_ENV,
    BaldesPatrimoniais,
    SignGuardMode,
    aplicar_guarda_de_sinal,
    review_reasons_do_artefato,
    sign_guard_mode,
)
from pipeline.domain.services.patrimonio_types import (
    CaixaDetalhe,
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
)

_IDENT = MemberIdentity(
    titular_key="david", conjuge_key="mariana", titular_nome="David", conjuge_nome="Mariana"
)


def _inputs(baseline: dict, **kw) -> PatrimonioInputs:
    """Injeta `members` — obrigatório desde a [[ADR-410]] D2."""
    return PatrimonioInputs(
        baseline=baseline,
        members=resolve_members(baseline, _IDENT),
        carteira=build_carteira_por_papel(
            kw.get("investimentos_atuais"),
            titular_key=_IDENT.titular_key,
            conjuge_key=_IDENT.conjuge_key,
        ),
        **kw,
    )


def _baldes(**overrides: str) -> BaldesPatrimoniais:
    base = {
        "residencia": "500000",
        "imoveis_investimento": "300000",
        "veiculos": "50000",
        "investimentos_titular": "200000",
        "investimentos_conjuge": "100000",
        "caixa_total_brl": "80000",
        "imoveis_geradores": "180000",
        "imoveis_nao_geradores": "120000",
    }
    base.update(overrides)
    return BaldesPatrimoniais(**{k: Decimal(v) for k, v in base.items()})


# =============================================================================
# Serviço puro — rota de reclassificação
# =============================================================================


@pytest.mark.parametrize(
    "balde", ["caixa_total_brl", "investimentos_titular", "investimentos_conjuge"]
)
def test_negativo_financeiro_vira_divida_de_curto_prazo(balde: str) -> None:
    """Cheque especial e conta margem publicam: balde vai a zero, montante vai à dívida."""
    result = aplicar_guarda_de_sinal(_baldes(**{balde: "-4000"}), modo=SignGuardMode.enforce)

    assert result.baldes.valor(balde) == Decimal("0")
    assert result.dividas_curto_prazo_brl == Decimal("4000")
    assert [r.balde for r in result.reclassificados] == [balde]
    assert result.cobertura_completa, "reclassificado publica normal — nada a suprimir"


def test_reclassificacao_preserva_o_patrimonio_liquido() -> None:
    """O montante sai do ativo e entra no passivo: a diferença não se move."""
    antes = _baldes(caixa_total_brl="-4000")
    soma_antes = (
        antes.residencia
        + antes.imoveis_investimento
        + antes.veiculos
        + antes.investimentos_titular
        + antes.investimentos_conjuge
        + antes.caixa_total_brl
    )
    result = aplicar_guarda_de_sinal(antes, modo=SignGuardMode.enforce)
    depois = result.baldes
    soma_depois = (
        depois.residencia
        + depois.imoveis_investimento
        + depois.veiculos
        + depois.investimentos_titular
        + depois.investimentos_conjuge
        + depois.caixa_total_brl
    )

    assert soma_depois - result.dividas_curto_prazo_brl == soma_antes


def test_dois_baldes_financeiros_negativos_somam_na_mesma_divida() -> None:
    result = aplicar_guarda_de_sinal(
        _baldes(caixa_total_brl="-1000", investimentos_conjuge="-2500"),
        modo=SignGuardMode.enforce,
    )

    assert result.dividas_curto_prazo_brl == Decimal("3500")
    assert len(result.reclassificados) == 2


# =============================================================================
# Serviço puro — sobrevivente físico
# =============================================================================


@pytest.mark.parametrize("balde", ["residencia", "imoveis_investimento", "veiculos"])
def test_negativo_fisico_sobrevive_sem_mutacao(balde: str) -> None:
    """Imóvel não tem saldo devedor próprio: mover inventaria passivo, zerar inventaria bem."""
    result = aplicar_guarda_de_sinal(_baldes(**{balde: "-7000"}), modo=SignGuardMode.enforce)

    assert result.baldes.valor(balde) == Decimal("-7000"), "publica o valor, não o esconde"
    assert result.dividas_curto_prazo_brl == Decimal("0")
    assert [s.balde for s in result.sobreviventes] == [balde]
    assert not result.cobertura_completa
    assert result.motivo_supressao == f"balde_negativo: {balde}"


# O r6 (`7b64b6c7`) publicou `imoveis_nao_geradores` = −125.381,88 com o agregado
# `imoveis_investimento` POSITIVO em 437.324,36 — guarda restrita aos 7 baldes
# ADR-145 erraria exatamente o run que motivou a lane.
def test_split_derivado_negativo_e_pego_com_agregado_positivo() -> None:
    result = aplicar_guarda_de_sinal(
        _baldes(imoveis_investimento="437324.36", imoveis_nao_geradores="-125381.88"),
        modo=SignGuardMode.enforce,
    )

    assert [s.balde for s in result.sobreviventes] == ["imoveis_nao_geradores"]
    assert result.baldes.imoveis_nao_geradores == Decimal("-125381.88")
    assert result.baldes.imoveis_investimento == Decimal("437324.36")


def test_corpus_limpo_nao_dispara_nada() -> None:
    """Guard anti-vacuidade: sem negativo, o veredito é inerte e a cobertura completa."""
    result = aplicar_guarda_de_sinal(_baldes(), modo=SignGuardMode.enforce)

    assert result.reclassificados == () and result.sobreviventes == ()
    assert result.dividas_curto_prazo_brl == Decimal("0")
    assert result.motivo_supressao is None


# =============================================================================
# Kill-switch
# =============================================================================


def test_modo_off_restaura_o_status_quo_ante(monkeypatch: pytest.MonkeyPatch) -> None:
    """`off` reaplica o clamp `max(0, caixa)` que o ramo de posições atuais tinha."""
    monkeypatch.setenv(SIGN_GUARD_ENV, "off")
    result = aplicar_guarda_de_sinal(_baldes(caixa_total_brl="-4000", veiculos="-7000"))

    assert result.baldes.caixa_total_brl == Decimal("0"), "clamp legado"
    assert result.baldes.veiculos == Decimal("-7000"), "físico seguia cru antes da guarda"
    assert result.dividas_curto_prazo_brl == Decimal("0")
    assert result.sobreviventes == () and result.cobertura_completa


def test_modo_desconhecido_cai_em_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SIGN_GUARD_ENV, "talvez")
    assert sign_guard_mode() is SignGuardMode.enforce


def test_env_ausente_e_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SIGN_GUARD_ENV, raising=False)
    assert sign_guard_mode() is SignGuardMode.enforce


# =============================================================================
# Projeção para review_reason (ADR-272) — é o modo que separa pausa de ressalva
# =============================================================================


def _artefato(modo: SignGuardMode) -> dict:
    guarda = aplicar_guarda_de_sinal(_baldes(veiculos="-7000"), modo=modo)
    return {"guarda_de_sinal": guarda.to_dict()}


def test_enforce_projeta_review_reason_tipado() -> None:
    reasons = review_reasons_do_artefato(
        _artefato(SignGuardMode.enforce), stage="analyze_finances", artifact_key="analise"
    )

    assert len(reasons) == 1
    assert reasons[0]["code"] == "domain.balde_patrimonial_negativo"
    assert reasons[0]["offending_value"] == "balde=veiculos"
    assert reasons[0]["expected"] == "veiculos >= 0"


def test_warn_declara_no_artefato_mas_nao_projeta_razao() -> None:
    """`warn` rebaixa sem cegar: a evidência fica, a pausa não acontece."""
    artefato = _artefato(SignGuardMode.warn)

    assert artefato["guarda_de_sinal"]["baldes_negativos"] == [
        {"balde": "veiculos", "valor_brl": -7000.0}
    ]
    assert artefato["guarda_de_sinal"]["motivo_supressao"] == "balde_negativo: veiculos"
    assert (
        review_reasons_do_artefato(artefato, stage="analyze_finances", artifact_key="analise") == []
    )


def test_review_reason_nao_carrega_valor_monetario() -> None:
    """`message`/`offending_value` só nomeiam o balde — ADR-273 anti-PII."""
    reasons = review_reasons_do_artefato(
        _artefato(SignGuardMode.enforce), stage="analyze_finances", artifact_key="analise"
    )

    assert "7000" not in reasons[0]["message"] + reasons[0]["offending_value"]


# =============================================================================
# Integração no PatrimonioCalculator — a montante das duas somas
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


def _inputs_com_caixa(caixa: float) -> PatrimonioInputs:
    return _inputs(
        baseline={"members": {"david": {"total_bens": 0, "total_dividas": 10_000}}},
        investimentos_atuais={
            "dados": [{"membro": "david", "valor": 200_000.0}],
            "total_por_membro": {"david": 200_000.0},
        },
        caixa_total_brl=caixa,
        caixa_detalhes=[
            CaixaDetalhe(
                conta="itau_cc",
                moeda="BRL",
                saldo_original=caixa,
                valor_brl=caixa,
                tipo="caixa",
                conversao=identity_native_brl(caixa),
            )
        ],
    )


def test_cheque_especial_publica_e_soma_na_divida(config: PatrimonioConfig) -> None:
    result = PatrimonioCalculator(config).calculate(_inputs_com_caixa(-4_000.0))

    assert result["caixa_total_brl"] == 0.0
    assert result["dividas"] == 14_000.0, "10k do IRPF + 4k reclassificados"
    assert result["bruto"] == 200_000.0
    assert result["liquido"] == 186_000.0
    assert result["guarda_de_sinal"]["reclassificados"] == [
        {"balde": "caixa_total_brl", "montante_brl": 4000.0}
    ]


def test_reclassificacao_preserva_composicao_identica_ao_bruto(config: PatrimonioConfig) -> None:
    """O seam corrigido: as duas somas independentes continuam concordando."""
    result = PatrimonioCalculator(config).calculate(_inputs_com_caixa(-4_000.0))

    assert round(sum(c["valor"] for c in result["composicao"]), 2) == result["bruto"]
    assert round(sum(c["pct"] for c in result["composicao"]), 2) == 100.0


def test_liquido_e_o_mesmo_com_e_sem_o_negativo_no_caixa(config: PatrimonioConfig) -> None:
    """A reclassificação move o montante de lado, não o cria nem o destrói."""
    com_negativo = PatrimonioCalculator(config).calculate(_inputs_com_caixa(-4_000.0))
    sem_negativo = PatrimonioCalculator(config).calculate(_inputs_com_caixa(0.0))

    assert com_negativo["liquido"] == sem_negativo["liquido"] - 4_000.0
    assert com_negativo["bruto"] == sem_negativo["bruto"]


def test_corpus_limpo_publica_veredito_inerte(config: PatrimonioConfig) -> None:
    result = PatrimonioCalculator(config).calculate(_inputs_com_caixa(80_000.0))

    assert result["guarda_de_sinal"]["cobertura_completa"] is True
    assert result["guarda_de_sinal"]["motivo_supressao"] is None
    assert result["caixa_total_brl"] == 80_000.0


# =============================================================================
# Estado terminal do stage — needs_review, nunca run vermelho
# =============================================================================


def _legacy(modo: SignGuardMode, **baldes: str) -> dict:
    guarda = aplicar_guarda_de_sinal(_baldes(**baldes), modo=modo)
    return {
        "score": {"valor": 7.0, "classificacao": "Bom"},
        "patrimonio": {"bruto": 1_000_000, "guarda_de_sinal": guarda.to_dict()},
        "goals": {},
    }


def test_balde_negativo_pausa_o_stage_em_needs_review() -> None:
    """`valid: False` + `review_reasons` é o contrato que o backend lê para pausar."""
    from scripts.analyze_finances import _e5_build_result_dict

    result = _e5_build_result_dict(_legacy(SignGuardMode.enforce, veiculos="-7000"), [])

    assert result["validation"]["valid"] is False
    # A40.l69: com duas fontes de razão (guarda + cobertura), o prefixo fixo
    # rotularia errado a razão da outra — a mensagem passa a vir da própria razão.
    assert result["validation"]["errors"] == [
        "E5: Balde patrimonial fisico publicou valor negativo — balde=veiculos"
    ]
    assert result["validation"]["review_reasons"][0]["code"] == "domain.balde_patrimonial_negativo"


def test_stage_entrega_o_artefato_mesmo_com_balde_negativo() -> None:
    """needs_review é pausa, não aborto: os KPIs do resultado continuam publicados."""
    from scripts.analyze_finances import _e5_build_result_dict

    result = _e5_build_result_dict(_legacy(SignGuardMode.enforce, veiculos="-7000"), [])

    assert result["total"] == 1 and result["score_valor"] == 7.0
    assert result["patrimonio_bruto"] == 1_000_000


def test_kill_switch_em_warn_nao_pausa_o_stage() -> None:
    from scripts.analyze_finances import _e5_build_result_dict

    result = _e5_build_result_dict(_legacy(SignGuardMode.warn, veiculos="-7000"), [])

    assert result["validation"] == {"valid": True, "errors": [], "review_reasons": []}


def test_kill_switch_em_off_nao_detecta_nada() -> None:
    from scripts.analyze_finances import _e5_build_result_dict

    result = _e5_build_result_dict(_legacy(SignGuardMode.off, veiculos="-7000"), [])

    assert result["validation"]["valid"] is True


# =============================================================================
# Prescrição exige cobertura (via e5_serialization)
# =============================================================================


def _derived_com_guarda(guarda: dict | None) -> tuple[dict, dict]:
    from pipeline.domain.services.e5_serialization import build_e5_output
    from tests.unit.pipeline.test_e5_serialization import _inputs

    patrimonio = {"bruto": 1_000_000, "liquido": 800_000}
    if guarda is not None:
        patrimonio["guarda_de_sinal"] = guarda
    alvo = {"rf_pos_pct": 40, "acoes_br_pct": 30, "acoes_int_pct": 20, "fiis_pct": 10}
    carteira = [{"categoria": "Renda Fixa", "valor": 100_000}]
    out = build_e5_output(
        _inputs(
            patrimonio=patrimonio,
            goals={"if_meta": 5_000_000, "alocacao_alvo": alvo},
            investimentos_classes={"tabela_classes": carteira},
        )
    )
    return out, out["goals"]["alocacao_alvo"]["derived"]


def test_cobertura_completa_publica_a_prescricao() -> None:
    _out, derived = _derived_com_guarda({"cobertura_completa": True})
    assert derived["next_aporte_classe"] is not None
    assert derived["desvio_max_pct"] is not None
    assert derived["motivo_supressao"] is None


def test_balde_negativo_suprime_so_a_prescricao() -> None:
    out, derived = _derived_com_guarda(
        {"cobertura_completa": False, "motivo_supressao": "balde_negativo: veiculos"}
    )
    assert derived["next_aporte_classe"] is None
    assert derived["desvio_max_pct"] is None
    assert derived["motivo_supressao"] == "balde_negativo: veiculos"
    assert derived["comparaveis"]
    assert derived["carteira_liquida_brl"] == 100_000.0
    assert out["patrimonio"]["bruto"] == 1_000_000


def test_artefato_sem_guarda_publica_normal() -> None:
    _out, derived = _derived_com_guarda(None)
    assert derived["next_aporte_classe"] is not None
    assert derived["motivo_supressao"] is None
