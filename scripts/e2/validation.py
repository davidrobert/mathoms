#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Validation — post-parse quality checks for extraction results.

Consolidates validate_result() from e2_extract_extratos.py and
validate_parse_result() from e2_extract_faturas.py.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import MIN_XLS_BYTES, MIN_CSV_BYTES


def validate_extrato_result(result: Dict[str, Any], file_path: Path, is_csv: bool = False) -> List[str]:
    """Validate extraction result for extratos. Returns list of warnings/errors."""
    issues = []

    n_tx = len(result.get("transacoes", []))
    periodo = result.get("periodo", {})

    if not periodo.get("inicio"):
        issues.append("WARN: periodo.inicio ausente")
    if not periodo.get("fim"):
        issues.append("WARN: periodo.fim ausente")

    if is_csv:
        try:
            total_chars = file_path.stat().st_size
        except Exception:
            total_chars = 0

        is_xls = str(file_path).endswith(".xls")
        size_threshold = MIN_XLS_BYTES if is_xls else MIN_CSV_BYTES

        if n_tx == 0 and total_chars > size_threshold:
            notas_lower = [n.lower() for n in result.get("notas", [])]
            is_empty_period = any(
                "sem lançamentos" in n or "sem movimentação" in n
                for n in notas_lower
            )
            if not is_empty_period:
                issues.append(
                    f"ERROR: 0 transações extraídas de {'XLS' if is_xls else 'CSV'} com {total_chars} bytes "
                    f"— provável falha de parsing"
                )
    else:
        if pdfplumber is None:
            total_chars = 0
            n_pages = 0
        else:
            try:
                with pdfplumber.open(file_path) as pdf:
                    total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
                    n_pages = len(pdf.pages)
            except Exception:
                total_chars = 0
                n_pages = 0

        if n_tx == 0 and total_chars > 500 and n_pages > 0:
            notas_lower = [n.lower() for n in result.get("notas", [])]
            is_dormant = any(
                "sem movimentação" in n or "sem lançamentos" in n
                for n in notas_lower
            )
            if not is_dormant:
                issues.append(
                    f"ERROR: 0 transações extraídas de PDF com {total_chars} chars / "
                    f"{n_pages} páginas — provável falha de parsing"
                )

    none_vals = sum(1 for t in result.get("transacoes", []) if t.get("valor") is None)
    if none_vals > 0:
        issues.append(f"WARN: {none_vals} transações com valor None")

    seen = set()
    dupes = 0
    for t in result.get("transacoes", []):
        key = (t.get("data"), t.get("valor"), t.get("descricao", "")[:30])
        if key in seen:
            dupes += 1
        seen.add(key)
    if dupes > 0:
        issues.append(f"INFO: {dupes} possíveis duplicatas intra-arquivo")

    return issues


def validate_fatura_result(result: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Validate fatura parse result: sets parse_quality and appends issues to notas."""
    issues = result.setdefault("notas", []) if isinstance(result.get("notas"), list) else []
    if not isinstance(result.get("notas"), list):
        result["notas"] = issues = []

    saldo = result.get("saldo_atual") or 0
    txns = len(result.get("transacoes", []))
    itens = len(result.get("itens", []))
    venc = result.get("data_vencimento", "")

    if saldo == 0 and txns == 0 and itens == 0 and not venc:
        result["parse_quality"] = "empty_result"
        issues.append(f"ERROR: fatura vazia — saldo=0, transacoes=0, sem data_vencimento ({filename})")
    elif saldo > 0 and txns == 0 and itens == 0:
        result["parse_quality"] = "missing_transactions"
        issues.append(
            f"ERROR: fatura com saldo {saldo} mas 0 transações/itens — provável falha de parsing ({filename})"
        )
    else:
        result["parse_quality"] = "ok"

    if not venc and txns > 0:
        issues.append(f"WARN: data_vencimento ausente na fatura ({filename})")

    none_vals = sum(1 for t in result.get("transacoes", []) if t.get("valor") is None)
    if none_vals > 0:
        issues.append(f"WARN: {none_vals} transações com valor None ({filename})")

    return result
