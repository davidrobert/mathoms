"""Watchdog de drift de duração de job de CI (ADR-210 §Adendo 2026-08-05): amostra pequena não dispara, mediana sob o teto não dispara, mediana sobre o teto dispara com o formato certo — sem rede (gh mockado via monkeypatch)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MOD = "check_backend_job_duration_drift"


def _load_gate():
    spec = importlib.util.spec_from_file_location(_MOD, _REPO / "dev" / f"{_MOD}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MOD] = module
    spec.loader.exec_module(module)
    return module


def test_amostra_pequena_nao_dispara():
    gate = _load_gate()
    report = gate.check_drift([25.0, 25.0, 25.0], "job-x", ceiling_min=20, threshold_pct=60)
    assert report is None


def test_mediana_sob_o_teto_nao_dispara():
    gate = _load_gate()
    durations = [9.0, 9.5, 10.0, 10.5, 11.0, 11.5]
    report = gate.check_drift(durations, "job-x", ceiling_min=20, threshold_pct=60)
    assert report is None


def test_mediana_sobre_o_teto_dispara():
    gate = _load_gate()
    durations = [13.0, 13.5, 14.0, 14.5, 15.0]
    report = gate.check_drift(durations, "job-x", ceiling_min=20, threshold_pct=60)
    assert report is not None
    assert report.median_min == 14.0
    assert report.n_samples == 5


def test_render_report_vazio_quando_sem_drift():
    gate = _load_gate()
    assert gate.render_report(None) == ""


def test_render_report_cita_job_e_mediana():
    gate = _load_gate()
    report = gate.DriftReport("job-x", 14.0, 20.0, 60.0, 5)
    rendered = gate.render_report(report)
    assert "job-x" in rendered
    assert "14.00min" in rendered
    assert "ADR-210" in rendered


def test_fetch_recent_job_durations_agrega_por_run(monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "_recent_successful_run_ids", lambda *_: [1, 2, 3])
    durations_by_run = {1: 9.0, 2: None, 3: 11.0}
    monkeypatch.setattr(
        gate, "_job_duration_minutes", lambda repo, run_id, job: durations_by_run[run_id]
    )
    result = gate.fetch_recent_job_durations("o/r", "ci.yml", "job-x", 3)
    assert result == [9.0, 11.0]


def test_main_offline_degrada_para_pass(monkeypatch, capsys):
    gate = _load_gate()
    monkeypatch.setattr(gate, "repo_slug", lambda: None)
    monkeypatch.setattr(sys, "argv", ["prog", "--report"])
    assert gate.main() == 0
    assert capsys.readouterr().out.strip() == ""
