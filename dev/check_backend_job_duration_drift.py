#!/usr/bin/env python3
"""Vigia a mediana de duração de um job de CI contra o teto declarado (ADR-210 §Adendo 2026-08-05): sem isso, a próxima erosão do timeout exige arqueologia manual de dezenas de jobs via API; offline/sem ``gh`` degrada para pass silencioso."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from statistics import median

DEFAULT_WORKFLOW = "ci.yml"
DEFAULT_JOB_NAME = "Backend tests (backend/tests/)"
DEFAULT_CEILING_MIN = 20.0
DEFAULT_THRESHOLD_PCT = 60.0
DEFAULT_N_RUNS = 20


@dataclass(frozen=True)
class DriftReport:
    """Achado do watchdog de duração; `median_min` é a mediana observada."""

    job_name: str
    median_min: float
    ceiling_min: float
    threshold_pct: float
    n_samples: int

    def format(self) -> str:
        pct_of_ceiling = (self.median_min / self.ceiling_min) * 100
        return (
            f"Job `{self.job_name}`: mediana de {self.median_min:.2f}min em "
            f"{self.n_samples} runs — {pct_of_ceiling:.0f}% do teto de "
            f"{self.ceiling_min:.0f}min (gatilho: >{self.threshold_pct:.0f}%)."
        )


def _run(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def repo_slug() -> str | None:
    override = os.environ.get("MATHOMS_REPO_SLUG")
    if override:
        return override
    out = _run(["gh", "repo", "view", "--json", "nameWithOwner"])
    if out is None:
        return None
    try:
        return json.loads(out)["nameWithOwner"]
    except (json.JSONDecodeError, KeyError):
        return None


def _recent_successful_run_ids(repo: str, workflow_file: str, n: int) -> list[int]:
    out = _run(
        [
            "gh",
            "api",
            f"repos/{repo}/actions/workflows/{workflow_file}/runs",
            "-X",
            "GET",
            "-f",
            "status=success",
            "-f",
            f"per_page={n}",
            "--jq",
            ".workflow_runs[].id",
        ]
    )
    if out is None:
        return []
    return [int(line) for line in out.splitlines() if line.strip()]


def _job_duration_minutes(repo: str, run_id: int, job_name: str) -> float | None:
    jq_filter = (
        f'.jobs[] | select(.name == "{job_name}") | '
        "((.completed_at | fromdateiso8601) - (.started_at | fromdateiso8601)) / 60"
    )
    out = _run(
        [
            "gh",
            "api",
            f"repos/{repo}/actions/runs/{run_id}/jobs",
            "--jq",
            jq_filter,
        ]
    )
    if not out or not out.strip():
        return None
    try:
        return float(out.strip().splitlines()[0])
    except ValueError:
        return None


def fetch_recent_job_durations(repo: str, workflow_file: str, job_name: str, n: int) -> list[float]:
    """Duração (minutos) do job nomeado nos últimos `n` runs bem-sucedidos."""
    durations: list[float] = []
    for run_id in _recent_successful_run_ids(repo, workflow_file, n):
        duration = _job_duration_minutes(repo, run_id, job_name)
        if duration is not None:
            durations.append(duration)
    return durations


def check_drift(
    durations: list[float],
    job_name: str,
    ceiling_min: float,
    threshold_pct: float,
) -> DriftReport | None:
    """`None` se a amostra for pequena demais ou a mediana estiver sob o gatilho."""
    if len(durations) < 5:
        return None
    observed = median(durations)
    if observed <= ceiling_min * (threshold_pct / 100):
        return None
    return DriftReport(job_name, observed, ceiling_min, threshold_pct, len(durations))


def render_report(report: DriftReport | None) -> str:
    if report is None:
        return ""
    return "\n".join(
        [
            report.format(),
            "",
            "Antes de bumpar o teto, leia a tabela do `--durations=25` do job",
            "(ADR-210 §Adendo 2026-08-03) e separe volume de regressão. Só bumpe",
            "se o crescimento for de volume — ADR-210 §PRÓXIMA VEZ.",
        ]
    )


def _evaluate(args: argparse.Namespace) -> DriftReport | None:
    """`None` sem repo (offline) ou sem drift — `main` decide o print por `--report`."""
    repo = repo_slug()
    if repo is None:
        return None
    durations = fetch_recent_job_durations(repo, args.workflow, args.job_name, args.n_runs)
    return check_drift(durations, args.job_name, args.ceiling_min, args.threshold_pct)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--job-name", default=DEFAULT_JOB_NAME)
    parser.add_argument("--ceiling-min", type=float, default=DEFAULT_CEILING_MIN)
    parser.add_argument("--threshold-pct", type=float, default=DEFAULT_THRESHOLD_PCT)
    parser.add_argument("--n-runs", type=int, default=DEFAULT_N_RUNS)
    parser.add_argument(
        "--report",
        action="store_true",
        help="Imprime relatório markdown (vazio = sem drift); sempre exit 0.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    report = _evaluate(args)
    if args.report:
        print(render_report(report))
        return 0
    if report is not None:
        print(report.format(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
