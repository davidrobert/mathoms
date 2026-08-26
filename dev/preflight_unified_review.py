#!/usr/bin/env python3
"""Preflight da rodada unificada `ledger-certify` -> `pipeline-review` -> `report-review`.

Mecaniza os modos de falha que invalidam a rodada **antes** de ela custar API e
uma hora de relogio: worker com codigo velho, budget em hard-stop, run em voo que
o guard atual nao ve, `config/passwords.txt` ausente (mata o stage 1/18), frontend
fora do ar (a captura de render e o que tira `clareza-ux` da inferencia de codigo).

Nao escreve no DB e nao dispara run; faz `git fetch`. Cada check devolve
PASS/WARN/FAIL com a remediacao — **FAIL bloqueia o disparo**.

Rode da RAIZ do checkout principal:
    .venv/bin/python dev/preflight_unified_review.py <email|uuid> [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from backend.app.core.database import SyncSessionLocal  # noqa: E402
from backend.app.models.pipeline_run import PipelineRunStatus  # noqa: E402

# Terminal e a lista curta e estavel; "em voo" e o COMPLEMENTO, para status novo
# no enum entrar bloqueante por default em vez de sumir do guard.
RUN_TERMINAL = {
    PipelineRunStatus.completed,
    PipelineRunStatus.partial_failure,
    PipelineRunStatus.failed,
    PipelineRunStatus.cancelled,
}
RUN_EM_VOO = tuple(s.value for s in PipelineRunStatus if s not in RUN_TERMINAL)

# Hard-stop da ADR-173 e a 110% do cap; abaixo disso um run de ~US$3 ainda estoura.
BUDGET_HARD_STOP = Decimal("1.10")
BUDGET_ALERTA = Decimal("0.80")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

# Remediacao e dado, nao logica — mantida fora do corpo dos checks.
FIX_EXECUTOR_NULL = "ADR-362: NULL em dev sem MATHOMS_BUILD_SHA"
FIX_EXECUTOR_ORFAO = "worker bootou de branch deletada?"
FIX_EXECUTOR_ATRAS = "reiniciar o worker corrige; declare o executor no entregavel"
FIX_BUDGET_SEM_CAP = "default da ADR-173 se aplica"
FIX_BUDGET_ESTOURADO = (
    "elevar o cap e decisao do dono (update_workspace_llm_budget, nunca UPDATE cru)"
)
FIX_BUDGET_PERTO = "confirme com o dono antes de disparar"
FIX_ATRAS_EM_MAIN = "git pull --ff-only — senao a rodada mede o codigo de ontem (licao do §r8)"
FIX_ATRAS_FORA_DE_MAIN = (
    "NAO puxe na branch alheia — coordene com a sessao dona, ou rode de um checkout em main"
)
FIX_ADIANTE = "rodar sobre codigo nao-mergeado pode ser a decisao certa; declare o executor no entregavel (licao do §r6)"
FIX_SUJO = "trabalho de outra sessao? git stash push -- <arquivos>"


@dataclass(frozen=True)
class Check:
    nome: str
    nivel: str
    detalhe: str
    fix: str = ""


def _sh(cmd: str) -> str:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.stdout.strip()


def _month_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def check_checkout(root: Path) -> Check:
    if ".claude/worktrees/" in str(root):
        return Check(
            "checkout", FAIL, f"cwd e worktree: {root}", "rode da raiz do checkout principal"
        )
    faltam = [p for p in (".env", ".venv", "config", "dev") if not (root / p).exists()]
    if faltam:
        return Check(
            "checkout", FAIL, f"ausentes no cwd: {faltam}", "cd para a raiz do checkout principal"
        )
    return Check("checkout", PASS, str(root))


def _posicao_vs_main() -> tuple[str, int, int, int]:
    _sh("git fetch --quiet origin")
    branch = _sh("git rev-parse --abbrev-ref HEAD")
    atras = _sh("git rev-list --count HEAD..origin/main")
    adiante = _sh("git rev-list --count origin/main..HEAD")
    sujos = len([ln for ln in _sh("git status --porcelain").splitlines() if ln])
    return branch, int(atras or 0), int(adiante or 0), sujos


def check_sync_main() -> Check:
    """Distingue "atras de main" de "fora de main" — a remediacao dos dois e oposta."""
    branch, atras, adiante, sujos = _posicao_vs_main()
    em_main = branch == "main"
    if atras and em_main:
        return Check(
            "sync-main", FAIL, f"HEAD esta {atras} commits atras de origin/main", FIX_ATRAS_EM_MAIN
        )
    if atras:
        detalhe = f"branch `{branch}` (de outra sessao) esta {atras} commits atras de origin/main"
        return Check("sync-main", FAIL, detalhe, FIX_ATRAS_FORA_DE_MAIN)
    if adiante:
        detalhe = (
            f"HEAD = origin/main + {adiante} commit(s) de `{branch}` — a rodada mede ESSE codigo"
        )
        return Check("sync-main", WARN, detalhe, FIX_ADIANTE)
    if sujos:
        return Check("sync-main", WARN, f"em `{branch}`, {sujos} arquivo(s) sujo(s)", FIX_SUJO)
    return Check("sync-main", PASS, f"`{branch}` == origin/main, tree limpo")


def check_caffeinate() -> Check:
    if _sh("pgrep -x caffeinate"):
        return Check("caffeinate", PASS, "maquina segura acordada")
    return Check(
        "caffeinate",
        WARN,
        "nenhum caffeinate ativo",
        "nohup caffeinate -dimsu & — sleep no meio do run faz o Celery redeliverar stage LLM ja pago",
    )


def check_redis() -> Check:
    pong = _sh("redis-cli ping")
    if pong != "PONG":
        return Check("redis", FAIL, f"redis-cli ping devolveu {pong!r}", "make dev-redis-up")
    return Check("redis", PASS, "PONG")


def _parse_etime(bruto: str) -> int | None:
    """`ps -o etime=` do BSD: `[[dd-]hh:]mm:ss`. macOS nao tem `etimes` (GNU)."""
    if not bruto:
        return None
    dias, sep, resto = bruto.partition("-")
    if not sep:
        dias, resto = "0", bruto
    partes = resto.split(":")
    if not dias.isdigit() or not all(x.isdigit() for x in partes):
        return None
    segundos = 0
    for parte in partes:
        segundos = segundos * 60 + int(parte)
    return segundos + int(dias) * 86400


def _boot_epoch(pid: str) -> int | None:
    decorrido = _parse_etime(_sh(f"ps -o etime= -p {pid}"))
    return int(time.time()) - decorrido if decorrido is not None else None


def check_worker() -> Check:
    pids = _sh("pgrep -f 'celery.*worker'").split()
    if not pids:
        return Check("worker", FAIL, "nenhum processo celery worker", "make dev-restart-worker")
    boot = _boot_epoch(pids[0])
    head = _sh("git log -1 --format=%ct")
    if boot is None or not head.isdigit():
        return Check(
            "worker", WARN, f"{len(pids)} processo(s), idade indeterminada", "confira ps -o lstart"
        )
    if boot < int(head):
        horas = (int(head) - boot) // 3600
        return Check(
            "worker",
            FAIL,
            f"bootado {horas}h ANTES do commit de HEAD",
            "make dev-restart-worker — prefork nao recarrega codigo (nao ha --reload)",
        )
    return Check("worker", PASS, f"{len(pids)} processo(s), posterior ao HEAD")


def _ultimo_executor(db) -> str | None:
    row = db.execute(
        text(
            "SELECT executor_revision FROM pipeline_stage_logs "
            "WHERE executor_revision IS NOT NULL ORDER BY started_at DESC LIMIT 1"
        )
    ).first()
    return str(row[0]).replace("-dirty", "") if row else None


def check_executor_revision(db) -> Check:
    """O executor do E3 persistido e o unico eixo que revela codigo de ontem no run."""
    sha = _ultimo_executor(db)
    if sha is None:
        return Check(
            "executor-rev", WARN, "nenhum stage log declara executor_revision", FIX_EXECUTOR_NULL
        )
    a_frente = _sh(f"git rev-list --count {sha}..origin/main 2>/dev/null")
    if not a_frente.isdigit():
        return Check(
            "executor-rev", WARN, f"executor {sha[:8]} nao resolve no repo", FIX_EXECUTOR_ORFAO
        )
    if a_frente != "0":
        atras = f"executor {sha[:8]} esta {a_frente} commits atras de origin/main"
        return Check("executor-rev", WARN, atras, FIX_EXECUTOR_ATRAS)
    return Check("executor-rev", PASS, f"executor {sha[:8]} == origin/main")


def check_passwords(root: Path) -> Check:
    alvo = root / "config" / "passwords.txt"
    if not alvo.exists():
        return Check(
            "passwords",
            FAIL,
            "config/passwords.txt ausente",
            "unlock_documents faz sys.exit(1) ANTES de saber se ha PDF cifrado — mata o stage 1/18",
        )
    return Check("passwords", PASS, "presente")


def _resolve_workspace(db, alvo: str) -> str | None:
    if "@" in alvo:
        row = db.execute(
            text(
                "SELECT w.id FROM workspaces w JOIN users u ON u.id = w.owner_id "
                "WHERE u.email = :e ORDER BY w.created_at LIMIT 1"
            ),
            {"e": alvo},
        ).first()
    else:
        row = db.execute(text("SELECT id FROM workspaces WHERE id = :i"), {"i": alvo}).first()
    return row[0] if row else None


def _run_em_voo(db, ws: str):
    marcadores = ",".join(f"'{s}'" for s in RUN_EM_VOO)
    return (
        db.execute(
            text(
                f"SELECT id, status, current_stage, paused_at_stage FROM pipeline_runs "
                f"WHERE workspace_id = :ws AND status IN ({marcadores}) ORDER BY started_at DESC LIMIT 1"
            ),
            {"ws": ws},
        )
        .mappings()
        .first()
    )


# "marque terminal" nao existia como acao sancionada quando este texto foi escrito, e
# mandava direto para a escrita ORM. A ADR-417 D1 abriu a porta; o texto passa a nomea-la.
FIX_PAUSADO = (
    "retome por resume_pipeline_run, ou descarte por "
    "POST /workspaces/<ws>/pipeline/runs/<id>/cancel — nao dispare por cima, "
    "nao escreva status no DB"
)


def check_run_em_voo(db, ws: str) -> Check:
    """O guard de resolve_workspace.py filtra 'paused' (inexistente) e omite estes dois."""
    row = _run_em_voo(db, ws)
    if row is None:
        return Check(
            "run-em-voo", PASS, "nenhum run em voo (predicado inclui needs_review e resuming)"
        )
    if row["status"] == "needs_review":
        return Check(
            "run-em-voo",
            FAIL,
            f"run {row['id'][:8]} PAUSADO em needs_review (stage {row['paused_at_stage']})",
            FIX_PAUSADO,
        )
    return Check(
        "run-em-voo",
        FAIL,
        f"run {row['id'][:8]} em {row['status']} (stage {row['current_stage']})",
        "aguarde o terminal — nao dispare outro",
    )


def _razao_do_budget(db, ws: str) -> Decimal | None:
    cap = db.execute(
        text("SELECT monthly_llm_budget_usd FROM workspaces WHERE id = :ws"), {"ws": ws}
    ).scalar()
    if cap is None or Decimal(str(cap)) == 0:
        return None
    gasto = db.execute(
        text(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_call_log WHERE workspace_id = :ws AND created_at >= :m"
        ),
        {"ws": ws, "m": _month_start_utc()},
    ).scalar()
    return Decimal(str(gasto or 0)) / Decimal(str(cap))


def check_budget(db, ws: str) -> Check:
    razao = _razao_do_budget(db, ws)
    if razao is None:
        return Check("budget-llm", WARN, "workspace sem cap declarado", FIX_BUDGET_SEM_CAP)
    detalhe = f"mes corrente em {razao:.0%} do cap"
    if razao >= BUDGET_HARD_STOP:
        return Check("budget-llm", FAIL, detalhe + " — hard-stop ATIVO", FIX_BUDGET_ESTOURADO)
    if razao >= BUDGET_ALERTA:
        return Check("budget-llm", WARN, detalhe + " — run de ~US$3 estoura", FIX_BUDGET_PERTO)
    return Check("budget-llm", PASS, detalhe)


def check_frontend(base: str) -> Check:
    try:
        with urllib.request.urlopen(base, timeout=4) as resp:
            if resp.status < 400:
                return Check("frontend", PASS, f"{base} responde {resp.status}")
            return Check(
                "frontend",
                FAIL,
                f"{base} responde {resp.status}",
                "suba o frontend — sem ele nao ha captura de render",
            )
    except (urllib.error.URLError, OSError) as exc:
        return Check(
            "frontend",
            FAIL,
            f"{base} inacessivel ({type(exc).__name__})",
            "sem captura de render, clareza-ux fica SEM COBERTURA e nao pode ser afirmada",
        )


def _storage_root(root: Path) -> Path:
    """`MATHOMS_STORAGE_ROOT` vence o cwd — o storage nao acompanha o worktree."""
    return Path(os.environ.get("MATHOMS_STORAGE_ROOT") or root / "storage")


def check_baselines(root: Path, ws: str) -> Check:
    raiz = _storage_root(root)
    reviews = sorted((raiz / ws / "reviews").glob("*")) if (raiz / ws / "reviews").exists() else []
    ledger = (
        sorted((raiz / ws / "ledger_certify").glob("*"))
        if (raiz / ws / "ledger_certify").exists()
        else []
    )
    if not reviews and not ledger:
        return Check(
            "baselines",
            WARN,
            "nenhum baseline duravel",
            "a rodada vira fotografia, nao gate anti-regressao",
        )
    return Check(
        "baselines",
        PASS,
        f"{len(reviews)} review(s) + {len(ledger)} ledger disponiveis para --compare",
    )


def check_instrumento_ledger(root: Path) -> Check:
    alvo = "investimentos_consolidados|imoveis_consolidados|veiculos_consolidados"
    hits = _sh(f"rg -l '{alvo}' {root}/dev/ledger_*.py 2>/dev/null")
    if not hits:
        return Check(
            "instrumento-ledger",
            WARN,
            "harness nao le nenhuma populacao consolidada (LC06 aberto)",
            "a P0 no 1 da rubrica segue sem cobertura — declare no cabecalho da rodada ou feche a A42.l3",
        )
    return Check(
        "instrumento-ledger", PASS, "harness alcanca as populacoes consolidadas (LC06 fechado?)"
    )


def check_concorrencia() -> Check:
    worktrees = len([ln for ln in _sh("git worktree list").splitlines() if ln])
    recentes = len(
        [
            ln
            for ln in _sh(
                "git for-each-ref --format='%(refname:short)' refs/remotes/origin/agent/"
            ).splitlines()
            if ln
        ]
    )
    if worktrees > 1:
        return Check(
            "concorrencia",
            WARN,
            f"{worktrees} worktrees, {recentes} branch(es) agent remotas",
            "outro agente pode tocar o mesmo DB/worker",
        )
    return Check("concorrencia", PASS, f"{worktrees} worktree, {recentes} branch(es) agent remotas")


def _checks_de_ambiente(root: Path, base_frontend: str) -> list[Check]:
    return [
        check_checkout(root),
        check_sync_main(),
        check_caffeinate(),
        check_redis(),
        check_worker(),
        check_passwords(root),
        check_frontend(base_frontend),
        check_concorrencia(),
    ]


def _checks_de_workspace(db, ws: str, root: Path) -> list[Check]:
    return [
        Check("workspace", PASS, ws),
        check_executor_revision(db),
        check_run_em_voo(db, ws),
        check_budget(db, ws),
        check_baselines(root, ws),
    ]


def rodar(alvo: str, base_frontend: str) -> list[Check]:
    root = Path.cwd()
    checks = _checks_de_ambiente(root, base_frontend)
    with SyncSessionLocal() as db:
        ws = _resolve_workspace(db, alvo)
        if ws is None:
            checks.append(Check("workspace", FAIL, f"nao resolve: {alvo!r}", "confira email/uuid"))
            return checks
        checks.extend(_checks_de_workspace(db, ws, root))
    checks.append(check_instrumento_ledger(root))
    return checks


def imprimir(checks: list[Check]) -> None:
    largura = max(len(c.nome) for c in checks)
    for c in checks:
        print(f"  [{c.nivel}] {c.nome.ljust(largura)}  {c.detalhe}")
        if c.fix and c.nivel != PASS:
            print(f"         {' ' * largura}  -> {c.fix}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", help="email ou uuid")
    ap.add_argument("--frontend", default="http://localhost:3000", help="base-url do frontend")
    ap.add_argument("--json", action="store_true", dest="como_json")
    args = ap.parse_args()

    checks = rodar(args.workspace, args.frontend)
    falhas = [c for c in checks if c.nivel == FAIL]
    if args.como_json:
        print(json.dumps([asdict(c) for c in checks], ensure_ascii=False, indent=2))
    else:
        print("\nPreflight da rodada unificada\n")
        imprimir(checks)
        alertas = len([c for c in checks if c.nivel == WARN])
        print(
            f"\n  {len(checks) - len(falhas) - alertas} PASS · {alertas} WARN · {len(falhas)} FAIL"
        )
        print("  FAIL bloqueia o disparo do run.\n" if falhas else "  Liberado para disparar.\n")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
