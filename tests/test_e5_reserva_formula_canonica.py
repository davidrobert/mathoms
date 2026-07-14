"""Critério de aceite da A28.l1 — reserva conforme FORMULAS.md §Reserva, fim-a-fim.

Roda o substrato dogfood (E1.5c→E3→E4→E5) com perfil PJ-dominante, despesa
essencial documentada e carteira mista (RF + ações + FII + exterior) e trava:

1. numerador exclui ações/FII/exterior (reserva_liquida_disponivel);
2. denominador é o custo essencial mensal da janela 12m (ADR-306 §D4);
3. perfil PJ-dominante avalia contra 18 meses; "Excessiva" só acima do alvo;
4. nenhum campo exibe coberturas divergentes (reserva == score == composição).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import load_fixture, run_dogfood_pipeline, write_e5_config

_REPO = Path(__file__).resolve().parents[1]
_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"

_FAMILY = {
    "titular": "alex",
    "membros": {
        "alex": {"nome_curto": "Alex", "data_nascimento": "1985-03-10"},
        "bia": {"nome_curto": "Bia", "data_nascimento": "1987-07-22"},
    },
}

_BASELINE_CARTEIRA_MISTA = {
    "pipeline_stage": "E1.5_Baseline_Patrimonial",
    "data_processamento": "2024-12-31",
    "itens": [
        {
            "codigo": "31",
            "descricao": "CDB BANCO FICTICIO LIQUIDEZ DIARIA",
            "categoria": "investimento",
            "valor_brl": 100_000.0,
            "membro": "alex",
            "ano": 2024,
            "instituicao": "bancoficticio",
        },
        {
            "codigo": "31",
            "descricao": "ACOES ITSA4 CORRETORA FICTICIA",
            "categoria": "investimento",
            "valor_brl": 200_000.0,
            "membro": "alex",
            "ano": 2024,
            "instituicao": "corretoraficticia",
        },
        {
            "codigo": "73",
            "descricao": "FII HGLG11 CORRETORA FICTICIA",
            "categoria": "investimento",
            "valor_brl": 100_000.0,
            "membro": "alex",
            "ano": 2024,
            "instituicao": "corretoraficticia",
        },
        {
            "codigo": "31",
            "descricao": "ETF IVVB11 EXTERIOR",
            "categoria": "investimento",
            "valor_brl": 100_000.0,
            "membro": "bia",
            "ano": 2024,
            "instituicao": "corretoraficticia",
        },
    ],
    "resumo": {"ano_referencia": 2024, "membros": ["alex", "bia"]},
}

_EXTRATO_PJ = {
    "pipeline_stage": "E2",
    "banco": "itau",
    "tipo": "extratoconta",
    "moeda": "BRL",
    "numero_conta": "12.345-6",
    "numero_conta_norm": "123456",
    "periodo": {"inicio": "2026-01-01", "fim": "2026-01-31"},
    "saldo_inicial": 0.0,
    "saldo_final": 21_000.0,
    "transacoes": [
        {"data": "2026-01-15", "descricao": "PIX RECEBIDO CONSULTORIA PJ", "valor": 30_000.0},
        {"data": "2026-01-20", "descricao": "PAGAMENTO SUPERMERCADO FICTICIO", "valor": -9_000.0},
    ],
}


@pytest.fixture(scope="module")
def payload(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("reserva_formula_canonica")
    write_e5_config(
        root,
        family=_FAMILY,
        expense_keywords={"alimentacao": ["SUPERMERCADO"]},
        # ADR-330/331: código E4 real (lucros_distribuidos), não o agregado fantasma receita_pj.
        income_keywords={"lucros_distribuidos": ["PIX"]},
    )
    return run_dogfood_pipeline(
        root,
        raw_baseline=_BASELINE_CARTEIRA_MISTA,
        e2_extracts={"extrato-pj": _EXTRATO_PJ},
    )


def test_numerador_exclui_acoes_fii_exterior(payload: dict):
    reserva = payload["reserva_emergencia"]
    assert reserva["total_liquida"] == pytest.approx(100_000.0)
    assert reserva["excluido_da_reserva"]["investimentos_nao_liquidos"] == pytest.approx(400_000.0)


def test_denominador_e_custo_essencial_da_janela_12m(payload: dict):
    reserva = payload["reserva_emergencia"]
    j12m = payload["fluxo_caixa"]["janela_12m"]
    assert reserva["base_denominador"] == "custo_essencial"
    assert reserva["janela"] == "12m"
    assert reserva["despesas_mensais"] == pytest.approx(j12m["despesa_mensal_essencial"])
    assert reserva["custo_essencial_mensal"] == pytest.approx(9_000.0)


def test_perfil_pj_dominante_avalia_contra_18_meses(payload: dict):
    reserva = payload["reserva_emergencia"]
    assert reserva["perfil_renda"] == "pj_dominante"
    assert reserva["meses_alvo"] == 18
    assert reserva["alvo_brl"] == pytest.approx(18 * 9_000.0)
    # 100k ÷ 9k ≈ 11,1 meses — abaixo do alvo de 18: nunca "Excessiva".
    assert reserva["cobertura_meses"] == pytest.approx(11.1)
    assert reserva["avaliacao_liquidity"] != "Excessiva"
    assert reserva["gap_brl"] == pytest.approx(62_000.0)


def test_nenhum_campo_exibe_coberturas_divergentes(payload: dict):
    reserva = payload["reserva_emergencia"]
    cobertura = reserva["cobertura_meses"]
    assert reserva["composicao_liquida"]["cobertura_meses"] == cobertura
    comp_score = next(
        c for c in payload["score"]["componentes"] if c["code"] == "cobertura_despesas"
    )
    assert comp_score["valor"] == pytest.approx(cobertura, abs=0.05)


def test_lineage_total_liquida_soma_dos_componentes(payload: dict):
    """check_lineage_sum sobrevive ao filtro: Σ inputs == total_liquida."""
    field = payload["_lineage"]["fields"]["reserva_emergencia.total_liquida"]
    composicao = payload["reserva_emergencia"]["composicao_liquida"]
    soma = sum(composicao[ref["field"].rsplit(".", 1)[-1]] for ref in field["inputs"])
    assert soma == pytest.approx(float(field["value"]))
