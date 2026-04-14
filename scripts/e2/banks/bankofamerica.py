#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bank of America — extrato conta corrente (PDF com regex, formato US)."""

import re
from pathlib import Path
from typing import Any, Dict

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_BOA,
    detect_member_from_text, infer_periodo_from_filename,
    log, make_result_template, parse_usd, safe_date,
)

LOG_PREFIX = "E2-EXTRATO"

PARSERS = [
    (r'^bankofamerica_extratoconta_', "parse_bankofamerica"),
]


def parse_bankofamerica(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Bank of America statement."""
    log(LOG_PREFIX, "INFO", f"Parsing Bank of America: {filename}")
    result = make_result_template(BANCO_BOA, "extratoconta", "USD")

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

            m = re.search(r'Account\s+number[:\s]+([\d\s]+)', all_text)
            if m:
                result["numero_conta"] = m.group(1).strip()

            pm = re.search(
                r'for\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+to\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',
                all_text
            )
            if pm:
                months_en = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12,
                }
                m1 = months_en.get(pm.group(1).lower(), 0)
                m2 = months_en.get(pm.group(4).lower(), 0)
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(int(pm.group(3)), m1, int(pm.group(2)))
                    result["periodo"]["fim"] = safe_date(int(pm.group(6)), m2, int(pm.group(5)))

            bb = re.search(r'Beginning balance.*?\$([\d.,]+)', all_text)
            eb = re.search(r'Ending balance.*?\$([\d.,]+)', all_text)
            if bb:
                result["saldo_inicial"] = parse_usd(bb.group(1))
            if eb:
                result["saldo_final"] = parse_usd(eb.group(1))

            tx_pattern = re.compile(
                r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(-?[\d.,]+)\s*$',
                re.MULTILINE
            )
            for m in tx_pattern.finditer(all_text):
                mm, dd, yy = m.group(1).split("/")
                yy_full = 2000 + int(yy)
                iso_date = safe_date(yy_full, int(mm), int(dd))
                result["transacoes"].append({
                    "data": iso_date,
                    "descricao": m.group(2).strip(),
                    "valor": parse_usd(m.group(3)),
                })

            if not result["transacoes"] and result["saldo_inicial"] == result["saldo_final"]:
                result["notas"].append("Conta sem movimentação no período (saldo inicial = saldo final)")

    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result
