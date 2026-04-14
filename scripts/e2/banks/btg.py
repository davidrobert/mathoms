#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTG Pactual — extrato conta corrente (PDF com regex)."""

import re
from pathlib import Path
from typing import Any, Dict, List

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_BTG,
    detect_member_from_text, infer_periodo_from_filename,
    log, make_result_template, parse_brl,
)

LOG_PREFIX = "E2-EXTRATO"

PARSERS = [
    (r'^btgpactual_extratoconta_', "parse_btg"),
]


def parse_btg(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse BTG Pactual bank statement."""
    log(LOG_PREFIX, "INFO", f"Parsing BTG Pactual: {filename}")
    result = make_result_template(BANCO_BTG, "extratoconta", "BRL")

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

            m = re.search(r'Conta Corrente[:\s]+([\d]+)', all_text)
            if m:
                result["numero_conta"] = m.group(1)

            m = re.search(r'CPF[:\s]+([\d.\-]+)', all_text)

            pm = re.search(r'Per[ií]odo\s+de\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', all_text)
            if pm:
                p1 = pm.group(1).split("/")
                p2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{p1[2]}-{p1[1]}-{p1[0]}"
                result["periodo"]["fim"] = f"{p2[2]}-{p2[1]}-{p2[0]}"

            lines = all_text.split("\n")
            in_movimentacao = False

            for line in lines:
                line = line.strip()

                if "Movimentação" in line and "Conta Corrente" in line:
                    in_movimentacao = True
                    continue

                if not in_movimentacao:
                    continue

                if line.startswith("Data") and "Descrição" in line:
                    continue

                si_match = re.match(r'(\d{2}/\d{2}/\d{4})\s+Saldo Inicial\s+([\d.,]+)', line)
                if si_match:
                    result["saldo_inicial"] = parse_brl(si_match.group(2))
                    continue

                sf_match = re.match(r'(\d{2}/\d{2}/\d{4})\s+Saldo Final\s+([\d.,]+)', line)
                if sf_match:
                    result["saldo_final"] = parse_brl(sf_match.group(2))
                    continue

                if line.startswith("Total de"):
                    continue

                tx_match = re.match(
                    r'(\d{2}/\d{2}/\d{4})\s+'
                    r'(.+?)\s+'
                    r'([\d.,]+)\s+'
                    r'([\d.,]+)\s*$',
                    line
                )
                if tx_match:
                    date_parts = tx_match.group(1).split("/")
                    iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                    descricao = tx_match.group(2).strip()
                    valor_raw = parse_brl(tx_match.group(3))
                    saldo_after = parse_brl(tx_match.group(4))

                    if valor_raw is None:
                        continue

                    credit_keywords = [
                        "RESGATE", "REMUNERAÇÃO", "CREDITO", "CRÉDITO",
                        "RECEBIMENTO", "CUPOM", "DIVIDENDO", "Rendimento",
                        "RENDIMENT", "FRAÇÕES",
                    ]
                    desc_upper = descricao.upper()
                    is_credit = any(kw.upper() in desc_upper for kw in credit_keywords)

                    if is_credit:
                        valor = valor_raw
                    else:
                        valor = -valor_raw

                    result["transacoes"].append({
                        "data": iso_date,
                        "descricao": descricao,
                        "valor": valor,
                    })

                tx_match2 = re.match(
                    r'(\d{2}/\d{2}/\d{4})\s+'
                    r'(.+?)\s+-\s+'
                    r'([\d.,]+)\s+'
                    r'([\d.,]+)\s*$',
                    line
                )
                if tx_match2 and not tx_match:
                    date_parts = tx_match2.group(1).split("/")
                    iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                    descricao = tx_match2.group(2).strip()
                    valor_raw = parse_brl(tx_match2.group(3))
                    if valor_raw is not None:
                        result["transacoes"].append({
                            "data": iso_date,
                            "descricao": descricao,
                            "valor": valor_raw,
                        })

    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result
