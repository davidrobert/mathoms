"""Gate de fronteira pipeline↔backend (A36.l1a · ADR-325).

Trava: (a) o repo real passa sob o gate novo (offenders allowlistados +
exercidos); (b) um `from backend...` novo em stage não-allowlistado FALHA;
(c) allowlist exime só `backend`, não frameworks; (d) entrada de allowlist
não-exercida (stale) falha — o allowlist só encolhe.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "cpb", _REPO / "dev" / "check_pipeline_boundaries.py"
)
assert _spec and _spec.loader
cpb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpb)


def _write(tmp_path: Path, src: str) -> Path:
    p = tmp_path / "mod.py"
    p.write_text(src, encoding="utf-8")
    return p


def test_repo_real_passa_sob_o_gate() -> None:
    """Part A deixa o repo verde: offenders allowlistados, nenhum stale."""
    assert cpb.collect_violations() == []


def test_backend_novo_em_stage_nao_allowlistado_falha(tmp_path: Path) -> None:
    viol, exercised = cpb._scan_file(
        _write(tmp_path, "from backend.app.services import x\n"), backend_allowed=False
    )
    assert viol and not exercised


def test_allowlistado_exime_backend_mas_nao_framework(tmp_path: Path) -> None:
    ok, exercised = cpb._scan_file(
        _write(tmp_path, "from backend.app.x import y\n"), backend_allowed=True
    )
    assert ok == [] and exercised is True
    viol, _ = cpb._scan_file(_write(tmp_path, "import sqlalchemy\n"), backend_allowed=True)
    assert viol  # framework segue proibido mesmo em arquivo allowlistado


def test_entrada_stale_do_allowlist_falha(tmp_path: Path, monkeypatch) -> None:
    """Allowlist só encolhe: entrada cujo arquivo não importa backend é reportada."""
    (tmp_path / "ghost.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(cpb, "_PIPELINE_ROOT", tmp_path)
    monkeypatch.setattr(cpb, "_BACKEND_ALLOWLIST", {"ghost.py": "sem import de backend"})
    errors = cpb.collect_violations()
    assert any("stale allowlist entry" in e and "ghost.py" in e for e in errors)
