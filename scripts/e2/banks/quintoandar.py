#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QuintoAndar — fatura de aluguel (PDF)."""

import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_QUINTOANDAR,
    infer_year_from_filename,
    log,
    parse_brl,
)

LOG_PREFIX = "E2-FATURA"

PARSERS = [
    (r"quintoandar_faturaaluguel", "parse_quintoandar"),
]


def parse_quintoandar(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse QuintoAndar rental invoice."""
    log(LOG_PREFIX, "INFO", f"Parsing QuintoAndar: {filename}")

    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r"(\d{4})(\d{2})", filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))

    prop_m = re.search(r"faturaaluguel(\w+?)_\d{6}", filename)
    propriedade = prop_m.group(1) if prop_m else "desconhecida"

    result = {
        "banco": BANCO_QUINTOANDAR,
        "tipo": "faturaaluguel",
        "propriedade": propriedade,
        "moeda": "BRL",
        "periodo_referencia": f"{ref_year}-{ref_month:02d}" if ref_year and ref_month else None,
        "total_recebido": None,
        "itens": [],
        "data_recebimento": None,
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        full_text = "\n".join(all_text)

        m = re.search(r"Faturas de aluguel\s*\n(.+)", full_text)
        if m:
            result["endereco"] = m.group(1).strip()

        m = re.search(r"Total de\s*\n?\s*R\$\s*([\d.,]+)", full_text)
        if m:
            result["total_recebido"] = parse_brl(m.group(1))

        m = re.search(r"[Rr]eceber até\s+(\d{2}/\d{2}/\d{4})", full_text)
        if m:
            parts = m.group(1).split("/")
            result["data_recebimento"] = f"{parts[2]}-{parts[1]}-{parts[0]}"

        item_pattern = re.compile(
            r"(.+?)\s+(-?R\$\s*[\d.,]+)",
        )

        SKIP_EXACT = {"total de", "subtotal", "você recebe", "recebido"}

        for line in full_text.split("\n"):
            stripped = line.strip()
            item_m = item_pattern.match(stripped)
            if item_m:
                desc = item_m.group(1).strip()
                valor_str = item_m.group(2).strip()
                valor = parse_brl(valor_str)

                if valor is not None and desc and len(desc) > 3:
                    if desc.lower().strip() in SKIP_EXACT:
                        continue
                    result["itens"].append(
                        {
                            "descricao": desc,
                            "valor": valor,
                        }
                    )

        log(LOG_PREFIX, "INFO", f"  → {len(result['itens'])} itens extraídos")
    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result
