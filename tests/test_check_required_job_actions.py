"""Gate estático do registro de actions (ADR-320 §Emendas 2026-08-03 e 2026-10-08): docker/não-registrada/node20 em required falha, ref divergente ou runtime < node24 em qualquer workflow falha, prova de mutação nos dois sentidos — 100% offline, sem chamar gh."""

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
      - uses: actions/checkout@v5
      - {uses_line}
""",
        encoding="utf-8",
    )
    return workflow_dir


def _registry(**actions) -> dict:
    return {
        "actions": {
            "actions/checkout": {"ref": "v5", "runs_using": "node24"},
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
    registry = _registry(**{"some-org/safe-action": {"ref": "abc123", "runs_using": "node24"}})
    assert gate.check_all(registry) == []
    assert gate.check_pinned_refs(registry) == []


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


def test_action_node20_em_required_reprova(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: some-org/old-action@abc123")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    registry = _registry(**{"some-org/old-action": {"ref": "abc123", "runs_using": "node20"}})
    violations = gate.check_all(registry)
    assert [v.action_ref for v in violations] == ["some-org/old-action"]


def test_ref_divergente_do_registro_reprova(tmp_path, monkeypatch):
    """O buraco que a emenda 2026-10-08 fecha: registro diz node24 para v5, workflow usa v4."""
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: actions/checkout@v4")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    assert gate.check_all(_registry()) == []
    violations = gate.check_pinned_refs(_registry())
    assert len(violations) == 1
    assert "@v4" in violations[0].reason


def test_node20_fora_de_required_reprova(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: some-org/old-action@abc123")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    registry = _registry(**{"some-org/old-action": {"ref": "abc123", "runs_using": "node20"}})
    registry["required_jobs"] = {}
    violations = gate.check_pinned_refs(registry)
    assert len(violations) == 1
    assert "piso node24" in violations[0].reason


def test_docker_fora_de_required_passa(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: some-org/docker-action@abc123")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    registry = _registry(**{"some-org/docker-action": {"ref": "abc123", "runs_using": "docker"}})
    registry["required_jobs"] = {}
    assert gate.check_pinned_refs(registry) == []


def test_registro_real_casa_todo_uses_do_repo():
    gate = _load_gate()
    registry = gate.load_registry()
    assert gate.check_pinned_refs(registry) == []


def test_registro_real_pega_ref_divergente_injetado():
    """Mutação sobre o registro real: troca o ref de uma action usada e confere que
    o gate reprova — prova que o verde anterior não é vacuidade (nenhum uses lido)."""
    gate = _load_gate()
    registry = gate.load_registry()
    used = gate.iter_action_uses(gate.WORKFLOW_DIR)
    assert used, "nenhum uses: lido em .github/workflows — teste vacuo"
    target = used[0].action
    registry["actions"][target]["ref"] = "v0-inexistente"
    violations = gate.check_pinned_refs(registry)
    assert any(v.action_ref == target for v in violations)


def test_suggest_imprime_entrada_com_ref_em_uso(tmp_path, monkeypatch):
    gate = _load_gate()
    workflow_dir = _write_workflow(tmp_path, "uses: some-org/new-action@v9")
    monkeypatch.setattr(gate, "WORKFLOW_DIR", workflow_dir)
    monkeypatch.setattr(gate, "_fetch_runs_using", lambda action, ref: "node24")
    violations = gate.check_pinned_refs(_registry())
    entries = gate.suggest_entries(violations)
    assert len(entries) == 1
    assert 'some-org/new-action:\n    ref: "v9"\n    runs_using: node24' in entries[0]
