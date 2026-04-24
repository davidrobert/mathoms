#!/usr/bin/env python3
"""Codegen: config/report_layout.yaml → TS + Pydantic (ADR-076 · F0.2.5).

Gera tipos e constantes para consumo pelo frontend (Next.js) e backend
(FastAPI/Pydantic), a partir da fonte única `config/report_layout.yaml`.

Também valida o YAML contra `config/schemas/report_layout.schema.json`.

Uso:
    python3 dev/codegen_report_layout.py         # gera artefatos
    python3 dev/codegen_report_layout.py --check # valida sync (CI/pre-commit)

Saídas:
    frontend/src/generated/report-layout.ts
    backend/app/generated/report_layout.py
"""

from __future__ import annotations

import argparse
import json
import pprint
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "config" / "report_layout.yaml"
SCHEMA_PATH = ROOT / "config" / "schemas" / "report_layout.schema.json"
TS_OUTPUT = ROOT / "frontend" / "src" / "generated" / "report-layout.ts"
PY_OUTPUT = ROOT / "backend" / "app" / "generated" / "report_layout.py"


# ---------------------------------------------------------------------------
# Load + validate
# ---------------------------------------------------------------------------


def load_yaml() -> dict[str, Any]:
    import yaml  # pyyaml

    return yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))


def validate(layout: dict[str, Any]) -> None:
    """Valida YAML contra JSON Schema. Sobe ValidationError se quebrar."""
    try:
        import jsonschema
    except ImportError:
        print("WARNING: jsonschema não instalado — pulando validação", file=sys.stderr)
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=layout, schema=schema)


# ---------------------------------------------------------------------------
# TS emitter
# ---------------------------------------------------------------------------

TS_HEADER = """/**
 * GENERATED FILE — do not edit by hand.
 * Source: config/report_layout.yaml
 * Regenerate: python3 dev/codegen_report_layout.py
 *
 * Schema: config/schemas/report_layout.schema.json (ADR-076)
 */
"""


def _collect_ids(sections: list[dict[str, Any]], key: str) -> list[str]:
    """Extract unique IDs from sections[*][key][*].id."""
    seen: list[str] = []
    for section in sections:
        for item in section.get(key, []) or []:
            if item["id"] not in seen:
                seen.append(item["id"])
    return seen


def render_ts(layout: dict[str, Any]) -> str:
    all_sections = (
        layout["estrategico"]["sections"] + layout["tatico"]["sections"] + layout["usa"]["sections"]
    )
    all_cards = _collect_ids(all_sections, "cards")
    all_charts = _collect_ids(all_sections, "charts")

    as_json = json.dumps(layout, indent=2, ensure_ascii=False)

    lines = [
        TS_HEADER,
        "",
        "export type CardVariant =",
        "  | 'highlight'",
        "  | 'feature'",
        "  | 'success'",
        "  | 'warn'",
        "  | 'critical'",
        "  | 'primary'",
        "  | 'neutral'",
        "  | 'top-danger'",
        "  | 'top-accent';",
        "",
        "export type CardSize = 'full' | 'half';",
        "",
        "export type ReportMode = 'estrategico' | 'tatico' | 'usa';",
        "",
        "export type TopBorder = 'danger' | 'accent';",
        "",
        "export type ChartHeight = number | 'auto';",
        "",
        "export interface CardSpec {",
        "  id: string;",
        "  enabled: boolean;",
        "  variant?: CardVariant;",
        "  size?: CardSize;",
        "  top_border?: TopBorder;",
        "  comparison_anchor_id?: string;",
        "}",
        "",
        "export interface ChartSpec {",
        "  id: string;",
        "  enabled: boolean;",
        "  row?: string;",
        "  conclusion?: boolean;",
        "  context?: boolean;",
        "  period_toggle?: boolean;",
        "  height?: ChartHeight;",
        "}",
        "",
        "export interface SectionSpec {",
        "  id: string;",
        "  title: string;",
        "  enabled: boolean;",
        "  charts?: ChartSpec[];",
        "  cards?: CardSpec[];",
        "  data_source?: string;",
        "  summary?: boolean;",
        "  divider_before?: boolean;",
        "  collapsible?: boolean;",
        "}",
        "",
        "export interface AppendixSpec {",
        "  id: string;",
        "  title: string;",
        "  enabled: boolean;",
        "  charts?: ChartSpec[];",
        "  cards?: CardSpec[];",
        "}",
        "",
        "export interface KpiSpec {",
        "  id: string;",
        "  label: string;",
        "  enabled: boolean;",
        "}",
        "",
        "export interface CoverMetaSpec {",
        "  label_key: string;",
        "  value_key?: string;",
        "}",
        "",
        "export interface CoverSpec {",
        "  enabled: boolean;",
        "  badge?: string;",
        "  title_key?: string;",
        "  subtitle_key?: string;",
        "  meta?: CoverMetaSpec[];",
        "}",
        "",
        "export interface NavLinkSpec {",
        "  section_id: string;",
        "  num?: string;",
        "  is_appendix?: boolean;",
        "}",
        "",
        "export interface NavGroupSpec {",
        "  label?: string;",
        "  links: NavLinkSpec[];",
        "}",
        "",
        "export interface NavigationSpec {",
        "  estrategico?: NavGroupSpec[];",
        "  tatico?: NavGroupSpec[];",
        "  usa?: NavGroupSpec[];",
        "}",
        "",
        "export interface ReportLayout {",
        "  version: string;",
        "  estrategico: {",
        "    sections: SectionSpec[];",
        "    appendices?: AppendixSpec[];",
        "  };",
        "  tatico: {",
        "    kpis?: KpiSpec[];",
        "    sections: SectionSpec[];",
        "  };",
        "  usa: {",
        "    sections: SectionSpec[];",
        "  };",
        "  cover?: CoverSpec;",
        "  navigation?: NavigationSpec;",
        "  footer?: boolean;",
        "  export_toolbar?: boolean;",
        "  chart_palette?: string[];",
        "  chart_canvas_map?: Record<string, string>;",
        "  chart_titles?: Record<string, string>;",
        "}",
        "",
        f"export const LAYOUT: ReportLayout = {as_json} as ReportLayout;",
        "",
        f"export const ALL_CARD_IDS = {json.dumps(all_cards)} as const;",
        "export type CardId = (typeof ALL_CARD_IDS)[number];",
        "",
        f"export const ALL_CHART_IDS = {json.dumps(all_charts)} as const;",
        "export type ChartId = (typeof ALL_CHART_IDS)[number];",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pydantic emitter
# ---------------------------------------------------------------------------

PY_HEADER = '''"""GENERATED FILE — do not edit by hand.

Source: config/report_layout.yaml
Regenerate: python3 dev/codegen_report_layout.py
Schema: config/schemas/report_layout.schema.json (ADR-076)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

CardVariant = Literal[
    "highlight",
    "feature",
    "success",
    "warn",
    "critical",
    "primary",
    "neutral",
    "top-danger",
    "top-accent",
]

CardSize = Literal["full", "half"]

ReportMode = Literal["estrategico", "tatico", "usa"]

TopBorder = Literal["danger", "accent"]

ChartHeight = int | Literal["auto"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CardSpec(_Base):
    id: str
    enabled: bool
    variant: CardVariant | None = None
    size: CardSize | None = None
    top_border: TopBorder | None = None
    comparison_anchor_id: str | None = None


class ChartSpec(_Base):
    id: str
    enabled: bool
    row: str | None = None
    conclusion: bool | None = None
    context: bool | None = None
    period_toggle: bool | None = None
    height: ChartHeight | None = None


class SectionSpec(_Base):
    id: str
    title: str
    enabled: bool
    charts: list[ChartSpec] = []
    cards: list[CardSpec] = []
    data_source: str | None = None
    summary: bool | None = None
    divider_before: bool | None = None
    collapsible: bool | None = None


class AppendixSpec(_Base):
    id: str
    title: str
    enabled: bool
    charts: list[ChartSpec] = []
    cards: list[CardSpec] = []


class KpiSpec(_Base):
    id: str
    label: str
    enabled: bool


class CoverMetaSpec(_Base):
    label_key: str
    value_key: str | None = None


class CoverSpec(_Base):
    enabled: bool
    badge: str | None = None
    title_key: str | None = None
    subtitle_key: str | None = None
    meta: list[CoverMetaSpec] = []


class NavLinkSpec(_Base):
    section_id: str
    num: str | None = None
    is_appendix: bool | None = None


class NavGroupSpec(_Base):
    label: str | None = None
    links: list[NavLinkSpec]


class NavigationSpec(_Base):
    estrategico: list[NavGroupSpec] = []
    tatico: list[NavGroupSpec] = []
    usa: list[NavGroupSpec] = []


class Estrategico(_Base):
    sections: list[SectionSpec]
    appendices: list[AppendixSpec] = []


class Tatico(_Base):
    kpis: list[KpiSpec] = []
    sections: list[SectionSpec]


class Usa(_Base):
    sections: list[SectionSpec]


class ReportLayout(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str
    estrategico: Estrategico
    tatico: Tatico
    usa: Usa
    cover: CoverSpec | None = None
    navigation: NavigationSpec | None = None
    footer: bool | None = None
    export_toolbar: bool | None = None
    chart_palette: list[str] | None = None
    chart_canvas_map: dict[str, str] | None = None
    chart_titles: dict[str, str] | None = None

'''


def render_py(layout: dict[str, Any]) -> str:
    all_sections = (
        layout["estrategico"]["sections"] + layout["tatico"]["sections"] + layout["usa"]["sections"]
    )
    all_cards = _collect_ids(all_sections, "cards")
    all_charts = _collect_ids(all_sections, "charts")

    # pprint emite literais Python válidos (True/False/None), json.dumps não.
    layout_py = pprint.pformat(layout, indent=4, width=100, sort_dicts=False)

    return (
        PY_HEADER
        + f"LAYOUT_DICT: dict = {layout_py}\n"
        + "\n"
        + "LAYOUT: ReportLayout = ReportLayout.model_validate(LAYOUT_DICT)\n"
        + "\n"
        + f"ALL_CARD_IDS: tuple[str, ...] = {tuple(all_cards)!r}\n"
        + f"ALL_CHART_IDS: tuple[str, ...] = {tuple(all_charts)!r}\n"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build() -> tuple[str, str]:
    layout = load_yaml()
    validate(layout)
    return render_ts(layout), render_py(layout)


def ensure_init_py(path: Path) -> None:
    """Cria __init__.py para que a pasta seja um package Python."""
    init = path.parent / "__init__.py"
    if not init.exists():
        init.write_text('"""Generated modules (do not edit)."""\n', encoding="utf-8")


def write_outputs(ts: str, py: str) -> None:
    TS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ensure_init_py(PY_OUTPUT)
    TS_OUTPUT.write_text(ts, encoding="utf-8")
    PY_OUTPUT.write_text(py, encoding="utf-8")
    print(f"✓ wrote {TS_OUTPUT.relative_to(ROOT)} ({len(ts)} bytes)")
    print(f"✓ wrote {PY_OUTPUT.relative_to(ROOT)} ({len(py)} bytes)")


def check_in_sync() -> int:
    ts, py = build()
    mismatches: list[str] = []
    for path, expected in [(TS_OUTPUT, ts), (PY_OUTPUT, py)]:
        if not path.exists():
            mismatches.append(f"MISSING: {path.relative_to(ROOT)}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            mismatches.append(f"OUT OF SYNC: {path.relative_to(ROOT)}")
    if mismatches:
        print("✗ report layout codegen out of sync:", file=sys.stderr)
        for m in mismatches:
            print(f"  {m}", file=sys.stderr)
        print("  fix: python3 dev/codegen_report_layout.py", file=sys.stderr)
        return 1
    print("✓ report layout codegen in sync")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Codegen report_layout.yaml → TS + Pydantic.")
    parser.add_argument("--check", action="store_true", help="Verifica sync (exit 1 se divergir)")
    args = parser.parse_args()

    if args.check:
        return check_in_sync()

    ts, py = build()
    write_outputs(ts, py)
    return 0


if __name__ == "__main__":
    sys.exit(main())
