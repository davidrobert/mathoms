"""Baseline ← Informe PF merger — A17 L3 P3 (ADR-238 D5; PTAX injetado via callable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Optional

# CBE BACEN: declaração obrigatória se total ativos exterior > USD 1MM
# (Circular 3.624/2013). Fora do escopo Mathoms — só warning em E5.
_CBE_USD_THRESHOLD: Decimal = Decimal("1000000")

#: Tipo da função opcional de cotação. `(moeda, ano_base) → Decimal | None`.
PtaxGetter = Callable[[str, int], Optional[Decimal]]


def _to_decimal(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


@dataclass(frozen=True)
class BaselineMergeResult:
    """Resultado do merge — baseline enriched + telemetria + warnings (ADR-238 D5)."""

    baseline: dict
    informes_processed: int = 0
    saldos_added: int = 0
    warnings: list[str] = field(default_factory=list)


class BaselineInformeMerger:
    """Anexa `informe_pf_saldos_31_12[]` ao baseline (ADR-238 D5 + D1 Wise multi-moeda)."""

    def __init__(self, ptax_getter: Optional[PtaxGetter] = None) -> None:
        # ptax_getter=None → conversão graceful: saldo_brl ausente, warning emitido.
        self._ptax: PtaxGetter = ptax_getter or (lambda _m, _a: None)

    def merge(self, baseline: dict, informes: list[dict]) -> BaselineMergeResult:
        """Anexa saldos_31_12 dos informes ao baseline; preserva entries existentes."""
        novas_entradas: list[dict] = []
        warnings: list[str] = []
        total_exterior_usd: Decimal = Decimal("0")
        for informe in informes:
            entradas, ws, usd_exterior = self._process_informe(informe)
            novas_entradas.extend(entradas)
            warnings.extend(ws)
            total_exterior_usd += usd_exterior
        if total_exterior_usd > _CBE_USD_THRESHOLD:
            warnings.append(_cbe_warning(total_exterior_usd))
        baseline_out = {**baseline, "informe_pf_saldos_31_12": novas_entradas}
        return BaselineMergeResult(
            baseline=baseline_out,
            informes_processed=len(informes),
            saldos_added=len(novas_entradas),
            warnings=warnings,
        )

    def _process_informe(self, informe: dict) -> tuple[list[dict], list[str], Decimal]:
        """Processa 1 informe — retorna (entradas, warnings, usd_exterior_acumulado)."""
        payload = informe.get("financeiro_pf") or {}
        ano_base = int(informe.get("ano_base", 0))
        cnpj_emissor = payload.get("cnpj_emissor", "")
        entradas, warnings = [], []
        usd_exterior = Decimal("0")
        for s in payload.get("saldos_31_12") or []:
            entry, w = self._process_saldo(s, ano_base, cnpj_emissor)
            entradas.append(entry)
            warnings.extend(w)
            usd_exterior += _exterior_usd_or_zero(s)
        return entradas, warnings, usd_exterior

    def _process_saldo(
        self, saldo: dict, ano_base: int, cnpj_emissor: str
    ) -> tuple[dict, list[str]]:
        """Constrói entry enriched com saldo_brl via PTAX (graceful se ausente)."""
        moeda = saldo.get("moeda", "BRL")
        valor = _to_decimal(saldo.get("saldo"))
        saldo_brl, taxa, warnings = self._convert_to_brl(valor, moeda, ano_base, saldo)
        entry = _build_entry(saldo, ano_base, cnpj_emissor, valor, saldo_brl, taxa)
        return entry, warnings

    def _convert_to_brl(
        self, valor: Decimal, moeda: str, ano_base: int, saldo: dict
    ) -> tuple[Optional[Decimal], Optional[Decimal], list[str]]:
        """Aplica PTAX 31/12 do ano_base. Graceful: PTAX ausente → (None, None, warning)."""
        if moeda == "BRL":
            return valor, Decimal("1"), []
        taxa = self._ptax(moeda, ano_base)
        if taxa is None:
            return None, None, [_ptax_missing_warning(moeda, ano_base, saldo)]
        return valor * taxa, taxa, []


# ─────────────────────── helpers (pure) ─────────────────────────────────────


_TWO_PLACES = Decimal("0.01")


def _money_str(v: Decimal) -> str:
    """Quantize Decimal monetário para 2 casas (ADR-090 wire format)."""
    return str(v.quantize(_TWO_PLACES))


def _build_entry(
    saldo: dict,
    ano_base: int,
    cnpj_emissor: str,
    valor: Decimal,
    saldo_brl: Optional[Decimal] = None,
    taxa: Optional[Decimal] = None,
) -> dict:
    """Entry shape consumido por E5 narrativas / S4 UI (ADR-238 D5)."""
    fields_origem = {k: saldo.get(k, default) for k, default in _ENTRY_FIELDS_FROM_SALDO.items()}
    return {
        "ano_base": ano_base,
        "cnpj_emissor": cnpj_emissor,
        **fields_origem,
        "saldo_original": _money_str(valor),
        "saldo_brl": _money_str(saldo_brl) if saldo_brl is not None else None,
        "taxa_ptax_aplicada": str(taxa) if taxa is not None else None,
        "ptax_status": "applied" if saldo_brl is not None else "missing",
    }


_ENTRY_FIELDS_FROM_SALDO: dict[str, str] = {
    "tipo": "outros",
    "descricao": "",
    "codigo_rfb": "",
    "fonte_pagadora_cnpj": "",
    "moeda": "BRL",
}


def _exterior_usd_or_zero(saldo: dict) -> Decimal:
    """Soma USD para tracker CBE BACEN — só conta exterior em USD."""
    if saldo.get("moeda") != "USD":
        return Decimal("0")
    if saldo.get("tipo") != "conta_exterior":
        return Decimal("0")
    return _to_decimal(saldo.get("saldo"))


def _cbe_warning(total_usd: Decimal) -> str:
    return (
        f"CBE BACEN: total ativos exterior USD {total_usd:.2f} > limite USD 1MM "
        f"(Circular 3.624/2013) — obrigação declaratória BACEN fora do escopo Mathoms."
    )


def _ptax_missing_warning(moeda: str, ano_base: int, saldo: dict) -> str:
    desc = saldo.get("descricao", "")[:50]
    return (
        f"PTAX {moeda}/BRL ausente para 31/12/{ano_base} ({desc}). "
        f"saldo_brl ficou None — workspace deve fornecer cotação ou aceitar saldo em moeda original."
    )
