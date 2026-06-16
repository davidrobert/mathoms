"""Eval golden do evidencia_path com LLM real (A26.l1) — fora do PR gate."""

# Roda só com MATHOMS_RUN_LLM_EVAL=1 + ANTHROPIC_API_KEY (custo/flakiness). Mede
# no holdout lacrado (10 fixtures × 5 runs, temperature de produção 0.1) a taxa
# PER-PARECER de violação de citação — gate = limite superior do IC95 (Wilson)
# < 5%, que é como produção falha (1 violação → parecer inteiro vira needs_review
# no strict da A26.l2). Braço diagnóstico temp=0 separa bug de design de variância
# de amostragem. Guarda anti-sub-citação: densidade de citação não pode colapsar.
# O eval ANTECIPA o gate; NÃO substitui o gate de produção da A26.l2 (≥20 gerações
# reais). Relatório por fixture em _scratch/parecer_evidencia_eval_report.json.

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

import pytest

from backend.app.services.parecer_orchestrator import (
    ParecerOrchestratorConfig,
    generate_parecer,
)
from tests.fixtures.parecer_eval import HOLDOUT

pytestmark = pytest.mark.llm_eval

_REPO = Path(__file__).resolve().parents[1]
_REPORT_PATH = _REPO / "_scratch" / "parecer_evidencia_eval_report.json"

_GATE_RUNS = 5
_GATE_TEMP = 0.1
_DIAG_TEMP = 0.0
_PER_PARECER_GATE = 0.05
# Colapso-guarda: mediana de tokens R$/parecer não pode despencar (baseline warn
# 1.5.0 ~17 tokens; piso conservador tolera estratos de baixo ativo).
_DENSITY_FLOOR = 8
_COST_CAP_USD = 20.0


def _env_or_skip() -> None:
    if os.environ.get("MATHOMS_RUN_LLM_EVAL") != "1":
        pytest.skip("eval real só roda fora do PR gate (MATHOMS_RUN_LLM_EVAL=1)")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY ausente")


class _NoCache:
    """Cache no-op — cada run é geração fresca (5 amostras independentes)."""

    def get(self, key):  # noqa: ANN001
        return None

    def set(self, key, value, ttl_s=0):  # noqa: ANN001
        return None


def _run_once(fixture, temperature: float, run_idx: int) -> dict:
    """Gera 1 parecer real e extrai o veredito de citação (PII-free)."""
    config = ParecerOrchestratorConfig(
        workspace_id=f"eval-{fixture.fixture_id}-{run_idx}", temperature=temperature
    )
    result = generate_parecer(e5_data=fixture.e5, config=config, cache=_NoCache())
    summary = result.evidencia_summary or {}
    failed = int(summary.get("evidencia_failed", 0))
    return {
        "fixture": fixture.fixture_id,
        "stratum": fixture.stratum,
        "ok": result.output is not None,
        "failed": failed,
        "verified": int(summary.get("evidencia_verified", 0)),
        "money_tokens": int(summary.get("money_tokens_total", 0)),
        "failures_by_layer": summary.get("failures_by_layer", {}),
        "violation": failed > 0,
        "cost_usd": float(result.cost_usd),
    }


def _wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    """Limite superior do IC95 (Wilson) da proporção k/n."""
    if n == 0:
        return 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (centre + margin) / denom


def _collect() -> dict:
    gate = [_run_once(f, _GATE_TEMP, i) for f in HOLDOUT for i in range(_GATE_RUNS)]
    diag = [_run_once(f, _DIAG_TEMP, 0) for f in HOLDOUT]
    ok_gate = [r for r in gate if r["ok"]]
    violations = sum(r["violation"] for r in ok_gate)
    report = {
        "gate_runs": gate,
        "diag_runs": diag,
        "n_ok_gate": len(ok_gate),
        "per_parecer_violations": violations,
        "per_parecer_ub_ic95": _wilson_upper(violations, len(ok_gate)),
        "per_citation_conformidade": _conformidade(ok_gate),
        "density_median": statistics.median([r["money_tokens"] for r in ok_gate] or [0]),
        "diag_violations": sum(r["violation"] for r in diag if r["ok"]),
        "total_cost_usd": sum(r["cost_usd"] for r in gate + diag),
    }
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _conformidade(runs: list[dict]) -> float:
    verified = sum(r["verified"] for r in runs)
    failed = sum(r["failed"] for r in runs)
    total = verified + failed
    return verified / total if total else 1.0


@pytest.fixture(scope="module")
def eval_report() -> dict:
    _env_or_skip()
    return _collect()


def test_holdout_per_parecer_violation_ub_under_5pct(eval_report):
    ub = eval_report["per_parecer_ub_ic95"]
    assert eval_report["n_ok_gate"] >= len(HOLDOUT) * _GATE_RUNS * 0.9, "muitos erros de LLM"
    assert ub < _PER_PARECER_GATE, (
        f"UB IC95 per-parecer {ub:.2%} ≥ 5% "
        f"({eval_report['per_parecer_violations']}/{eval_report['n_ok_gate']} pareceres com violação)"
    )


def test_diagnostic_temp0_zero_violations(eval_report):
    """temp=0: violação aqui = bug de design (catálogo/prompt), não variância."""
    assert (
        eval_report["diag_violations"] == 0
    ), f"{eval_report['diag_violations']} violações em temp=0 — design ainda tem bug"


def test_citation_density_floor(eval_report):
    """Anti-sub-citação: 95% conforme não pode ser 'o LLM calou a boca'."""
    assert (
        eval_report["density_median"] >= _DENSITY_FLOOR
    ), f"densidade {eval_report['density_median']} < piso {_DENSITY_FLOOR} — possível sub-citação"


def test_cost_within_cap(eval_report):
    assert (
        eval_report["total_cost_usd"] <= _COST_CAP_USD
    ), f"custo US$ {eval_report['total_cost_usd']:.2f} acima do cap US$ {_COST_CAP_USD}"
