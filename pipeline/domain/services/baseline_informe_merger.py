"""Baseline ← Informe PF merger — A17 L3 P3+P5 (ADR-238 D5; PTAX injetado via callable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Optional

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
    """Resultado do merge — baseline + telemetria; `fiscal_flags` é estruturado (ADR-238 D5+P5)."""

    baseline: dict
    informes_processed: int = 0
    saldos_added: int = 0
    warnings: list[str] = field(default_factory=list)
    fiscal_flags: list = field(default_factory=list)  # list[FiscalFlag]


class BaselineInformeMerger:
    """Anexa `informe_pf_saldos_31_12[]` ao baseline (ADR-238 D5 + D1 Wise multi-moeda)."""

    def __init__(self, ptax_getter: Optional[PtaxGetter] = None) -> None:
        # ptax_getter=None → conversão graceful: saldo_brl ausente, warning emitido.
        self._ptax: PtaxGetter = ptax_getter or (lambda _m, _a: None)

    def merge(self, baseline: dict, informes: list[dict]) -> BaselineMergeResult:
        """Anexa saldos_31_12 + fiscal_flags Wise (A17 L3 P5) ao baseline; preserva entries."""
        novas_entradas, warnings, fiscal_flags = self._collect(informes)
        warnings.extend(f.descricao for f in fiscal_flags)
        baseline_out = {
            **baseline,
            "informe_pf_saldos_31_12": novas_entradas,
            "wise_fiscal_flags": [_flag_to_dict(f) for f in fiscal_flags],
        }
        return BaselineMergeResult(
            baseline=baseline_out,
            informes_processed=len(informes),
            saldos_added=len(novas_entradas),
            warnings=warnings,
            fiscal_flags=fiscal_flags,
        )

    def _collect(self, informes: list[dict]) -> tuple[list[dict], list[str], list]:
        """Itera informes coletando (entradas, warnings, fiscal_flags) — separa loop de merge."""
        from pipeline.domain.services.wise_fiscal_flags import detect_all_wise_flags

        novas_entradas: list[dict] = []
        warnings: list[str] = []
        fiscal_flags: list = []
        for informe in informes:
            entradas, ws = self._process_informe(informe)
            novas_entradas.extend(entradas)
            warnings.extend(ws)
            fiscal_flags.extend(detect_all_wise_flags(informe.get("financeiro_pf") or {}))
        return novas_entradas, warnings, fiscal_flags

    def _process_informe(self, informe: dict) -> tuple[list[dict], list[str]]:
        """Processa 1 informe — retorna (entradas, warnings de PTAX faltante)."""
        payload = informe.get("financeiro_pf") or {}
        ano_base = int(informe.get("ano_base", 0))
        cnpj_emissor = payload.get("cnpj_emissor", "")
        entradas, warnings = [], []
        for s in payload.get("saldos_31_12") or []:
            entry, w = self._process_saldo(s, ano_base, cnpj_emissor)
            entradas.append(entry)
            warnings.extend(w)
        return entradas, warnings

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


def _flag_to_dict(flag) -> dict:
    """Serializa FiscalFlag → dict para persistência no baseline (A17 L3 P5)."""
    return {
        "code": flag.code,
        "severity": flag.severity,
        "title": flag.title,
        "descricao": flag.descricao,
        "codigo_rfb": flag.codigo_rfb,
        "valor_brl": str(flag.valor_brl) if flag.valor_brl is not None else None,
        "valor_original": str(flag.valor_original) if flag.valor_original is not None else None,
        "moeda": flag.moeda,
        "metadata": dict(flag.metadata),
    }


def _ptax_missing_warning(moeda: str, ano_base: int, saldo: dict) -> str:
    desc = saldo.get("descricao", "")[:50]
    return (
        f"PTAX {moeda}/BRL ausente para 31/12/{ano_base} ({desc}). "
        f"saldo_brl ficou None — workspace deve fornecer cotação ou aceitar saldo em moeda original."
    )
