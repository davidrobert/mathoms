"""Gate estático de action de risco em job required (ADR-320 §Emenda 2026-08-05): docker/não-registrada falha, node/composite registrada passa, prova de mutação nos dois sentidos — 100% offline, sem chamar gh."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_MOD = "check_required_job_actions"


def _load_gate():
    spec = importlib.util.spec_from_file_location(_MOD, _REPO / "dev" / f"{_MOD}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MOD] = module
    spec.loader.exec_module(module)
    return module


def _write_workflow(tmp_path: Path, uses_line: str) -> Path:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "fixture.yml").write_text(
        f"""
jobs:
  required-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - {uses_line}
""",
        encoding="utf-8",
    )
    return workflow_dir


def _registry(**actions) -> dict:
    return {
        "actions": {
            "actions/checkout": {"runs_using": "node20"},
            **actions,
        },
        "required_jobs": {"fixture.yml": ["required-job"]},
    }


def test_action_docker_reprova(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: some-org/risky-action@abc123")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    registry = _registry(**{"some-org/risky-action": {"runs_using": "docker"}})
    violations = gate.check_all(registry)
    assert len(violations) == 1
    assert "vedado em job required" in violations[0].reason


def test_action_nao_registrada_reprova(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: some-org/unknown-action@abc123")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    registry = _registry()
    violations = gate.check_all(registry)
    assert len(violations) == 1
    assert "não registrada" in violations[0].reason


def test_action_node_registrada_passa(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: some-org/safe-action@abc123")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    registry = _registry(**{"some-org/safe-action": {"runs_using": "node20"}})
    assert gate.check_all(registry) == []


def test_action_local_composite_e_ignorada(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: ./.github/actions/local-thing")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    assert gate.check_all(_registry()) == []


def test_registro_real_do_repo_esta_verde():
    """Prova que o registro real cobre o fecho real de jobs required."""
    gate = _load_gate()
    registry = gate.load_registry()
    assert gate.check_all(registry) == []


def test_registro_real_pega_docker_injetado():
    """Mutação sobre o registro real: injeta `runs_using: docker` numa action
    que o fecho required de verdade usa e confere que o gate reprova — prova
    que o teste anterior não passa por vacuidade (fecho vazio)."""
    gate = _load_gate()
    registry = gate.load_registry()
    used_refs = {
        ref
        for workflow_file, jobs in registry["required_jobs"].items()
        for job in jobs
        for ref in gate._job_uses_refs(gate.WORKFLOW_DIR / workflow_file, job)
        if not ref.startswith(".")
    }
    assert used_refs, "fecho required não referencia nenhuma action — teste vacuo"
    target = sorted(used_refs)[0]
    registry["actions"][target]["runs_using"] = "docker"
    violations = gate.check_all(registry)
    assert any(v.action_ref == target for v in violations)
