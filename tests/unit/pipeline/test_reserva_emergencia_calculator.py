"""Testes para :class:`EmergencyReserveCalculator` (A28.l1 — FORMULAS.md §Reserva)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.patrimonio_types import MemberIdentity
from pipeline.domain.services.reserva_emergencia_calculator import (
    EmergencyReserveCalculator,
    ReservaClassificacao,
    ReservaEmergenciaConfig,
)


@pytest.fixture
def identity() -> MemberIdentity:
    return MemberIdentity(
        titular_key="david",
        conjuge_key="mariana",
        titular_nome="David",
        conjuge_nome="Mariana",
    )


@pytest.fixture
def config(identity: MemberIdentity) -> ReservaEmergenciaConfig:
    return ReservaEmergenciaConfig(members=identity)


def _bens(investimentos: list[dict] | None = None, contas: list[dict] | None = None) -> dict:
    bens: dict = {}
    if investimentos is not None:
        bens["investimentos"] = investimentos
    if contas is not None:
        bens["contas_bancarias"] = contas
    return {"bens": bens}


# =============================================================================
# ReservaEmergenciaConfig.from_scoring_json
# =============================================================================


def test_config_from_scoring_json_uses_defaults_when_empty(identity: MemberIdentity):
    cfg = ReservaEmergenciaConfig.from_scoring_json({}, identity)
    assert cfg.niveis_meses == (6, 12)
    assert len(cfg.classificacao) == 3
    assert cfg.classificacao[0].label == "Excelente"
    assert cfg.meses_alvo("pj_dominante") == 18
    assert cfg.meses_alvo("clt_estavel") == 6


def test_config_from_scoring_json_custom(identity: MemberIdentity):
    scoring = {
        "reserva_emergencia": {
            "niveis_meses": [3, 6, 12],
            "classificacao": [
                {"minimo_meses": 24, "label": "Supra", "acao": "realocar_excedente"},
                {"minimo_meses": 6, "label": "OK"},
            ],
            "_base_calculo": {
                "meses_alvo_por_perfil_renda": {"pj_dominante": {"meses": 20}},
            },
        }
    }
    cfg = ReservaEmergenciaConfig.from_scoring_json(scoring, identity)
    assert cfg.niveis_meses == (3, 6, 12)
    assert cfg.classificacao[0].label == "Supra"
    assert cfg.classificacao[0].acao == "realocar_excedente"
    assert cfg.meses_alvo("pj_dominante") == 20
    assert cfg.meses_alvo("renda_mista") == 12


# =============================================================================
# Numerador — filtro de liquidez (FORMULAS.md §Reserva)
# =============================================================================


_CARTEIRA_MISTA = [
    {"descricao": "CDB BANCO X", "valor": 60_000},
    {"descricao": "ACOES ITSA4", "valor": 200_000},
    {"descricao": "FII HGLG11", "valor": 100_000},
    {"descricao": "ETF GLOBAL EXTERIOR", "valor": 90_000},
    {"descricao": "BITCOIN BINANCE", "valor": 30_000},
    {"descricao": "PGBL PREVIDENCIA", "valor": 20_000},
]


def test_acoes_fii_exterior_excluidos_do_numerador(config: ReservaEmergenciaConfig):
    """Invariante de aceite A28.l1: carteira produtiva NÃO é reserva."""
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 10_000},
        patrimonio={"investimentos_david": 500_000, "investimentos_mariana": 0},
        bens_por_membro={
            "david": _bens(investimentos=_CARTEIRA_MISTA),
            "mariana": _bens(investimentos=[]),
        },
    )
    assert result["total_liquida"] == 60_000.0
    assert result["composicao_liquida"]["investimentos_david"] == 60_000.0
    assert result["excluido_da_reserva"]["investimentos_nao_liquidos"] == 440_000.0
    assert result["cobertura_meses"] == 6.0


def test_conta_corrente_e_poupanca_entram_como_liquidez(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 5_000},
        patrimonio={"investimentos_david": 30_000, "investimentos_mariana": 0},
        bens_por_membro={
            "david": _bens(
                investimentos=[{"descricao": "POUPANCA BANCO Y", "valor": 10_000}],
                contas=[{"descricao": "CONTA CORRENTE BANCO Y", "valor": 20_000}],
            ),
            "mariana": _bens(investimentos=[]),
        },
    )
    assert result["total_liquida"] == 30_000.0


def test_rf_sem_liquidez_diaria_excluida(config: ReservaEmergenciaConfig):
    """Debênture/CRA/CRI são RF de mercado secundário — fora da reserva."""
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000},
        patrimonio={"investimentos_david": 30_000, "investimentos_mariana": 0},
        bens_por_membro={
            "david": _bens(
                investimentos=[
                    {"descricao": "TESOURO SELIC", "valor": 10_000},
                    {"descricao": "DEBENTURE VALE", "valor": 15_000},
                    {"descricao": "CRA AGRO XP", "valor": 5_000},
                ]
            ),
            "mariana": _bens(investimentos=[]),
        },
    )
    assert result["total_liquida"] == 10_000.0
    assert result["excluido_da_reserva"]["investimentos_nao_liquidos"] == 20_000.0


def test_caixa_me_excluida_por_default(config: ReservaEmergenciaConfig):
    """Caixa ME só entra com finalidade explícita = reserva."""
    calc = EmergencyReserveCalculator(config)
    patrimonio = {
        "investimentos_david": 0,
        "investimentos_mariana": 0,
        "caixa_moeda_estrangeira": 60_000,
        "caixa_detalhes": [
            {"conta": "banco brl", "moeda": "BRL", "valor_brl": 10_000, "tipo": "caixa"},
            {"conta": "wise", "moeda": "USD", "valor_brl": 50_000, "tipo": "moeda_estrangeira"},
        ],
    }
    bens = {"david": _bens(investimentos=[]), "mariana": _bens(investimentos=[])}
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000}, patrimonio=patrimonio, bens_por_membro=bens
    )
    assert result["total_liquida"] == 10_000.0
    assert result["composicao_liquida"]["caixa"] == 10_000.0
    assert result["composicao_liquida"]["caixa_moeda_estrangeira"] == 0.0
    assert result["excluido_da_reserva"]["caixa_moeda_estrangeira"] == 50_000.0


def test_caixa_me_entra_com_finalidade_reserva(identity: MemberIdentity):
    cfg = ReservaEmergenciaConfig(members=identity, incluir_caixa_me=True)
    calc = EmergencyReserveCalculator(cfg)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000},
        patrimonio={
            "investimentos_david": 0,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 50_000,
            "caixa_detalhes": [
                {"conta": "wise", "moeda": "USD", "valor_brl": 50_000, "tipo": "moeda_estrangeira"}
            ],
        },
        bens_por_membro={"david": _bens(investimentos=[]), "mariana": _bens(investimentos=[])},
    )
    assert result["total_liquida"] == 50_000.0
    assert result["excluido_da_reserva"]["caixa_moeda_estrangeira"] == 0.0


def test_caixa_residual_sem_detalhes_fica_fora(config: ReservaEmergenciaConfig):
    """Residual IRPF (sem caixa_detalhes) é não-verificável — excluído e exposto."""
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000},
        patrimonio={
            "investimentos_david": 0,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 50_000,
        },
        bens_por_membro={"david": _bens(investimentos=[]), "mariana": _bens(investimentos=[])},
    )
    assert result["total_liquida"] == 0.0
    assert result["excluido_da_reserva"]["caixa_nao_classificado"] == 50_000.0


def test_posicoes_atuais_tem_precedencia_sobre_irpf(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000},
        patrimonio={"investimentos_david": 99_999, "investimentos_mariana": 0},
        investimentos_atuais={
            "dados": [
                {"nome": "CDB LIQUIDEZ DIARIA", "membro": "david", "valor_atual": 12_000},
                {"nome": "ACOES PETR4", "membro": "david", "valor_atual": 40_000},
            ]
        },
        bens_por_membro={
            "david": _bens(investimentos=[{"descricao": "CDB ANTIGO IRPF", "valor": 77_000}]),
            "mariana": _bens(investimentos=[]),
        },
    )
    assert result["total_liquida"] == 12_000.0
    assert result["excluido_da_reserva"]["investimentos_nao_liquidos"] == 40_000.0


def test_sem_itens_cai_no_agregado_legado(config: ReservaEmergenciaConfig):
    """Sem item-level data, preserva o agregado (fixtures antigas) em vez de zerar."""
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 10_000},
        patrimonio={"investimentos_david": 30_000, "investimentos_mariana": 20_000},
    )
    assert result["total_liquida"] == 50_000.0
    assert result["cobertura_meses"] == 5.0


def test_total_liquido_soma_exata_dos_componentes(config: ReservaEmergenciaConfig):
    """Invariante check_lineage_sum: total == Σ componentes da composição."""
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000},
        patrimonio={
            "investimentos_david": 1000.126,
            "investimentos_mariana": 0.456,
            "caixa_moeda_estrangeira": 10.128,
            "caixa_detalhes": [
                {"conta": "b", "moeda": "BRL", "valor_brl": 10.128, "tipo": "caixa"}
            ],
        },
    )
    comp = result["composicao_liquida"]
    parcelas = [v for k, v in comp.items() if k not in ("total_liquido", "cobertura_meses")]
    assert round(sum(parcelas), 2) == comp["total_liquido"] == result["total_liquida"]


# =============================================================================
# Denominador — custo essencial da janela canônica (ADR-306 §D4)
# =============================================================================


def test_denominador_prefere_custo_essencial_da_janela(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={
            "despesa_mensal_media": 44_000,
            "janela_12m": {
                "despesa_mensal_media": 80_000,
                "despesa_mensal_essencial": 25_000,
                "n_meses": 12,
            },
        },
        patrimonio={"investimentos_david": 300_000, "investimentos_mariana": 0},
    )
    assert result["despesas_mensais"] == 25_000.0
    assert result["custo_essencial_mensal"] == 25_000.0
    assert result["base_denominador"] == "custo_essencial"
    assert result["janela"] == "12m"
    assert result["cobertura_meses"] == 12.0
    assert result["nivel_6_meses"] == 150_000.0


def test_denominador_fallback_despesa_total_rotulado(config: ReservaEmergenciaConfig):
    """Sem categoria essencial documentada → fallback explícito à despesa total."""
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={
            "despesa_mensal_media": 1_000,
            "janela_12m": {
                "despesa_mensal_media": 2_000,
                "despesa_mensal_essencial": 0,
                "n_meses": 12,
            },
        },
        patrimonio={"investimentos_david": 24_000, "investimentos_mariana": 0},
    )
    assert result["despesas_mensais"] == 2_000.0
    assert result["custo_essencial_mensal"] == 0.0
    assert result["base_denominador"] == "despesa_total"
    assert result["cobertura_meses"] == 12.0


def test_fallback_full_period_sem_janela(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000, "janela_meses": 40},
        patrimonio={"investimentos_david": 6_000, "investimentos_mariana": 0},
    )
    assert result["despesas_mensais"] == 1_000.0
    assert result["janela"] == "full"
    assert result["janela_meses"] == 40


def test_cobertura_zero_despesa_returns_zero(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 0},
        patrimonio={"investimentos_david": 100, "investimentos_mariana": 0},
    )
    assert result["cobertura_meses"] == 0.0


# =============================================================================
# meses_alvo por composição de renda (FORMULAS.md §Reserva-alvo)
# =============================================================================


@pytest.mark.parametrize(
    ("pj", "clt", "perfil", "meses"),
    [
        (90_000, 10_000, "pj_dominante", 18),
        (45_000, 55_000, "pj_relevante", 12),
        (20_000, 80_000, "renda_mista", 12),
        (5_000, 95_000, "clt_unica_fonte", 12),
        (0, 0, "indefinido", 12),
    ],
)
def test_perfil_renda_define_meses_alvo(
    config: ReservaEmergenciaConfig, pj: float, clt: float, perfil: str, meses: int
):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={
            "despesa_mensal_media": 1_000,
            # ADR-330: perfil lê o bloco derivado receita_por_natureza (não por_fonte).
            "receita_por_natureza": {
                "receita_pj": pj,
                "receita_clt": clt,
                "receita_aluguel": 0,
                "receita_outras": 0,
            },
        },
        patrimonio={"investimentos_david": 1_000, "investimentos_mariana": 0},
    )
    assert result["perfil_renda"] == perfil
    assert result["meses_alvo"] == meses


def test_perfil_usa_receita_por_natureza_nao_por_fonte(config: ReservaEmergenciaConfig):
    """ADR-330 (cluster B): sobre o SHAPE REAL do E4 — por_fonte tem pro_labore +
    lucros_distribuidos, nunca a chave agregada receita_pj — o perfil deve vir do
    bloco derivado receita_por_natureza. Guarda contra a regressão da chave morta
    (por_fonte.receita_pj → 0 → clt_unica_fonte falso)."""
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={
            "despesa_mensal_media": 1_000,
            # shape real: sem 'receita_pj' agregado
            "por_fonte": {"pro_labore": 3_000, "lucros_distribuidos": 4_000, "receita_clt": 3_000},
            "receita_por_natureza": {
                "receita_pj": 7_000,  # pro_labore + lucros_distribuidos
                "receita_clt": 3_000,
                "receita_aluguel": 0,
                "receita_outras": 0,
            },
        },
        patrimonio={"investimentos_david": 1_000, "investimentos_mariana": 0},
    )
    assert result["perfil_renda"] == "pj_dominante"  # 70% ≥ 60
    assert result["receita_pj_pct"] == 70.0


def test_alvo_e_gap_dimensionados_pelo_perfil(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={
            "despesa_mensal_media": 10_000,
            "receita_por_natureza": {
                "receita_pj": 100_000,
                "receita_clt": 0,
                "receita_aluguel": 0,
                "receita_outras": 0,
            },
        },
        patrimonio={"investimentos_david": 100_000, "investimentos_mariana": 0},
    )
    assert result["meses_alvo"] == 18
    assert result["alvo_brl"] == 180_000.0
    assert result["gap_brl"] == 80_000.0


# =============================================================================
# Avaliação — "Excessiva" só acima do alvo do perfil
# =============================================================================


_SCORING_BANDS = (
    ReservaClassificacao(minimo_meses=24, label="Excessiva", acao="realocar_excedente"),
    ReservaClassificacao(minimo_meses=12, label="Robusta", acao="manter"),
    ReservaClassificacao(minimo_meses=6, label="Adequada", acao="manter_se_clt"),
    ReservaClassificacao(minimo_meses=3, label="Mínima", acao="completar_para_alvo"),
    ReservaClassificacao(minimo_meses=0, label="Insuficiente", acao="prioridade_maxima"),
)


def _calc_bands(identity: MemberIdentity, meses_alvo_pj: int = 18) -> EmergencyReserveCalculator:
    cfg = ReservaEmergenciaConfig(
        members=identity,
        classificacao=_SCORING_BANDS,
        meses_alvo_por_perfil={"pj_dominante": meses_alvo_pj, "renda_mista": 12},
    )
    return EmergencyReserveCalculator(cfg)


def test_excessiva_quando_acima_do_alvo_do_perfil(identity: MemberIdentity):
    calc = _calc_bands(identity)
    result = calc.calculate(
        fluxo={
            "despesa_mensal_media": 1_000,
            "receita_por_natureza": {
                "receita_pj": 100,
                "receita_clt": 0,
                "receita_aluguel": 0,
                "receita_outras": 0,
            },
        },
        patrimonio={"investimentos_david": 30_000, "investimentos_mariana": 0},
    )
    assert result["cobertura_meses"] == 30.0
    assert result["avaliacao_liquidity"] == "Excessiva"


def test_excessiva_demovida_quando_cobertura_dentro_do_alvo(identity: MemberIdentity):
    """Alvo do perfil ≥ faixa Excessiva → nunca rotular excedente dentro do alvo."""
    calc = _calc_bands(identity, meses_alvo_pj=30)
    result = calc.calculate(
        fluxo={
            "despesa_mensal_media": 1_000,
            "receita_por_natureza": {
                "receita_pj": 100,
                "receita_clt": 0,
                "receita_aluguel": 0,
                "receita_outras": 0,
            },
        },
        patrimonio={"investimentos_david": 25_000, "investimentos_mariana": 0},
    )
    assert result["cobertura_meses"] == 25.0
    assert result["avaliacao_liquidity"] == "Robusta"


def test_avaliacao_insuficiente_below_min(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000},
        patrimonio={"investimentos_david": 2_000, "investimentos_mariana": 0},
    )
    assert result["avaliacao_liquidity"] == "Insuficiente"


def test_avaliacao_custom_bands(identity: MemberIdentity):
    cfg = ReservaEmergenciaConfig(
        members=identity,
        classificacao=(
            ReservaClassificacao(minimo_meses=24, label="Supra"),
            ReservaClassificacao(minimo_meses=0, label="Atenção"),
        ),
    )
    calc = EmergencyReserveCalculator(cfg)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1_000},
        patrimonio={"investimentos_david": 30_000, "investimentos_mariana": 0},
    )
    assert result["avaliacao_liquidity"] == "Supra"


# =============================================================================
# Shape do payload
# =============================================================================


_EXPECTED_PAYLOAD_KEYS = {
    "despesas_mensais",
    "custo_essencial_mensal",
    "base_denominador",
    "janela",
    "janela_meses",
    "perfil_renda",
    "receita_pj_pct",
    "meses_alvo",
    "alvo_brl",
    "gap_brl",
    "nivel_6_meses",
    "nivel_12_meses",
    "composicao_liquida",
    "excluido_da_reserva",
    "total_liquida",
    "cobertura_meses",
    "avaliacao_liquidity",
    "niveis",
}


def test_output_shape(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={"investimentos_david": 1000, "investimentos_mariana": 500},
    )
    assert set(result.keys()) == _EXPECTED_PAYLOAD_KEYS
    assert result["niveis"] == ["6 meses", "12 meses"]


def test_composicao_liquida_keys_dynamic(identity: MemberIdentity):
    """composicao_liquida usa identity dinâmica (solo preserva shape legado)."""
    solo = MemberIdentity(titular_key="joao", conjuge_key="", titular_nome="João", conjuge_nome="")
    cfg = ReservaEmergenciaConfig(members=solo)
    calc = EmergencyReserveCalculator(cfg)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={"investimentos_joao": 5_000},
    )
    assert result["composicao_liquida"]["investimentos_joao"] == 5_000.0
    assert result["composicao_liquida"]["investimentos_"] == 0.0
    assert result["total_liquida"] == 5_000.0
