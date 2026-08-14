"""Janelas interativas precomputadas do fluxo de caixa (ADR-377)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal, TypedDict

PeriodoJanela = Literal["3m", "6m", "12m", "ytd"]

PERIODOS_JANELA: tuple[PeriodoJanela, ...] = ("3m", "6m", "12m", "ytd")
_LIMITES: dict[PeriodoJanela, int | None] = {"3m": 3, "6m": 6, "12m": 12, "ytd": None}
_CENTAVO = Decimal("0.01")
_PERCENTUAL = Decimal("0.01")
_RECEITA_PJ = frozenset({"pro_labore", "lucros_distribuidos"})


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value is not None else 0))
    except (ArithmeticError, ValueError):
        return Decimal("0")


def _cents(value: Decimal) -> int:
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _from_cents(value: int) -> Decimal:
    return (Decimal(value) / 100).quantize(_CENTAVO)


def _wire_number(value: Decimal) -> float:
    return float(value.quantize(_CENTAVO, rounding=ROUND_HALF_UP))


def _wire_pct(value: Decimal) -> float:
    return float(value.quantize(_PERCENTUAL, rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class TabelaReceitaRow:
    fonte: str
    total: Decimal
    mensal_media: Decimal
    participacao_pct: Decimal

    def to_dict(self) -> dict[str, str | float]:
        return {
            "fonte": self.fonte,
            "total": _wire_number(self.total),
            "mensal_media": _wire_number(self.mensal_media),
            "participacao_pct": _wire_pct(self.participacao_pct),
        }


@dataclass(frozen=True)
class TabelaNaturezaRow:
    natureza: str
    total: Decimal
    mensal_media: Decimal
    participacao_pct: Decimal

    def to_dict(self) -> dict[str, str | float]:
        return {
            "natureza": self.natureza,
            "total": _wire_number(self.total),
            "mensal_media": _wire_number(self.mensal_media),
            "participacao_pct": _wire_pct(self.participacao_pct),
        }


@dataclass(frozen=True)
class TabelaConsumoRow:
    categoria: str
    total: Decimal
    mensal_media: Decimal
    participacao_pct: Decimal
    participacao_acumulada_pct: Decimal

    def to_dict(self) -> dict[str, str | float]:
        return {
            "categoria": self.categoria,
            "total": _wire_number(self.total),
            "mensal_media": _wire_number(self.mensal_media),
            "participacao_pct": _wire_pct(self.participacao_pct),
            "participacao_acumulada_pct": _wire_pct(self.participacao_acumulada_pct),
        }


class FluxoJanelaPayload(TypedDict):
    janela: PeriodoJanela
    janela_meses: int
    mes_inicio: str | None
    mes_fim: str | None
    receita_total: int | float
    despesa_total: int | float
    receita_mensal_media: int | float
    despesa_mensal_media: int | float
    despesa_consumo_mensal_media: int | float
    transferencia_patrimonial_mensal: int | float
    tabela_receitas_por_fonte_mensal: list[dict[str, str | float]]
    tabela_receita_por_natureza_mensal: list[dict[str, str | float]]
    tabela_consumo_por_categoria_mensal: list[dict[str, str | float]]


@dataclass(frozen=True)
class FluxoJanela:
    janela: PeriodoJanela
    meses: tuple[str, ...]
    receita_total: Decimal
    despesa_total: Decimal
    receita_mensal_media: Decimal
    despesa_mensal_media: Decimal
    despesa_consumo_mensal_media: Decimal
    transferencia_patrimonial_mensal: Decimal
    tabela_receitas_por_fonte_mensal: tuple[TabelaReceitaRow, ...]
    tabela_receita_por_natureza_mensal: tuple[TabelaNaturezaRow, ...]
    tabela_consumo_por_categoria_mensal: tuple[TabelaConsumoRow, ...]

    @property
    def janela_meses(self) -> int:
        return len(self.meses)

    def _scalar_payload(self) -> FluxoJanelaPayload:
        return {
            "janela": self.janela,
            "janela_meses": self.janela_meses,
            "mes_inicio": self.meses[0] if self.meses else None,
            "mes_fim": self.meses[-1] if self.meses else None,
            "receita_total": _wire_number(self.receita_total),
            "despesa_total": _wire_number(self.despesa_total),
            "receita_mensal_media": _wire_number(self.receita_mensal_media),
            "despesa_mensal_media": _wire_number(self.despesa_mensal_media),
            "despesa_consumo_mensal_media": _wire_number(self.despesa_consumo_mensal_media),
            "transferencia_patrimonial_mensal": _wire_number(self.transferencia_patrimonial_mensal),
            "tabela_receitas_por_fonte_mensal": [],
            "tabela_receita_por_natureza_mensal": [],
            "tabela_consumo_por_categoria_mensal": [],
        }

    def to_dict(self) -> FluxoJanelaPayload:
        payload = self._scalar_payload()
        payload["tabela_receitas_por_fonte_mensal"] = [
            row.to_dict() for row in self.tabela_receitas_por_fonte_mensal
        ]
        payload["tabela_receita_por_natureza_mensal"] = [
            row.to_dict() for row in self.tabela_receita_por_natureza_mensal
        ]
        payload["tabela_consumo_por_categoria_mensal"] = [
            row.to_dict() for row in self.tabela_consumo_por_categoria_mensal
        ]
        return payload


def _por_mes(fluxo_mensal: dict, chave: str) -> dict[str, dict[str, Any]]:
    return (fluxo_mensal.get(chave) or {}).get("por_mes") or {}


def _tem_movimento(mes: str, receitas: dict, despesas: dict) -> bool:
    valores = [*(receitas.get(mes) or {}).values(), *(despesas.get(mes) or {}).values()]
    return any(_money(value) != 0 for value in valores)


def _meses_documentados(fluxo_mensal: dict) -> tuple[str, ...]:
    receitas = _por_mes(fluxo_mensal, "receitas")
    despesas = _por_mes(fluxo_mensal, "despesas")
    meses = sorted(set(fluxo_mensal.get("meses_ordenados") or ()))
    return tuple(mes for mes in meses if _tem_movimento(mes, receitas, despesas))


def _seleciona_meses(meses: tuple[str, ...], periodo: PeriodoJanela) -> tuple[str, ...]:
    if not meses:
        return ()
    limite = _LIMITES[periodo]
    if limite is not None:
        return meses[-limite:]
    ano_ancora = meses[-1][:4]
    return tuple(mes for mes in meses if mes.startswith(f"{ano_ancora}-"))


def _totais_mensais(fluxo_mensal: dict, chave: str, meses: tuple[str, ...]) -> Decimal:
    por_mes = _por_mes(fluxo_mensal, chave)
    return sum((_money((por_mes.get(mes) or {}).get("_total")) for mes in meses), Decimal("0"))


def _totais_por_categoria(unified: dict, meses: tuple[str, ...]) -> dict[str, Decimal]:
    selecionados = set(meses)
    out: dict[str, Decimal] = {}
    for categoria, transacoes in (unified.get("dados") or {}).items():
        total = sum(
            (
                _money(tx.get("valor"))
                for tx in transacoes
                if str(tx.get("data") or "")[:7] in selecionados
            ),
            Decimal("0"),
        )
        if total > 0:
            out[str(categoria)] = total
    return out


def _totais_despesa_categoria(fluxo_mensal: dict, meses: tuple[str, ...]) -> dict[str, Decimal]:
    por_mes = _por_mes(fluxo_mensal, "despesas")
    categorias = {key for mes in meses for key in (por_mes.get(mes) or {}) if key != "_total"}
    return {
        categoria: sum(
            (_money((por_mes.get(mes) or {}).get(categoria)) for mes in meses), Decimal("0")
        )
        for categoria in sorted(categorias)
        if any(_money((por_mes.get(mes) or {}).get(categoria)) > 0 for mes in meses)
    }


def _media_total(total: Decimal, meses: int) -> Decimal:
    if meses == 0:
        return Decimal("0.00")
    return _from_cents(_cents(total / Decimal(meses)))


def _medias_alocadas(totais: dict[str, Decimal], meses: int) -> dict[str, Decimal]:
    if not totais or meses == 0:
        return {}
    cents = {key: _cents(value) for key, value in totais.items()}
    floors = {key: value // meses for key, value in cents.items()}
    alvo = _cents(sum(totais.values(), Decimal("0")) / Decimal(meses))
    faltantes = alvo - sum(floors.values())
    ordem = sorted(cents, key=lambda key: (-(cents[key] % meses), -cents[key], key))
    for key in ordem[:faltantes]:
        floors[key] += 1
    return {key: _from_cents(value) for key, value in floors.items()}


def _basis_points(totais: dict[str, Decimal]) -> dict[str, int]:
    cents = {key: _cents(value) for key, value in totais.items() if value > 0}
    total = sum(cents.values())
    if total == 0:
        return {}
    floors = {key: value * 10_000 // total for key, value in cents.items()}
    faltantes = 10_000 - sum(floors.values())
    ordem = sorted(cents, key=lambda key: (-(cents[key] * 10_000 % total), -cents[key], key))
    for key in ordem[:faltantes]:
        floors[key] += 1
    return floors


def _ordenadas(totais: dict[str, Decimal]) -> list[str]:
    return sorted(
        (key for key, value in totais.items() if value > 0), key=lambda key: (-totais[key], key)
    )


def _receita_rows(totais: dict[str, Decimal], meses: int) -> tuple[TabelaReceitaRow, ...]:
    medias = _medias_alocadas(totais, meses)
    bps = _basis_points(totais)
    return tuple(
        TabelaReceitaRow(key, totais[key], medias[key], Decimal(bps[key]) / 100)
        for key in _ordenadas(totais)
    )


def _natureza_totais(totais: dict[str, Decimal], total: Decimal) -> dict[str, Decimal]:
    pj = sum((totais.get(key, Decimal("0")) for key in _RECEITA_PJ), Decimal("0"))
    clt = totais.get("receita_clt", Decimal("0"))
    aluguel = totais.get("receita_aluguel", Decimal("0"))
    return {
        "receita_pj": pj,
        "receita_clt": clt,
        "receita_aluguel": aluguel,
        "receita_outras": total - pj - clt - aluguel,
    }


def _natureza_rows(totais: dict[str, Decimal], meses: int) -> tuple[TabelaNaturezaRow, ...]:
    medias = _medias_alocadas(totais, meses)
    bps = _basis_points(totais)
    return tuple(
        TabelaNaturezaRow(key, totais[key], medias[key], Decimal(bps[key]) / 100)
        for key in _ordenadas(totais)
    )


def _consumo_rows(totais: dict[str, Decimal], meses: int) -> tuple[TabelaConsumoRow, ...]:
    medias = _medias_alocadas(totais, meses)
    bps = _basis_points(totais)
    acumulado = 0
    rows: list[TabelaConsumoRow] = []
    for key in _ordenadas(totais):
        acumulado += bps[key]
        rows.append(
            TabelaConsumoRow(
                key, totais[key], medias[key], Decimal(bps[key]) / 100, Decimal(acumulado) / 100
            )
        )
    return tuple(rows)


@dataclass(frozen=True)
class _JanelaRequest:
    periodo: PeriodoJanela
    meses: tuple[str, ...]
    receitas: dict
    fluxo_mensal: dict
    transfer_categories: frozenset[str]


@dataclass(frozen=True)
class _JanelaValues:
    request: _JanelaRequest
    receita_total: Decimal
    despesa_total: Decimal
    despesa_media: Decimal
    consumo_media: Decimal
    receitas_categoria: dict[str, Decimal]
    natureza: dict[str, Decimal]
    consumo: dict[str, Decimal]


def _consumo_metrics(
    fluxo_mensal: dict,
    meses: tuple[str, ...],
    transfer_categories: frozenset[str],
    despesa_total: Decimal,
) -> tuple[dict[str, Decimal], Decimal, Decimal]:
    categorias = _totais_despesa_categoria(fluxo_mensal, meses)
    consumo = {key: value for key, value in categorias.items() if key not in transfer_categories}
    despesa_media = _media_total(despesa_total, len(meses))
    consumo_media = _media_total(sum(consumo.values(), Decimal("0")), len(meses))
    return consumo, despesa_media, consumo_media


def _assemble_janela(values: _JanelaValues) -> FluxoJanela:
    meses = values.request.meses
    return FluxoJanela(
        values.request.periodo,
        meses,
        values.receita_total,
        values.despesa_total,
        _media_total(values.receita_total, len(meses)),
        values.despesa_media,
        values.consumo_media,
        values.despesa_media - values.consumo_media,
        _receita_rows(values.receitas_categoria, len(meses)),
        _natureza_rows(values.natureza, len(meses)),
        _consumo_rows(values.consumo, len(meses)),
    )


def _build_janela(request: _JanelaRequest) -> FluxoJanela:
    receita_total = _totais_mensais(request.fluxo_mensal, "receitas", request.meses)
    despesa_total = _totais_mensais(request.fluxo_mensal, "despesas", request.meses)
    receitas_categoria = _totais_por_categoria(request.receitas, request.meses)
    consumo, despesa_media, consumo_media = _consumo_metrics(
        request.fluxo_mensal, request.meses, request.transfer_categories, despesa_total
    )
    natureza = _natureza_totais(receitas_categoria, receita_total)
    values = _JanelaValues(
        request,
        receita_total,
        despesa_total,
        despesa_media,
        consumo_media,
        receitas_categoria,
        natureza,
        consumo,
    )
    return _assemble_janela(values)


def build_fluxo_janelas(
    receitas: dict,
    fluxo_mensal: dict,
    transfer_categories: frozenset[str],
) -> dict[PeriodoJanela, FluxoJanela]:
    """Precomputa as quatro seleções fechadas sobre os meses documentados."""
    documentados = _meses_documentados(fluxo_mensal)
    return {
        periodo: _build_janela(
            _JanelaRequest(
                periodo,
                _seleciona_meses(documentados, periodo),
                receitas,
                fluxo_mensal,
                transfer_categories,
            )
        )
        for periodo in PERIODOS_JANELA
    }
