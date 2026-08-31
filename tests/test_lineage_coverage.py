"""Gate de cobertura do grafo de lineage (ADR-281 · A27.l2).

Fecha o vício que ``dev/check_lineage_refs.py`` não alcança: aquele gate é **existência
pura** (o ``rule_ref`` importa, a ADR existe) e não tem noção de cobertura — raiz nova no
E5 sem entrada no ``lineage_registry`` não movia gate nem accuracy. Aqui o denominador vem
do **payload publicado** (raízes que emitem dinheiro), então raiz nova sem rastro **derruba
a métrica** e reprova. O controle positivo abaixo é a prova de não-inércia: ele mede a
mesma mutação **derruba a métrica** aqui.

A assimetria com `check_lineage_refs` é **estrutural, não testável**: aquele gate recebe o
registry, nunca o payload, então não existe mutação de payload que ele possa ver. Afirmar
isso como teste seria asseverar mais do que o corpo checa; o verde dele sobre o registry
real já é coberto por `test_lineage_skeleton.py::test_check_lineage_refs_green_on_real_registry`.

Rebaseline: ``MATHOMS_UPDATE_LINEAGE_COVERAGE=1 pytest tests/test_lineage_coverage.py``.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from dev.lineage_coverage import measure_coverage
from tests.pipeline_golden_substrate import (
    load_fixture,
    run_dogfood_pipeline,
    write_e5_config,
)

_REPO = Path(__file__).resolve().parents[1]
_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"
_BASELINE = _REPO / "dev" / "snapshots" / "lineage_coverage_baseline.json"

# Raiz que não existe no E5 e publica dinheiro pelo marcador `_brl` — o veículo do
# controle positivo. Nome improvável de propósito: colidir com raiz real tornaria o
# contrafactual mudo.
_RAIZ_SINTETICA = "raiz_sintetica_do_controle_positivo"


@pytest.fixture(scope="module")
def dogfood_e5(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("lineage_coverage_dogfood")
    write_e5_config(root)
    return run_dogfood_pipeline(
        root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )


def _com_raiz_monetaria_nova(payload: dict) -> dict:
    mutated = copy.deepcopy(payload)
    mutated[_RAIZ_SINTETICA] = {"total_brl": 1234.56}
    return mutated


def _read_baseline() -> dict:
    return json.loads(_BASELINE.read_text(encoding="utf-8"))


def _write_baseline(coverage) -> None:
    _BASELINE.write_text(
        json.dumps(
            {
                "monetary_roots": sorted(coverage.monetary_roots),
                "covered_roots": sorted(coverage.covered_roots),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# ───────────────────────────── anti-vacuidade ─────────────────────────────


def test_a_medida_tem_populacao_dos_dois_lados(dogfood_e5):
    """Denominador e numerador não-vazios — sem isto, todo assert abaixo passa mudo."""
    coverage = measure_coverage(dogfood_e5)
    assert len(coverage.monetary_roots) >= 5, "denominador degenerado — payload sem dinheiro?"
    assert coverage.covered_roots, "numerador vazio — `_lineage.fields` sumiu do payload"
    assert coverage.covered_roots <= coverage.monetary_roots, (
        "raiz com rastro fora do denominador: "
        f"{sorted(coverage.covered_roots - coverage.monetary_roots)}"
    )


# ────────────────────────────────── gate ──────────────────────────────────


def test_nenhuma_raiz_monetaria_nova_sem_rastro(dogfood_e5):
    """O gate: `uncovered` só pode encolher. Raiz monetária nova sem nó reprova aqui."""
    coverage = measure_coverage(dogfood_e5)
    if os.environ.get("MATHOMS_UPDATE_LINEAGE_COVERAGE") == "1":
        _write_baseline(coverage)
    novas = sorted(coverage.uncovered_roots - set(_read_baseline()["monetary_roots"]))
    assert not novas, (
        f"raiz(es) monetária(s) sem entrada no lineage_registry: {novas}. "
        "Declare o nó em `LINEAGE_RULE_REFS` + emissor em `e5_lineage.py`, "
        "ou justifique na lane por que a raiz publica dinheiro sem proveniência."
    )


def test_baseline_de_cobertura_esta_sincronizado(dogfood_e5):
    """Sincronia exata: cobertura que SOBE também exige rebaseline (o KR é um número)."""
    coverage = measure_coverage(dogfood_e5)
    baseline = _read_baseline()
    assert sorted(coverage.monetary_roots) == baseline["monetary_roots"], (
        "conjunto de raízes monetárias mudou — não é a contagem que vale, é o conjunto. "
        f"medido={sorted(coverage.monetary_roots)}"
    )
    assert sorted(coverage.covered_roots) == baseline["covered_roots"], (
        "conjunto de raízes com rastro mudou. Se SUBIU, rebaseline e atualize o KR na "
        f"lane A27.l2; se CAIU, é regressão. medido={sorted(coverage.covered_roots)}"
    )


# ──────────────────────────── controle positivo ────────────────────────────


def test_raiz_monetaria_nova_derruba_a_metrica(dogfood_e5):
    """Contrafactual: acrescentar raiz monetária sem registro **baixa** a cobertura."""
    antes = measure_coverage(dogfood_e5)
    depois = measure_coverage(_com_raiz_monetaria_nova(dogfood_e5))
    assert depois.ratio < antes.ratio, (
        f"métrica inerte à raiz nova: {antes.ratio:.4f} → {depois.ratio:.4f}. "
        "É exatamente o defeito que esta lane fecha."
    )
    assert _RAIZ_SINTETICA in depois.uncovered_roots
    assert depois.covered_roots == antes.covered_roots, "numerador não devia se mover"


def test_o_gate_reprova_a_raiz_nova(dogfood_e5):
    """A mesma mutação atravessa o assert do gate — não só a métrica interna."""
    mutated = measure_coverage(_com_raiz_monetaria_nova(dogfood_e5))
    novas = mutated.uncovered_roots - set(_read_baseline()["monetary_roots"])
    assert novas == {_RAIZ_SINTETICA}, f"gate cego à raiz nova (viu {sorted(novas)})"
