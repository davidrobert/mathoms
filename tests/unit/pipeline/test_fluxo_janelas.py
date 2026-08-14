"""Contrato das janelas interativas precomputadas (ADR-377)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.fluxo_janelas import build_fluxo_janelas


def _tx(data: str, valor: int | str) -> dict:
    return {"data": data, "valor": valor}


def _receitas(dados: dict[str, list[dict]]) -> dict:
    return {"dados": dados}


def _fluxo(
    meses: list[str],
    receitas: dict[str, dict],
    despesas: dict[str, dict],
) -> dict:
    return {
        "meses_ordenados": meses,
        "receitas": {"por_mes": receitas},
        "despesas": {"por_mes": despesas},
    }


def _sum_money(rows: list[dict], key: str) -> Decimal:
    return sum((Decimal(str(row[key])) for row in rows), Decimal("0"))


def _janela_centavos() -> dict:
    meses = ["2026-01", "2026-02"]
    receitas = _receitas(
        {
            "receita_clt": [_tx("2026-01-01", "0.01")],
            "pro_labore": [_tx("2026-01-02", "0.01")],
            "receita_aluguel": [_tx("2026-02-01", "0.01")],
        }
    )
    receitas_mes = {"2026-01": {"A": 0.02, "_total": 0.02}, "2026-02": {"B": 0.01, "_total": 0.01}}
    despesas_mes = {
        "2026-01": {"moradia": 0.01, "_total": 0.01},
        "2026-02": {"lazer": 0.02, "_total": 0.02},
    }
    return build_fluxo_janelas(receitas, _fluxo(meses, receitas_mes, despesas_mes), frozenset())[
        "3m"
    ].to_dict()


def _janela_orcamento() -> dict:
    meses = ["2026-01", "2026-02"]
    despesas = {
        "2026-01": {"moradia": 600, "aporte_investimento": 400, "_total": 1000},
        "2026-02": {"moradia": 400, "aporte_investimento": 600, "_total": 1000},
    }
    fluxo = _fluxo(meses, {mes: {"_total": 0} for mes in meses}, despesas)
    return build_fluxo_janelas(_receitas({}), fluxo, frozenset({"aporte_investimento"}))[
        "3m"
    ].to_dict()


def test_quatro_janelas_usam_meses_documentados_e_ytd_da_ancora() -> None:
    meses = ["2025-12", "2026-01", "2026-03", "2026-04", "2026-05"]
    receitas_mes = {mes: {"Origem": 100, "_total": 100} for mes in meses}
    despesas_mes = {mes: {"moradia": 40, "_total": 40} for mes in meses}
    receitas = _receitas({"receita_clt": [_tx(f"{mes}-10", 100) for mes in meses]})

    janelas = build_fluxo_janelas(
        receitas,
        _fluxo(meses, receitas_mes, despesas_mes),
        frozenset({"aporte_investimento"}),
    )

    assert tuple(janelas) == ("3m", "6m", "12m", "ytd")
    assert janelas["3m"].meses == ("2026-03", "2026-04", "2026-05")
    assert janelas["6m"].meses == tuple(meses)
    assert janelas["12m"].meses == tuple(meses)
    assert janelas["ytd"].meses == ("2026-01", "2026-03", "2026-04", "2026-05")


def test_mes_sem_movimento_nao_entra_no_denominador() -> None:
    fluxo = _fluxo(
        ["2026-01", "2026-02", "2026-03"],
        {
            "2026-01": {"_total": 100},
            "2026-02": {"_total": 0},
            "2026-03": {"_total": 100},
        },
        {mes: {"_total": 0} for mes in ("2026-01", "2026-02", "2026-03")},
    )
    receitas = _receitas({"receita_clt": [_tx("2026-01-01", 100), _tx("2026-03-01", 100)]})

    janela = build_fluxo_janelas(receitas, fluxo, frozenset())["3m"]

    assert janela.meses == ("2026-01", "2026-03")
    assert janela.janela_meses == 2
    assert janela.receita_mensal_media == Decimal("100.00")


def test_rows_fecham_em_centavos_e_percentuais() -> None:
    janela = _janela_centavos()
    fontes = janela["tabela_receitas_por_fonte_mensal"]
    naturezas = janela["tabela_receita_por_natureza_mensal"]
    consumo = janela["tabela_consumo_por_categoria_mensal"]
    assert _sum_money(fontes, "mensal_media") == Decimal(str(janela["receita_mensal_media"]))
    assert _sum_money(naturezas, "mensal_media") == Decimal(str(janela["receita_mensal_media"]))
    assert _sum_money(consumo, "mensal_media") == Decimal(
        str(janela["despesa_consumo_mensal_media"])
    )
    assert sum(Decimal(str(row["participacao_pct"])) for row in fontes) == Decimal("100")
    assert consumo[-1]["participacao_acumulada_pct"] == 100.0


def test_orcamento_exclui_transferencia_e_reconcilia_bruto() -> None:
    janela = _janela_orcamento()
    assert janela["despesa_mensal_media"] == 1000.0
    assert janela["despesa_consumo_mensal_media"] == 500.0
    assert janela["transferencia_patrimonial_mensal"] == 500.0
    assert [row["categoria"] for row in janela["tabela_consumo_por_categoria_mensal"]] == [
        "moradia"
    ]


def test_janela_so_com_aporte_tem_consumo_vazio() -> None:
    fluxo = _fluxo(
        ["2026-01"],
        {"2026-01": {"_total": 0}},
        {"2026-01": {"aporte_investimento": 1000, "_total": 1000}},
    )

    janela = build_fluxo_janelas(_receitas({}), fluxo, frozenset({"aporte_investimento"}))[
        "3m"
    ].to_dict()

    assert janela["despesa_mensal_media"] == 1000.0
    assert janela["despesa_consumo_mensal_media"] == 0.0
    assert janela["transferencia_patrimonial_mensal"] == 1000.0
    assert janela["tabela_consumo_por_categoria_mensal"] == []


def test_janela_vazia_declara_bounds_nulos() -> None:
    janela = build_fluxo_janelas(_receitas({}), _fluxo([], {}, {}), frozenset())["ytd"]

    assert janela.to_dict() == {
        "janela": "ytd",
        "janela_meses": 0,
        "mes_inicio": None,
        "mes_fim": None,
        "receita_total": 0.0,
        "despesa_total": 0.0,
        "receita_mensal_media": 0.0,
        "despesa_mensal_media": 0.0,
        "despesa_consumo_mensal_media": 0.0,
        "transferencia_patrimonial_mensal": 0.0,
        "tabela_receitas_por_fonte_mensal": [],
        "tabela_receita_por_natureza_mensal": [],
        "tabela_consumo_por_categoria_mensal": [],
    }
