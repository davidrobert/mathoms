#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E6 Sanitize — monetary format and narrative text sanitization.

Extracted from e6_render.py for testability and maintainability.
"""

import re


def sanitize_monetary_format(text: str) -> str:
    """Fix monetary format issues in narrative text.

    Corrections applied:
      - R$ X.Yk → R$ X,Yk  (ponto decimal → vírgula)
      - R$ X.YM → R$ X,YM
      - Ensures no "KM" suffix (should be "k" or "M" separately)
      - Ensures space between R$ and value
    """
    if not text:
        return text

    # Fix decimal point in R$ values with k/M suffix: R$ 2.5k → R$ 2,5k
    text = re.sub(r"(R\$\s*\d+)\.(\d+)([kKmM])", r"\1,\2\3", text)

    # Fix standalone numeric values with dot+suffix (without R$): 2.5k → 2,5k
    # But only when preceded by space/start to avoid matching things like URLs
    text = re.sub(r"(?<=\s)(\d+)\.(\d+)([kK])(?!\w)", r"\1,\2\3", text)

    # Fix "KM" suffix → proper format (R$ 2,3KM is wrong)
    text = re.sub(r"(R\$\s*[\d.,]+)\s*KM\b", r"\1k", text)

    return text


def sanitize_narrativas(narrativas: dict) -> dict:
    """Apply monetary format sanitization to all narrative text fields."""
    if not narrativas:
        return narrativas

    # Sanitize summaries
    summaries = narrativas.get("summaries", {})
    for key, value in summaries.items():
        if isinstance(value, str):
            summaries[key] = sanitize_monetary_format(value)

    # Sanitize perfil_familia
    perfil = narrativas.get("perfil_familia", {})
    for key, value in perfil.items():
        if isinstance(value, str):
            perfil[key] = sanitize_monetary_format(value)
        elif isinstance(value, list):
            perfil[key] = [sanitize_monetary_format(v) if isinstance(v, str) else v for v in value]

    # Sanitize chart narratives
    charts = narrativas.get("charts", {})
    for chart_key, chart_data in charts.items():
        if isinstance(chart_data, dict):
            for field in ("titulo", "narrativa", "insight", "context", "conclusion"):
                if field in chart_data and isinstance(chart_data[field], str):
                    chart_data[field] = sanitize_monetary_format(chart_data[field])

    return narrativas
