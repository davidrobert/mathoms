"""Gates determinísticos de PR do eval (ADR-281 · A25.l4 F7): estrutura da suite 24+5, mutações aplicam em memória, anomalias visíveis no renderer, diff detecta a regressão, harness localize com LLM mockado (oracle/parse-fail/tool-greedy) e métricas — zero chamada de rede."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import pytest
import yaml

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.lineage_registry import LINEAGE_RULE_REFS
from pipeline.domain.services.lineage_debug_tools import (
    LineageDebugTools,
    lineage_debug_whitelist,
)
from pipeline.domain.services.lineage_diff import lineage_diff
from pipeline.domain.services.lineage_render_llm import render_lineage_linear
from pipeline.domain.services.lineage_resolver import LineageResolver
from pipeline.llm.lineage_debug import (
    LocalizationOutcome,
    load_lineage_debug_config,
    localize,
)
from pipeline.llm.litellm_client import LLMValidationError
from pipeline.llm.schemas.lineage_debug import LineageDebugStep, LocalizationResult
from tests.lineage_eval.cases import E5, KEY, LineageEvalCase, build_cases
from tests.lineage_eval.metrics import TrialRecord, aggregate_metrics, percentile_95

_CASES = build_cases()
_FAMILIES = (
    "value_delta@leaf",
    "value_delta@aggregate",
    "input_removed",
    "rule_ref_wrong",
    "dedup_overcollapse",
    "needs_review_ignored",
)


def _mutated(base: dict, case: LineageEvalCase) -> dict:
    payload = copy.deepcopy(base)
    case.mutate_fn(payload)
    return payload


def _resolve(payload: dict, field: str) -> dict:
    store = InMemoryArtifactStore()
    store.seed(E5, KEY, payload)
    return LineageResolver(store).resolve(E5, KEY, field)


def _tree_keys(node: dict) -> set[tuple[str, str, str]]:
    keys = {(node["stage"], node["artifact_key"], node["field"])}
    for child in node.get("inputs", []):
        keys |= _tree_keys(child)
    return keys


# ─────────────────────────── estrutura da suite ───────────────────────────


def test_suite_has_24_plus_5_cases():
    assert len(_CASES) == 29
    sealed = [c for c in _CASES if c.sealed]
    assert len(sealed) == 5
    for family in _FAMILIES:
        assert sum(c.family == family for c in _CASES) == 4, family


def test_case_ids_unique_and_rule_refs_resolve_in_registry():
    ids = [c.case_id for c in _CASES]
    assert len(ids) == len(set(ids))
    registry_refs = {entry["ref"] for entry in LINEAGE_RULE_REFS.values()}
    assert all(c.expected_rule_ref in registry_refs for c in _CASES)


def test_sealed_cases_model_the_historical_bugs():
    """Selados são NÃO-TUNÁVEIS: ids fixos modelando ADR-271/246/255 + 811k + CPF."""
    assert [c.case_id for c in _CASES if c.sealed] == [
        "sel-adr271",
        "sel-adr246",
        "sel-adr255",
        "sel-811k",
        "sel-membro-cpf",
    ]


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.case_id)
def test_mutation_applies_in_memory_and_target_exists(case, dogfood_e5):
    mutated = _mutated(dogfood_e5, case)
    assert mutated != dogfood_e5, "mutação não alterou o payload"
    tree = _resolve(mutated, case.entry_field)
    assert tree["node_type"] == "lineage"
    assert case.target_node_id in _tree_keys(tree), "target fora da árvore do entry_field"


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.case_id)
def test_renderer_anomaly_visibility_matches_family_contract(case, dogfood_e5):
    rendered = render_lineage_linear(_resolve(_mutated(dogfood_e5, case), case.entry_field))
    if case.renderer_flags_anomaly:
        assert "⚠" in rendered, f"{case.case_id}: família deveria gerar anomalia no renderer"
    assert len(rendered) <= 1500 * 4


@pytest.mark.parametrize(
    "case",
    [c for c in _CASES if c.family != "needs_review_ignored"],
    ids=lambda c: c.case_id,
)
def test_lineage_diff_detects_regression_vs_golden(case, dogfood_e5):
    """needs_review fora: flag injetada não muda value/rule/inputs — é caso de renderer."""
    base_tree = _resolve(dogfood_e5, case.entry_field)
    mutated_tree = _resolve(_mutated(dogfood_e5, case), case.entry_field)
    diff = lineage_diff(base_tree, mutated_tree)
    assert diff["changed_nodes"], f"{case.case_id}: diff vazio para mutação real"


# ─────────────────────────── harness com LLM fake ───────────────────────────


@dataclass
class _FakeCall:
    output: Any
    tokens_in: int = 200
    tokens_out: int = 80

    def __post_init__(self) -> None:
        # Atributo lido por getattr no harness; rate USD mock de API (ADR-090
        # não se aplica — não é money de domínio).
        self.cost_estimate_usd = 0.002


class _ScriptedLLM:
    """Devolve passos roteirizados; Exception no roteiro é levantada."""

    def __init__(self, script: list) -> None:
        self._script = list(script)
        self.calls = 0
        self.kwargs_seen: list[dict] = []

    def call(self, **kwargs):
        self.calls += 1
        self.kwargs_seen.append(kwargs)
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return _FakeCall(output=item)


def _tools_for(payload: dict) -> LineageDebugTools:
    store = InMemoryArtifactStore()
    store.seed(E5, KEY, payload)
    return LineageDebugTools(store=store, whitelist=lineage_debug_whitelist())


def _localization(target: tuple[str, str, str]) -> LocalizationResult:
    return LocalizationResult(
        stage=target[0],
        artifact_key=target[1],
        field=target[2],
        confidence="alta",
        reasoning_short="conservação local falha neste nó",
    )


def _localize_step(target: tuple[str, str, str]) -> LineageDebugStep:
    return LineageDebugStep(action="localize", localization=_localization(target))


def _tool_step(field: str) -> LineageDebugStep:
    return LineageDebugStep(action="trace_source", field=field)


@pytest.fixture(scope="module")
def config():
    return load_lineage_debug_config()


def test_config_pins_model_literal_and_temperature_zero(config):
    assert config.model_id == "anthropic/claude-sonnet-4-20250514"
    assert config.temperature == 0.0
    assert config.max_tool_iterations == 6
    assert config.trials_per_case == 3
    assert config.accuracy_floor == 0.85
    assert config.usd_cap_run == 5.0
    assert config.seed == 281


def test_config_seed_is_optional_for_backward_compat(tmp_path):
    """YAML sem ``seed`` (formato v1.0) carrega com seed=None — não quebra override antigo."""
    from pipeline.llm.lineage_debug import _DEFAULT_CONFIG_PATH

    raw = yaml.safe_load(_DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    del raw["seed"]
    legacy = tmp_path / "lineage_debug.yaml"
    legacy.write_text(yaml.safe_dump(raw), encoding="utf-8")
    assert load_lineage_debug_config(legacy).seed is None


def test_localize_passes_pinned_seed_to_llm_service(dogfood_e5, config):
    """Determinismo (ADR-281): o seed do YAML chega em TODA chamada do harness."""
    llm = _ScriptedLLM([_localize_step((E5, KEY, "patrimonio.bruto"))])
    localize(
        complaint="número errado",
        entry_field="patrimonio.liquido",
        tools=_tools_for(dogfood_e5),
        llm_service=llm,
        config=config,
    )
    assert llm.kwargs_seen and all(k["seed"] == 281 for k in llm.kwargs_seen)


def test_localize_oracle_hits_target(dogfood_e5, config):
    case = next(c for c in _CASES if c.case_id == "vdl-01")
    payload = _mutated(dogfood_e5, case)
    llm = _ScriptedLLM([_tool_step("patrimonio.bruto"), _localize_step(case.target_node_id)])
    outcome = localize(
        complaint=case.complaint,
        entry_field=case.entry_field,
        tools=_tools_for(payload),
        llm_service=llm,
        config=config,
    )
    assert outcome.localized and outcome.result is not None
    assert outcome.result.node_id() == case.target_node_id
    assert outcome.llm_calls == 2
    assert outcome.tool_iterations == 1
    assert outcome.usd_spent == pytest.approx(0.004)
    assert [t["tool"] for t in outcome.tool_trace] == ["trace_source"]


def test_localize_parse_fail_twice_is_miss_not_crash(dogfood_e5, config):
    llm = _ScriptedLLM([LLMValidationError("bad json"), LLMValidationError("bad json")])
    outcome = localize(
        complaint="número errado",
        entry_field="patrimonio.liquido",
        tools=_tools_for(dogfood_e5),
        llm_service=llm,
        config=config,
    )
    assert not outcome.localized
    assert outcome.miss_reason == "parse_failure"
    assert outcome.parse_failures == 2


def test_localize_tool_greedy_is_capped_then_miss(dogfood_e5, config):
    llm = _ScriptedLLM([_tool_step("patrimonio.bruto")] * 12)
    outcome = localize(
        complaint="número errado",
        entry_field="patrimonio.liquido",
        tools=_tools_for(dogfood_e5),
        llm_service=llm,
        config=config,
    )
    assert not outcome.localized
    assert outcome.miss_reason == "tool_budget_exhausted"
    assert outcome.tool_iterations <= config.max_tool_iterations


def test_localize_recovers_after_single_parse_failure(dogfood_e5, config):
    target = (E5, KEY, "patrimonio.bruto")
    llm = _ScriptedLLM([LLMValidationError("bad"), _localize_step(target)])
    outcome = localize(
        complaint="número errado",
        entry_field="patrimonio.liquido",
        tools=_tools_for(dogfood_e5),
        llm_service=llm,
        config=config,
    )
    assert outcome.localized
    assert outcome.parse_failures == 1


# ─────────────────────────────── métricas ───────────────────────────────


def _record(case_id: str, family: str, hit: bool, iters: int, predicted_suffix="x") -> TrialRecord:
    target = (E5, KEY, "campo.alvo")
    return TrialRecord(
        case_id=case_id,
        family=family,
        sealed=False,
        predicted=target if hit else (E5, KEY, f"campo.errado-{predicted_suffix}"),
        target=target,
        tool_iterations=iters,
        llm_calls=iters + 1,
        tokens_in=1000,
        tokens_out=200,
        usd_spent=0.01,
        miss_reason=None if hit else "wrong_node",
    )


def test_aggregate_metrics_accuracy_p95_and_agreement():
    records = [
        _record("c1", "f1", True, 1),
        _record("c1", "f1", True, 2),
        _record("c1", "f1", False, 6, predicted_suffix="a"),
        _record("c2", "f2", True, 3),
        _record("c2", "f2", True, 3),
        _record("c2", "f2", True, 4),
    ]
    metrics = aggregate_metrics(records)
    assert metrics["trials"] == 6
    assert metrics["localization_accuracy_at_node"] == pytest.approx(5 / 6, abs=1e-4)
    assert metrics["accuracy_by_family"] == {"f1": pytest.approx(2 / 3, abs=1e-4), "f2": 1.0}
    assert metrics["tool_iterations_p95"] == 6
    assert metrics["trials_agreement_mean"] == pytest.approx((2 / 3 + 1.0) / 2, abs=1e-4)
    assert metrics["total_usd_spent"] == pytest.approx(0.06)


def test_percentile_95_edge_cases():
    assert percentile_95([]) == 0
    assert percentile_95([4]) == 4
    assert percentile_95(list(range(1, 101))) == 95


def test_outcome_default_is_miss():
    assert LocalizationOutcome().localized is False
