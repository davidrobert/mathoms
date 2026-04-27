"""Parsers compartilhados FiscalParameter row ↔ dataclass ↔ legacy JSON (A7.2b · ADR-135)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.types.config import FiscalParameters, IRPFBracket


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _to_cents(value: Any) -> int:
    """Converte valor BRL (float ou string) para int cents."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return int((Decimal(str(value)) * 100).quantize(Decimal("1")))


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
        "ir_brackets": list(row.ir_brackets or []),
        "pgbl_limit_brl_cents": int(row.pgbl_limit_brl_cents),
        "inss_ceiling_brl_cents": int(row.inss_ceiling_brl_cents),
        "lucro_presumido_aliquota": str(row.lucro_presumido_aliquota),
        "effective_from": row.effective_from.isoformat() if row.effective_from else None,
        "effective_to": row.effective_to.isoformat() if row.effective_to else None,
        "source": str(row.source or ""),
    }


def _payload_brackets(brackets_raw: list) -> tuple[IRPFBracket, ...]:
    out: list[IRPFBracket] = []
    for raw in brackets_raw:
        if not isinstance(raw, Mapping):
            continue
        upper = raw.get("upper_brl_cents")
        out.append(
            IRPFBracket(
                upper_brl_cents=int(upper) if upper is not None else None,
                aliquota_pct=_decimal(raw.get("aliquota_pct")),
                deducao_brl_cents=int(raw.get("deducao_brl_cents") or 0),
            )
        )
    return tuple(out)


def fiscal_payload_to_dataclass(payload: Mapping[str, Any]) -> FiscalParameters:
    """Dict (cache ou seed) → :class:`FiscalParameters` frozen."""
    return FiscalParameters(
        year=int(payload.get("year") or 0),
        pgbl_limit_brl_cents=int(payload.get("pgbl_limit_brl_cents") or 0),
        inss_ceiling_brl_cents=int(payload.get("inss_ceiling_brl_cents") or 0),
        lucro_presumido_aliquota=_decimal(payload.get("lucro_presumido_aliquota")),
        ir_brackets=_payload_brackets(payload.get("ir_brackets") or []),
        effective_from=_date_or_none(payload.get("effective_from")),
        effective_to=_date_or_none(payload.get("effective_to")),
        source=str(payload.get("source") or ""),
    )


def _legacy_brackets(faixas_raw: list) -> tuple[IRPFBracket, ...]:
    out: list[IRPFBracket] = []
    for raw in faixas_raw:
        if not isinstance(raw, Mapping):
            continue
        upper_anual = raw.get("limite_anual")
        upper_cents = _to_cents(upper_anual) if upper_anual is not None else None
        out.append(
            IRPFBracket(
                upper_brl_cents=upper_cents,
                aliquota_pct=_decimal(raw.get("aliquota_pct")),
                deducao_brl_cents=0,
            )
        )
    return tuple(out)


_DEFAULT_LEGACY_SOURCE = "config/parametros_fiscais.json (FileConfigStore bridge)"


def legacy_json_to_fiscal(
    data: Mapping[str, Any], *, year: int, source: str = _DEFAULT_LEGACY_SOURCE
) -> FiscalParameters:
    """``config/parametros_fiscais.json`` → :class:`FiscalParameters` (bridge A7.5)."""
    brackets = _legacy_brackets((data.get("irpf_tabela_progressiva") or {}).get("faixas") or [])
    lp_pct = _decimal((data.get("lucro_presumido") or {}).get("percentual_servicos_pct") or 0)
    return FiscalParameters(
        year=year,
        pgbl_limit_brl_cents=0,  # legacy JSON expressa PGBL via pct, não absoluto
        inss_ceiling_brl_cents=0,
        lucro_presumido_aliquota=(lp_pct / Decimal("100")) if lp_pct else Decimal("0"),
        ir_brackets=brackets,
        effective_from=date(year, 1, 1),
        effective_to=date(year, 12, 31),
        source=source,
    )
