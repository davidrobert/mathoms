"""Gates do walking skeleton de lineage (A24.l5 · ADR-279/ADR-281): espelhamento ``_lineage.value`` ↔ payload em cents int, soma derivada dos ``inputs[]`` (check_lineage_sum), byte-identidade do bloco em 2 runs, resolver até a folha e refs do registry por import real. Decimal(str(v)) sempre (ADR-090)."""

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
    """ADR-279: inputs sorted canônico, member_hashes vazio (baseline-fed), value string."""
    assert e5_payload["_lineage"]["lineage_version"] == "1.0"
    for entry in e5_payload["_lineage"]["fields"].values():
        assert isinstance(entry["value"], str) and "." in entry["value"]
        assert entry["member_hashes"] == []
        keys = [(i["stage"], i["artifact_key"], i["field"]) for i in entry["inputs"]]
        assert keys == sorted(keys)


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
