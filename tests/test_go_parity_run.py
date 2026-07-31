"""Testes do núcleo puro de ``dev/go_parity_run.py`` (F2 GO_SHELL, [[ADR-150]] §7).

Cobre o que dá para exercitar sem disparar run: resolução de DB, guard de
inbox, extração de run_id e a tabela-verdade do veredito. O caminho de
orquestração (make/dispatch/poll) é exercitado ao vivo pelo `make go-parity`.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.go_parity_run import (  # noqa: E402
    _RUN_ID_RE,
    GateError,
    RunRecord,
    _db_path,
    _inbox_files,
    _llm_artifact_count,
    _ws_flags,
    assert_preconditions,
    render_verdict,
)

WS = "1b9f2cf5-0000-0000-0000-000000000000"


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """DB mínimo com as duas tabelas que o harness lê (nunca mocar DB — CLAUDE.md)."""
    path = tmp_path / "t.db"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE pipeline_runs (id TEXT PRIMARY KEY, workspace_id TEXT, status TEXT);
        CREATE TABLE pipeline_artifacts (id TEXT PRIMARY KEY, pipeline_run_id TEXT, stage TEXT);
        """
    )
    con.execute("INSERT INTO pipeline_runs VALUES ('r1', ?, 'completed')", (WS,))
    con.commit()
    return con


def test_db_path_prefers_explicit(tmp_path: Path) -> None:
    assert _db_path(str(tmp_path / "x.db")) == tmp_path / "x.db"


def test_db_path_falls_back_to_repo_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MATHOMS_DATABASE_URL", raising=False)
    assert _db_path(None) == _REPO / "mathoms.db"


def test_db_path_rejects_non_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tier-1 foi reancorado no dogfood SQLite; Postgres exige o re-gate (emenda 2026-07-31)."""
    monkeypatch.setenv("MATHOMS_DATABASE_URL", "postgresql+asyncpg://h/d")
    with pytest.raises(GateError, match="SQLite"):
        _db_path(None)


def test_inbox_files_empty_when_dir_absent(tmp_path: Path) -> None:
    assert _inbox_files(WS, tmp_path) == []


def test_inbox_files_counts_nested(tmp_path: Path) -> None:
    nested = tmp_path / WS / "inbox" / "sub"
    nested.mkdir(parents=True)
    (nested / "a.pdf").write_text("x")
    (tmp_path / WS / "inbox" / "b.csv").write_text("y")
    assert len(_inbox_files(WS, tmp_path)) == 2


def test_precondition_blocks_on_non_empty_inbox(tmp_path: Path, db: sqlite3.Connection) -> None:
    inbox = tmp_path / WS / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "nao_classificado.xls").write_text("x")
    with pytest.raises(GateError, match="inbox do workspace tem 1"):
        assert_preconditions(WS, tmp_path, db)


def test_precondition_passes_on_empty_inbox(tmp_path: Path, db: sqlite3.Connection) -> None:
    (tmp_path / WS / "inbox").mkdir(parents=True)
    assert_preconditions(WS, tmp_path, db)


def test_precondition_rejects_unknown_workspace(tmp_path: Path, db: sqlite3.Connection) -> None:
    with pytest.raises(GateError, match="não tem run algum"):
        assert_preconditions("outro-uuid", tmp_path, db)


def test_llm_artifact_count_catches_escalation(db: sqlite3.Connection) -> None:
    """A pré-condição 0-LLM é assert de run, não de fixture — precisa pegar o stage LLM."""
    assert _llm_artifact_count(db, "r1") == 0
    db.execute("INSERT INTO pipeline_artifacts VALUES ('a1', 'r1', 'extract_with_llm')")
    db.commit()
    assert _llm_artifact_count(db, "r1") == 1


def test_run_id_regex_extracts_uuid() -> None:
    out = "✅ Run 7f3a1b2c-4d5e-6f70-8901-234567890abc disparado — todos, sem LLM, tier=premium."
    assert _RUN_ID_RE.search(out).group(1) == "7f3a1b2c-4d5e-6f70-8901-234567890abc"


def test_verdict_dirty_control_outranks_clean_mains(capsys: pytest.CaptureFixture) -> None:
    """Controle sujo invalida o gate mesmo com Go↔Py limpo — senão mascara."""
    assert render_verdict(False, [True, True, True]) == 2
    assert "o gate NÃO está pronto" in capsys.readouterr().out


def test_verdict_fails_on_any_divergence() -> None:
    assert render_verdict(True, [True, False, True]) == 1


def test_verdict_passes_when_all_clean() -> None:
    assert render_verdict(True, [True, True, True]) == 0


def test_ws_flags_omitted_without_capture() -> None:
    """Tier-1 não captura evento — passar --*-ws vazio faria o gate comparar lista nula."""
    assert _ws_flags(RunRecord("a"), RunRecord("b"), RunRecord("c")) == []


def test_ws_flags_emitted_per_arm(tmp_path: Path) -> None:
    main = RunRecord("a", tmp_path / "py.json")
    control = RunRecord("b", tmp_path / "ctl.json")
    go = RunRecord("c", tmp_path / "go.json")
    flags = _ws_flags(main, control, go)
    assert flags[::2] == ["--python-ws", "--control-ws", "--go-ws"]
    assert flags[1::2] == [str(main.ws_path), str(control.ws_path), str(go.ws_path)]


def test_ws_flags_skip_go_on_control_pass(tmp_path: Path) -> None:
    """No run de controle (go=None) só entram os dois braços Python."""
    main = RunRecord("a", tmp_path / "py.json")
    control = RunRecord("b", tmp_path / "ctl.json")
    assert "--go-ws" not in _ws_flags(main, control, None)
