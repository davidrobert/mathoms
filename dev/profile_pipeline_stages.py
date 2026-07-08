#!/usr/bin/env python3
"""A2.1 (ADR-150 §Escopo deferido): perfil RSS/CPU/duração por stage.

Roda a sequência determinística que a fixture dogfood exercita
(E1.5c→E3→E4→E5) via CLI ``run-stage`` — subprocess POR stage, espelhando
o modelo de execução do Caminho 1 — e mede por filho, via
``os.wait4``/rusage (zero dependência nova):

- wall e ``duration_ms`` do StageResult (overhead = wall − duration,
  mesma fórmula do §11 do PERFORMANCE_BASELINE);
- CPU (ru_utime+ru_stime) e razão CPU/wall — o sinal que refalsifica o
  gatilho "GIL/CPU-bound → Caminho 3" (CPU≈wall = CPU-bound);
- peak RSS (ru_maxrss, normalizado: bytes no macOS, KB no Linux). O RSS
  é interpretador + imports + stage — fiel ao subprocess do Caminho 1,
  NÃO o custo incremental do stage.

Seeding espelha ``tests/pipeline_golden_substrate.py`` (fonte de verdade):
``("E1.5", "baseline_patrimonial")`` + ``("E2-extratos", "fict_a"/"fict_b")``.
Roda em ``MATHOMS_PIPELINE_SCHEMA_MODE=warn`` explícito: o baseline bruto é
input EXTERNO (produzido pelo E1.5 real em produção) e não passa validação
strict — mesma razão pela qual o substrate usa ``InMemoryArtifactStore.seed``.

Uso: python3 dev/profile_pipeline_stages.py [--runs 3]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "pipeline_golden" / "dogfood"
_TEST_FERNET_KEY = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="

# Antes de qualquer import de backend.* (settings lê env no import): o seed
# in-process usa o mesmo ambiente do subprocess (crypto off no perfil, mesma
# baseline do §11; Redis em porta fechada — higiene, nada de cache dev).
os.environ.setdefault("MATHOMS_FERNET_KEY", _TEST_FERNET_KEY)
os.environ.setdefault("MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS", "false")
os.environ.setdefault("MATHOMS_REDIS_URL", "redis://127.0.0.1:6390/0")
os.environ.setdefault("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
# validate_cross (E7) fica FORA: exige narrativas do E5.N (generate_narratives,
# LLM) — "missing_narrativas" no run determinístico. Rerun owner-gated com key.
_STAGES = [
    ("consolidate_baseline", ""),
    ("reconcile_transactions", ""),
    ("categorize_transactions", ""),
    ("analyze_finances", ""),
]
_WS_ID = "ws-profile"


def _rss_mb(ru_maxrss: int) -> float:
    """ru_maxrss é bytes no macOS e KB no Linux — normaliza para MB."""
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return ru_maxrss / divisor


def _make_workspace(tmp: Path) -> Path:
    cfg = tmp / "config"
    cfg.mkdir(parents=True)
    (cfg / "pipeline.json").write_text(
        '{"reconciliation": {"skip_types": [], "skip_files": []}}', encoding="utf-8"
    )
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "institutions.json").write_text('{"banco_canonical": {}}', encoding="utf-8")
    return tmp


def _seed_dogfood(db_url: str, run_id: str) -> None:
    """Espelho de ``pipeline_golden_substrate._seed_dogfood_store`` — via DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import backend.app.models  # noqa: F401 — registra tabelas no metadata
    from backend.app.core.database import Base
    from backend.app.services.storage.db_artifact_store import DBArtifactStore

    engine = create_engine(db_url.replace("+aiosqlite", ""))
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    store = DBArtifactStore(session, workspace_id=_WS_ID, pipeline_run_id=run_id)
    store.write("E1.5", "baseline_patrimonial", _load(_FIXTURES / "baseline-1.5.json"))
    store.write("E2-extratos", "fict_a", _load(_FIXTURES / "extrato-a-2_extract.json"))
    store.write("E2-extratos", "fict_b", _load(_FIXTURES / "extrato-b-2_extract.json"))
    session.add(_if_goal_row())
    session.commit()
    session.close()
    engine.dispose()


def _if_goal_row():
    """Meta IF mínima — a hidratação DB-first sobrepõe goals.json de disco,
    e o E5 hard-faila sem meta IF; espelha _DEFAULT_GOALS do substrate."""
    from datetime import date

    from backend.app.models.goal import Goal

    return Goal(
        workspace_id=_WS_ID,
        type="INDEPENDENCIA_FINANCEIRA",
        params_json={"inputs": {"trs_pct": 4.0}},
        derived_json={"if_meta_brl": 1_000_000.0},
        effective_from=date(2026, 1, 1),
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _profile_env(db_url: str) -> dict[str, str]:
    return {
        **os.environ,
        "MATHOMS_DATABASE_URL": db_url,
        "MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS": "false",
        "MATHOMS_FERNET_KEY": os.environ.get("MATHOMS_FERNET_KEY", _TEST_FERNET_KEY),
        "MATHOMS_REDIS_URL": "redis://127.0.0.1:6390/0",
        "MATHOMS_PIPELINE_SCHEMA_MODE": "warn",
        "PYTHONPATH": str(REPO_ROOT),
    }


def _parse_stage_result(stage: str, status: int, stdout: str, stderr: str) -> dict:
    if os.waitstatus_to_exitcode(status) != 0:
        raise RuntimeError(
            f"{stage} falhou (exit {os.waitstatus_to_exitcode(status)}): {stderr[:500]}"
        )
    result = json.loads(stdout)
    if not result.get("success"):
        raise RuntimeError(f"{stage} success=false: {result.get('error')}")
    return result


def _run_stage_measured(stage: str, workspace: Path, db_url: str, run_id: str) -> dict:
    cmd = [
        sys.executable, "-m", "pipeline.orchestrator", "run-stage", stage,
        "--workspace", str(workspace), "--run-id", run_id, "--workspace-id", _WS_ID,
    ]  # fmt: skip
    start = time.perf_counter()
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, env=_profile_env(db_url)
    )
    _, status, ru = os.wait4(proc.pid, 0)
    wall_ms = (time.perf_counter() - start) * 1000
    stdout = proc.stdout.read().decode() if proc.stdout else ""
    stderr = proc.stderr.read().decode() if proc.stderr else ""
    result = _parse_stage_result(stage, status, stdout, stderr)
    return _measurement(stage, wall_ms, float(result["duration_ms"]), ru)


def _measurement(
    stage: str, wall_ms: float, duration_ms: float, ru: resource.struct_rusage
) -> dict:
    cpu_s = ru.ru_utime + ru.ru_stime
    return {
        "stage": stage,
        "wall_ms": wall_ms,
        "duration_ms": duration_ms,
        "overhead_ms": wall_ms - duration_ms,
        "cpu_s": cpu_s,
        "cpu_wall_ratio": cpu_s / (wall_ms / 1000) if wall_ms else 0.0,
        "rss_mb": _rss_mb(ru.ru_maxrss),
    }


def _profile_run(run_idx: int) -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        workspace = _make_workspace(Path(td))
        db_url = f"sqlite+aiosqlite:///{td}/profile.db"
        run_id = f"profile-{run_idx}"
        _seed_dogfood(db_url, run_id)
        return [_run_stage_measured(stage, workspace, db_url, run_id) for stage, _note in _STAGES]


def _median_by_stage(runs: list[list[dict]]) -> list[dict]:
    out = []
    for i, (stage, note) in enumerate(_STAGES):
        rows = [run[i] for run in runs]
        med = {k: statistics.median(r[k] for r in rows) for k in rows[0] if k != "stage"}
        out.append({"stage": stage, "note": note, **med})
    return out


def _print_report(medians: list[dict], n_runs: int) -> None:
    print(f"\nMáquina: {platform.platform()} · {_cpu_brand()} · Python {platform.python_version()}")
    print(
        f"Runs: {n_runs} (mediana por stage) · fixture dogfood sintética PII-zero · schema_mode=warn"
    )
    print(
        f"{'stage':26} {'wall':>8} {'stage_ms':>9} {'overhead':>9} {'cpu_s':>7} {'cpu/wall':>9} {'peakRSS':>9}"
    )
    for m in medians:
        _print_stage_row(m)
    total_wall = sum(m["wall_ms"] for m in medians)
    print(f"\nTotal wall (sequência {len(medians)} stages): {total_wall / 1000:.1f}s")
    print(
        "RSS = interpretador + imports + stage (fiel ao subprocess do Caminho 1, não incremental)"
    )
    print("cpu/wall ≈ 1.0 ⇒ CPU-bound single-thread (GIL relevante); << 1.0 ⇒ I/O-bound")
    print(
        "Fora do perfil: E0-E2 (parsing real), stages LLM e E7 (exige narrativas E5.N) — rerun owner-gated"
    )


def _cpu_brand() -> str:
    cpu = platform.processor() or "?"
    if sys.platform == "darwin":
        out = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
        )
        cpu = out.stdout.strip() or cpu
    return cpu


def _print_stage_row(m: dict) -> None:
    label = f"{m['stage']}*" if m["note"] else m["stage"]
    print(
        f"{label:26} {m['wall_ms']:>7.0f}ms {m['duration_ms']:>8.0f}ms {m['overhead_ms']:>8.0f}ms"
        f" {m['cpu_s']:>6.2f}s {m['cpu_wall_ratio']:>9.2f} {m['rss_mb']:>7.0f}MB"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    runs = []
    for i in range(args.runs):
        print(f"run {i + 1}/{args.runs}…")
        runs.append(_profile_run(i))
    _print_report(_median_by_stage(runs), args.runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
