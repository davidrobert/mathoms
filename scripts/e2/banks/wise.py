#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wise — extrato conta USD/BRL (PDF com regex)."""

import re
from pathlib import Path
from typing import Any, Dict, List

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_WISE, MESES_BR_INT, detect_member_from_text,
    infer_periodo_from_filename, log, make_result_template, parse_brl, safe_date,
)

LOG_PREFIX = "E2-EXTRATO"

PARSERS = [
    (r'^wise_extratoconta', "parse_wise"),
]


def parse_wise(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Wise bank statement."""
    is_usd = "usd" in filename.lower()
    moeda = "USD" if is_usd else "BRL"
    tipo = f"extratoconta{moeda.lower()}"

    log(LOG_PREFIX, "INFO", f"Parsing Wise ({moeda}): {filename}")
    result = make_result_template(BANCO_WISE, tipo, moeda)

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

            m = re.search(r'N[úu]mero da conta\s+.*?(\d{10,})', all_text)
            if m:
                result["numero_conta"] = m.group(1)

            pm = re.search(
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+\[.*?\]\s*-\s*'
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
                all_text
            )
            if pm:
                d1, m1, y1 = int(pm.group(1)), MESES_BR_INT.get(pm.group(2).lower(), 0), int(pm.group(3))
                d2, m2, y2 = int(pm.group(4)), MESES_BR_INT.get(pm.group(5).lower(), 0), int(pm.group(6))
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(y1, m1, d1)
                    result["periodo"]["fim"] = safe_date(y2, m2, d2)

            bal_match = re.search(
                r'(?:USD|BRL)\s+em\s+.*?\s+([\d.,]+)\s+(?:USD|BRL)',
                all_text
            )
            if bal_match:
                result["saldo_final"] = parse_brl(bal_match.group(1))

            lines = all_text.split("\n")
            transactions: List[Dict] = []
            i = 0

            while i < len(lines):
                line = lines[i].strip()

                date_match = re.match(
                    r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+Transação',
                    line
                )

                if date_match and transactions:
                    d = int(date_match.group(1))
                    m_name = date_match.group(2).lower()
                    y = int(date_match.group(3))
                    mo = MESES_BR_INT.get(m_name, 0)
                    if mo:
                        transactions[-1]["data"] = safe_date(y, mo, d)
                    i += 1
                    continue

                tx_match = re.match(
                    r'(.+?)\s+(-?[\d.,]+)\s+([\d.,]+)\s*$',
                    line
                )

                if tx_match:
                    descricao = tx_match.group(1).strip()
                    valor = parse_brl(tx_match.group(2))
                    if descricao in ("Descrição", "Descrição Entrada Saída Valor"):
                        i += 1
                        continue
                    if "Entrada" in descricao and "Saída" in descricao:
                        i += 1
                        continue

                    if valor is not None:
                        transactions.append({
                            "data": None,
                            "descricao": descricao,
                            "valor": valor,
                        })

                i += 1

            result["transacoes"] = [t for t in transactions if t.get("data")]
            result["transacoes"].reverse()

            if not result["transacoes"] and result["saldo_final"] is not None:
                result["notas"].append(
                    "Conta sem movimentação no período (saldo estável)"
                )

            if result["saldo_final"] is not None and result["transacoes"]:
                total = sum(t["valor"] for t in result["transacoes"] if t["valor"])
                saldo_ini = round(result["saldo_final"] - total, 2)
                result["saldo_inicial"] = saldo_ini + 0.0

    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result
