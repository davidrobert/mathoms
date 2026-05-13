"""Smoke tests do gate dev/check_planner_manifest_coverage.py (T-09): green path, manifest com path ausente do E5, tool com section ausente, drift de snapshot, cobertura inversa de layout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.check_planner_manifest_coverage import (  # noqa: E402
    DEFAULT_E5_SCHEMA,
    DEFAULT_MANIFEST,
    DEFAULT_MANIFEST_SCHEMA,
    DEFAULT_REPORT_LAYOUT,
    canonical_schema_hash,
    run_coverage,
)

# ---------------------------------------------------------------------------
# Builders (prefixo make_ — fora do escopo do audit P1, igual a conftest.py)
# ---------------------------------------------------------------------------


def make_yaml_file(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def make_json_file(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def make_e5_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "score": {"type": "object"},
            "patrimonio": {"type": "object"},
            "fluxo_caixa": {"type": "object"},
            "investimentos": {"type": "object"},
        },
    }


def make_context_section(layout_id: str = "S1") -> dict:
    return {
        "id": "patrimonio",
        "title": "Patrimônio",
        "aligned_with_layout": layout_id,
        "blocks": [
            {
                "format": "key_value",
                "title": "Visão geral",
                "fields": [{"path": "$.patrimonio.bruto", "label": "Bruto", "format": "brl"}],
            }
        ],
    }


def make_tool() -> dict:
    return {
        "name": "get_e5_section",
        "description": "Lê uma chave top-level do E5 quando o contexto destilado for insuficiente.",
        "args_schema": {"section": {"type": "string", "enum": ["score", "patrimonio"]}},
        "cache_in_session": True,
    }


_MANIFEST_HARD_CAPS = {"riscos": 12, "sugestoes_por_horizonte": 5, "metricas": 10, "p0_total": 2}
_MANIFEST_PERSONA = {
    "path": "config/agents/planner_persona.md",
    "required_frontmatter_fields": ["id", "version"],
}


def make_manifest(**overrides) -> dict:
    base = {
        "version": "1.0",
        "output_schema": "config/schemas/parecer_planejador.schema.json",
        "input_schema_ref": "config/schemas/e5_analysis.schema.json",
        "persona": _MANIFEST_PERSONA,
        "context_sections": [make_context_section()],
        "tools": [make_tool()],
        "max_tool_iterations": 6,
        "max_total_input_tokens": 50000,
        "max_exec_context_bytes": 5120,
        "hard_caps": _MANIFEST_HARD_CAPS,
        "gating": {"free": {"all": False}, "premium": {"all": True}},
    }
    base.update(overrides)
    return base


def make_layout(*section_ids: str) -> dict:
    return {
        "version": "1.2",
        "estrategico": {
            "sections": [{"id": sid, "title": sid, "enabled": True} for sid in section_ids]
        },
    }


def make_snapshot(path: Path, schema: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_schema_hash(schema) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def fixtures(tmp_path: Path) -> dict:
    schema = make_e5_schema()
    return {
        "tmp": tmp_path,
        "e5_schema": schema,
        "e5_path": make_json_file(tmp_path / "e5.schema.json", schema),
        "layout_path": make_yaml_file(tmp_path / "layout.yaml", make_layout("S1", "S_parecer")),
        "snapshot_path": make_snapshot(tmp_path / "snapshots" / "e5_hash.txt", schema),
    }


def _run(manifest: dict, fx: dict):
    manifest_path = make_yaml_file(fx["tmp"] / "manifest.yaml", manifest)
    return run_coverage(
        manifest_path=manifest_path,
        manifest_schema_path=DEFAULT_MANIFEST_SCHEMA,
        e5_schema_path=fx["e5_path"],
        layout_path=fx["layout_path"],
        snapshot_path=fx["snapshot_path"],
        update_snapshot=False,
    )


# ---------------------------------------------------------------------------
# 1) Green path
# ---------------------------------------------------------------------------


def test_green_path_repo_vigente(tmp_path: Path) -> None:
    """Manifest commitado no repo passa o gate (warnings tolerados)."""
    e5 = json.loads(DEFAULT_E5_SCHEMA.read_text(encoding="utf-8"))
    snapshot = make_snapshot(tmp_path / "e5_hash.txt", e5)
    report = run_coverage(
        manifest_path=DEFAULT_MANIFEST,
        manifest_schema_path=DEFAULT_MANIFEST_SCHEMA,
        e5_schema_path=DEFAULT_E5_SCHEMA,
        layout_path=DEFAULT_REPORT_LAYOUT,
        snapshot_path=snapshot,
        update_snapshot=False,
    )
    assert report.ok, f"Erros: {report.errors}"


def test_green_path_minimal_fixtures(fixtures: dict) -> None:
    """Fixtures sintéticas mínimas: manifest + schemas + layout coerentes."""
    report = _run(make_manifest(), fixtures)
    assert report.ok, f"Erros inesperados: {report.errors}"


# ---------------------------------------------------------------------------
# 2) Manifest referencia campo ausente no E5
# ---------------------------------------------------------------------------


def _manifest_with_path(path: str) -> dict:
    section = make_context_section()
    section["blocks"] = [
        {
            "format": "key_value",
            "title": "Inválido",
            "fields": [{"path": path, "label": "Inválido", "format": "brl"}],
        }
    ]
    return make_manifest(context_sections=[section])


def test_manifest_referencia_path_ausente_no_e5(fixtures: dict) -> None:
    """Path top-level ausente do E5 schema → erro com mensagem clara."""
    report = _run(_manifest_with_path("$.campo_inexistente.foo"), fixtures)
    assert not report.ok
    assert any(
        "campo_inexistente" in err and "E5 schema não" in err for err in report.errors
    ), f"Erros: {report.errors}"


def test_tool_enum_referencia_key_ausente(fixtures: dict) -> None:
    """Tool get_e5_section permite section ausente do E5 → erro."""
    tool = make_tool()
    tool["args_schema"]["section"]["enum"] = ["score", "nao_existe"]
    manifest = make_manifest(tools=[tool])
    report = _run(manifest, fixtures)
    assert not report.ok
    assert any("nao_existe" in err and "get_e5_section" in err for err in report.errors)


# ---------------------------------------------------------------------------
# 3) Snapshot drift
# ---------------------------------------------------------------------------


def test_snapshot_drift_emite_warning(fixtures: dict) -> None:
    """Snapshot baseline divergente do hash atual → warning ativo."""
    fixtures["snapshot_path"].write_text("0" * 64 + "\n", encoding="utf-8")
    report = _run(make_manifest(), fixtures)
    assert report.ok, "Drift do schema E5 é warning, não erro"
    assert any("schema E5 mudou" in warn for warn in report.warnings)


def test_snapshot_ausente_emite_warning(fixtures: dict) -> None:
    """Sem snapshot baseline, gate emite warning instruindo --update-snapshot."""
    fixtures["snapshot_path"] = fixtures["tmp"] / "snapshots" / "missing.txt"
    report = _run(make_manifest(), fixtures)
    assert report.ok
    assert any("hash baseline ausente" in warn for warn in report.warnings)


def test_update_snapshot_regenera(fixtures: dict) -> None:
    """--update-snapshot grava hash atual do schema E5."""
    target = fixtures["tmp"] / "snapshots" / "fresh.txt"
    manifest_path = make_yaml_file(fixtures["tmp"] / "manifest.yaml", make_manifest())
    report = run_coverage(
        manifest_path=manifest_path,
        manifest_schema_path=DEFAULT_MANIFEST_SCHEMA,
        e5_schema_path=fixtures["e5_path"],
        layout_path=fixtures["layout_path"],
        snapshot_path=target,
        update_snapshot=True,
    )
    assert report.ok
    assert target.read_text(encoding="utf-8").strip() == canonical_schema_hash(
        fixtures["e5_schema"]
    )


# ---------------------------------------------------------------------------
# 4) Cobertura inversa
# ---------------------------------------------------------------------------


def test_layout_section_sem_extracao_emite_warning(fixtures: dict) -> None:
    """Section habilitada no layout sem context_section correspondente → warning."""
    fixtures["layout_path"] = make_yaml_file(
        fixtures["tmp"] / "layout2.yaml",
        make_layout("S1", "S2", "S_parecer"),
    )
    report = _run(make_manifest(), fixtures)
    assert report.ok
    assert any("'S2'" in warn for warn in report.warnings), report.warnings
