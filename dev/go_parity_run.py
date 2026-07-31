#!/usr/bin/env python3
"""Orquestra os runs do gate de paridade Go↔Python (F2 do PLAN-go-shell, [[ADR-150]] §7 Tier-1): dispara N runs determinísticos em cada braço (Python InProcess e shell Go), espera o terminal de cada um e chama ``dev/go_parity_gate.py`` para o veredito."""

# Divisão de trabalho: este script ORQUESTRA (pré-condições, overlay, dispatch,
# espera, pareamento); go_parity_gate.py COMPARA. A separação existe porque o
# gate é puro sobre run_ids — dá para rodá-lo à mão sobre runs pré-existentes.
#
# NÃO MUTA DADO DO OWNER. A pré-condição de inbox vazio (senão o E0 classifica e
# gasta LLM — ver track f2-cutover §Pré-condições 2) é VERIFICADA, nunca
# "consertada" movendo documento: um harness de gate que mexe no workspace real
# do dono é pior que um gate que falha com instrução clara.
#
# Tier-1 só: paridade de artefato. O envelope WS (Tier-2) precisa de psubscribe
# ANTES do dispatch — o run_id não existe antes dele, e pub/sub não faz replay,
# então subscrever depois perde os primeiros eventos de forma não-determinística
# (falso positivo). Fica para a fatia A4.
#
# Uso:
#   python dev/go_parity_run.py --workspace <uuid> [--runs 3] [--json-out dir/]

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

_TERMINAL = frozenset({"completed", "failed", "cancelled"})
_RUN_ID_RE = re.compile(r"Run ([0-9a-f-]{36}) disparado")


class GateError(RuntimeError):
    """Falha de pré-condição ou de orquestração — nunca de paridade (isso é veredito)."""


@dataclass(frozen=True)
class Arm:
    """Um braço do gate: qual executor e como ligá-lo."""

    name: str
    make_target: str


PYTHON_ARM = Arm(name="python", make_target="go-off")
GO_ARM = Arm(name="go", make_target="go-on")


# ───────────────────────────── DB (read-only) ─────────────────────────────


def _db_path(explicit: str | None) -> Path:
    """Resolve o SQLite do dogfood do mesmo jeito que o Makefile (fallback mathoms.db)."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    url = os.environ.get("MATHOMS_DATABASE_URL", "")
    if url.startswith("sqlite"):
        return Path(url.split(":///")[-1]).expanduser().resolve()
    if url:
        raise GateError(f"gate Tier-1 assume SQLite local; MATHOMS_DATABASE_URL={url!r}")
    return _REPO / "mathoms.db"


def _connect(db: Path) -> sqlite3.Connection:
    if not db.exists():
        raise GateError(f"DB não encontrado: {db}")
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def _run_ids(con: sqlite3.Connection, workspace: str) -> set[str]:
    rows = con.execute("SELECT id FROM pipeline_runs WHERE workspace_id=?", (workspace,))
    return {r[0] for r in rows}


def _status(con: sqlite3.Connection, run_id: str) -> str | None:
    row = con.execute("SELECT status FROM pipeline_runs WHERE id=?", (run_id,)).fetchone()
    return row[0] if row else None


def _llm_artifact_count(con: sqlite3.Connection, run_id: str) -> int:
    """Assert de 0-LLM: artefato em extract_with_llm invalida o Tier-1 (ver §Pré-condições 2)."""
    row = con.execute(
        "SELECT COUNT(*) FROM pipeline_artifacts WHERE pipeline_run_id=? AND stage LIKE '%llm%'",
        (run_id,),
    ).fetchone()
    return int(row[0])


# ───────────────────────────── pré-condições ─────────────────────────────


def _inbox_files(workspace: str, storage_root: Path) -> list[Path]:
    inbox = storage_root / workspace / "inbox"
    if not inbox.is_dir():
        return []
    return [p for p in inbox.rglob("*") if p.is_file()]


def assert_preconditions(workspace: str, storage_root: Path, con: sqlite3.Connection) -> None:
    """Falha ANTES de gastar run. Inbox não-vazio faria o E0 classificar (e gastar LLM)."""
    if not _run_ids(con, workspace):
        raise GateError(f"workspace {workspace} não tem run algum — confirme o uuid")
    pending = _inbox_files(workspace, storage_root)
    if pending:
        raise GateError(
            f"inbox do workspace tem {len(pending)} arquivo(s) — o E0 classificaria e "
            f"dispararia o fallback LLM para doc com confidence < 0,8, quebrando o "
            f"determinismo do Tier-1.\n"
            f"   Mova-os para fora antes do gate (e devolva depois):\n"
            f"     {storage_root / workspace / 'inbox'}\n"
            f"   Este harness não move documento seu de propósito."
        )


# ───────────────────────────── orquestração ─────────────────────────────


def _make(target: str, *, env_name: str = "native") -> None:
    cmd = ["make", "-s", target, f"ENV={env_name}"]
    proc = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateError(f"`{' '.join(cmd)}` falhou:\n{proc.stdout}\n{proc.stderr}")


def switch_arm(arm: Arm) -> None:
    print(f"▶  ligando braço {arm.name} (`make {arm.make_target} ENV=native`)…")
    _make(arm.make_target)


def dispatch_run(workspace: str, con: sqlite3.Connection) -> str:
    """Dispara 1 run determinístico e devolve o run_id (diff de conjunto, não parse de log)."""
    before = _run_ids(con, workspace)
    cmd = ["make", "-s", "pipeline-run", f"WS={workspace}", "SKIP_LLM=1", "YES=1"]
    proc = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateError(f"dispatch falhou:\n{proc.stdout}\n{proc.stderr}")
    match = _RUN_ID_RE.search(proc.stdout)
    if match:
        return match.group(1)
    fresh = _run_ids(con, workspace) - before
    if len(fresh) != 1:
        raise GateError(f"esperava 1 run novo, achei {len(fresh)}:\n{proc.stdout}")
    return fresh.pop()


def wait_terminal(con: sqlite3.Connection, run_id: str, *, timeout_s: int, poll_s: int) -> str:
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        status = _status(con, run_id)
        if status in _TERMINAL:
            return status
        if status != last:
            print(f"   · {run_id[:8]} → {status}")
            last = status
        time.sleep(poll_s)
    raise GateError(f"run {run_id} não terminou em {timeout_s}s (status={last})")


def execute_arm(arm: Arm, workspace: str, con: sqlite3.Connection, args) -> list[str]:
    """Liga o braço e roda N runs sequenciais; aborta no primeiro que não completar."""
    switch_arm(arm)
    ids: list[str] = []
    for i in range(args.runs):
        print(f"▶  {arm.name} run {i + 1}/{args.runs}…")
        run_id = dispatch_run(workspace, con)
        status = wait_terminal(con, run_id, timeout_s=args.timeout, poll_s=args.poll)
        if status != "completed":
            raise GateError(f"run {run_id} do braço {arm.name} terminou {status}")
        escalated = _llm_artifact_count(con, run_id)
        if escalated:
            raise GateError(
                f"run {run_id} produziu {escalated} artefato(s) de stage LLM — a "
                f"pré-condição 0-LLM quebrou; o Tier-1 flakaria (ver track §Pré-condições 2)"
            )
        print(f"   ✓ {run_id[:8]} completed, 0 artefato LLM")
        ids.append(run_id)
    return ids


# ───────────────────────────── veredito ─────────────────────────────


def invoke_gate(*, python_run: str, go_run: str | None, control: str | None, args) -> bool:
    """Chama o comparador. go_run=None → é o run de controle Py↔Py."""
    cmd = [sys.executable, str(_REPO / "dev" / "go_parity_gate.py"), "--tier", "tier1"]
    cmd += ["--python-run", python_run, "--go-run", go_run or control or ""]
    if control and go_run:
        cmd += ["--control-run", control]
    if args.storage_root:
        cmd += ["--storage-root", str(args.storage_root)]
    if args.json_out:
        label = f"{'main' if go_run else 'control'}-{(go_run or control or '')[:8]}"
        cmd += ["--json-out", str(Path(args.json_out) / f"{label}.json")]
    proc = subprocess.run(cmd, cwd=_REPO, text=True)
    return proc.returncode == 0


def render_verdict(control_ok: bool, mains: list[bool]) -> int:
    print("\n" + "─" * 60)
    print(f"controle Py↔Py (piso de ruído): {'✓ 0 diff' if control_ok else '✗ diff residual'}")
    print(f"Go↔Py: {sum(mains)}/{len(mains)} pares limpos")
    if not control_ok:
        print("\n::error:: o gate NÃO está pronto — controle sujo significa normalização")
        print("          incompleta ou não-determinismo fora da allowlist. Investigue")
        print("          antes de confiar em qualquer veredito Go↔Py.")
        return 2
    if not all(mains):
        print("\n::error:: Tier-1 FALHOU — divergência Go↔Py com controle limpo é bug de executor.")
        return 1
    print("\n✓ Tier-1 PASSOU — paridade value-exact com controle limpo.")
    return 0


# ───────────────────────────── CLI ─────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--workspace", required=True, help="uuid do workspace")
    p.add_argument("--runs", type=int, default=3, help="runs por braço (default 3, o do §7)")
    p.add_argument("--timeout", type=int, default=1800, help="timeout por run em s")
    p.add_argument("--poll", type=int, default=10, help="intervalo de poll em s")
    p.add_argument("--storage-root", type=Path, help="raiz de storage (absoluta)")
    p.add_argument("--db", help="path do SQLite (default: MATHOMS_DATABASE_URL ou ./mathoms.db)")
    p.add_argument("--json-out", type=Path, help="diretório para os relatórios JSON")
    return p.parse_args(argv)


def _storage_root(args: argparse.Namespace) -> Path:
    if args.storage_root:
        return args.storage_root.expanduser().resolve()
    return (_REPO / os.environ.get("STORAGE_ROOT", "storage")).resolve()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    args.storage_root = _storage_root(args)
    if args.runs < 2:
        raise GateError("--runs >= 2: o controle Py↔Py exige dois runs Python")
    con = _connect(_db_path(args.db))
    assert_preconditions(args.workspace, args.storage_root, con)
    if args.json_out:
        args.json_out.mkdir(parents=True, exist_ok=True)

    py_runs = execute_arm(PYTHON_ARM, args.workspace, con, args)
    go_runs = execute_arm(GO_ARM, args.workspace, con, args)
    print("\n▶  devolvendo o worker ao executor Python…")
    switch_arm(PYTHON_ARM)

    control_ok = invoke_gate(python_run=py_runs[0], go_run=None, control=py_runs[1], args=args)
    mains = [
        invoke_gate(python_run=py_runs[0], go_run=g, control=py_runs[1], args=args) for g in go_runs
    ]
    return render_verdict(control_ok, mains)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GateError as exc:
        print(f"::error:: {exc}", file=sys.stderr)
        sys.exit(2)
