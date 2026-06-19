#!/usr/bin/env python3
"""Runner paralelo do eval golden do evidencia_path (A26.l9 · Slice 0).

O gate pytest (`tests/test_parecer_evidencia_llm_eval.py`) roda as 60 gerações em
série (~1,7h) e sofre kill antes de fechar o critério de aceite da A26.l9 (re-eval
holdout). Este harness roda as MESMAS gerações em paralelo — I/O-bound na API, libera
o GIL; ~13 min com 6 workers — reusando `_run_once`/`_build_report` do gate, sem
duplicar a lógica de veredito/agregação/IC95. Owner-gated: exige ANTHROPIC_API_KEY.
Relatório byte-idêntico ao do gate em _scratch/parecer_evidencia_eval_report.json.

Uso: `python3 dev/run_parecer_eval_parallel.py [--workers N] [--report PATH]`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.fixtures.parecer_eval import HOLDOUT
from tests.test_parecer_evidencia_llm_eval import (  # reuso: zero duplicação de veredito
    _COST_CAP_USD,
    _DENSITY_FLOOR,
    _DIAG_TEMP,
    _GATE_RUNS,
    _GATE_TEMP,
    _PER_PARECER_GATE,
    _REPORT_PATH,
    _build_report,
    _run_once,
)

_DEFAULT_WORKERS = 6


@dataclass(frozen=True)
class _Task:
    """Uma geração agendável: fixture + temperatura + índice + braço (gate|diag)."""

    fixture: Any
    temperature: float
    run_idx: int
    is_diag: bool


def _plan_tasks() -> list[_Task]:
    """60 tarefas: gate (holdout × _GATE_RUNS @ temp prod) + diag (holdout @ temp=0)."""
    gate = [_Task(f, _GATE_TEMP, i, False) for f in HOLDOUT for i in range(_GATE_RUNS)]
    diag = [_Task(f, _DIAG_TEMP, 0, True) for f in HOLDOUT]
    return gate + diag


def _run_task(task: _Task) -> tuple[bool, dict]:
    verdict = _run_once(task.fixture, task.temperature, task.run_idx)
    return task.is_diag, verdict


def _progress(done: int, total: int, verdict: dict) -> None:
    flag = "✗ viol" if verdict["violation"] else ("· miss" if verdict["missing_path"] else "ok")
    print(f"[{done:>2}/{total}] {verdict['fixture']:<18} {flag}", flush=True)


def _collect_parallel(workers: int) -> dict:
    """Roda as gerações concorrentemente; particiona vereditos em gate vs diag."""
    gate: list[dict] = []
    diag: list[dict] = []
    tasks = _plan_tasks()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_task, t) for t in tasks]
        for done, fut in enumerate(as_completed(futures), 1):
            is_diag, verdict = fut.result()
            (diag if is_diag else gate).append(verdict)
            _progress(done, len(tasks), verdict)
    return _build_report(gate, diag)


# (predicado, mensagem) — os mesmos 4 invariantes do gate pytest (+ guarda de erro de LLM).
_GATE_CHECKS = (
    (
        lambda r: r["per_parecer_ub_ic95"] >= _PER_PARECER_GATE,
        lambda r: f"UB IC95 per-parecer {r['per_parecer_ub_ic95']:.2%} ≥ {_PER_PARECER_GATE:.0%}",
    ),
    (
        lambda r: r["diag_violations"] != 0,
        lambda r: f"{r['diag_violations']} violações em temp=0 (bug de design)",
    ),
    (
        lambda r: r["density_median"] < _DENSITY_FLOOR,
        lambda r: f"densidade {r['density_median']} < piso {_DENSITY_FLOOR}",
    ),
    (
        lambda r: r["total_cost_usd"] > _COST_CAP_USD,
        lambda r: f"custo US$ {r['total_cost_usd']:.2f} > cap US$ {_COST_CAP_USD}",
    ),
)


def _gate_failures(report: dict) -> list[str]:
    """Os invariantes do gate pytest como mensagens (lista vazia = passou)."""
    fails = [msg(report) for pred, msg in _GATE_CHECKS if pred(report)]
    if report["n_ok_gate"] < len(HOLDOUT) * _GATE_RUNS * 0.9:
        fails.insert(0, f"erros de LLM demais: {report['n_ok_gate']} ok")
    return fails


_SUMMARY_ROWS = (
    ("gerações ok (gate)", "n_ok_gate", "{}"),
    ("per-parecer violações", "per_parecer_violations", "{}"),
    ("per-parecer UB IC95", "per_parecer_ub_ic95", "{:.2%}"),
    ("missing_path pareceres", "missing_path_pareceres", "{}"),
    ("conformidade citação", "per_citation_conformidade", "{:.2%}"),
    ("densidade (mediana)", "density_median", "{}"),
    ("diag temp=0 violações", "diag_violations", "{}"),
    ("custo total US$", "total_cost_usd", "{:.2f}"),
)


def _print_summary(report: dict) -> None:
    print("\n── resumo ──")
    for label, key, fmt in _SUMMARY_ROWS:
        print(f"{label:<24}{fmt.format(report[key])}")


def _write_report(report: dict, path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nrelatório → {out}")


def _report_gate(fails: list[str]) -> int:
    if not fails:
        print("\n✓ GATE PASSOU")
        return 0
    print("\n✗ GATE FALHOU:")
    for f in fails:
        print(f"  - {f}")
    return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Eval paralelo do evidencia_path (A26.l9)")
    parser.add_argument(
        "--workers", type=int, default=_DEFAULT_WORKERS, help="threads paralelas (default 6)"
    )
    parser.add_argument("--report", default=str(_REPORT_PATH), help="caminho do relatório JSON")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("erro: ANTHROPIC_API_KEY ausente (eval owner-gated)", file=sys.stderr)
        return 2
    print(f"rodando {len(_plan_tasks())} gerações em {args.workers} workers…", flush=True)
    report = _collect_parallel(args.workers)
    _write_report(report, args.report)
    _print_summary(report)
    return _report_gate(_gate_failures(report))


if __name__ == "__main__":
    raise SystemExit(main())
