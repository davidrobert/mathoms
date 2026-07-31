"""Watchdog de liveness dos workflows agendados (ADR-210 §camada 4): cobertura do manifesto, os 3 sinais, ciclo de vida do waiver e degradação graciosa offline — sem rede (gh mockado via monkeypatch)."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MOD = "check_scheduled_workflows"


def _load_gate():
    """`@dataclass` resolve tipos via sys.modules — registre antes de exec_module."""
    spec = importlib.util.spec_from_file_location(_MOD, _REPO / "dev" / f"{_MOD}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MOD] = module
    spec.loader.exec_module(module)
    return module


def _entry(**over) -> dict:
    base = {"file": "nightly.yml", "max_age_days": 3, "why": "x"}
    return {**base, **over}


def test_manifesto_cobre_todo_workflow_agendado_do_disco():
    """O manifesto apodrece se um `schedule:` novo puder entrar sem entrada."""
    gate = _load_gate()
    assert gate.check_manifest_coverage(gate.load_manifest()) == []


def test_manifesto_denuncia_orfao_e_fantasma():
    gate = _load_gate()
    violations = gate.check_manifest_coverage([_entry(file="nao-existe.yml")])
    signals = {(v.signal, v.workflow) for v in violations}
    assert ("S0", "nao-existe.yml") in signals
    assert ("S0", "nightly.yml") in signals


def test_s1_pega_workflow_desabilitado(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "workflow_state", lambda *_: "disabled_manually")
    found = gate._check_state("o/r", _entry())
    assert [v.signal for v in found] == ["S1"]
    assert "disabled_manually" in found[0].detail


def test_s2_pega_cron_parado(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "last_scheduled_run_age", lambda *_: 44)
    found = gate._check_liveness("o/r", _entry(), date(2026, 7, 30))
    assert [v.signal for v in found] == ["S2"]
    assert "44d" in found[0].detail


def test_s2_tolera_run_dentro_da_janela(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "last_scheduled_run_age", lambda *_: 2)
    assert gate._check_liveness("o/r", _entry(), date(2026, 7, 30)) == []


def test_s3_pega_issue_apodrecendo(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(
        gate,
        "stale_alert_issues",
        lambda *_: [{"number": 642, "title": "drift", "age": 46}],
    )
    entry = _entry(alerts=[{"label": "main-smoke-fail", "max_issue_age_days": 7}])
    found = gate._check_issue_rot(entry, date(2026, 7, 30))
    assert [v.signal for v in found] == ["S3"]
    assert "#642" in found[0].detail


def test_s3_ignora_label_sem_limite_de_idade(monkeypatch):
    """`ci-budget` é crônica por design — idade não é sinal de abandono."""
    gate = _load_gate()
    monkeypatch.setattr(
        gate, "stale_alert_issues", lambda *_: [{"number": 1, "title": "x", "age": 90}]
    )
    entry = _entry(alerts=[{"label": "ci-budget"}])
    assert gate._check_issue_rot(entry, date(2026, 7, 30)) == []


def test_waiver_vigente_degrada_violacao_para_warning(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "workflow_state", lambda *_: "disabled_manually")
    monkeypatch.setattr(gate, "last_scheduled_run_age", lambda *_: 44)
    entry = _entry(waiver={"until": "2026-08-13", "reason": "decisão do owner"})
    found = gate.check_entry("o/r", entry, date(2026, 7, 30))
    assert found and all(v.waived for v in found)


def test_waiver_vencido_vira_hard_fail(monkeypatch):
    """A exceção não pode apodrecer como apodreceu a Issue que ela cobre."""
    gate = _load_gate()
    monkeypatch.setattr(gate, "workflow_state", lambda *_: "active")
    monkeypatch.setattr(gate, "last_scheduled_run_age", lambda *_: 0)
    entry = _entry(waiver={"until": "2026-08-13", "reason": "x"})
    found = gate.check_entry("o/r", entry, date(2026, 8, 20))
    assert [v.signal for v in found] == ["WAIVER"]
    assert not found[0].waived


def test_offline_degrada_para_pass(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "repo_slug", lambda: None)
    monkeypatch.setattr("sys.argv", ["check_scheduled_workflows.py"])
    assert gate.main() == 0


def test_escape_hatch_por_label(monkeypatch):
    """Sem isso, o PR que conserta o drift não mergeia — deadlock."""
    gate = _load_gate()
    monkeypatch.setenv("MATHOMS_PR_LABELS", "ops-override,size:S")
    assert gate.pr_has_override() is True
    monkeypatch.setenv("MATHOMS_PR_LABELS", "size:S")
    assert gate.pr_has_override() is False


def test_modo_report_nunca_falha(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "repo_slug", lambda: "o/r")
    monkeypatch.setattr(gate, "collect", lambda *_: [gate.Violation("S1", "x.yml", "d")])
    monkeypatch.setattr("sys.argv", ["check_scheduled_workflows.py", "--report"])
    assert gate.main() == 0
