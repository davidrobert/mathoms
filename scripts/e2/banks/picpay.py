#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PicPay — extrato conta corrente (PDF com tabelas)."""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_PICPAY,
    MESES_BR_INT,
    detect_member_from_text,
    infer_periodo_from_filename,
    log,
    make_result_template,
    parse_brl,
    safe_date,
)

LOG_PREFIX = "E2-EXTRATO"

PARSERS = [
    (r"^picpay_extratoconta_", "parse_picpay"),
]


def parse_picpay(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse PicPay bank statement."""
    log(LOG_PREFIX, "INFO", f"Parsing PicPay: {filename}")
    result = make_result_template(BANCO_PICPAY, "extratoconta", "BRL")
    result["tipo_conta"] = "corrente"

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            result["titular"] = detect_member_from_text(first_text)

            m = re.search(r"Conta[:\s]+(\d+)", first_text)
            if m:
                result["numero_conta"] = m.group(1)

            pm = re.search(
                r"MOVIMENTA[ÇC][ÕO]ES\s+(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})\s+A\s+"
                r"(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})",
                first_text,
                re.IGNORECASE,
            )
            if pm:
                d1, m1_name, y1 = int(pm.group(1)), pm.group(2).lower(), int(pm.group(3))
                d2, m2_name, y2 = int(pm.group(4)), pm.group(5).lower(), int(pm.group(6))
                m1 = MESES_BR_INT.get(m1_name, 0)
                m2 = MESES_BR_INT.get(m2_name, 0)
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(y1, m1, d1)
                    result["periodo"]["fim"] = safe_date(y2, m2, d2)

            saldo_first = None
            saldo_last = None

            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue
                        cols = [str(c).strip() if c else "" for c in row]

                        if "Data/Hora" in cols[0] or "Descrição" in cols[1]:
                            continue

                        date_match = re.match(r"(\d{2}/\d{2}/\d{4})", cols[0])
                        if not date_match:
                            continue

                        parts = date_match.group(1).split("/")
                        iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        descricao = cols[1]
                        valor = parse_brl(cols[2])
                        saldo = parse_brl(cols[3])

                        if valor is None:
                            continue

                        result["transacoes"].append(
                            {
                                "data": iso_date,
                                "descricao": descricao,
                                "valor": valor,
                            }
                        )

                        if saldo is not None:
                            if saldo_first is None:
                                saldo_first = saldo
                            saldo_last = saldo

            result["transacoes"].reverse()

            if saldo_first is not None:
                result["saldo_final"] = saldo_first
            if saldo_last is not None:
                result["saldo_inicial"] = saldo_last

    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result
