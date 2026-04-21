"""Testes para dev/check_main_drift.py.

Cobrem os 4 caminhos do hook pre-push:
  - Push para main com drift → bloqueia (exit 1 + mensagem actionable)
  - Push para main sem drift → passa (exit 0)
  - Push para feature branch muito atrás de main → avisa, não bloqueia
  - Bypass emergencial MATHOMS_SKIP_DRIFT_CHECK=1 → passa

Ver CLAUDE.md §"Protocolo obrigatório" item 5.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE_PATH = Path(__file__).parent.parent / "dev" / "check_main_drift.py"
_SPEC = importlib.util.spec_from_file_location("check_main_drift", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
cmd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cmd)


_ZEROS = "0" * 40
_A = "a" * 40
_B = "b" * 40
_C = "c" * 40


def _stub_run(script: dict[tuple, tuple[int, str]]):
    """Factory de fake subprocess.run que consulta dict (args_tuple → (rc, stdout))."""
    def _fake(cmd_args, capture_output=False, text=False):
        key = tuple(cmd_args)
        if key not in script:
            raise AssertionError(f"Unexpected git call: {key}")
        rc, out = script[key]
        return subprocess.CompletedProcess(cmd_args, rc, stdout=out, stderr="")
    return _fake


@pytest.fixture(autouse=True)
def _clear_bypass_env(monkeypatch):
    monkeypatch.delenv("MATHOMS_SKIP_DRIFT_CHECK", raising=False)


# ─── Bypass ─────────────────────────────────────────────────────────────

def test_bypass_env_skips_entirely(monkeypatch, capsys):
    monkeypatch.setenv("MATHOMS_SKIP_DRIFT_CHECK", "1")
    monkeypatch.setattr("sys.stdin", io.StringIO(f"refs/heads/main {_A} refs/heads/main {_B}\n"))
    # Mesmo com script vazio, não deve chamar git — bypass early return
    with patch("subprocess.run", side_effect=AssertionError("should not be called")):
        assert cmd.main() == 0
    assert capsys.readouterr().err == ""


# ─── Empty stdin ────────────────────────────────────────────────────────

def test_empty_stdin_returns_zero(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    with patch("subprocess.run", side_effect=AssertionError("should not be called")):
        assert cmd.main() == 0


# ─── Push para main ─────────────────────────────────────────────────────

def test_push_main_with_zero_drift_passes(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(f"refs/heads/main {_A} refs/heads/main {_B}\n"))
    script = {
        ("git", "fetch", "origin", "--quiet"): (0, ""),
        ("git", "rev-list", "--count", f"{_A}..origin/main"): (0, "0"),
    }
    with patch("subprocess.run", side_effect=_stub_run(script)):
        assert cmd.main() == 0
    assert capsys.readouterr().err == ""


def test_push_main_with_drift_blocks(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(f"refs/heads/main {_A} refs/heads/main {_B}\n"))
    script = {
        ("git", "fetch", "origin", "--quiet"): (0, ""),
        ("git", "rev-list", "--count", f"{_A}..origin/main"): (0, "3"),
    }
    with patch("subprocess.run", side_effect=_stub_run(script)):
        assert cmd.main() == 1
    err = capsys.readouterr().err
    assert "bloqueado" in err
    assert "3 commit(s)" in err
    assert "rebase origin/main" in err
    assert "MATHOMS_SKIP_DRIFT_CHECK" in err


# ─── Push para branch feature ───────────────────────────────────────────

def test_push_feature_branch_small_drift_silent(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(f"refs/heads/agent/x {_A} refs/heads/agent/x {_B}\n"),
    )
    script = {
        ("git", "fetch", "origin", "--quiet"): (0, ""),
        ("git", "rev-list", "--count", f"{_A}..origin/main"): (0, "2"),  # < threshold
    }
    with patch("subprocess.run", side_effect=_stub_run(script)):
        assert cmd.main() == 0
    assert capsys.readouterr().err == ""


def test_push_feature_branch_large_drift_warns(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(f"refs/heads/agent/x {_A} refs/heads/agent/x {_B}\n"),
    )
    script = {
        ("git", "fetch", "origin", "--quiet"): (0, ""),
        ("git", "rev-list", "--count", f"{_A}..origin/main"): (0, "12"),  # ≥ threshold
    }
    with patch("subprocess.run", side_effect=_stub_run(script)):
        assert cmd.main() == 0
    err = capsys.readouterr().err
    assert "12 commit(s) atrás" in err
    assert "item 6" in err  # cita CLAUDE.md


# ─── Edge cases ─────────────────────────────────────────────────────────

def test_delete_branch_is_skipped(monkeypatch, capsys):
    """local_sha = 0000...0000 significa delete — não deve chamar rev-list."""
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(f"refs/heads/main {_ZEROS} refs/heads/main {_B}\n"),
    )
    script = {
        ("git", "fetch", "origin", "--quiet"): (0, ""),
    }
    with patch("subprocess.run", side_effect=_stub_run(script)):
        assert cmd.main() == 0
    assert capsys.readouterr().err == ""


def test_fetch_failure_degrades_gracefully(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(f"refs/heads/main {_A} refs/heads/main {_B}\n"))
    script = {
        ("git", "fetch", "origin", "--quiet"): (1, ""),  # offline, etc.
    }
    with patch("subprocess.run", side_effect=_stub_run(script)):
        assert cmd.main() == 0
    err = capsys.readouterr().err
    assert "fetch origin falhou" in err
    assert "pulando validação" in err


def test_multiple_refs_main_blocks_feature_warns(monkeypatch, capsys):
    """Push simultâneo de main (drift) + feature (drift): main bloqueia."""
    stdin = (
        f"refs/heads/main {_A} refs/heads/main {_B}\n"
        f"refs/heads/agent/y {_C} refs/heads/agent/y {_B}\n"
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    script = {
        ("git", "fetch", "origin", "--quiet"): (0, ""),
        ("git", "rev-list", "--count", f"{_A}..origin/main"): (0, "2"),
        ("git", "rev-list", "--count", f"{_C}..origin/main"): (0, "8"),
    }
    with patch("subprocess.run", side_effect=_stub_run(script)):
        assert cmd.main() == 1
    err = capsys.readouterr().err
    assert "bloqueado" in err  # main
    assert "8 commit(s) atrás" in err  # warning feature
