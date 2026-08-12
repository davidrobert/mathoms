"""Corte de provisionado no E5: transação com ``data`` posterior ao ``data_corte``
sai dos agregados realizados e vira bloco irmão ``provisionado``.

O corte é **só do E5**. E3/E4 seguem sendo o ledger — um JCP provisionado existe,
é direito do usuário e continua em ``GET /transactions``. O que ele não pode é
esticar a série mensal para o futuro: o card que ancora a janela no último label
passava a dividir receita de 2 meses por 3.

Zero-behavior quando não há transação futura: os dicts do E4 voltam por
identidade (nenhuma re-soma de float), então diff de golden é atribuível só ao
corte.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_CENTAVO = Decimal("0.01")


def _dec(value: Any) -> Decimal:
    """Converte valor do wire (JSON number) em Decimal sem passar por float."""
    try:
        return Decimal(str(value if value is not None else 0))
    except (ArithmeticError, ValueError):
        return Decimal("0")


def _as_float(value: Decimal) -> float:
    """Serializa no wire do E4/E5 (JSON number, 2 casas — ADR-090 §consequências)."""
    return float(value.quantize(_CENTAVO, rounding=ROUND_HALF_UP))


def _soma(transacoes: list[dict]) -> Decimal:
    total = sum((_dec(t.get("valor")) for t in transacoes), Decimal("0"))
    return total.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def _e_futura(transacao: dict, corte_iso: str) -> bool:
    """``YYYY-MM-DD`` ordena lexicograficamente == cronologicamente; sem data, fica."""
    return str(transacao.get("data") or "")[:10] > corte_iso


def _mes(transacao: dict) -> str:
    return str(transacao.get("data") or "")[:7]


@dataclass(frozen=True)
class ProvisionadoBlock:
    """Agregado das transações futuras — fora de qualquer janela e de ``por_fonte``."""

    data_corte: str
    receita: Decimal
    despesa: Decimal
    por_fonte: dict[str, Decimal]
    por_categoria: dict[str, Decimal]
    transacoes: int
    primeiro_mes: str | None
    ultimo_mes: str | None

    def to_dict(self) -> dict:
        return {
            "data_corte": self.data_corte,
            "receita_brl": _as_float(self.receita),
            "despesa_brl": _as_float(self.despesa),
            "por_fonte": {k: _as_float(v) for k, v in self.por_fonte.items()},
            "por_categoria": {k: _as_float(v) for k, v in self.por_categoria.items()},
            "transacoes": self.transacoes,
            "primeiro_mes": self.primeiro_mes,
            "ultimo_mes": self.ultimo_mes,
        }


@dataclass(frozen=True)
class FluxoRealizado:
    """Dicts do E4 já sem o provisionado + o bloco que saiu."""

    receitas: dict
    despesas: dict
    fluxo_mensal: dict
    provisionado: ProvisionadoBlock | None


def _futuras_por_categoria(unified: dict | None, corte_iso: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for categoria, transacoes in ((unified or {}).get("dados") or {}).items():
        futuras = [t for t in (transacoes or []) if _e_futura(t, corte_iso)]
        if futuras:
            out[categoria] = futuras
    return out


def _build_block(
    corte_iso: str,
    futuras_receita: dict[str, list[dict]],
    futuras_despesa: dict[str, list[dict]],
) -> ProvisionadoBlock:
    por_fonte = {cat: _soma(txs) for cat, txs in sorted(futuras_receita.items())}
    por_categoria = {cat: _soma(txs) for cat, txs in sorted(futuras_despesa.items())}
    todas = [t for txs in (*futuras_receita.values(), *futuras_despesa.values()) for t in txs]
    meses = sorted({_mes(t) for t in todas if t.get("data")})
    return ProvisionadoBlock(
        data_corte=corte_iso,
        # Soma das partes já quantizadas: garante `receita_brl == Σ por_fonte` em cents.
        receita=sum(por_fonte.values(), Decimal("0")),
        despesa=sum(por_categoria.values(), Decimal("0")),
        por_fonte=por_fonte,
        por_categoria=por_categoria,
        transacoes=len(todas),
        primeiro_mes=meses[0] if meses else None,
        ultimo_mes=meses[-1] if meses else None,
    )


def _periodo(dados: dict[str, list[dict]]) -> str:
    meses = sorted({_mes(t) for txs in dados.values() for t in txs if t.get("data")})
    return f"{meses[0]} a {meses[-1]}" if meses else "N/D"


def _categoria_pos_corte(valor_original: Any, futuras: list[dict]) -> Any:
    """Categoria intocada devolve o valor original — re-somar float introduziria drift."""
    if not futuras:
        return valor_original
    return _as_float(_dec(valor_original) - _soma(futuras))


def _categorias_sem_futuras(
    unified: dict | None, corte_iso: str
) -> tuple[dict[str, list[dict]], dict[str, Any]]:
    totais_in = (unified or {}).get("totais_por_categoria") or {}
    dados_out: dict[str, list[dict]] = {}
    totais_out: dict[str, Any] = {}
    for categoria, transacoes in ((unified or {}).get("dados") or {}).items():
        futuras = [t for t in (transacoes or []) if _e_futura(t, corte_iso)]
        restantes = [t for t in (transacoes or []) if not _e_futura(t, corte_iso)]
        if not restantes:
            continue
        dados_out[categoria] = restantes
        totais_out[categoria] = _categoria_pos_corte(totais_in.get(categoria, 0), futuras)
    return dados_out, totais_out


def _sem_futuras(unified: dict | None, corte_iso: str) -> dict:
    """Reconstrói ``receitas``/``despesas`` unified sem as transações futuras."""
    dados_out, totais_out = _categorias_sem_futuras(unified, corte_iso)
    out = dict(unified or {})
    out["dados"] = dados_out
    out["totais_por_categoria"] = totais_out
    out["total_geral"] = _as_float(sum((_dec(v) for v in totais_out.values()), Decimal("0")))
    out["total_transacoes"] = sum(len(txs) for txs in dados_out.values())
    out["categorias"] = sorted(dados_out)
    out["total_categorias"] = len(dados_out)
    out["periodo"] = _periodo(dados_out)
    return out


def _descontos(futuras: dict[str, list[dict]], chave: str) -> dict[tuple[str, str], Decimal]:
    """``(mes, origem|categoria) -> valor futuro`` — a granularidade do ``por_mes`` do E4."""
    out: dict[tuple[str, str], Decimal] = {}
    datadas = (t for txs in futuras.values() for t in txs if t.get("data"))
    for t in datadas:
        k = (_mes(t), str(t.get(chave) or ""))
        out[k] = out.get(k, Decimal("0")) + _dec(t.get("valor"))
    return out


def _mes_descontado(entradas: dict, mes: str, descontos: dict[tuple[str, str], Decimal]) -> dict:
    out = dict(entradas)
    for chave, valor in ((k[1], v) for k, v in descontos.items() if k[0] == mes):
        out[chave] = _as_float(_dec(out.get(chave, 0)) - valor)
    total = sum((_dec(v) for k, v in out.items() if k != "_total"), Decimal("0"))
    out["_total"] = _as_float(total)
    return out


def _bloco_mensal(bloco: dict | None, meses: list[str], descontos: dict) -> dict:
    """Aplica os descontos mês a mês; mês sem desconto sai por identidade."""
    por_mes_in = (bloco or {}).get("por_mes") or {}
    meses_tocados = {mes for mes, _ in descontos}
    por_mes = {
        mes: (
            _mes_descontado(por_mes_in.get(mes) or {}, mes, descontos)
            if mes in meses_tocados
            else (por_mes_in.get(mes) or {})
        )
        for mes in meses
    }
    out = dict(bloco or {})
    out["por_mes"] = por_mes
    return out


def _fluxo_sem_futuras(
    fluxo_mensal: dict | None,
    meses: list[str],
    futuras_receita: dict[str, list[dict]],
    futuras_despesa: dict[str, list[dict]],
) -> dict:
    out = dict(fluxo_mensal or {})
    out["meses_ordenados"] = meses
    out["receitas"] = _bloco_mensal(
        (fluxo_mensal or {}).get("receitas"), meses, _descontos(futuras_receita, "origem")
    )
    out["despesas"] = _bloco_mensal(
        (fluxo_mensal or {}).get("despesas"), meses, _descontos(futuras_despesa, "categoria")
    )
    out["periodo"] = f"{meses[0]} a {meses[-1]}" if meses else "N/D"
    return out


def _meses_realizados(*unifieds: dict) -> list[str]:
    meses = {
        _mes(t)
        for unified in unifieds
        for transacoes in (unified.get("dados") or {}).values()
        for t in transacoes
        if t.get("data")
    }
    return sorted(meses)


def _corta(
    receitas: dict | None,
    despesas: dict | None,
    fluxo_mensal: dict | None,
    corte_iso: str,
    futuras_receita: dict[str, list[dict]],
    futuras_despesa: dict[str, list[dict]],
) -> tuple[dict, dict, dict]:
    receitas_ok = _sem_futuras(receitas, corte_iso)
    despesas_ok = _sem_futuras(despesas, corte_iso)
    meses = _meses_realizados(receitas_ok, despesas_ok)
    fluxo_ok = _fluxo_sem_futuras(fluxo_mensal, meses, futuras_receita, futuras_despesa)
    return receitas_ok, despesas_ok, fluxo_ok


def split_provisionado(
    receitas: dict | None,
    despesas: dict | None,
    fluxo_mensal: dict | None,
    *,
    data_corte: date | None,
) -> FluxoRealizado:
    """Separa realizado × provisionado; ``data_corte=None`` devolve tudo por identidade."""
    if data_corte is None:
        return FluxoRealizado(receitas or {}, despesas or {}, fluxo_mensal or {}, None)
    corte_iso = data_corte.isoformat()
    futuras_receita = _futuras_por_categoria(receitas, corte_iso)
    futuras_despesa = _futuras_por_categoria(despesas, corte_iso)
    bloco = _build_block(corte_iso, futuras_receita, futuras_despesa)
    if bloco.transacoes == 0:
        return FluxoRealizado(receitas or {}, despesas or {}, fluxo_mensal or {}, bloco)
    cortado = _corta(receitas, despesas, fluxo_mensal, corte_iso, futuras_receita, futuras_despesa)
    return FluxoRealizado(*cortado, bloco)
