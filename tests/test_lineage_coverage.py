"""Gate de cobertura do grafo de lineage (ADR-281 · A27.l2 · A27.l3).

Fecha o vício que ``dev/check_lineage_refs.py`` não alcança: aquele gate é **existência
pura** (o ``rule_ref`` importa, a ADR existe) e não tem noção de cobertura — raiz nova no
E5 sem entrada no ``lineage_registry`` não movia gate nem accuracy. Aqui o denominador vem
de **payload medido** (raízes que emitem dinheiro), então raiz nova sem rastro **derruba a
métrica** e reprova.

A assimetria com `check_lineage_refs` é **estrutural, não testável**: aquele gate recebe o
registry, nunca o payload, então não existe mutação de payload que ele possa ver. Afirmar
isso como teste seria asseverar mais do que o corpo checa; o verde dele sobre o registry
real já é coberto por `test_lineage_skeleton.py::test_check_lineage_refs_green_on_real_registry`.

**A27.l3 — o sujeito da medição.** A A27.l2 derivava o universo do payload da **fixture**
e publicava aquilo como *a* cobertura. A fixture é subconjunto **estrito** da produção (não
tem IRPF, imóvel locado nem PJ), então três raízes monetárias ficavam fora do denominador e
o número saía **otimista**. O universo agora é o **roster** de origens observadas, e
`test_o_denominador_publicado_nao_e_o_da_fixture` é o contrafactual que discrimina os dois
desenhos: ele **reprova** no desenho anterior, onde as duas medidas eram iguais por
construção.

Rebaseline da fixture: ``MATHOMS_UPDATE_LINEAGE_COVERAGE=1 pytest tests/test_lineage_coverage.py``.
Observação de produção: ``python3 dev/lineage_coverage.py <payload.json> --origem producao:<run8> --update``.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from dev.lineage_coverage import ORIGEM_FIXTURE, ROSTER_PATH, Roster, measure_coverage
from tests.pipeline_golden_substrate import (
    load_fixture,
    run_dogfood_pipeline,
    write_e5_config,
)

_REPO = Path(__file__).resolve().parents[1]
_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"

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


@pytest.fixture(scope="module")
def roster(dogfood_e5) -> Roster:
    if os.environ.get("MATHOMS_UPDATE_LINEAGE_COVERAGE") == "1":
        Roster.load().observing(ORIGEM_FIXTURE, measure_coverage(dogfood_e5)).dump()
    return Roster.load()


def _com_raiz_monetaria_nova(payload: dict) -> dict:
    mutated = copy.deepcopy(payload)
    mutated[_RAIZ_SINTETICA] = {"total_brl": 1234.56}
    return mutated


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


def test_nenhuma_raiz_monetaria_fora_do_roster(dogfood_e5, roster):
    """O gate: raiz monetária medida que o roster não conhece reprova."""
    fora = sorted(roster.outside(measure_coverage(dogfood_e5).monetary_roots))
    assert not fora, (
        f"raiz(es) monetária(s) fora do universo publicado: {fora}. "
        "Declare o nó em `LINEAGE_RULE_REFS` + emissor em `e5_lineage.py`, ou incorpore a "
        "observação ao roster (o número publicado CAI, e é para cair)."
    )


def test_o_roster_da_fixture_bate_com_a_medida(dogfood_e5, roster):
    """Sincronia exata da metade que o CI mede — conjunto, não contagem."""
    coverage = measure_coverage(dogfood_e5)
    assert sorted(roster.roots_de(ORIGEM_FIXTURE)) == sorted(coverage.monetary_roots), (
        f"raízes monetárias da fixture divergem do roster. medido={sorted(coverage.monetary_roots)}"
    )
    assert sorted(roster.cobertos_de(ORIGEM_FIXTURE)) == sorted(coverage.covered_roots), (
        "raízes com rastro na fixture divergem do roster. Se SUBIU, rebaseline e atualize o "
        f"KR; se CAIU, é regressão. medido={sorted(coverage.covered_roots)}"
    )


def test_o_numero_publicado_declara_denominador_e_origem(roster):
    """Critério 3 da A27.l3: o número publicado carrega o denominador e de onde ele veio."""
    publicado = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["cobertura_publicada"]
    assert publicado["denominador"] == roster.denominador
    assert publicado["numerador"] == roster.numerador
    assert publicado["ratio_pct"] == pytest.approx(round(roster.ratio * 100, 1))
    assert publicado["origens"] == list(roster.origens)
    assert len(roster.origens) >= 2, (
        "roster de origem única — é exatamente o defeito da A27.l3: o universo volta a ser "
        f"'o que uma fonte emite'. origens={roster.origens}"
    )


# ──────────────────────────── controle positivo ────────────────────────────


def test_raiz_monetaria_nova_cai_fora_do_roster(dogfood_e5, roster):
    """Contrafactual: acrescentar raiz monetária sem rastro **baixa** a cobertura e reprova."""
    antes = measure_coverage(dogfood_e5)
    depois = measure_coverage(_com_raiz_monetaria_nova(dogfood_e5))
    assert depois.ratio < antes.ratio, (
        f"métrica inerte à raiz nova: {antes.ratio:.4f} → {depois.ratio:.4f}."
    )
    assert roster.outside(depois.monetary_roots) == {_RAIZ_SINTETICA}, (
        f"gate cego à raiz nova (viu {sorted(roster.outside(depois.monetary_roots))})"
    )
    assert depois.covered_roots == antes.covered_roots, "numerador não devia se mover"


def test_o_denominador_publicado_nao_e_o_da_fixture(dogfood_e5, roster):
    """A prova de não-inércia desta lane — o desenho anterior reprova aqui: na A27.l2 o
    universo era o da fixture por construção, as duas medidas eram a mesma e o viés não tinha
    como aparecer. Aqui o roster é maior, e a medida só-fixture é mais alta: o viés, com sinal."""
    so_fixture = measure_coverage(dogfood_e5)
    fora_da_fixture = roster.roots - so_fixture.monetary_roots
    assert fora_da_fixture, (
        "o roster não conhece nenhuma raiz além das da fixture — o universo voltou a ser "
        "single-origin e o número publicado é o da fixture de novo"
    )
    assert so_fixture.ratio > roster.ratio, (
        f"viés sem sinal: fixture={so_fixture.ratio:.4f} vs publicado={roster.ratio:.4f}. "
        f"raízes fora da fixture: {sorted(fora_da_fixture)}"
    )
