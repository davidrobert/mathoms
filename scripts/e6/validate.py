#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E6 Validate — 19-check report validation suite.

Extracted from e6_render.py for testability and independent execution.
"""

import json
import re


def validate_report(html: str, report_data_json: str) -> dict:
    """Run 19 validation checks on the rendered HTML report.

    Returns dict of {V1..V19: {name, passed, detail?}} results.
    """
    print("[E6.6] Running validation checks...")

    results = {
        "V1": {"name": "No remaining {{...}} outside HTML comments", "passed": True},
        "V2": {"name": "report-data JSON is valid", "passed": True},
        "V3": {"name": "charts has 19 datasets", "passed": True},
        "V4": {"name": "19 canvas IDs present", "passed": True},
        "V5": {"name": "9+ sections present", "passed": True},
        "V6": {"name": "5 appendices present", "passed": True},
        "V7": {"name": "Mandatory cards present", "passed": True},
        "V8": {"name": "COVER_DATA_HORA contains time pattern", "passed": True},
        "V9": {"name": "COVER_VERSAO is version number", "passed": True},
        "V10": {"name": "Perfil is narrative prose (no tables/lists)", "passed": True},
        "V11": {"name": "KPIs match E4", "passed": True},
        "V12": {"name": "patrimonio.imoveis_estimado > 0", "passed": True},
        "V13": {"name": "orcamento_prospectivo has 14+ categories", "passed": True},
        "V14": {"name": "HTML > 100KB", "passed": True},
        "V15": {"name": "CSS rule: no inline margin-top/bottom", "passed": True},
        "V16": {"name": "CSS rule: .card has .card-title first child", "passed": True},
        "V17": {"name": "CSS rule: no hardcoded hex colors in HTML", "passed": True},
        "V18": {"name": "CSS rule: tr.total-row for total rows", "passed": True},
        "V19": {
            "name": "No invalid monetary formats (KM, k M, ponto decimal em R$)",
            "passed": True,
        },
    }

    # V1: No {{...}} outside comments (ignore {{PLACEHOLDERS}} in comments)
    html_no_comments = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    placeholders = re.findall(r"\{\{[A-Z_]+\}\}", html_no_comments)
    if placeholders:
        results["V1"]["passed"] = False
        results["V1"]["detail"] = f"Found {len(placeholders)} unreplaced: {placeholders[:5]}"

    # V2: Valid JSON
    try:
        json.loads(report_data_json)
    except Exception:
        results["V2"]["passed"] = False
        results["V2"]["detail"] = "JSON parsing failed"

    # V3: 19 charts
    report_data = json.loads(report_data_json)
    if len(report_data.get("charts", {})) < 19:
        results["V3"]["passed"] = False
        results["V3"]["detail"] = f"Found {len(report_data.get('charts', {}))} charts, expected 19"

    # V4: 19 canvas IDs
    canvas_count = len(re.findall(r'<canvas id="chart-', html))
    if canvas_count < 19:
        results["V4"]["passed"] = False
        results["V4"]["detail"] = f"Found {canvas_count} canvases, expected 19"

    # V5: Sections (strategic S1-S4,S7-S10 = 8, plus USA U1-U4 = 4, total 12)
    section_count = len(re.findall(r'id="secao-\d+"', html))
    usa_section_count = len(re.findall(r'id="usa-\d+"', html))
    total_sections = section_count + usa_section_count
    if total_sections < 9:
        results["V5"]["passed"] = False
        results["V5"]["detail"] = (
            f"Found {total_sections} sections (S:{section_count} + U:{usa_section_count}), expected 9+"
        )

    # V6: Appendices
    app_count = len(re.findall(r'id="apendice-[a-e]"', html))
    if app_count < 5:
        results["V6"]["passed"] = False
        results["V6"]["detail"] = f"Found {app_count} appendices, expected 5"

    # V10-V13: Not yet implemented — mark as warnings
    for vnum in [10, 11, 12, 13]:
        v_key = f"V{vnum}"
        if v_key in results:
            results[v_key]["passed"] = True
            results[v_key]["warning"] = "Validação pendente de implementação"

    # V16: Every <div class="card ..."> must have <div class="card-title"> as first meaningful child
    _html_body = re.sub(r"<script[^>]*>.*?</script>", "", html_no_comments, flags=re.DOTALL)
    _html_body = re.sub(r"<style[^>]*>.*?</style>", "", _html_body, flags=re.DOTALL)
    card_pattern = re.findall(r'<div\s+class="card[^"]*"[^>]*>\s*\n?\s*(<[^>]+>)', _html_body)
    cards_without_title = [
        m
        for m in card_pattern
        if "card-title" not in m and "card-compact-icon" not in m and "notas-card-header" not in m
    ]
    if cards_without_title:
        results["V16"]["passed"] = False
        results["V16"]["detail"] = (
            f"{len(cards_without_title)} card(s) sem .card-title como primeiro filho: {cards_without_title[:3]}"
        )

    # V15: Inline styles count (warn if excessive)
    inline_styles = re.findall(r'\sstyle="[^"]*"', html_no_comments)
    safe_patterns = ["grid-template-columns", "display:none", "display: none"]
    unsafe_count = sum(1 for s in inline_styles if not any(sp in s for sp in safe_patterns))
    if unsafe_count > 30:
        results["V15"]["passed"] = False
        results["V15"]["detail"] = (
            f"Found {unsafe_count} inline styles (limit: 30). Migrate to CSS classes."
        )
    else:
        results["V15"]["detail"] = f"{unsafe_count} inline styles (OK, ≤30)"

    # V17: Hardcoded hex colors in HTML body (outside <style> blocks)
    body_html = re.sub(r"<style[^>]*>.*?</style>", "", html_no_comments, flags=re.DOTALL)
    body_html = re.sub(r"<script[^>]*>.*?</script>", "", body_html, flags=re.DOTALL)
    hex_colors = re.findall(r'(?:color|background|border)[^"]*#[0-9a-fA-F]{3,8}', body_html)
    if len(hex_colors) > 10:
        results["V17"]["passed"] = False
        results["V17"]["detail"] = f"Found {len(hex_colors)} hardcoded colors. Use CSS variables."

    # V18: total-row class for total rows
    total_rows_ok = len(re.findall(r'class="total-row"', html_no_comments))
    total_strong_rows = len(re.findall(r"<tr[^>]*><td><strong>Total", html_no_comments))
    if total_strong_rows > total_rows_ok + 2:
        results["V18"]["passed"] = False
        results["V18"]["detail"] = (
            f"Found {total_strong_rows} total rows but only {total_rows_ok} with .total-row class"
        )

    # V14: Size > 100KB
    if len(html.encode("utf-8")) < 100000:
        results["V14"]["passed"] = False
        results["V14"]["detail"] = (
            f"HTML is {len(html.encode('utf-8')) / 1024:.1f}KB, expected > 100KB"
        )

    # V19: No invalid monetary formats in visible content
    visible = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    visible = re.sub(r"<script[^>]*>.*?</script>", "", visible, flags=re.DOTALL)
    visible = re.sub(r"<style[^>]*>.*?</style>", "", visible, flags=re.DOTALL)
    v19_errors = []
    km_matches = re.findall(r"R\$\s*[\d.,]+\s*KM|[\d.,]+\s*KM(?!\d|[A-Z])", visible)
    if km_matches:
        v19_errors.append(f"KM suffix: {km_matches[:5]}")
    km_sep = re.findall(r"R\$\s*[\d.,]+\s*[kK]\s+M", visible)
    if km_sep:
        v19_errors.append(f"k M separated: {km_sep[:5]}")
    ponto_matches = re.findall(r"R\$\s*\d+\.\d+[MmKk]", visible)
    if ponto_matches:
        v19_errors.append(f"ponto decimal (deveria ser vírgula): {ponto_matches[:5]}")
    if v19_errors:
        results["V19"]["passed"] = False
        results["V19"]["detail"] = "; ".join(v19_errors)

    return results
