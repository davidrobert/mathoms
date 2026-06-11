"""Gates do skeleton de lineage (A24.l5 patrimônio + A24.l6 reserva/despesa/total investido · ADR-279/ADR-281): espelhamento ``_lineage.value`` ↔ payload em cents int, soma derivada dos ``inputs[]`` (check_lineage_sum, incl. caminho K4 da despesa), byte-identidade do bloco em 2 runs, resolver até a folha e refs do registry por import real. Decimal(str(v)) sempre (ADR-090)."""

from __future__ import annotations

import importlib.util
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.services.lineage_resolver import (
    LineageResolver,
    is_missing,
    resolve_field_path,
)
from tests.pipeline_golden_substrate import (
    load_fixture,
    run_dogfood_pipeline,
    run_e3_e4_e5,
    write_e5_config,
)

_REPO = Path(__file__).resolve().parents[1]
_FIX = _REPO / "tests" / "fixtures" / "pipeline_golden"
_DOGFOOD = _FIX / "dogfood"
_E3_MIN = _FIX / "e3" / "minimal-conta-3_reconciled.json"
_E3_MIXED = _FIX / "e3" / "minimal-conta-com-despesa-3_reconciled.json"
_BASELINE = _FIX / "e2" / "minimal-baseline-1.5_consolidated.json"
_BASELINE_DIV = _FIX / "e2" / "minimal-baseline-divergent-1.5_consolidated.json"

# Mesmos 4 casos do substrato de conservação (tests/test_e5_conservation_invariants.py
# `_CASES`) + dogfood (dedup genuíno E1.5c/E3).
_CASES = {
    "minimal": (_E3_MIN, None, None),
    "mixed": (_E3_MIXED, None, {"lazer": ["CINEMA"]}),
    "baseline": (_E3_MIN, _BASELINE, None),
    "divergent": (_E3_MIN, _BASELINE_DIV, None),
}


def _cents(value) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _run_case(name: str, root: Path) -> dict:
    e3_path, baseline_path, expense_kw = _CASES[name]
    write_e5_config(root, expense_keywords=expense_kw)
    return run_e3_e4_e5(
        root,
        e3_payloads={e3_path.stem.replace("-3_reconciled", ""): load_fixture(e3_path)},
        baseline=load_fixture(baseline_path) if baseline_path else None,
    )


def _run_dogfood(root: Path) -> dict:
    write_e5_config(root)
    return run_dogfood_pipeline(
        root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )


@pytest.fixture(scope="module", params=[*sorted(_CASES), "dogfood"])
def e5_payload(request, tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp(f"lineage_{request.param}")
    if request.param == "dogfood":
        return _run_dogfood(root)
    return _run_case(request.param, root)


def _field(payload: dict, name: str) -> dict:
    return payload["_lineage"]["fields"][name]


def _resolved_cents(payload: dict, field_path: str) -> int:
    value = resolve_field_path(payload, field_path)
    assert not is_missing(value), f"input irresolúvel no payload: {field_path!r}"
    return _cents(value)


def test_lineage_value_mirrors_payload(e5_payload: dict):
    """to_cents(_lineage.fields[X].value) == to_cents(payload[X]) p/ liquido e bruto."""
    pat = e5_payload["patrimonio"]
    assert _cents(_field(e5_payload, "patrimonio.liquido")["value"]) == _cents(pat["liquido"])
    assert _cents(_field(e5_payload, "patrimonio.bruto")["value"]) == _cents(pat["bruto"])


def test_bruto_equals_sum_of_lineage_inputs(e5_payload: dict):
    """check_lineage_sum: Σ inputs[] da composição (resolvidos no payload) == value."""
    bruto = _field(e5_payload, "patrimonio.bruto")
    soma = sum(_resolved_cents(e5_payload, i["field"]) for i in bruto["inputs"])
    assert _cents(bruto["value"]) == soma


def test_liquido_equals_bruto_minus_dividas_inputs(e5_payload: dict):
    """check_lineage_sum: bruto − dividas (resolvidos dos inputs[]) == value."""
    liquido = _field(e5_payload, "patrimonio.liquido")
    by_field = {i["field"]: _resolved_cents(e5_payload, i["field"]) for i in liquido["inputs"]}
    assert set(by_field) == {"patrimonio.bruto", "patrimonio.dividas"}
    assert _cents(liquido["value"]) == by_field["patrimonio.bruto"] - by_field["patrimonio.dividas"]


def test_lineage_shape_invariants(e5_payload: dict):
    """ADR-279: inputs sorted canônico, value string; member_hashes vazio nas
    fixtures (baseline-fed na l5; despesa cai em k4_coverage parcial na l6)."""
    assert e5_payload["_lineage"]["lineage_version"] == "1.0"
    for entry in e5_payload["_lineage"]["fields"].values():
        assert isinstance(entry["value"], str) and "." in entry["value"]
        assert entry["member_hashes"] == []
        keys = [(i["stage"], i["artifact_key"], i["field"]) for i in entry["inputs"]]
        assert keys == sorted(keys)


# ──────────────── agregados da l6 (A24.l6 + A25.l6 KR2 6/6) ────────────────

_L6_FIELDS = (
    "reserva_emergencia.total_liquida",
    "fluxo_caixa.despesa_total",
    "investimentos.total",
    "endividamento.total_dividas",
)
_FORMULA_FIELDS = ("fluxo_caixa.fluxo_liquido",)


@pytest.mark.parametrize("field_name", _L6_FIELDS + _FORMULA_FIELDS)
def test_l6_value_mirrors_payload(e5_payload: dict, field_name: str):
    """to_cents(_lineage.fields[X].value) == to_cents(payload[X]) — campo é o dot-path."""
    assert _cents(_field(e5_payload, field_name)["value"]) == _resolved_cents(
        e5_payload, field_name
    )


@pytest.mark.parametrize("field_name", _L6_FIELDS)
def test_l6_aggregate_equals_sum_of_lineage_inputs(e5_payload: dict, field_name: str):
    """check_lineage_sum: Σ inputs[] (resolvidos no payload) == value, em cents int."""
    entry = _field(e5_payload, field_name)
    soma = sum(_resolved_cents(e5_payload, i["field"]) for i in entry["inputs"])
    assert _cents(entry["value"]) == soma


def test_fluxo_liquido_equals_receita_minus_despesa_inputs(e5_payload: dict):
    """check_lineage_sum (A25.l6): receita_total − despesa_total (resolvidos
    dos inputs[]) == value — mesma identidade do invariante G-b."""
    entry = _field(e5_payload, "fluxo_caixa.fluxo_liquido")
    by_field = {i["field"]: _resolved_cents(e5_payload, i["field"]) for i in entry["inputs"]}
    assert set(by_field) == {"fluxo_caixa.despesa_total", "fluxo_caixa.receita_total"}
    assert (
        _cents(entry["value"])
        == by_field["fluxo_caixa.receita_total"] - by_field["fluxo_caixa.despesa_total"]
    )


def test_total_dividas_is_distinct_node_of_patrimonio_dividas(e5_payload: dict):
    """A25.l6: nó declarado no enforcer (EndividamentoAnalyzer) aponta para
    ``patrimonio.dividas`` — 2 nós distintos, 1 fonte, mesmo valor em cents."""
    entry = _field(e5_payload, "endividamento.total_dividas")
    assert [i["field"] for i in entry["inputs"]] == ["patrimonio.dividas"]
    assert entry["edge_type"] == "aggregation"
    assert _cents(entry["value"]) == _resolved_cents(e5_payload, "patrimonio.dividas")


def test_despesa_k4_coverage_partial_contract(e5_payload: dict):
    """Q3/B8: fixtures não estampam natural_key v2 em E4 (só transaction_hash v1,
    ADR-278 B4) → member_hashes vazio + signals.k4_coverage=partial quando há tx.
    A25.l5 (N2): sinais de conferência do dedup E4 viajam junto — string int."""
    entry = _field(e5_payload, "fluxo_caixa.despesa_total")
    assert entry["member_hashes"] == []
    signals = entry.get("signals") or {}
    if _cents(entry["value"]) > 0:
        assert signals.get("k4_coverage") == "partial"
    else:
        assert "k4_coverage" not in signals
    for key in ("tx_total", "dedup_collapsed", "dedup_review"):
        assert signals.get(key, "0").isdigit()
    assert int(signals.get("dedup_collapsed", "0")) <= int(signals.get("tx_total", "0"))


def test_lineage_byte_identical_across_runs(tmp_path: Path):
    """Run 2× na fixture dogfood → bloco _lineage byte-idêntico (zero timestamp/UUID)."""
    first = json.dumps(_run_dogfood(tmp_path / "a")["_lineage"], sort_keys=True)
    second = json.dumps(_run_dogfood(tmp_path / "b")["_lineage"], sort_keys=True)
    assert first == second


# ─────────────────────────────── resolver ───────────────────────────────


def _seeded_resolver(payload: dict) -> LineageResolver:
    store = InMemoryArtifactStore()
    store.seed("E5", "analise_financeira", payload)
    return LineageResolver(store)


def test_resolver_walks_liquido_to_leaves(e5_payload: dict):
    tree = _seeded_resolver(e5_payload).resolve("E5", "analise_financeira", "patrimonio.liquido")
    assert tree["node_type"] == "lineage"
    bruto = next(n for n in tree["inputs"] if n["field"] == "patrimonio.bruto")
    assert bruto["node_type"] == "lineage"
    assert bruto["inputs"], "bruto sem folhas de composição"
    assert all(leaf["node_type"] == "no_lineage" for leaf in bruto["inputs"])


@pytest.mark.parametrize("field_name", _L6_FIELDS)
def test_resolver_walks_l6_aggregates_to_leaves(e5_payload: dict, field_name: str):
    """Cada agregado da l6 resolve até folhas no_lineage sem dangling."""
    tree = _seeded_resolver(e5_payload).resolve("E5", "analise_financeira", field_name)
    assert tree["node_type"] == "lineage"
    assert all(leaf["node_type"] == "no_lineage" for leaf in tree["inputs"])


def test_resolver_walks_fluxo_liquido_through_despesa_total(e5_payload: dict):
    """A25.l6: fluxo_liquido desce 2 níveis — despesa_total é nó lineage
    (com folhas próprias), receita_total é folha no_lineage."""
    tree = _seeded_resolver(e5_payload).resolve(
        "E5", "analise_financeira", "fluxo_caixa.fluxo_liquido"
    )
    assert tree["node_type"] == "lineage"
    by_field = {n["field"]: n for n in tree["inputs"]}
    assert by_field["fluxo_caixa.receita_total"]["node_type"] == "no_lineage"
    despesa = by_field["fluxo_caixa.despesa_total"]
    assert despesa["node_type"] == "lineage"
    assert all(leaf["node_type"] == "no_lineage" for leaf in despesa["inputs"])


def test_resolver_field_without_lineage_is_no_lineage_node(e5_payload: dict):
    node = _seeded_resolver(e5_payload).resolve("E5", "analise_financeira", "patrimonio.dividas")
    assert node["node_type"] == "no_lineage"
    assert _cents(node["value"]) == _cents(e5_payload["patrimonio"]["dividas"])


def test_resolver_unresolvable_refs_are_dangling_never_exception():
    resolver = _seeded_resolver({"patrimonio": {"bruto": 1.0}})
    missing_artifact = resolver.resolve("E4", "despesas", "total")
    missing_field = resolver.resolve("E5", "analise_financeira", "patrimonio.nao_existe")
    assert missing_artifact["node_type"] == "dangling"
    assert "E4" in missing_artifact["reason"]
    assert missing_field["node_type"] == "dangling"
    assert "patrimonio.nao_existe" in missing_field["reason"]


# ───────────────── despesa_member_hashes (K4 · Q3/B8, unit) ─────────────────


def _tx(wire_float: float, k4: str | None, *, version: int = 2) -> dict:
    """Tx wire-shaped de E4 (``valor`` é float no wire legado, pré-cutover amount)."""
    tx = {"valor": wire_float, "transaction_hash": "deadbeef00000000"}
    if k4 is not None:
        tx["natural_key"] = {"hash": k4, "hash_version": version}
    return tx


def test_despesa_member_hashes_full_coverage_emits_sorted_unique_k4():
    from pipeline.domain.services.e5_lineage import despesa_member_hashes

    e4 = {
        "dados": {"lazer": [_tx(30.0, "b" * 16), _tx(10.0, "a" * 16)], "casa": [_tx(5.0, "a" * 16)]}
    }
    hashes, signals = despesa_member_hashes(e4)
    assert hashes == ["a" * 16, "b" * 16]
    assert signals == {}


def test_despesa_member_hashes_partial_or_v1_only_empties_and_signals():
    """transaction_hash v1 NÃO é K4 (ADR-278 B4); hash parcial não vale (all-or-nothing)."""
    from pipeline.domain.services.e5_lineage import despesa_member_hashes

    sem_key = {"dados": {"lazer": [_tx(30.0, None)]}}
    parcial = {"dados": {"lazer": [_tx(30.0, "a" * 16), _tx(10.0, None)]}}
    v1 = {"dados": {"lazer": [_tx(30.0, "a" * 16, version=1)]}}
    for e4 in (sem_key, parcial, v1):
        assert despesa_member_hashes(e4) == ([], {"k4_coverage": "partial"})


def test_conferencia_signals_from_e4_propagates_only_valid_string_ints():
    """A25.l5 (N2): só chaves de conferência com string-int passam; artefato
    pré-A25 (sem ``_lineage``) ou malformado degrada para ``{}``."""
    from pipeline.domain.services.e5_lineage import conferencia_signals_from_e4

    ok = {"_lineage": {"signals": {"tx_total": "12", "dedup_collapsed": "2", "dedup_review": "1"}}}
    assert conferencia_signals_from_e4(ok) == {
        "tx_total": "12",
        "dedup_collapsed": "2",
        "dedup_review": "1",
    }
    assert conferencia_signals_from_e4({}) == {}
    assert conferencia_signals_from_e4({"_lineage": "corrompido"}) == {}
    assert conferencia_signals_from_e4({"_lineage": {"signals": {"tx_total": 12}}}) == {}
    assert conferencia_signals_from_e4({"_lineage": {"signals": {"tx_total": "-3"}}}) == {}
    extra = {"_lineage": {"signals": {"tx_total": "5", "stage": "E4"}}}
    assert conferencia_signals_from_e4(extra) == {"tx_total": "5"}


def test_despesa_member_hashes_inline_cap_exceeded_empties_and_signals():
    from pipeline.domain.services.e5_lineage import despesa_member_hashes

    e4 = {"dados": {"lazer": [_tx(1.0, f"{i:016x}") for i in range(201)]}}
    assert despesa_member_hashes(e4) == ([], {"k4_coverage": "full", "inline_cap": "exceeded"})


def test_despesa_member_hashes_sum_matches_total_when_full_coverage():
    """check_lineage_sum no caminho K4: Σ cents(valor das txs com hash listado) == cents(total)."""
    from pipeline.domain.services.e5_lineage import despesa_member_hashes

    txs = [_tx(30.55, "a" * 16), _tx(10.45, "b" * 16), _tx(9.0, "c" * 16)]
    e4 = {"dados": {"lazer": txs[:2], "casa": txs[2:]}, "total_geral": 50.0}
    hashes, _ = despesa_member_hashes(e4)
    amount_by_hash = {t["natural_key"]["hash"]: t["valor"] for t in txs}
    assert sum(_cents(amount_by_hash[h]) for h in hashes) == _cents(e4["total_geral"])


# ──────────────────────────── check_lineage_refs ────────────────────────────


def _load_check_lineage_refs():
    spec = importlib.util.spec_from_file_location(
        "check_lineage_refs", _REPO / "dev" / "check_lineage_refs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_lineage_refs_green_on_real_registry():
    assert _load_check_lineage_refs().main() == 0


def test_check_lineage_refs_broken_ref_exits_1(capsys):
    broken = {
        "x.y": {
            "ref": "pipeline.domain.services.patrimonio_calculator:Inexistente.calculate",
            "adr": "ADR-999",
        }
    }
    assert _load_check_lineage_refs().main(broken) == 1
    err = capsys.readouterr().err
    assert "Inexistente" in err and "ADR-999" in err
