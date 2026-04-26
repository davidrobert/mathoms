#!/usr/bin/env python3
"""Build design tokens — gera CSS para o app Next.js e o console ops.

Uso:
    python design-tokens/build.py
    python design-tokens/build.py --check   # verifica se arquivos gerados estão em sync

Fontes:
    design-tokens/tokens.json     ← única fonte de verdade

Saídas:
    frontend/src/styles/tokens.css       — site (Next.js + Tailwind v4 @theme inline)
    frontend-ops/src/styles/tokens.css   — console ops (Next sem @theme inline)

Referência: ADR-076, ADR-129 (docs/DECISIONS.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TOKENS_PATH = ROOT / "design-tokens" / "tokens.json"
FRONTEND_OUTPUT = ROOT / "frontend" / "src" / "styles" / "tokens.css"
FRONTEND_OPS_OUTPUT = ROOT / "frontend-ops" / "src" / "styles" / "tokens.css"

HEADER = """/* =====================================================================
 * {name} — design tokens
 * {description}
 *
 * GENERATED FILE — do not edit by hand.
 * Source: design-tokens/tokens.json
 * Regenerate: python design-tokens/build.py
 *
 * Version: {version}
 * ===================================================================== */
"""


def load_tokens() -> dict[str, Any]:
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CSS emitters
# ---------------------------------------------------------------------------


def _kebab(name: str) -> str:
    return name.replace("_", "-")


def _mode_block(mode_data: dict[str, Any]) -> list[str]:
    """Emit CSS vars from a mode dict (light/dark)."""
    lines: list[str] = []

    # brand
    for k, v in mode_data["brand"].items():
        lines.append(f"    --brand-{_kebab(k)}: {v};")
    lines.append("")

    # surface
    for k, v in mode_data["surface"].items():
        lines.append(f"    --surface-{_kebab(k)}: {v};")
    lines.append("")

    # semantic
    for k, v in mode_data["semantic"].items():
        lines.append(f"    --semantic-{_kebab(k)}: {v};")
    lines.append("")

    # chart palette
    for i, color in enumerate(mode_data["chart"], start=1):
        lines.append(f"    --chart-{i}: {color};")
    lines.append("")

    # sidebar
    for k, v in mode_data["sidebar"].items():
        lines.append(f"    --sidebar-{_kebab(k)}: {v};")

    return lines


def _static_tokens_block(tokens: dict[str, Any], *, emit_fonts: bool) -> list[str]:
    """Typography, spacing, radius, shadow — invariantes de modo.

    `emit_fonts=False` no output do Next.js: as vars --font-* são
    providenciadas pelo next/font/google em runtime (layout.tsx) para
    preservar otimizações (subsetting, self-hosting, font-display:swap).
    Emitir aqui criaria conflito de cascata.

    `emit_fonts=True` no output do frontend-ops: não há next/font no app
    ops — o CSS precisa das vars para resolver as famílias via @import
    Google Fonts.
    """
    lines: list[str] = []

    # typography
    typo = tokens["typography"]
    if emit_fonts:
        for k, v in typo["fonts"].items():
            lines.append(f"    --font-{_kebab(k)}: {v};")
        lines.append("")
    for k, v in typo["sizes"].items():
        lines.append(f"    --font-size-{_kebab(k)}: {v};")
    lines.append("")
    for k, v in typo["line_heights"].items():
        lines.append(f"    --line-height-{_kebab(k)}: {v};")
    lines.append("")
    for k, v in typo["weights"].items():
        lines.append(f"    --font-weight-{_kebab(k)}: {v};")
    lines.append("")
    # tracking (letter-spacing)
    if "tracking" in typo:
        for k, v in typo["tracking"].items():
            lines.append(f"    --tracking-{_kebab(k)}: {v};")
        lines.append("")

    # spacing
    for k, v in tokens["spacing"].items():
        lines.append(f"    --space-{_kebab(k)}: {v};")
    lines.append("")

    # radius
    for k, v in tokens["radius"].items():
        lines.append(f"    --radius-{_kebab(k)}: {v};")
    lines.append("")

    # shadow
    for k, v in tokens["shadow"].items():
        lines.append(f"    --shadow-{_kebab(k)}: {v};")

    return lines


def _card_variants_block(tokens: dict[str, Any]) -> list[str]:
    """Emit utility classes for card variants."""
    lines: list[str] = ["", "/* Card variants — visual DNA do relatório */"]
    for variant, style in tokens["card_variants"].items():
        class_name = f"card-variant-{variant}"
        lines.append(f".{class_name} {{")
        for css_prop, value in style.items():
            lines.append(f"    {_kebab(css_prop)}: {value};")
        lines.append("    border-radius: var(--radius-card);")
        lines.append("    padding: var(--space-2xl);")
        lines.append("    background-clip: padding-box;")
        lines.append("}")
    return lines


def _report_palette_vars(palette_mode: dict[str, Any]) -> list[str]:
    """Emit --report-* vars for one mode (light/dark)."""
    lines: list[str] = []
    for group_key in ("surface_ext", "alert", "badge", "table", "gradient"):
        group = palette_mode.get(group_key, {})
        prefix_map = {
            "surface_ext": "report-surface",
            "alert": "report-alert",
            "badge": "report-badge",
            "table": "report-table",
            "gradient": "report-gradient",
        }
        prefix = prefix_map[group_key]
        for k, v in group.items():
            lines.append(f"    --{prefix}-{_kebab(k)}: {v};")
        lines.append("")
    return lines


def _report_typography_vars(scale: dict[str, Any]) -> list[str]:
    """Emit --report-font-size-* + --report-font-base-px vars for one scale preset."""
    lines: list[str] = []
    lines.append(f"    --report-font-base-px: {scale['base_px']}px;")
    for key, value in scale.items():
        if key == "base_px":
            continue
        lines.append(f"    --report-font-size-{_kebab(key)}: {value};")
    return lines


def _report_scope_block(tokens: dict[str, Any]) -> list[str]:
    """Emit [data-report-scope] scoped block — report palette + typography.

    Lives alongside :root vars; activates only inside ReportShell where
    `<div data-report-scope data-font-scale="compact">` wraps the tree.
    Dark mode uses the .dark/[data-theme='dark'] parent selectors.
    """
    palette = tokens["report_palette"]
    typo = tokens["report_typography"]
    default_scale = typo["default_scale"]
    scales = typo["scales"]
    spacing = typo.get("spacing_scope", {})
    radius = typo.get("radius_scope", {})

    out: list[str] = ["", "/* Report scope — ADR-117 palette + ADR-121 typography */"]

    # Base scope block (light + default scale + spacing/radius extras)
    out.append("[data-report-scope] {")
    out.extend(_report_palette_vars(palette["light"]))
    out.extend(_report_typography_vars(scales[default_scale]))
    out.append("")
    for k, v in spacing.items():
        out.append(f"    --report-space-{_kebab(k)}: {v};")
    for k, v in radius.items():
        out.append(f"    --report-radius-{_kebab(k)}: {v};")
    transition = typo.get("transition")
    if transition:
        out.append(f"    transition: {transition};")
    out.append("}")

    # Non-default font scales
    for scale_name, scale_def in scales.items():
        if scale_name == default_scale:
            continue
        out.append(f'[data-report-scope][data-font-scale="{scale_name}"] {{')
        out.extend(_report_typography_vars(scale_def))
        out.append("}")

    # Dark mode overrides for report palette only (typography is theme-agnostic)
    out.append(".dark [data-report-scope],")
    out.append("[data-theme='dark'] [data-report-scope] {")
    out.extend(_report_palette_vars(palette["dark"]))
    out.append("}")

    return out


def _theme_inline_block(tokens: dict[str, Any]) -> list[str]:
    """@theme inline block for Tailwind v4 — só no output do frontend."""
    lines = ["", "@theme inline {"]
    # cores brand
    for k in tokens["modes"]["light"]["brand"]:
        lines.append(f"    --color-brand-{_kebab(k)}: var(--brand-{_kebab(k)});")
    # cores surface
    for k in tokens["modes"]["light"]["surface"]:
        lines.append(f"    --color-{_kebab(k)}: var(--surface-{_kebab(k)});")
    # semantic
    for k in tokens["modes"]["light"]["semantic"]:
        lines.append(f"    --color-{_kebab(k)}: var(--semantic-{_kebab(k)});")
    # chart
    for i in range(1, len(tokens["modes"]["light"]["chart"]) + 1):
        lines.append(f"    --color-chart-{i}: var(--chart-{i});")
    # sidebar
    for k in tokens["modes"]["light"]["sidebar"]:
        lines.append(f"    --color-sidebar-{_kebab(k)}: var(--sidebar-{_kebab(k)});")
    lines.append("")
    # typography — font families
    lines.append("    --font-heading: var(--font-display);")
    lines.append("    --font-sans: var(--font-body);")
    lines.append("    --font-mono: var(--font-mono);")
    lines.append("")
    # typography — font sizes (wire tokens into Tailwind)
    typo = tokens["typography"]
    for k in typo["sizes"]:
        tw_key = _kebab(k)
        lines.append(f"    --text-{tw_key}: var(--font-size-{tw_key});")
    lines.append("")
    # typography — line heights
    for k in typo["line_heights"]:
        tw_key = _kebab(k)
        lines.append(f"    --leading-{tw_key}: var(--line-height-{tw_key});")
    lines.append("")
    # typography — tracking (letter-spacing)
    if "tracking" in typo:
        for k in typo["tracking"]:
            tw_key = _kebab(k)
            lines.append(f"    --tracking-{tw_key}: var(--tracking-{tw_key});")
        lines.append("")
    # radius
    for k in tokens["radius"]:
        lines.append(f"    --radius-{_kebab(k)}: var(--radius-{_kebab(k)});")
    lines.append("}")

    # text styles — CSS utility classes from composite tokens
    if "text_styles" in typo:
        lines.append("")
        lines.append("/* Text styles — composições tipográficas semânticas (ADR-076) */")
        for style_name, style_def in typo["text_styles"].items():
            class_name = f"text-style-{_kebab(style_name)}"
            font_var = f"var(--font-{style_def['font']})"
            size_var = f"var(--font-size-{_kebab(style_def['size'])})"
            weight_var = f"var(--font-weight-{_kebab(style_def['weight'])})"
            lh_var = f"var(--line-height-{_kebab(style_def['line_height'])})"
            tracking_var = f"var(--tracking-{_kebab(style_def['tracking'])})"
            lines.append(f".{class_name} {{")
            lines.append(f"    font-family: {font_var};")
            lines.append(f"    font-size: {size_var};")
            lines.append(f"    font-weight: {weight_var};")
            lines.append(f"    line-height: {lh_var};")
            lines.append(f"    letter-spacing: {tracking_var};")
            lines.append("}")

    return lines


def render_css(tokens: dict[str, Any], *, include_tailwind_theme: bool) -> str:
    """Render the full CSS file.

    `include_tailwind_theme=True` emite o bloco @theme inline do Tailwind v4
    (para o Next.js). Nesse caso `--font-*` NÃO são emitidas aqui, já que
    vêm do next/font/google em runtime.

    `include_tailwind_theme=False` é o output do frontend-ops: inclui
    `--font-*` porque o app ops não usa next/font.
    """
    meta = tokens["meta"]
    out: list[str] = [HEADER.format(**meta)]

    out.append(":root {")
    out.extend(_static_tokens_block(tokens, emit_fonts=not include_tailwind_theme))
    out.append("")
    out.extend(_mode_block(tokens["modes"]["light"]))
    out.append("}")
    out.append("")

    # Dark mode — both selectors supported
    out.append(".dark,")
    out.append("[data-theme='dark'] {")
    out.extend(_mode_block(tokens["modes"]["dark"]))
    # dark-specific shadows
    shadow = tokens["shadow"]
    out.append("")
    out.append(f"    --shadow-card: {shadow['card_dark']};")
    out.append(f"    --shadow-card-hover: {shadow['card_hover_dark']};")
    out.append("}")

    if "report_palette" in tokens and "report_typography" in tokens:
        out.extend(_report_scope_block(tokens))

    out.extend(_card_variants_block(tokens))

    if include_tailwind_theme:
        out.extend(_theme_inline_block(tokens))

    out.append("")  # trailing newline
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build() -> tuple[str, str]:
    tokens = load_tokens()
    frontend_css = render_css(tokens, include_tailwind_theme=True)
    ops_css = render_css(tokens, include_tailwind_theme=False)
    return frontend_css, ops_css


def write_outputs(frontend_css: str, ops_css: str) -> None:
    FRONTEND_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_OPS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_OUTPUT.write_text(frontend_css, encoding="utf-8")
    FRONTEND_OPS_OUTPUT.write_text(ops_css, encoding="utf-8")
    print(f"✓ wrote {FRONTEND_OUTPUT.relative_to(ROOT)} ({len(frontend_css)} bytes)")
    print(f"✓ wrote {FRONTEND_OPS_OUTPUT.relative_to(ROOT)} ({len(ops_css)} bytes)")


def check_in_sync() -> int:
    frontend_css, ops_css = build()
    mismatches: list[str] = []
    for path, expected in [
        (FRONTEND_OUTPUT, frontend_css),
        (FRONTEND_OPS_OUTPUT, ops_css),
    ]:
        if not path.exists():
            mismatches.append(f"MISSING: {path.relative_to(ROOT)}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            mismatches.append(f"OUT OF SYNC: {path.relative_to(ROOT)}")
    if mismatches:
        print("✗ design tokens out of sync:", file=sys.stderr)
        for m in mismatches:
            print(f"  {m}", file=sys.stderr)
        print("  fix: python design-tokens/build.py", file=sys.stderr)
        return 1
    print("✓ design tokens in sync")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build design tokens CSS artifacts.")
    parser.add_argument(
        "--check", action="store_true", help="Verify generated files are in sync with tokens.json"
    )
    args = parser.parse_args()

    if args.check:
        return check_in_sync()

    frontend_css, ops_css = build()
    write_outputs(frontend_css, ops_css)
    return 0


if __name__ == "__main__":
    sys.exit(main())
