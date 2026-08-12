"""Tests — linhas de posição com data de referência e id estável (A40.l39)."""

from __future__ import annotations

from pipeline.domain.services.patrimonio_types import normalize_data_referencia
from pipeline.domain.services.posicao_31_12_builder import build_posicao_31_12


def _informe_entry(**over) -> dict:
    base = {
        "descricao": "RDB/CDB - Ag 9652 Conta 0004397-8",
        "tipo": "cdb",
        "moeda": "BRL",
        "saldo_brl": "1000.00",
        "saldo_original": "1000.00",
        "ano_base": 2025,
        "cnpj_emissor": "60701190000104",
        "fonte": "informe_31_12",
    }
    return {**base, **over}


def _detalhe_extrato(**over) -> dict:
    base = {
        "conta": "Picpay (extratoconta)",
        "moeda": "BRL",
        "saldo_original": 500.0,
        "valor_brl": 500.0,
        "tipo": "caixa",
        "fonte": "extrato",
        "data_referencia": "2026-03-28",
        "data_referencia_precisao": "dia",
    }
    return {**base, **over}


def test_linha_de_informe_carrega_31_12_do_ano_base():
    baseline = {"informe_pf_saldos_31_12": [_informe_entry()]}
    (row,) = build_posicao_31_12(baseline, [])
    assert row["data_referencia"] == "2025-12-31"
    assert row["data_referencia_precisao"] == "dia"


def test_linha_de_extrato_propaga_fim_de_periodo_do_detalhe():
    (row,) = build_posicao_31_12({}, [_detalhe_extrato()])
    assert row["data_referencia"] == "2026-03-28"
    assert row["data_referencia_precisao"] == "dia"
    assert row["ano_base"] is None


def test_id_estavel_e_distinto_para_entries_do_mesmo_emissor():
    """Duas entries do mesmo CNPJ/tipo/moeda/ano (ex.: dois CDBs do mesmo banco)
    não podem colidir — a descrição normalizada discrimina via hash curto."""
    baseline = {
        "informe_pf_saldos_31_12": [
            _informe_entry(descricao="CDB Op. 111"),
            _informe_entry(descricao="CDB Op. 222"),
        ]
    }
    rows = build_posicao_31_12(baseline, [])
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 2
    rows2 = build_posicao_31_12(baseline, [])
    assert [r["id"] for r in rows2] == ids


def test_id_de_extrato_deriva_da_conta_construida():
    (row,) = build_posicao_31_12({}, [_detalhe_extrato()])
    assert row["id"] == "extrato:picpay_extratoconta:brl"


def test_normalize_data_referencia_formatos():
    assert normalize_data_referencia("2026-03-28") == ("2026-03-28", "dia")
    assert normalize_data_referencia("2026-02") == ("2026-02-28", "mes")
    assert normalize_data_referencia("") == (None, "desconhecida")
    assert normalize_data_referencia(None) == (None, "desconhecida")
    assert normalize_data_referencia("202603") == (None, "desconhecida")
