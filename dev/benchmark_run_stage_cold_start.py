#!/usr/bin/env python3
"""Benchmark A3.cli.benchmark (ADR-150 §4): cold start do run-stage via subprocess.

Mede o overhead de fork+exec+imports do ``python -m pipeline.orchestrator
run-stage`` — tempo de parede do subprocess menos o ``duration_ms`` que o
próprio ``StageResult`` reporta — contra fixture sintética PII-zero e SQLite
descartável. Gate falsificável: **mediana ≤500ms** mantém o Caminho 1;
>500ms reabre o Caminho 2 (worker pool warm) ANTES do 1º PR Go.

Uso:
    python3 dev/benchmark_run_stage_cold_start.py [--samples 20] [--importtime]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_E2_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-extrato-2_extract.json"
)
_STAGE = "reconcile_transactions"
_GATE_MS = 500.0

os.environ.setdefault("MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS", "false")


def _make_workspace(tmp: Path) -> Path:
    cfg = tmp / "config"
    cfg.mkdir(parents=True)
    (cfg / "pipeline.json").write_text(
        '{"reconciliation": {"skip_types": [], "skip_files": []}}', encoding="utf-8"
    )
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "institutions.json").write_text('{"banco_canonical": {}}', encoding="utf-8")
    return tmp


def _seed_e2(engine) -> None:
    from sqlalchemy.orm import sessionmaker

    from backend.app.services.db_artifact_store import DBArtifactStore

    payload = json.loads(_E2_FIXTURE.read_text(encoding="utf-8"))
    payload.update(saldo_inicial=0.0, saldo_final=100.0)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    DBArtifactStore(session, workspace_id="ws-bench", pipeline_run_id="run-seed").write(
        "E2-extratos", "golden-minimal", payload
    )
    session.commit()
    session.close()


def _make_seeded_db(tmp: Path) -> str:
    """Cria SQLite com schema + 1 artefato E2 (lido via fallback workspace, ADR-241)."""
    from sqlalchemy import create_engine

    import backend.app.models  # noqa: F401 — registra tabelas no metadata
    from backend.app.core.database import Base

    db_path = tmp / "bench.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    _seed_e2(engine)
    engine.dispose()
    return f"sqlite+aiosqlite:///{db_path}"


def _cli_cmd(workspace: Path, run_id: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pipeline.orchestrator",
        "run-stage",
        _STAGE,
        "--workspace",
        str(workspace),
        "--run-id",
        run_id,
        "--workspace-id",
        "ws-bench",
    ]


def _bench_env(db_url: str) -> dict[str, str]:
    return {
        **os.environ,
        "MATHOMS_DATABASE_URL": db_url,
        "MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS": "false",
        "PYTHONPATH": str(REPO_ROOT),
    }


def _run_once(workspace: Path, db_url: str, run_id: str) -> tuple[float, float]:
    """Retorna (total_ms de parede, duration_ms do stage reportado pelo CLI)."""
    start = time.perf_counter()
    proc = subprocess.run(
        _cli_cmd(workspace, run_id),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_bench_env(db_url),
        timeout=300,
    )
    total_ms = (time.perf_counter() - start) * 1000
    if proc.returncode != 0:
        raise RuntimeError(f"run-stage falhou (exit {proc.returncode}): {proc.stderr[:500]}")
    return total_ms, float(json.loads(proc.stdout)["duration_ms"])


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))
    return ordered[idx]


def _importtime_top(workspace: Path, db_url: str, top_n: int = 10) -> list[str]:
    cmd = [sys.executable, "-X", "importtime", "-m", *_cli_cmd(workspace, "run-importtime")[2:]]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=_bench_env(db_url), timeout=300
    )
    rows = []
    for line in proc.stderr.splitlines():
        if not line.startswith("import time:") or "cumulative" in line:
            continue
        parts = [p.strip() for p in line.removeprefix("import time:").split("|")]
        if len(parts) == 3:
            rows.append((int(parts[1]), parts[2]))
    rows.sort(reverse=True)
    return [f"{cum / 1000:.0f}ms {name}" for cum, name in rows[:top_n]]


def _machine_label() -> str:
    cpu = platform.processor() or "?"
    if sys.platform == "darwin":
        out = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
        )
        cpu = out.stdout.strip() or cpu
    return f"{platform.platform()} · {cpu} · Python {platform.python_version()}"


def _print_metrics(totals: list[float], durations: list[float], overheads: list[float]) -> None:
    med = statistics.median
    print(f"\nMáquina: {_machine_label()}")
    print(f"Amostras: {len(totals)} · stage: {_STAGE} (fixture sintética)")
    print(f"Total subprocess  — mediana {med(totals):.0f}ms · p95 {_p95(totals):.0f}ms")
    print(f"Stage duration_ms — mediana {med(durations):.0f}ms")
    print(f"COLD START (overhead) — mediana {med(overheads):.0f}ms · p95 {_p95(overheads):.0f}ms")
    m = med(overheads)
    print(
        f"Acumulado projetado/run — 10 stages det.: {10 * m / 1000:.1f}s · 18 full: {18 * m / 1000:.1f}s"
    )
    print("Baseline in-process (Celery): overhead fork+exec ≈ 0")


def _report(totals: list[float], durations: list[float], importtime: list[str]) -> None:
    overheads = [t - d for t, d in zip(totals, durations)]
    med = statistics.median(overheads)
    _print_metrics(totals, durations, overheads)
    if importtime:
        print("\nTop imports (-X importtime, cumulativo):")
        for row in importtime:
            print(f"  {row}")
    verdict = (
        "≤500ms → Caminho 1 segue"
        if med <= _GATE_MS
        else ">500ms → REABRIR Caminho 2 (emenda ADR-150) antes do 1º PR Go"
    )
    print(f"\nGate ADR-150: mediana {med:.0f}ms — {verdict}")


def _collect_samples(workspace: Path, db_url: str, n: int) -> tuple[list[float], list[float]]:
    totals, durations = [], []
    for i in range(n):
        total, duration = _run_once(workspace, db_url, f"run-bench-{i}")
        totals.append(total)
        durations.append(duration)
        overhead = total - duration
        print(
            f"  amostra {i + 1:2d}/{n}: total {total:.0f}ms · stage {duration:.0f}ms · overhead {overhead:.0f}ms"
        )
    return totals, durations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument(
        "--importtime", action="store_true", help="Coleta top imports (1 amostra extra)."
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as td:
        workspace = _make_workspace(Path(td))
        db_url = _make_seeded_db(Path(td))
        totals, durations = _collect_samples(workspace, db_url, args.samples)
        importtime = _importtime_top(workspace, db_url) if args.importtime else []
        _report(totals, durations, importtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
