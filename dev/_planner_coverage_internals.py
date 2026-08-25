"""Internals do dev/check_planner_manifest_coverage.py — loaders, validações e checks granulares. O entrypoint público em ``dev/check_planner_manifest_coverage.py`` só monta o pipeline."""

from __future__ import annotations

import json
import os
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
# Drift E5 schema ↔ manifest (ADR-200 §D3.3)
# ---------------------------------------------------------------------------


def _git_changed_paths() -> frozenset[str]:
    """Paths mudados vs HEAD. Best-effort — sem git utilizável, retorna vazio."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return frozenset()
    if result.returncode != 0:
        return frozenset()
    return frozenset(line.strip() for line in result.stdout.splitlines() if line.strip())


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# Campo do E5 que o parecer NÃO recebe por decisão, com a razão. Entrar aqui é o ato
# consciente que o `warn` anterior não exigia — três ADRs passaram por ele sem que
# ninguém decidisse nada, e os seis campos de incerteza da A40 chegaram ao r8 invisíveis
# ao parecer (A40.l83 · RV8-05b).
E5_FIELDS_FORA_DO_PARECER: dict[str, str] = {
    "$._lineage": "rastro de proveniência do pipeline — insumo de debug, não de conselho",
    "$.narrativas": "texto já destilado em outra superfície; projetá-lo duplicaria prosa",
    "$.protection_computation_inputs_v1": "insumos crus do cálculo de proteção; o parecer lê o resultado",
}


def _e5_leaf_paths(schema: dict, prefix: str = "$") -> set[str]:
    """Folhas do schema E5 em JSONPath — o universo que o manifest decide projetar."""
    out: set[str] = set()
    for key, value in (schema.get("properties") or {}).items():
        path = f"{prefix}.{key}"
        sub = value.get("properties") if isinstance(value, dict) else None
        out.update(_e5_leaf_paths(value, path) if isinstance(sub, dict) else {path})
    return out


def _schema_at(ref: str, rel_path: str) -> dict | None:
    """Schema E5 como estava em `ref`. None quando o ref não existe (clone raso, fork)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"{ref}:{rel_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


# O check anterior derivava de ``git diff HEAD``, VAZIO em CI (o job roda
# `pre-commit --all-files` sobre árvore limpa): o gate só existia no pre-commit local do
# commit exato que tocava o schema. Comparar com a base de merge é o que o faz existir.
def _baseline_ref(rel_path: str) -> str | None:
    """`origin/main` quando alcançável, senão `HEAD`."""
    for ref in ("origin/main", "HEAD"):
        if _schema_at(ref, rel_path) is not None:
            return ref
    return None


def _escapado(path: str) -> bool:
    """Escape declarado cobre a SUBÁRVORE: `$.narrativas` vale por suas folhas."""
    return any(path == key or path.startswith(f"{key}.") for key in E5_FIELDS_FORA_DO_PARECER)


def _coberto_pelo_manifest(path: str, projetados: set[str]) -> bool:
    """Path coberto por projeção própria ou de um ancestral/descendente declarado."""
    return any(
        path == q or path.startswith(f"{q}.") or q.startswith(f"{path}.") for q in projetados
    )


# Precedente `check_scheduled_workflows`: instrumento mudo degrada para warning FORA do
# CI (clone raso, fork) e BLOQUEIA dentro dele. Degradar em silêncio no CI recriaria o
# fail-open que esta lane fecha — o gate anterior derivava de `git diff HEAD`, que é
# vazio sob `pre-commit --all-files`, e por isso nunca existiu no CI.
def _sem_baseline(report: CoverageReport) -> None:
    msg = (
        "[drift] `origin/main` inalcançável — campo novo no E5 não pôde ser aferido. "
        "Em CI, garanta `git fetch --no-tags --depth=1 origin main` antes do gate."
    )
    (report.fail if os.environ.get("CI") else report.warn)(msg)


def _fail_campo_novo(path: str, report: CoverageReport) -> None:
    report.fail(
        f"[drift] `{path}` é campo NOVO no schema E5 e o manifest do parecer não o "
        "projeta. O manifest é whitelist: campo não declarado não chega ao modelo, e "
        "ele só ressalva o que recebe. Projete-o em config/prompts/parecer_planejador.yaml "
        "ou declare a razão em E5_FIELDS_FORA_DO_PARECER (dev/_planner_coverage_internals.py)."
    )


# Hard-fail, não warn: o `warn` anterior não tinha destinatário. Escopo é o campo NOVO —
# o débito herdado sai como contagem, para ficar visível sem virar allowlist de ~90
# linhas, que é carimbada de uma vez e vira decoração.
def check_schema_manifest_drift(
    e5_schema_path: Path,
    manifest_path: Path,
    report: CoverageReport,
    changed_paths: frozenset[str] | None = None,
) -> None:
    """Campo novo no E5 é projetado no manifest ou escapado com razão (A40.l83 · RV8-05b)."""
    del changed_paths  # a decisão deixou de derivar de "o arquivo mudou?"
    rel = _repo_relative(e5_schema_path)
    baseline = _baseline_ref(rel)
    atual = load_json(e5_schema_path)
    projetados = {
        path.replace("[*]", "") for _section, path in iter_manifest_paths(load_yaml(manifest_path))
    }
    folhas = _e5_leaf_paths(atual)
    herdado = [p for p in folhas if not _coberto_pelo_manifest(p, projetados) and not _escapado(p)]
    if herdado:
        report.warn(
            f"[drift] {len(herdado)} folhas do E5 fora do manifest e sem razão declarada "
            "(débito herdado, não bloqueia). Campo NOVO bloqueia."
        )
    if baseline is None or baseline == "HEAD":
        _sem_baseline(report)
        return
    antes = _e5_leaf_paths(_schema_at(baseline, rel) or {})
    for path in sorted(folhas - antes):
        if not _coberto_pelo_manifest(path, projetados) and not _escapado(path):
            _fail_campo_novo(path, report)
