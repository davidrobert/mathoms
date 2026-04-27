"""Parsers compartilhados para ``FiscalParameters`` (A7.2b · ADR-135).

Conversões usadas pelos adapters do ``ConfigStore``:

- ``fiscal_row_to_payload``: SQLAlchemy ``FiscalParameter`` → dict serializável
  (cacheável em Redis). Não importa SQLAlchemy aqui — usado pelo adapter DB
  via duck typing.
- ``fiscal_payload_to_dataclass``: dict → :class:`FiscalParameters` frozen.
- ``legacy_json_to_fiscal``: dict no shape de ``parametros_fiscais.json`` →
  :class:`FiscalParameters` (bridge ``FileConfigStore`` até A7.5).

Pipeline domain consome apenas :class:`FiscalParameters` typed; nunca dict
ou Path (ADR-097/D2).
"""

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


def fiscal_payload_to_dataclass(payload: Mapping[str, Any]) -> FiscalParameters:
    """Dict (cache ou seed) → :class:`FiscalParameters` frozen."""
    brackets_raw = payload.get("ir_brackets") or []
    brackets: list[IRPFBracket] = []
    for raw in brackets_raw:
        if not isinstance(raw, Mapping):
            continue
        upper = raw.get("upper_brl_cents")
        upper_cents = int(upper) if upper is not None else None
        brackets.append(
            IRPFBracket(
                upper_brl_cents=upper_cents,
                aliquota_pct=_decimal(raw.get("aliquota_pct")),
                deducao_brl_cents=int(raw.get("deducao_brl_cents") or 0),
            )
        )
    return FiscalParameters(
        year=int(payload.get("year") or 0),
        pgbl_limit_brl_cents=int(payload.get("pgbl_limit_brl_cents") or 0),
        inss_ceiling_brl_cents=int(payload.get("inss_ceiling_brl_cents") or 0),
        lucro_presumido_aliquota=_decimal(payload.get("lucro_presumido_aliquota")),
        ir_brackets=tuple(brackets),
        effective_from=_date_or_none(payload.get("effective_from")),
        effective_to=_date_or_none(payload.get("effective_to")),
        source=str(payload.get("source") or ""),
    )


def legacy_json_to_fiscal(
    data: Mapping[str, Any],
    *,
    year: int,
    source: str = "config/parametros_fiscais.json (FileConfigStore bridge)",
) -> FiscalParameters:
    """``config/parametros_fiscais.json`` → :class:`FiscalParameters`.

    Bridge para ``FileConfigStore`` até A7.5. Tabela IRPF do JSON tem
    alíquotas em pct (já formatado) — converte para Decimal sem mudança
    de magnitude. ``deducao_brl_cents`` não existe no JSON antigo
    (default 0); precisa ser populado via seed do DB.
    """
    irpf_block = data.get("irpf_tabela_progressiva") or {}
    faixas_raw = irpf_block.get("faixas") or []
    brackets: list[IRPFBracket] = []
    for raw in faixas_raw:
        if not isinstance(raw, Mapping):
            continue
        upper_anual = raw.get("limite_anual")
        upper_cents = _to_cents(upper_anual) if upper_anual is not None else None
        brackets.append(
            IRPFBracket(
                upper_brl_cents=upper_cents,
                aliquota_pct=_decimal(raw.get("aliquota_pct")),
                deducao_brl_cents=0,
            )
        )

    pgbl_block = data.get("pgbl") or {}
    pgbl_limit_pct = _decimal(pgbl_block.get("limite_deducao_pct") or 0)
    # Legacy JSON expressa PGBL como % da renda — não há limite absoluto
    # no JSON, então grava 0 cents para sinalizar "calcular via pct".
    pgbl_limit_cents = 0
    del pgbl_limit_pct  # marker — semântica preservada via aliquota se reusarmos

    lp_block = data.get("lucro_presumido") or {}
    lp_pct = _decimal(lp_block.get("percentual_servicos_pct") or 0)
    lp_aliquota = lp_pct / Decimal("100") if lp_pct else Decimal("0")

    return FiscalParameters(
        year=year,
        pgbl_limit_brl_cents=pgbl_limit_cents,
        inss_ceiling_brl_cents=0,
        lucro_presumido_aliquota=lp_aliquota,
        ir_brackets=tuple(brackets),
        effective_from=date(year, 1, 1),
        effective_to=date(year, 12, 31),
        source=source,
    )
