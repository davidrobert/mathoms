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
# Colapso-guarda (ADR-296): pós-l9 a prosa não tem R$, então a densidade é a mediana
# de ÂNCORAS/parecer (não mais money_tokens). Piso conservador — re-ancorar na 1ª
# medição real (o anti-sub-citação importa, não o número absoluto).
_DENSITY_FLOOR = 5
# Cap escalado ao holdout estratificado (ADR-300 §Item 3): n=24 fixtures × _GATE_RUNS +
# diag (~144 gerações) vs. 60 do holdout monocultura — ~2,4×. ~US$29/run observado;
# cap com folga p/ jitter de tokens. Budget é não-binário (UX); este cap só barra fuga.
_COST_CAP_USD = 50.0


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


# ADR-292: missing_path (prosa cita R$ sem path verificável) é cobertura, não
# citação incorreta. Pós-coerção path-filtro → None ele sobe mecanicamente (antes
# morria em reask e nunca chegava ao verificador). Só estas camadas — citação que
# resolve ERRADO — contam como violação de gate; missing_path vira métrica à parte.
_HARD_LAYERS = ("pairing_mismatch", "whitelist_miss", "resolve_null")


def _verdict(fixture, result) -> dict:
    """Veredito de citação (PII-free) de uma geração."""
    summary = result.evidencia_summary or {}
    by_layer = summary.get("failures_by_layer", {})
    hard_failed = sum(int(by_layer.get(k, 0)) for k in _HARD_LAYERS)
    return {
        "fixture": fixture.fixture_id,
        "stratum": fixture.stratum,
        "ok": result.output is not None,
        "failed": int(summary.get("evidencia_failed", 0)),
        "hard_failed": hard_failed,
        "missing_path": int(by_layer.get("missing_path", 0)),
        "verified": int(summary.get("evidencia_verified", 0)),
        "number_in_prose": int(summary.get("money_tokens_total", 0)),  # ADR-296: deve=0
        "ancoras": int(summary.get("ancoras_total", 0)),  # densidade de citação
        "failures_by_layer": by_layer,
        "violation": hard_failed > 0,
        "cost_usd": float(result.cost_usd),
    }


def _run_once(fixture, temperature: float, run_idx: int) -> dict:
    """Gera 1 parecer real e extrai o veredito de citação (PII-free)."""
    config = ParecerOrchestratorConfig(
        workspace_id=f"eval-{fixture.fixture_id}-{run_idx}", temperature=temperature
    )
    result = generate_parecer(e5_data=fixture.e5, config=config, cache=_NoCache())
    return _verdict(fixture, result)


def _wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    """Limite superior do IC95 (Wilson) da proporção k/n."""
    if n == 0:
        return 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (centre + margin) / denom


def _build_report(gate: list[dict], diag: list[dict]) -> dict:
    """Agrega vereditos em métricas de gate + cobertura (missing_path à parte, ADR-292)."""
    ok_gate = [r for r in gate if r["ok"]]
    violations = sum(r["violation"] for r in ok_gate)
    return {
        "gate_runs": gate,
        "diag_runs": diag,
        "n_ok_gate": len(ok_gate),
        "per_parecer_violations": violations,
        "per_parecer_ub_ic95": _wilson_upper(violations, len(ok_gate)),
        "missing_path_pareceres": sum(1 for r in ok_gate if r["missing_path"] > 0),
        "per_citation_conformidade": _conformidade(ok_gate),
        "density_median": statistics.median([r["ancoras"] for r in ok_gate] or [0]),
        # ADR-296: R$ na prosa é budget (chip autoritativo), mediana 0 = maioria limpa.
        "number_in_prose_total": sum(r["number_in_prose"] for r in ok_gate),
        "number_in_prose_median": statistics.median([r["number_in_prose"] for r in ok_gate] or [0]),
        "diag_violations": sum(r["violation"] for r in diag if r["ok"]),
        "total_cost_usd": sum(r["cost_usd"] for r in gate + diag),
    }


def _collect() -> dict:
    gate = [_run_once(f, _GATE_TEMP, i) for f in HOLDOUT for i in range(_GATE_RUNS)]
    diag = [_run_once(f, _DIAG_TEMP, 0) for f in HOLDOUT]
    report = _build_report(gate, diag)
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


def test_holdout_zero_pairing_violations(eval_report):
    """Gate de segurança (A26.l2 redefinido): zero citação incorreta. O UB IC95 fica como
    telemetria — com 0 violações em n=50 ele é mecanicamente ~7,1% (Wilson), inalcançável
    <5% sem n≥74; o que importa é violações==0 (re-eval 2026-06-20)."""
    assert eval_report["n_ok_gate"] >= len(HOLDOUT) * _GATE_RUNS * 0.9, "muitos erros de LLM"
    assert eval_report["per_parecer_violations"] == 0, (
        f"{eval_report['per_parecer_violations']} pareceres com citação incorreta "
        f"(UB IC95 {eval_report['per_parecer_ub_ic95']:.2%})"
    )


def test_diagnostic_temp0_zero_violations(eval_report):
    """temp=0: violação aqui = bug de design (catálogo/prompt), não variância."""
    assert (
        eval_report["diag_violations"] == 0
    ), f"{eval_report['diag_violations']} violações em temp=0 — design ainda tem bug"


def test_citation_density_floor(eval_report):
    """Anti-sub-citação (ADR-296): mediana de âncoras/parecer não pode despencar."""
    assert (
        eval_report["density_median"] >= _DENSITY_FLOOR
    ), f"densidade {eval_report['density_median']} âncoras < piso {_DENSITY_FLOOR} — sub-citação"


def test_number_in_prose_within_budget(eval_report):
    """ADR-296: prosa sem R$ é budget (o chip é autoritativo; value_mismatch já impossível).
    Maioria dos pareceres limpa (mediana 0); resíduo raro tolerado (re-eval 2026-06-20:
    11 tokens / 50 ger ≈ 0,22/parecer, mediana 0)."""
    assert eval_report["number_in_prose_median"] == 0, (
        f"mediana de R$ na prosa = {eval_report['number_in_prose_median']} "
        f"(total {eval_report['number_in_prose_total']}) — maioria deveria ser limpa"
    )


def test_cost_within_cap(eval_report):
    assert (
        eval_report["total_cost_usd"] <= _COST_CAP_USD
    ), f"custo US$ {eval_report['total_cost_usd']:.2f} acima do cap US$ {_COST_CAP_USD}"
