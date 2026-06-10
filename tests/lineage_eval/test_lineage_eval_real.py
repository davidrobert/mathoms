"""Eval real de localização com LLM (ADR-281 · A25.l4 F7) — roda SÓ no job nightly ``lineage-eval`` (marker + env gate; PR-run pula): 29 casos × N trials, métricas vs baseline ``dev/snapshots/lineage_eval_baseline.json`` (KR1 accuracy ≥85% e ≥ baseline−2pp; KR3 p95 ≤6), cap duro US$ 5.00/run, relatório JSON por caso como artefato de CI."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.services.lineage_debug_tools import (
    LineageDebugTools,
    lineage_debug_whitelist,
)
from pipeline.llm.lineage_debug import (
    LineageDebugConfig,
    LocalizationOutcome,
    load_lineage_debug_config,
    localize,
)
from pipeline.llm.litellm_client import LLMConfig, LLMError, LLMService
from tests.lineage_eval.cases import E5, KEY, LineageEvalCase, build_cases
from tests.lineage_eval.metrics import TrialRecord, aggregate_metrics

pytestmark = pytest.mark.lineage_eval

_REPO = Path(__file__).resolve().parents[2]
_BASELINE_PATH = _REPO / "dev" / "snapshots" / "lineage_eval_baseline.json"
_REPORT_ENV = "MATHOMS_LINEAGE_EVAL_REPORT"


def _env_or_skip() -> str:
    if os.environ.get("MATHOMS_RUN_LINEAGE_EVAL") != "1":
        pytest.skip("eval real só roda no nightly (MATHOMS_RUN_LINEAGE_EVAL=1)")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY ausente — degrada p/ asserts determinísticos do PR")
    return api_key


def _llm_service(config: LineageDebugConfig, api_key: str) -> LLMService:
    provider, _, model_name = config.model_id.partition("/")
    return LLMService(
        LLMConfig(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )
    )


def _tools_for(case: LineageEvalCase, base: dict) -> LineageDebugTools:
    payload = copy.deepcopy(base)
    case.mutate_fn(payload)
    store = InMemoryArtifactStore()
    store.seed(E5, KEY, payload)
    return LineageDebugTools(store=store, whitelist=lineage_debug_whitelist())


def _run_trial(
    case: LineageEvalCase, base: dict, config: LineageDebugConfig, api_key: str
) -> TrialRecord:
    try:
        outcome = localize(
            complaint=case.complaint,
            entry_field=case.entry_field,
            tools=_tools_for(case, base),
            llm_service=_llm_service(config, api_key),
            config=config,
        )
    except LLMError as exc:
        return _record(case, LocalizationOutcome(miss_reason=f"llm_error:{type(exc).__name__}"))
    return _record(case, outcome)


def _record(case: LineageEvalCase, outcome: LocalizationOutcome) -> TrialRecord:
    return TrialRecord(
        case_id=case.case_id,
        family=case.family,
        sealed=case.sealed,
        predicted=outcome.result.node_id() if outcome.result else None,
        target=case.target_node_id,
        tool_iterations=outcome.tool_iterations,
        llm_calls=outcome.llm_calls,
        tokens_in=outcome.tokens_in,
        tokens_out=outcome.tokens_out,
        usd_spent=outcome.usd_spent,
        miss_reason=outcome.miss_reason,
    )


def _run_all_trials(config: LineageDebugConfig, base: dict, api_key: str) -> list[TrialRecord]:
    records: list[TrialRecord] = []
    spent = 0.0
    for case in build_cases():
        for _ in range(config.trials_per_case):
            assert spent < config.usd_cap_run, (
                f"cap duro de gasto estourado: ${spent:.2f} >= ${config.usd_cap_run:.2f} "
                "antes de completar a suite"
            )
            record = _run_trial(case, base, config, api_key)
            records.append(record)
            spent += record.usd_spent
    return records


def _write_report(config: LineageDebugConfig, metrics: dict, records: list[TrialRecord]) -> None:
    path = Path(os.environ.get(_REPORT_ENV, str(_REPO / "_scratch" / "lineage_eval_report.json")))
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "model_id": config.model_id,
        "prompt_version": config.version,
        "metrics": metrics,
        "trials": [r.to_dict() for r in records],
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _baseline_floor(config: LineageDebugConfig) -> float:
    """Floor efetivo: max(85%, baseline − 2pp); placeholder = só o floor KR1."""
    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    if baseline.get("status") == "pending_first_real_run":
        return config.accuracy_floor
    baseline_accuracy = baseline["metrics"]["localization_accuracy_at_node"]
    return max(config.accuracy_floor, baseline_accuracy - config.regression_band_pp / 100)


def _assert_thresholds(metrics: dict, config: LineageDebugConfig) -> None:
    floor = _baseline_floor(config)
    accuracy = metrics["localization_accuracy_at_node"]
    assert accuracy >= floor, (
        f"localization_accuracy@node={accuracy:.2%} < floor {floor:.2%} "
        f"(KR1 ≥85% e ≥ baseline−2pp); relatório em ${_REPORT_ENV}"
    )
    assert metrics["tool_iterations_p95"] <= config.max_tool_iterations, (
        f"tool_iterations_p95={metrics['tool_iterations_p95']} > KR3 cap "
        f"{config.max_tool_iterations}"
    )
    assert metrics["total_usd_spent"] <= config.usd_cap_run


def test_localization_eval_against_baseline(dogfood_e5):
    api_key = _env_or_skip()
    config = load_lineage_debug_config()
    records = _run_all_trials(config, dogfood_e5, api_key)
    metrics = aggregate_metrics(records)
    _write_report(config, metrics, records)
    _assert_thresholds(metrics, config)
