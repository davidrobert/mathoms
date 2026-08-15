"""Parsers compartilhados FiscalParameter row ↔ dataclass (A7.2b · ADR-135)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.types.config import FiscalParameters, IRPFBracket, TabelaProgressiva


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _date_or_none(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def fiscal_row_to_payload(row: Any) -> dict[str, Any]:
    """SQLAlchemy ``FiscalParameter`` → dict cacheável em Redis."""
    return {
        "year": int(row.year),
        "ir_brackets_anual": dict(row.ir_brackets_anual or {}),
        "ir_brackets_mensal": dict(row.ir_brackets_mensal or {}),
        "regime_completo": bool(row.regime_completo),
        "componentes_ausentes": list(row.componentes_ausentes or []),
        "pgbl_limit_brl_cents": int(row.pgbl_limit_brl_cents),
        "inss_ceiling_brl_cents": int(row.inss_ceiling_brl_cents),
        "lucro_presumido_aliquota": str(row.lucro_presumido_aliquota),
        "effective_from": row.effective_from.isoformat() if row.effective_from else None,
        "effective_to": row.effective_to.isoformat() if row.effective_to else None,
        "source": str(row.source or ""),
    }


class TabelaProgressivaMalformada(ValueError):
    """Payload de tabela sem chave obrigatória — defeito de dado, não de negócio."""


# Fail-closed em três frentes, e a mais perigosa NÃO era o `or 0` que a ADR-389
# nomeia. `upper_brl_cents` ausente virava `None`, e `None` é a faixa TERMINAL:
# `resolve_faixa_marginal` retorna na primeira, truncando a tabela e aplicando
# uma alíquota errada a TODA renda. Chave ausente agora levanta; item que não é
# Mapping também, em vez de ser pulado em silêncio.
def _bracket(raw: Any, indice: int) -> IRPFBracket:
    if not isinstance(raw, Mapping):
        raise TabelaProgressivaMalformada(
            f"faixa {indice} não é objeto: {type(raw).__name__}={raw!r}"
        )
    faltando = {"upper_brl_cents", "aliquota_pct", "deducao_brl_cents"} - set(raw)
    if faltando:
        raise TabelaProgressivaMalformada(
            f"faixa {indice} sem {sorted(faltando)}; recebido {sorted(raw)}"
        )
    upper = raw["upper_brl_cents"]
    return IRPFBracket(
        upper_brl_cents=int(upper) if upper is not None else None,
        aliquota_pct=_decimal(raw["aliquota_pct"]),
        deducao_brl_cents=int(raw["deducao_brl_cents"]),
    )


def _payload_brackets(brackets_raw: Any) -> tuple[IRPFBracket, ...]:
    return tuple(_bracket(raw, i) for i, raw in enumerate(brackets_raw or []))


def _payload_tabela(raw: Any) -> TabelaProgressiva:
    """Container de tabela → :class:`TabelaProgressiva`; ausência é tabela vazia."""
    if not isinstance(raw, Mapping):
        return TabelaProgressiva()
    return TabelaProgressiva(
        faixas=_payload_brackets(raw.get("faixas")),
        vigencia_ref=str(raw.get("vigencia_ref") or ""),
        source=str(raw.get("source") or ""),
        motivo_divergencia_x12=str(raw.get("motivo_divergencia_x12") or ""),
    )


def fiscal_payload_to_dataclass(payload: Mapping[str, Any]) -> FiscalParameters:
    """Dict (cache ou seed) → :class:`FiscalParameters` frozen."""
    return FiscalParameters(
        year=int(payload.get("year") or 0),
        pgbl_limit_brl_cents=int(payload.get("pgbl_limit_brl_cents") or 0),
        inss_ceiling_brl_cents=int(payload.get("inss_ceiling_brl_cents") or 0),
        lucro_presumido_aliquota=_decimal(payload.get("lucro_presumido_aliquota")),
        ir_brackets_anual=_payload_tabela(payload.get("ir_brackets_anual")),
        ir_brackets_mensal=_payload_tabela(payload.get("ir_brackets_mensal")),
        regime_completo=bool(payload.get("regime_completo", True)),
        componentes_ausentes=tuple(payload.get("componentes_ausentes") or ()),
        effective_from=_date_or_none(payload.get("effective_from")),
        effective_to=_date_or_none(payload.get("effective_to")),
        source=str(payload.get("source") or ""),
    )
