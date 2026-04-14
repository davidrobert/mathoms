#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rico Corretora — extrato conta (PDF com regex)."""

import re
from pathlib import Path
from typing import Any, Dict

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_RICO, detect_member_from_text, infer_periodo_from_filename,
    log, make_result_template, parse_brl,
)

LOG_PREFIX = "E2-EXTRATO"

PARSERS = [
    (r'^rico_extratoconta_', "parse_rico"),
]


def parse_rico(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Rico corretora bank statement."""
    log(LOG_PREFIX, "INFO", f"Parsing Rico: {filename}")
    result = make_result_template(BANCO_RICO, "extratoconta", "BRL")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

            result["titular"] = detect_member_from_text(all_text)

            m = re.search(r'Conta[:\s]+(\d+)', all_text)
            if m:
                result["numero_conta"] = m.group(1)

            pm = re.search(r'De[:\s]+(\d{2}/\d{2}/\d{4})\s+Até[:\s]+(\d{2}/\d{2}/\d{4})', all_text)
            if pm:
                p1 = pm.group(1).split("/")
                p2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{p1[2]}-{p1[1]}-{p1[0]}"
                result["periodo"]["fim"] = f"{p2[2]}-{p2[1]}-{p2[0]}"

            m = re.search(r'Saldo dispon[ií]vel[:\s]+R\$\s*([\d.,]+)', all_text)
            if m:
                result["saldo_final"] = parse_brl(m.group(1))

            tx_pattern = re.compile(
                r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+'
                r'(.+?)\s+'
                r'R\$\s*([\d.,]+)\s+'
                r'R\$\s*([\d.,]+)',
            )

            for m in tx_pattern.finditer(all_text):
                date_parts = m.group(1).split("/")
                iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                descricao = m.group(3).strip()
                valor = parse_brl(m.group(4))

                if valor is None:
                    continue

                result["transacoes"].append({
                    "data": iso_date,
                    "descricao": descricao,
                    "valor": valor,
                })

            if result["saldo_final"] is not None and result["transacoes"]:
                total = sum(t["valor"] for t in result["transacoes"] if t["valor"])
                result["saldo_inicial"] = round(result["saldo_final"] - total, 2)

    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result
