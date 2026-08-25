"""Smoke tests do gate dev/check_planner_manifest_coverage.py (T-09): green path, manifest com path ausente do E5, tool com section ausente, drift E5↔manifest derivado do diff, cobertura inversa de layout."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev import _planner_coverage_internals as internals  # noqa: E402
from dev.check_planner_manifest_coverage import (  # noqa: E402
    DEFAULT_E5_SCHEMA,
    DEFAULT_MANIFEST,
    DEFAULT_MANIFEST_SCHEMA,
    DEFAULT_REPORT_LAYOUT,
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
        # ADR-341 D2: obrigatório no schema — eviction determinística por seção.
        "eviction_priority": 1,
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


@pytest.fixture
def fixtures(tmp_path: Path) -> dict:
    schema = make_e5_schema()
    return {
        "tmp": tmp_path,
        "e5_schema": schema,
        "e5_path": make_json_file(tmp_path / "e5.schema.json", schema),
        "layout_path": make_yaml_file(tmp_path / "layout.yaml", make_layout("S1", "S_parecer")),
    }


def _run(manifest: dict, fx: dict):
    manifest_path = make_yaml_file(fx["tmp"] / "manifest.yaml", manifest)
    return run_coverage(
        manifest_path=manifest_path,
        manifest_schema_path=DEFAULT_MANIFEST_SCHEMA,
        e5_schema_path=fx["e5_path"],
        layout_path=fx["layout_path"],
    )


# ---------------------------------------------------------------------------
# 1) Green path
# ---------------------------------------------------------------------------


def test_green_path_repo_vigente() -> None:
    """Manifest commitado no repo passa o gate (warnings tolerados)."""
    report = run_coverage(
        manifest_path=DEFAULT_MANIFEST,
        manifest_schema_path=DEFAULT_MANIFEST_SCHEMA,
        e5_schema_path=DEFAULT_E5_SCHEMA,
        layout_path=DEFAULT_REPORT_LAYOUT,
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
# 3) Drift E5 ↔ manifest — campo NOVO bloqueia (A40.l83 · RV8-05b)
# ---------------------------------------------------------------------------
# O contrato mudou de "warn quando o arquivo mudou" para "fail quando existe campo
# NOVO sem projeção nem razão". O antigo derivava de `git diff HEAD`, vazio sob
# `pre-commit --all-files` — só existia no pre-commit local do commit exato.


E5_SCHEMA = internals.REPO_ROOT / "config" / "schemas" / "e5_analysis.schema.json"
MANIFEST = internals.REPO_ROOT / "config" / "prompts" / "parecer_planejador.yaml"

# Schema/manifest sintéticos: o contrato é "campo novo sem projeção bloqueia", e amarrar
# a asserção a um campo real do repo faria o teste medir o estado da branch em vez do
# contrato — foi o que aconteceu na primeira versão destes testes.
_SCHEMA_BASE = {"properties": {"patrimonio": {"properties": {"bruto": {"type": "number"}}}}}
_MANIFEST_FAKE = {
    "context_sections": [
        {
            "id": "s",
            "blocks": [{"format": "key_value", "fields": [{"path": "$.patrimonio.bruto"}]}],
        }
    ]
}


def _sintetico(tmp_path: Path, schema: dict, manifest: dict) -> tuple[Path, Path]:
    sp, mp = tmp_path / "e5.schema.json", tmp_path / "manifest.yaml"
    sp.write_text(json.dumps(schema), encoding="utf-8")
    mp.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return sp, mp


def _drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    atual: dict,
    baseline: dict | None,
    manifest: dict | None = None,
) -> internals.CoverageReport:
    sp, mp = _sintetico(tmp_path, atual, manifest if manifest is not None else _MANIFEST_FAKE)
    monkeypatch.setattr(internals, "_schema_at", lambda ref, rel: baseline)
    report = internals.CoverageReport()
    internals.check_schema_manifest_drift(sp, mp, report)
    return report


def test_estado_atual_do_repo_nao_bloqueia() -> None:
    """Sem campo novo, o gate passa — o débito herdado sai como contagem, não como erro."""
    if internals._baseline_ref(internals._repo_relative(E5_SCHEMA)) in (None, "HEAD"):
        pytest.skip(
            "sem `origin/main` alcançável (checkout raso): esta asserção é sobre o repo "
            "vigente e passaria vazia. A invocação real do gate cobre isto no lint-all, "
            "que faz o fetch da base."
        )
    report = internals.CoverageReport()
    internals.check_schema_manifest_drift(E5_SCHEMA, MANIFEST, report)
    assert report.ok, report.errors
    assert any("débito herdado" in w for w in report.warnings), report.warnings


def test_campo_novo_sem_projecao_bloqueia(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """O manifest é whitelist: campo que ele não declara não chega ao modelo."""
    atual = json.loads(json.dumps(_SCHEMA_BASE))
    atual["properties"]["incerteza_nova"] = {"type": "number"}
    report = _drift(monkeypatch, tmp_path, atual=atual, baseline=_SCHEMA_BASE)
    assert not report.ok
    assert any("`$.incerteza_nova`" in e for e in report.errors), report.errors


def test_campo_novo_projetado_passa(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Projetar é a saída principal — campo coberto não exige escape."""
    atual = json.loads(json.dumps(_SCHEMA_BASE))
    atual["properties"]["incerteza_nova"] = {"type": "number"}
    manifest = json.loads(json.dumps(_MANIFEST_FAKE))
    manifest["context_sections"][0]["blocks"][0]["fields"].append({"path": "$.incerteza_nova"})
    report = _drift(monkeypatch, tmp_path, atual=atual, baseline=_SCHEMA_BASE, manifest=manifest)
    assert report.ok, report.errors


def test_campo_novo_escapado_com_razao_passa(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A segunda saída é declarar a razão — ato consciente que o `warn` não exigia."""
    atual = json.loads(json.dumps(_SCHEMA_BASE))
    atual["properties"]["_lineage"] = {"type": "object"}
    report = _drift(monkeypatch, tmp_path, atual=atual, baseline=_SCHEMA_BASE)
    assert report.ok, report.errors


def test_campo_preexistente_nao_bloqueia(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Polaridade: o gate mira o campo NOVO. Débito herdado vira contagem, não erro —
    senão a saída barata seria escapar 92 paths de uma vez, e o escape viraria decoração."""
    atual = json.loads(json.dumps(_SCHEMA_BASE))
    atual["properties"]["ja_existia_sem_projecao"] = {"type": "number"}
    report = _drift(monkeypatch, tmp_path, atual=atual, baseline=atual)
    assert report.ok, report.errors
    assert any("débito herdado" in w for w in report.warnings), report.warnings


def test_escape_cobre_a_subarvore() -> None:
    """Declarar `$.narrativas` vale por suas folhas — senão o escape não escaparia nada."""
    assert internals._escapado("$.narrativas.resumo_executivo")
    assert not internals._escapado("$.patrimonio.bruto")


def test_sem_baseline_bloqueia_sob_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Instrumento mudo é hard-fail sob `strict` (precedente `check_scheduled_workflows`):
    degradar em silêncio recriaria o fail-open que esta lane fecha."""
    monkeypatch.setattr(internals, "_schema_at", lambda ref, rel: None)
    report = internals.CoverageReport()
    internals.check_schema_manifest_drift(E5_SCHEMA, MANIFEST, report, strict_baseline=True)
    assert not report.ok
    assert any("inalcançável" in e for e in report.errors), report.errors


def test_clone_raso_bloqueia_sob_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cenário REAL do checkout raso: `origin/main` ausente e `HEAD` presente — comparar
    com HEAD devolve zero campos novos e o gate ficaria verde sem ter medido nada."""
    real = internals._schema_at
    monkeypatch.setattr(
        internals,
        "_schema_at",
        lambda ref, rel: None if ref == "origin/main" else real(ref, rel),
    )
    report = internals.CoverageReport()
    internals.check_schema_manifest_drift(E5_SCHEMA, MANIFEST, report, strict_baseline=True)
    assert not report.ok, "baseline degradado para HEAD passou batido — gate cego"
    assert any("inalcançável" in e for e in report.errors), report.errors


def test_sem_baseline_degrada_sem_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chamada de biblioteca (teste, script) avisa em vez de travar — a rigidez é da
    INVOCAÇÃO do gate, que a liga via `strict_baseline`."""
    monkeypatch.setattr(internals, "_schema_at", lambda ref, rel: None)
    report = internals.CoverageReport()
    internals.check_schema_manifest_drift(E5_SCHEMA, MANIFEST, report, strict_baseline=False)
    assert report.ok, report.errors
    assert any("inalcançável" in w for w in report.warnings), report.warnings


def test_git_changed_paths_le_diff_real(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A derivação lê `git diff` de verdade — sem baseline em disco para conflitar."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for key, val in (("user.email", "t@t.dev"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", key, val], check=True)
    alvo = tmp_path / "alvo.json"
    alvo.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "base"], check=True)
    monkeypatch.setattr(internals, "REPO_ROOT", tmp_path)

    assert internals._git_changed_paths() == frozenset()
    alvo.write_text('{"novo": 1}\n', encoding="utf-8")
    assert "alvo.json" in internals._git_changed_paths()


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
