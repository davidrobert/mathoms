"""Testes do gate de não-consumo dos campos em de-leak (A24.l1 · F2-DB8)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import dev.check_no_leak_field_consumers as gate  # noqa: E402


def test_repo_is_green_today():
    assert gate.collect_violations() == []


def test_new_reader_in_pipeline_is_violation(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "_REPO_ROOT", tmp_path)
    leak = tmp_path / "pipeline" / "domain" / "novo_consumidor.py"
    leak.parent.mkdir(parents=True)
    leak.write_text('tipo = tx.get("tipo_lancamento")\n')

    errors = gate.collect_violations()
    assert len(errors) == 1
    assert "tipo_lancamento" in errors[0] and "novo_consumidor.py:1" in errors[0]


def test_allowlisted_fallback_does_not_fire(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "_REPO_ROOT", tmp_path)
    allowed = tmp_path / "pipeline" / "domain" / "models" / "document.py"
    allowed.parent.mkdir(parents=True)
    allowed.write_text('norm = d.get("numero_conta_norm") or normalize(x)\n')

    assert gate.collect_violations() == []


def test_tests_dirs_are_excluded(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "_REPO_ROOT", tmp_path)
    fixture = tmp_path / "backend" / "tests" / "test_x.py"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('payload = {"numero_conta_norm": "556677"}\n')

    assert gate.collect_violations() == []
