"""Internals do dev/check_planner_manifest_coverage.py — loaders, validações e checks granulares. O entrypoint público em ``dev/check_planner_manifest_coverage.py`` só monta o pipeline."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

JSONPATH_HEAD_RE = re.compile(r"^\$\.([A-Za-z_][A-Za-z_0-9]*)")
JSONPATH_TABLE_RE = re.compile(r"^\$\.([A-Za-z_][A-Za-z_0-9]*)\.([A-Za-z_][A-Za-z_0-9.]*)\[\*\]$")

PLANNER_INTERNAL_SECTIONS = frozenset({"S_parecer", "APP_A", "APP_B", "APP_C", "APP_D", "APP_E"})

MANIFEST_REQUIRED_TOP = (
    "version",
    "output_schema",
    "input_schema_ref",
    "persona",
    "context_sections",
    "tools",
    "max_tool_iterations",
    "max_total_input_tokens",
    "max_exec_context_bytes",
    "hard_caps",
    "gating",
)


@dataclass
class CoverageReport:
    """Acumula erros/warnings do gate."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"arquivo não encontrado: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"esperado dict no topo de {path}, recebi {type(data).__name__}")
    return data


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"arquivo não encontrado: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Manifest structure validation (against note-planner schema)
# ---------------------------------------------------------------------------


def _validate_via_jsonschema(manifest: dict, schema: dict, report: CoverageReport) -> bool:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return False
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path))
    for err in errors:
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        report.fail(f"[manifest schema] {path}: {err.message}")
    return True


def _validate_required_keys_fallback(manifest: dict, report: CoverageReport) -> None:
    for key in MANIFEST_REQUIRED_TOP:
        if key not in manifest:
            report.fail(f"[manifest schema] campo obrigatório ausente no topo: '{key}'")


def validate_manifest_structure(manifest: dict, schema: dict, report: CoverageReport) -> None:
    """Valida shape do manifest contra note-planner.schema.json."""
    if _validate_via_jsonschema(manifest, schema, report):
        return
    _validate_required_keys_fallback(manifest, report)


# ---------------------------------------------------------------------------
# E5 schema introspection
# ---------------------------------------------------------------------------


def e5_top_level_keys(e5_schema: dict) -> set[str]:
    return set((e5_schema.get("properties") or {}).keys())


def _jsonpath_head(path: str) -> str | None:
    table_match = JSONPATH_TABLE_RE.match(path)
    if table_match:
        return table_match.group(1)
    head_match = JSONPATH_HEAD_RE.match(path)
    if head_match:
        return head_match.group(1)
    return None


def e5_path_exists(e5_schema: dict, path: str) -> bool:
    """Resolve um JSONPath subset contra o E5 schema (presença estrutural)."""
    if path == "$":
        return True
    head = _jsonpath_head(path)
    if head is None:
        return False
    return head in e5_top_level_keys(e5_schema)


# ---------------------------------------------------------------------------
# Cobertura manifest ↔ E5
# ---------------------------------------------------------------------------


def _iter_field_paths(fields: Iterable[dict]) -> Iterable[str]:
    for field_ref in fields or []:
        path = field_ref.get("path")
        if path:
            yield path


def _iter_block_paths(block: dict) -> Iterable[str]:
    fmt = block.get("format")
    if fmt == "key_value":
        yield from _iter_field_paths(block.get("fields", []))
        return
    if fmt in ("table", "scalar"):
        path = block.get("path")
        if path:
            yield path


def _iter_section_blocks(section: dict) -> Iterable[tuple[str, dict]]:
    section_id = section.get("id", "<sem id>")
    for block in section.get("blocks", []) or []:
        yield section_id, block


def iter_manifest_paths(manifest: dict) -> Iterable[tuple[str, str]]:
    """Yields (section_id, path) para cada path referenciado no manifest."""
    for section in manifest.get("context_sections", []) or []:
        for section_id, block in _iter_section_blocks(section):
            yield from ((section_id, path) for path in _iter_block_paths(block))


def _fail_path_missing_in_e5(
    section_id: str, path: str, e5_schema_path: Path, report: CoverageReport
) -> None:
    report.fail(
        f"[manifest↔e5] context_section '{section_id}' referencia '{path}' "
        f"mas E5 schema não declara essa key top-level "
        f"(arquivo: {e5_schema_path})"
    )


def check_manifest_paths_in_e5(
    manifest: dict, e5_schema: dict, e5_schema_path: Path, report: CoverageReport
) -> None:
    for section_id, path in iter_manifest_paths(manifest):
        if not e5_path_exists(e5_schema, path):
            _fail_path_missing_in_e5(section_id, path, e5_schema_path, report)


def _tool_section_enum(tool: dict) -> Iterable[str]:
    if tool.get("name") != "get_e5_section":
        return ()
    section_arg = (tool.get("args_schema") or {}).get("section") or {}
    return section_arg.get("enum", []) or ()


def _fail_tool_section_missing(value: str, e5_schema_path: Path, report: CoverageReport) -> None:
    report.fail(
        f"[manifest↔e5] tool 'get_e5_section' permite section='{value}' "
        f"mas E5 schema não declara essa key top-level "
        f"(arquivo: {e5_schema_path})"
    )


def _iter_section_enum_values(manifest: dict) -> Iterable[str]:
    for tool in manifest.get("tools", []) or []:
        yield from _tool_section_enum(tool)


def check_tool_enum_in_e5(
    manifest: dict, e5_schema: dict, e5_schema_path: Path, report: CoverageReport
) -> None:
    keys = e5_top_level_keys(e5_schema)
    for value in _iter_section_enum_values(manifest):
        if value not in keys:
            _fail_tool_section_missing(value, e5_schema_path, report)


def check_e5_coverage(
    manifest: dict, e5_schema: dict, e5_schema_path: Path, report: CoverageReport
) -> None:
    check_manifest_paths_in_e5(manifest, e5_schema, e5_schema_path, report)
    check_tool_enum_in_e5(manifest, e5_schema, e5_schema_path, report)


# ---------------------------------------------------------------------------
# Cobertura manifest ↔ report_layout.yaml
# ---------------------------------------------------------------------------


def enabled_layout_section_ids(layout: dict) -> set[str]:
    """Coleta section_ids enabled no layout (modo estratégico)."""
    estrategico = layout.get("estrategico") or {}
    sections = estrategico.get("sections") or []
    return {
        s["id"] for s in sections if isinstance(s, dict) and s.get("id") and s.get("enabled", True)
    }


def _warn_missing_alignment(section_id: str, section: dict, report: CoverageReport) -> None:
    if section.get("internal_only"):
        return
    report.warn(
        f"[manifest↔layout] context_section '{section_id}' não declara "
        "aligned_with_layout — marque 'internal_only: true' se intencional."
    )


def _fail_unknown_layout(
    section_id: str, layout_id: str, layout_path: Path, report: CoverageReport
) -> None:
    report.fail(
        f"[manifest↔layout] context_section '{section_id}' "
        f"aligned_with_layout='{layout_id}' mas section não existe enabled "
        f"em {layout_path}"
    )


def check_manifest_alignment(
    manifest: dict, enabled: set[str], layout_path: Path, report: CoverageReport
) -> set[str]:
    """Valida aligned_with_layout em cada context_section. Retorna ids alinhados."""
    aligned: set[str] = set()
    for section in manifest.get("context_sections", []) or []:
        section_id = section.get("id", "<sem id>")
        layout_id = section.get("aligned_with_layout")
        if layout_id is None:
            _warn_missing_alignment(section_id, section, report)
            continue
        aligned.add(layout_id)
        if layout_id not in enabled:
            _fail_unknown_layout(section_id, layout_id, layout_path, report)
    return aligned


def warn_unmapped_layout_sections(
    enabled: set[str], aligned: set[str], report: CoverageReport
) -> None:
    for layout_id in enabled - aligned - PLANNER_INTERNAL_SECTIONS:
        report.warn(
            f"[manifest↔layout] section '{layout_id}' habilitada em "
            "report_layout.yaml mas sem extração no manifest do parecer — "
            "confirme se é intencional (adicione context_section ou inclua "
            "em PLANNER_INTERNAL_SECTIONS)."
        )


def check_layout_coverage(
    manifest: dict, layout: dict, layout_path: Path, report: CoverageReport
) -> None:
    enabled = enabled_layout_section_ids(layout)
    aligned = check_manifest_alignment(manifest, enabled, layout_path, report)
    warn_unmapped_layout_sections(enabled, aligned, report)


# ---------------------------------------------------------------------------
# Snapshot diff do schema E5
# ---------------------------------------------------------------------------


def canonical_schema_hash(schema: dict) -> str:
    blob = json.dumps(schema, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _git_file_changed_in_head(path: Path) -> bool:
    """True se o arquivo aparece no diff de HEAD (best-effort, falha => False)."""
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "HEAD", "--", str(rel)],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return False
    if result.returncode != 0:
        return False
    files = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return str(rel) in files


def _write_snapshot(snapshot_path: Path, current_hash: str) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(current_hash + "\n", encoding="utf-8")
    print(f"[snapshot] regenerado em {snapshot_path} → {current_hash[:12]}…")


def _warn_drift(manifest_path: Path, report: CoverageReport) -> None:
    if _git_file_changed_in_head(manifest_path):
        report.warn(
            "[snapshot] schema E5 mudou (hash divergente do snapshot) e manifest "
            "também — confirme se o tunning está em sync e regenere snapshot com "
            "--update-snapshot."
        )
        return
    report.warn(
        "[snapshot] schema E5 mudou neste PR; manifest do parecer NÃO foi tocado — "
        "confirme se é intencional. Para suprimir, rode --update-snapshot após "
        "revisar."
    )


def _warn_missing_snapshot(snapshot_path: Path, report: CoverageReport) -> None:
    report.warn(
        f"[snapshot] hash baseline ausente em {snapshot_path} — "
        "rode com --update-snapshot para criar."
    )


def check_snapshot_drift(
    e5_schema: dict,
    snapshot_path: Path,
    manifest_path: Path,
    report: CoverageReport,
    update: bool,
) -> None:
    current = canonical_schema_hash(e5_schema)
    if update:
        _write_snapshot(snapshot_path, current)
        return
    if not snapshot_path.exists():
        _warn_missing_snapshot(snapshot_path, report)
        return
    previous = snapshot_path.read_text(encoding="utf-8").strip()
    if previous != current:
        _warn_drift(manifest_path, report)
