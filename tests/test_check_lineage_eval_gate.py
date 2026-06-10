"""Gate de PR do eval de lineage (ADR-281 · A25.l4): matching de paths vigiados e degradação graciosa offline — sem rede (gh/git mockados via monkeypatch)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "check_lineage_eval_gate", _REPO / "dev" / "check_lineage_eval_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_watched_files_matches_lineage_surface():
    gate = _load_gate()
    changed = [
        "pipeline/domain/services/lineage_render_llm.py",
        "pipeline/domain/services/lineage_diff.py",
        "pipeline/domain/lineage_registry.py",
        "config/prompts/lineage_debug.yaml",
        "pipeline/domain/services/patrimonio_calculator.py",
        "docs/adr/281-lineage-rule-ref-debug-substrate.md",
        "tests/lineage_eval/cases.py",
    ]
    assert gate.watched_files(changed) == [
        "pipeline/domain/services/lineage_render_llm.py",
        "pipeline/domain/services/lineage_diff.py",
        "pipeline/domain/lineage_registry.py",
        "config/prompts/lineage_debug.yaml",
    ]


def test_pass_when_pr_does_not_touch_lineage(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "changed_files", lambda: ["backend/app/api/reports.py"])
    assert gate.main() == 0


def test_graceful_pass_when_diff_unresolvable(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "changed_files", lambda: None)
    assert gate.main() == 0


def test_graceful_pass_when_gh_offline(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "changed_files", lambda: ["pipeline/domain/lineage_registry.py"])
    monkeypatch.setattr(gate, "open_failure_issues", lambda: None)
    assert gate.main() == 0


def test_fails_when_lineage_touched_and_issue_open(monkeypatch, capsys):
    gate = _load_gate()
    monkeypatch.setattr(gate, "changed_files", lambda: ["pipeline/domain/lineage_registry.py"])
    monkeypatch.setattr(
        gate, "open_failure_issues", lambda: [{"number": 99, "title": "lineage eval < 85%"}]
    )
    assert gate.main() == 1
    err = capsys.readouterr().err
    assert "#99" in err and "lineage_registry" in err


def test_passes_when_lineage_touched_and_no_issue(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "changed_files", lambda: ["config/prompts/lineage_debug.yaml"])
    monkeypatch.setattr(gate, "open_failure_issues", lambda: [])
    assert gate.main() == 0
