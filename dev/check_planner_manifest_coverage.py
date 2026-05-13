#!/usr/bin/env python3
"""Coverage gate do manifest do parecer planejador (ADR-200 §D3 + ADR-206 §6). Cruza manifest YAML, schema E5 e report_layout e detecta drift. Internals em ``dev/_planner_coverage_internals.py``; ``--update-snapshot`` regenera baseline."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev._planner_coverage_internals import (  # noqa: E402
    CoverageReport,
    canonical_schema_hash,  # noqa: F401  (re-export para callers/tests)
    check_e5_coverage,
    check_layout_coverage,
    check_snapshot_drift,
    load_json,
    load_yaml,
    validate_manifest_structure,
)

DEFAULT_MANIFEST = REPO_ROOT / "config" / "prompts" / "parecer_planejador.yaml"
DEFAULT_MANIFEST_SCHEMA = REPO_ROOT / "docs" / "_schemas" / "note-planner.schema.json"
DEFAULT_E5_SCHEMA = REPO_ROOT / "config" / "schemas" / "e5_analysis.schema.json"
DEFAULT_REPORT_LAYOUT = REPO_ROOT / "config" / "report_layout.yaml"
DEFAULT_SNAPSHOT_PATH = REPO_ROOT / "dev" / "snapshots" / "e5_schema_hash.txt"


def _load_manifest_or_fail(path: Path, report: CoverageReport) -> dict | None:
    try:
        return load_yaml(path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        report.fail(f"[manifest] não foi possível carregar: {exc}")
        return None


def _load_manifest_schema(path: Path, manifest: dict, report: CoverageReport) -> None:
    try:
        schema = load_json(path)
    except FileNotFoundError as exc:
        report.fail(f"[manifest schema] {exc}")
        return
    validate_manifest_structure(manifest, schema, report)


def _load_e5_or_fail(path: Path, report: CoverageReport) -> dict | None:
    try:
        return load_json(path)
    except FileNotFoundError as exc:
        report.fail(f"[e5 schema] {exc}")
        return None


def _load_layout_optional(path: Path, report: CoverageReport) -> dict:
    try:
        return load_yaml(path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        report.fail(f"[layout] {exc}")
        return {}


@dataclass(frozen=True)
class CoveragePaths:
    """Conjunto de paths que o gate consulta — facilita assinatura única."""

    manifest: Path
    manifest_schema: Path
    e5_schema: Path
    layout: Path
    snapshot: Path


def _run_checks(
    p: CoveragePaths,
    manifest: dict,
    e5_schema: dict,
    layout: dict,
    update_snapshot: bool,
    report: CoverageReport,
) -> None:
    check_e5_coverage(manifest, e5_schema, p.e5_schema, report)
    if layout:
        check_layout_coverage(manifest, layout, p.layout, report)
    check_snapshot_drift(e5_schema, p.snapshot, p.manifest, report, update_snapshot)


def _load_inputs(
    paths: CoveragePaths, report: CoverageReport
) -> tuple[dict | None, dict | None, dict]:
    """Carrega manifest/E5/layout. None em manifest|E5 indica falha precoce."""
    manifest = _load_manifest_or_fail(paths.manifest, report)
    if manifest is None:
        return None, None, {}
    _load_manifest_schema(paths.manifest_schema, manifest, report)
    e5_schema = _load_e5_or_fail(paths.e5_schema, report)
    if e5_schema is None:
        return manifest, None, {}
    layout = _load_layout_optional(paths.layout, report)
    return manifest, e5_schema, layout


def run_coverage(  # noqa: PLR0913 - assinatura compatível com CLI legacy
    manifest_path: Path,
    manifest_schema_path: Path,
    e5_schema_path: Path,
    layout_path: Path,
    snapshot_path: Path,
    update_snapshot: bool,
) -> CoverageReport:
    paths = CoveragePaths(
        manifest_path, manifest_schema_path, e5_schema_path, layout_path, snapshot_path
    )
    report = CoverageReport()
    manifest, e5_schema, layout = _load_inputs(paths, report)
    if manifest is None or e5_schema is None:
        return report
    _run_checks(paths, manifest, e5_schema, layout, update_snapshot, report)
    return report


def emit_report(report: CoverageReport) -> int:
    for warn in report.warnings:
        print(f"WARNING: {warn}", file=sys.stderr)
    for err in report.errors:
        print(f"ERROR:   {err}", file=sys.stderr)
    if not report.ok:
        print(
            f"\nCoverage gate FAIL: {len(report.errors)} erro(s), "
            f"{len(report.warnings)} warning(s).",
            file=sys.stderr,
        )
        return 1
    suffix = f" com {len(report.warnings)} warning(s)" if report.warnings else ""
    print(f"Coverage gate OK{suffix}.", file=sys.stderr)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Coverage gate do manifest do parecer planejador (ADR-200)."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--manifest-schema", type=Path, default=DEFAULT_MANIFEST_SCHEMA)
    parser.add_argument("--e5-schema", type=Path, default=DEFAULT_E5_SCHEMA)
    parser.add_argument("--report-layout", type=Path, default=DEFAULT_REPORT_LAYOUT)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT_PATH)
    parser.add_argument(
        "--update-snapshot",
        action="store_true",
        help="Regenera o hash baseline do schema E5 após mudança intencional.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_coverage(
        args.manifest,
        args.manifest_schema,
        args.e5_schema,
        args.report_layout,
        args.snapshot,
        args.update_snapshot,
    )
    return emit_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
