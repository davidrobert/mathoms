#!/usr/bin/env python3
"""Orquestra os runs do gate de paridade Go↔Python (F2 do PLAN-go-shell, [[ADR-150]] §7): dispara N runs em cada braço (Python InProcess e shell Go), espera o terminal de cada um, captura os eventos WS no Tier-2 e chama ``dev/go_parity_gate.py`` para o veredito."""

# Divisão de trabalho: este script ORQUESTRA (pré-condições, overlay, dispatch,
# espera, captura, pareamento); go_parity_gate.py COMPARA. A separação existe
# porque o gate é puro sobre run_ids — dá para rodá-lo à mão sobre runs
# pré-existentes.
#
# NÃO MUTA DADO DO OWNER. A pré-condição de inbox vazio (senão o E0 classifica e
# gasta LLM — ver track f2-cutover §Pré-condições 2) é VERIFICADA, nunca
# "consertada" movendo documento: um harness de gate que mexe no workspace real
# do dono é pior que um gate que falha com instrução clara.
#
# Tier-1 (default) = DETERMINISTIC_ORDER, paridade value-exact de artefato, 0
# LLM. Tier-2 = run full + envelope WS; CUSTA LLM e é owner-run.
#
# A captura de eventos do Tier-2 sobe ANTES do dispatch, por psubscribe em
# pipeline:* — o run_id só nasce no dispatch e pub/sub não faz replay, então
# assinar pipeline:{run_id} depois perderia os primeiros envelopes numa janela
# que varia a cada run (falso positivo de divergência de sequência).
#
# Uso:
#   python dev/go_parity_run.py --workspace <uuid> [--runs 3] [--tier tier1|tier2]

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dev.go_parity_errors import GateError
from dev.go_parity_llm_free import (
    LLM_FREE_MARKER,
    assert_credential_symmetry,
    assert_llm_free,
    assert_scrub_applied,
    escalated_docs,
)

_REPO = Path(__file__).resolve().parents[1]

_TERMINAL = frozenset({"completed", "failed", "cancelled"})
_RUN_ID_RE = re.compile(r"Run ([0-9a-f-]{36}) disparado")

# `pending` = task enfileirada e NÃO consumida. Sem worker o run nunca sai desse
# estado, e esperar o timeout normal (1800s) confunde "stack de pé mas lenta" com
# "stack no chão". Grace curto separa os dois casos.
_PENDING_GRACE_S = 90


@dataclass(frozen=True)
class Arm:
    """Um braço do gate: qual executor e como ligá-lo."""

    name: str
    make_target: str


PYTHON_ARM = Arm(name="python", make_target="go-off")
GO_ARM = Arm(name="go", make_target="go-on")


@dataclass(frozen=True)
class RunRecord:
    """Um run executado: o id e, no Tier-2, o arquivo de envelopes WS recortado dele."""

    run_id: str
    ws_path: Path | None = None


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


# ───────────────────────────── pré-condições ─────────────────────────────


def _inbox_files(workspace: str, storage_root: Path) -> list[Path]:
    inbox = storage_root / workspace / "inbox"
    if not inbox.is_dir():
        return []
    return [p for p in inbox.rglob("*") if p.is_file()]


def _redis_endpoint() -> tuple[str, int]:
    url = (
        os.environ.get("MATHOMS_REDIS_URL")
        or os.environ.get("REDIS_URL")
        or "redis://localhost:6379/0"
    )
    parsed = urlparse(url)
    return parsed.hostname or "localhost", parsed.port or 6379


def assert_stack_up() -> None:
    """Redis no chão = dispatch enfileira e ninguém consome; o gate penduraria até o timeout."""
    host, port = _redis_endpoint()
    try:
        with socket.create_connection((host, port), timeout=3):
            return
    except OSError as exc:
        raise GateError(
            f"Redis inacessível em {host}:{port} ({exc}) — o run seria enfileirado e nunca "
            f"consumido.\n   Suba a stack antes do gate: `make native-up`"
        ) from exc


def _active_run(con: sqlite3.Connection, workspace: str) -> str | None:
    row = con.execute(
        "SELECT id FROM pipeline_runs WHERE workspace_id=? AND status IN ('pending','running') "
        "ORDER BY started_at DESC LIMIT 1",
        (workspace,),
    ).fetchone()
    return row[0] if row else None


def assert_no_active_run(con: sqlite3.Connection, workspace: str) -> None:
    """`_check_no_active_run` do trigger rejeita run concorrente — inclusive um `pending`
    órfão de tentativa anterior. Detectar aqui evita ConflictError no meio do braço."""
    stuck = _active_run(con, workspace)
    if stuck:
        raise GateError(
            f"workspace já tem run ativo ({stuck[:8]}) — o dispatch seria rejeitado por "
            f"conflito.\n   Se ele está preso (ex.: enfileirado com a stack no chão), cancele: "
            f"POST /v1/workspaces/{{ws}}/runs/{stuck}/cancel, ou pelo console interno."
        )


def assert_preconditions(
    workspace: str, storage_root: Path, con: sqlite3.Connection, tier: str = "tier1"
) -> None:
    """Falha ANTES de gastar run. Inbox não-vazio faria o E0 classificar (e gastar LLM)."""
    assert_stack_up()
    if not _run_ids(con, workspace):
        raise GateError(f"workspace {workspace} não tem run algum — confirme o uuid")
    assert_no_active_run(con, workspace)
    # O Tier-1 resolve a simetria de credencial apagando dos dois braços (LLM_FREE);
    # o Tier-2 precisa dela PRESENTE nos dois, e `.env` sozinho só alimenta o Go.
    assert_credential_symmetry(tier)
    assert_inbox_empty(workspace, storage_root)


def assert_inbox_empty(workspace: str, storage_root: Path) -> None:
    """Inbox com arquivo faz o E0 classificar — e gastar LLM em doc de baixa confiança."""
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


def _make(target: str, *, env_name: str = "native", llm_free: bool = False) -> str:
    cmd = ["make", "-s", target, f"ENV={env_name}"]
    if llm_free:
        cmd.append("LLM_FREE=1")
    proc = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateError(f"`{' '.join(cmd)}` falhou:\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout


def switch_arm(arm: Arm, *, llm_free: bool = False) -> None:
    """Liga o braço; no Tier-1 apaga a credencial LLM dos DOIS braços."""
    # Sem o scrub, `_go-on-native` injeta a key do .env no shell Go (repassada a
    # cada subprocess por os.Environ()) e `dev-worker-up` só herda o env do shell:
    # o MESMO extrato da Caixa saiu com 2986 bytes num braço e 1002 no outro.
    label = " [LLM_FREE]" if llm_free else ""
    print(f"▶  ligando braço {arm.name} (`make {arm.make_target} ENV=native`){label}…")
    out = _make(arm.make_target, llm_free=llm_free)
    if llm_free and arm is PYTHON_ARM and LLM_FREE_MARKER not in out:
        # `go-off` é idempotente: sem overlay Go ligado ele não reinicia o worker,
        # que seguiria com o env do dono. No 1º braço do gate é sempre o caso.
        out += _make("dev-worker-up", llm_free=True)
    if llm_free:
        assert_scrub_applied(arm, out)


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


def _assert_consumed(run_id: str, status: str | None, elapsed_s: float) -> None:
    """Distingue "worker no chão" de "run demorado" — sem isso ambos viram o mesmo timeout."""
    if status == "pending" and elapsed_s > _PENDING_GRACE_S:
        raise GateError(
            f"run {run_id} continua `pending` após {int(elapsed_s)}s — nenhum worker Celery "
            f"consumiu a task.\n   Suba a stack (`make native-up`) e confirme o worker: "
            f"`pgrep -fl 'celery.*worker'`"
        )


def wait_terminal(con: sqlite3.Connection, run_id: str, *, timeout_s: int, poll_s: int) -> str:
    started = time.monotonic()
    deadline = started + timeout_s
    last = None
    while time.monotonic() < deadline:
        status = _status(con, run_id)
        if status in _TERMINAL:
            return status
        _assert_consumed(run_id, status, time.monotonic() - started)
        if status != last:
            print(f"   · {run_id[:8]} → {status}")
            last = status
        time.sleep(poll_s)
    raise GateError(f"run {run_id} não terminou em {timeout_s}s (status={last})")


def _start_capture(out: Path) -> subprocess.Popen:
    """Sobe o coletor de eventos em pipeline:* ANTES do dispatch — ver corrida no topo de go_parity_capture."""
    cmd = [
        sys.executable,
        str(_REPO / "dev" / "go_parity_capture.py"),
        "--pattern",
        "--out",
        str(out),
    ]
    return subprocess.Popen(
        cmd, cwd=_REPO, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
    )


def _stop_capture(proc: subprocess.Popen, *, grace_s: int) -> None:
    """O coletor sai sozinho no evento terminal; o terminate é só rede de segurança."""
    try:
        proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=10)


def _finish_capture(proc: subprocess.Popen, out: Path, run_id: str, *, grace_s: int = 40) -> Path:
    """Recorta os envelopes do run. Sem eventos → falha: comparar sequência vazia daria falso verde."""
    from dev.go_parity_capture import filter_by_run

    _stop_capture(proc, grace_s=grace_s)
    if not out.exists():
        raise GateError(
            f"coletor de eventos não produziu {out} (Redis de pé? stderr: {proc.stderr.read()})"
        )
    events = filter_by_run(json.loads(out.read_text(encoding="utf-8")), run_id)
    if not events:
        raise GateError(
            f"0 envelope capturado para o run {run_id} — o Tier-2 compara sequência de eventos"
        )
    scoped = out.with_name(f"{out.stem}-{run_id[:8]}.json")
    scoped.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   · {len(events)} envelopes WS capturados")
    return scoped


def _one_run(arm: Arm, workspace: str, con: sqlite3.Connection, args, index: int) -> RunRecord:
    """Um run do braço: captura sobe ANTES do dispatch (corrida de pub/sub), depois espera e valida."""
    print(f"▶  {arm.name} run {index + 1}/{args.runs}…")
    ws_out = args.json_out / f"ws-{arm.name}-{index}.json"
    capture = _start_capture(ws_out) if args.tier == "tier2" else None
    run_id = dispatch_run(workspace, con)
    status = wait_terminal(con, run_id, timeout_s=args.timeout, poll_s=args.poll)
    if status != "completed":
        raise GateError(f"run {run_id} do braço {arm.name} terminou {status}")
    llm_evidence = assert_llm_free(con, run_id, arm, args.tier)
    escalated = escalated_docs(run_id)
    print(f"   ✓ {run_id[:8]} completed, {llm_evidence} evidência(s) de chamada LLM")
    if escalated:
        # Corpus encolhido, não gasto de LLM — ver docstring de `_escalated_docs`.
        print(
            f"   · {len(escalated)} doc(s) escalaram (corpus menor que o run full): "
            f"{', '.join(escalated[:3])}{'…' if len(escalated) > 3 else ''}"
        )
    ws_path = _finish_capture(capture, ws_out, run_id) if capture else None
    return RunRecord(run_id=run_id, ws_path=ws_path)


def _pair_order(index: int) -> tuple[Arm, Arm]:
    """Alterna quem vai primeiro em cada par, para nenhum braço monopolizar posição ordinal."""
    return (PYTHON_ARM, GO_ARM) if index % 2 == 0 else (GO_ARM, PYTHON_ARM)


def execute_interleaved(
    workspace: str, con: sqlite3.Connection, args
) -> tuple[list[RunRecord], list[RunRecord]]:
    """Intercala os braços em vez de rodar N de um e depois N do outro."""
    # Medido 2026-08-03: braços sequenciais (py,py,go,go) tornam "ser Go" e "ser o 3º
    # run" perfeitamente correlacionados — e o E3 lê artefato pelo mais recente ENTRE
    # runs, então efeito de acumulação é possível. Gate que confunde ordem com executor
    # produz falso positivo caro (manda caçar bug de Go que não existe). Intercalar +
    # alternar a ordem dentro do par balanceia a posição ordinal.
    runs: dict[str, list[RunRecord]] = {PYTHON_ARM.name: [], GO_ARM.name: []}
    llm_free = args.tier == "tier1"
    for i in range(args.runs):
        for arm in _pair_order(i):
            switch_arm(arm, llm_free=llm_free)
            runs[arm.name].append(_one_run(arm, workspace, con, args, i))
    return runs[PYTHON_ARM.name], runs[GO_ARM.name]


# ───────────────────────────── veredito ─────────────────────────────


def _ws_flags(main: RunRecord, control: RunRecord, go: RunRecord | None) -> list[str]:
    """Só passa --*-ws quando há captura; sem isso o gate compara artefato puro."""
    flags: list[str] = []
    if main.ws_path:
        flags += ["--python-ws", str(main.ws_path)]
    if control.ws_path:
        flags += ["--control-ws", str(control.ws_path)]
    if go and go.ws_path:
        flags += ["--go-ws", str(go.ws_path)]
    return flags


def invoke_gate(*, main: RunRecord, control: RunRecord, go: RunRecord | None, args) -> bool:
    """Chama o comparador. go=None → é o run de controle Py↔Py (mede o piso de ruído)."""
    cmd = [sys.executable, str(_REPO / "dev" / "go_parity_gate.py"), "--tier", args.tier]
    cmd += ["--python-run", main.run_id, "--go-run", (go or control).run_id]
    if go:
        cmd += ["--control-run", control.run_id]
    cmd += _ws_flags(main, control, go)
    if args.storage_root:
        cmd += ["--storage-root", str(args.storage_root)]
    label = f"{'main' if go else 'control'}-{(go or control).run_id[:8]}"
    cmd += ["--json-out", str(args.json_out / f"{label}.json")]
    proc = subprocess.run(cmd, cwd=_REPO, text=True)
    return proc.returncode == 0


def render_verdict(control_ok: bool, mains: list[bool], tier: str = "tier1") -> int:
    print("\n" + "─" * 60)
    print(f"controle Py↔Py (piso de ruído): {'✓ 0 diff' if control_ok else '✗ diff residual'}")
    print(f"Go↔Py: {sum(mains)}/{len(mains)} pares limpos")
    if not control_ok:
        print("\n::error:: o gate NÃO está pronto — controle sujo significa normalização")
        print("          incompleta ou não-determinismo fora da allowlist. Investigue")
        print("          antes de confiar em qualquer veredito Go↔Py.")
        return 2
    if not all(mains):
        print(
            f"\n::error:: {tier} FALHOU — divergência Go↔Py com controle limpo é bug de executor."
        )
        return 1
    print(f"\n✓ {tier} PASSOU — controle limpo e nenhuma divergência Go↔Py.")
    return 0


# ───────────────────────────── CLI ─────────────────────────────


def _add_env_args(p: argparse.ArgumentParser) -> None:
    """Onde o gate lê estado: storage no disco, runs no DB, saída dos relatórios."""
    p.add_argument("--storage-root", type=Path, help="raiz de storage (absoluta)")
    p.add_argument("--db", help="path do SQLite (default: MATHOMS_DATABASE_URL ou ./mathoms.db)")
    p.add_argument(
        "--json-out",
        type=Path,
        default=_REPO / "_scratch" / "go_parity",
        help="diretório dos relatórios e das capturas WS",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--workspace", required=True, help="uuid do workspace")
    p.add_argument("--runs", type=int, default=3, help="runs por braço (default 3, o do §7)")
    p.add_argument(
        "--tier",
        choices=("tier1", "tier2"),
        default="tier1",
        help="tier1 = determinístico, artefato value-exact; tier2 = full + envelope WS (custa LLM)",
    )
    p.add_argument("--timeout", type=int, default=1800, help="timeout por run em s")
    p.add_argument("--poll", type=int, default=10, help="intervalo de poll em s")
    _add_env_args(p)
    return p.parse_args(argv)


def _storage_root(args: argparse.Namespace) -> Path:
    if args.storage_root:
        return args.storage_root.expanduser().resolve()
    return (_REPO / os.environ.get("STORAGE_ROOT", "storage")).resolve()


def _restore_python_arm() -> None:
    """Roda SEMPRE, inclusive em falha: abortar no braço Go sem isso deixaria o
    dogfood executando stages pelo shell Go sem o owner ter feito o flip. Não
    propaga erro — mascararia a exceção original que interessa diagnosticar."""
    print("\n▶  devolvendo o worker ao executor Python (com credencial)…")
    try:
        switch_arm(PYTHON_ARM)
        # `go-off` não reinicia o worker quando o overlay Go não estava ligado, e o
        # worker do gate roda com a credencial APAGADA (`LLM_FREE=1`). Sem este
        # restart explícito o dono ficaria com a stack de dev sem ANTHROPIC_API_KEY
        # e veria stages LLM degradando em silêncio — exatamente a classe de bug
        # que esta lane fecha.
        _make("dev-worker-up")
    except GateError as exc:
        print(f"::error:: FALHA AO RESTAURAR o executor Python: {exc}", file=sys.stderr)
        print(
            "::error:: rode `make go-off ENV=native` — o worker pode estar no Go.", file=sys.stderr
        )


def _execute_both_arms(workspace: str, con: sqlite3.Connection, args) -> tuple[list, list]:
    try:
        return execute_interleaved(workspace, con, args)
    finally:
        _restore_python_arm()


def main(argv: list[str] | None = None) -> int:
    # Gate de dezenas de minutos: sem line-buffering o progresso só aparece no fim
    # quando stdout é arquivo/pipe (`make ... | tee`, background), e um run travado
    # fica indistinguível de um run silencioso.
    sys.stdout.reconfigure(line_buffering=True)
    args = _parse_args(argv)
    args.storage_root = _storage_root(args)
    if args.runs < 2:
        raise GateError("--runs >= 2: o controle Py↔Py exige dois runs Python")
    con = _connect(_db_path(args.db))
    assert_preconditions(args.workspace, args.storage_root, con, args.tier)
    args.json_out.mkdir(parents=True, exist_ok=True)

    py_runs, go_runs = _execute_both_arms(args.workspace, con, args)
    base, control = py_runs[0], py_runs[1]
    control_ok = invoke_gate(main=base, control=control, go=None, args=args)
    mains = [invoke_gate(main=base, control=control, go=g, args=args) for g in go_runs]
    return render_verdict(control_ok, mains, args.tier)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GateError as exc:
        print(f"::error:: {exc}", file=sys.stderr)
        sys.exit(2)
