"""Testes do núcleo puro de ``dev/go_parity_run.py`` (F2 GO_SHELL, [[ADR-150]] §7).

Cobre o que dá para exercitar sem disparar run: resolução de DB, guard de
inbox, extração de run_id e a tabela-verdade do veredito. O caminho de
orquestração (make/dispatch/poll) é exercitado ao vivo pelo `make go-parity`.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import dev.go_parity_run as gpr  # noqa: E402
from dev.go_parity_run import (  # noqa: E402
    _RUN_ID_RE,
    PYTHON_ARM,
    GateError,
    RunRecord,
    _assert_consumed,
    _db_path,
    _execute_both_arms,
    _inbox_files,
    _llm_artifact_count,
    _redis_endpoint,
    _ws_flags,
    assert_preconditions,
    render_verdict,
)

WS = "1b9f2cf5-0000-0000-0000-000000000000"

# Convenção do repo: 6390 é porta fechada (nunca acerta o Redis de dev por acidente).
CLOSED_PORT_URL = "redis://127.0.0.1:6390/0"

# Referência capturada antes de qualquer monkeypatch — o autouse abaixo troca o
# atributo do módulo, e o teste dedicado precisa da função real.
_REAL_STACK_CHECK = gpr.assert_stack_up


@pytest.fixture(autouse=True)
def _stub_stack_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """O guard de stack abre socket real; neutralizar evita que a suíte dependa
    do Redis de dev estar de pé. Ele tem teste dedicado abaixo."""
    monkeypatch.setattr(gpr, "assert_stack_up", lambda: None)


def test_stack_guard_fails_on_closed_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem este guard o dispatch enfileira e o gate pendura até o timeout de 1800s."""
    monkeypatch.setenv("MATHOMS_REDIS_URL", CLOSED_PORT_URL)
    with pytest.raises(GateError, match="Redis inacessível"):
        _REAL_STACK_CHECK()


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """DB mínimo com as duas tabelas que o harness lê (nunca mocar DB — CLAUDE.md)."""
    path = tmp_path / "t.db"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE pipeline_runs (
            id TEXT PRIMARY KEY, workspace_id TEXT, status TEXT, started_at TEXT
        );
        CREATE TABLE pipeline_artifacts (id TEXT PRIMARY KEY, pipeline_run_id TEXT, stage TEXT);
        """
    )
    con.execute(
        "INSERT INTO pipeline_runs VALUES ('r1', ?, 'completed', '2026-08-01 00:00:00')", (WS,)
    )
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


@pytest.mark.parametrize("status", ["pending", "running"])
def test_active_run_blocks_gate(status: str, tmp_path: Path, db: sqlite3.Connection) -> None:
    """Um `pending` órfão de tentativa anterior faria o dispatch dar ConflictError no meio."""
    (tmp_path / WS / "inbox").mkdir(parents=True)
    db.execute("INSERT INTO pipeline_runs VALUES ('r2', ?, ?, '2026-08-02 00:00:00')", (WS, status))
    db.commit()
    with pytest.raises(GateError, match="run ativo"):
        assert_preconditions(WS, tmp_path, db)


def test_terminal_runs_do_not_block(tmp_path: Path, db: sqlite3.Connection) -> None:
    (tmp_path / WS / "inbox").mkdir(parents=True)
    db.execute("INSERT INTO pipeline_runs VALUES ('r2', ?, 'failed', '2026-08-02 00:00:00')", (WS,))
    db.commit()
    assert_preconditions(WS, tmp_path, db)


def test_llm_artifact_count_catches_escalation(db: sqlite3.Connection) -> None:
    """A pré-condição 0-LLM é assert de run, não de fixture — precisa pegar o stage LLM."""
    assert _llm_artifact_count(db, "r1") == 0
    db.execute("INSERT INTO pipeline_artifacts VALUES ('a1', 'r1', 'extract_with_llm')")
    db.commit()
    assert _llm_artifact_count(db, "r1") == 1


def _stub_payloads(monkeypatch: pytest.MonkeyPatch, payloads: dict) -> None:
    import dev.go_parity_gate as gate

    monkeypatch.setattr(gate, "collect_run_artifacts", lambda _rid: payloads)


def test_fallback_flag_detected_in_e2_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contar stage '%llm%' é cego: caixa.py monta o SDK direto e não vira stage LLM."""
    _stub_payloads(
        monkeypatch,
        {
            ("extract_statements", "x_caixa_extratoconta"): {"requires_llm_fallback": True},
            ("extract_statements", "y_itau_extratoconta"): {"requires_llm_fallback": False},
            ("analyze_finances", "analise"): {"total": 1},
        },
    )
    assert gpr._llm_fallback_docs("r1") == ["extract_statements/x_caixa_extratoconta"]


def test_tier1_rejects_run_with_fallback_even_sem_stage_llm(
    monkeypatch: pytest.MonkeyPatch, db: sqlite3.Connection
) -> None:
    """O caso real de 2026-08-03: 0 artefato de stage LLM, mas houve chamada paga."""
    _stub_payloads(monkeypatch, {("extract_statements", "k"): {"requires_llm_fallback": True}})
    assert _llm_artifact_count(db, "r1") == 0
    with pytest.raises(GateError, match="não é 0-LLM"):
        gpr._assert_llm_free(db, "r1", PYTHON_ARM, "tier1")


def test_tier2_tolerates_fallback(monkeypatch: pytest.MonkeyPatch, db: sqlite3.Connection) -> None:
    _stub_payloads(monkeypatch, {("extract_statements", "k"): {"requires_llm_fallback": True}})
    assert gpr._assert_llm_free(db, "r1", PYTHON_ARM, "tier2") == 1


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


def test_redis_endpoint_parses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHOMS_REDIS_URL", "redis://127.0.0.1:6390/1")
    assert _redis_endpoint() == ("127.0.0.1", 6390)


def test_redis_endpoint_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MATHOMS_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert _redis_endpoint() == ("localhost", 6379)


def test_pending_past_grace_fails_fast() -> None:
    """Worker no chão: sem isso o gate esperaria o timeout inteiro (1800s)."""
    with pytest.raises(GateError, match="nenhum worker Celery"):
        _assert_consumed("r1", "pending", gpr._PENDING_GRACE_S + 1)


def test_pending_inside_grace_tolerated() -> None:
    _assert_consumed("r1", "pending", 5.0)


def test_running_never_trips_pending_guard() -> None:
    """`running` é run demorado legítimo — só `pending` significa não-consumido."""
    _assert_consumed("r1", "running", 99_999.0)


def test_pair_order_alternates_who_goes_first() -> None:
    """Se um braço sempre corre primeiro, posição ordinal vira variável confundida com executor."""
    assert [a.name for a in gpr._pair_order(0)] == ["python", "go"]
    assert [a.name for a in gpr._pair_order(1)] == ["go", "python"]


def test_interleaved_balances_ordinal_positions(monkeypatch: pytest.MonkeyPatch) -> None:
    """py,py,go,go correlaciona braço com ordem; intercalado não."""
    ordem: list[str] = []
    monkeypatch.setattr(gpr, "switch_arm", lambda arm: None)
    monkeypatch.setattr(
        gpr,
        "_one_run",
        lambda arm, ws, con, args, i: (ordem.append(arm.name), RunRecord(f"{arm.name}{i}"))[1],
    )
    args = argparse.Namespace(runs=2)
    py, go = gpr.execute_interleaved("ws", None, args)
    assert ordem == ["python", "go", "go", "python"]
    assert [r.run_id for r in py] == ["python0", "python1"]
    assert [r.run_id for r in go] == ["go0", "go1"]


def test_arms_restored_to_python_even_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Abortar no braço Go sem restaurar deixaria o dogfood executando via shell Go."""
    switched: list[str] = []
    monkeypatch.setattr(gpr, "switch_arm", lambda arm: switched.append(arm.name))
    monkeypatch.setattr(gpr, "_one_run", lambda *a: (_ for _ in ()).throw(GateError("boom")))
    with pytest.raises(GateError, match="boom"):
        _execute_both_arms("ws", None, argparse.Namespace(runs=2))
    assert switched[-1] == PYTHON_ARM.name, "última troca tem que voltar ao Python"


def _fail_only_after(state: dict) -> object:
    """switch_arm que funciona no corpo e quebra no restore — modela o pior caso real."""

    def fake_switch(arm):
        if state["falhou"]:
            raise GateError("go-off caiu")

    return fake_switch


def test_restore_failure_does_not_mask_original(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Erro no restore não pode engolir a exceção que interessa diagnosticar."""
    state = {"falhou": False}

    def fake_one_run(*_a):
        state["falhou"] = True
        raise GateError("causa raiz")

    monkeypatch.setattr(gpr, "_one_run", fake_one_run)
    monkeypatch.setattr(gpr, "switch_arm", _fail_only_after(state))
    with pytest.raises(GateError, match="causa raiz"):
        _execute_both_arms("ws", None, argparse.Namespace(runs=2))
    assert "FALHA AO RESTAURAR" in capsys.readouterr().err


def test_ws_flags_skip_go_on_control_pass(tmp_path: Path) -> None:
    """No run de controle (go=None) só entram os dois braços Python."""
    main = RunRecord("a", tmp_path / "py.json")
    control = RunRecord("b", tmp_path / "ctl.json")
    assert "--go-ws" not in _ws_flags(main, control, None)
