"""Gate A40.l110 — fixture de baseline não declara chave que produtor nenhum emite.

Os 2 fósseis (`pipeline_stage`, `data_processamento`) sobreviveram porque
produtor e teste concordavam na crença errada: o `BaselineNormalizer` os
sintetizava e as 6 fixtures os hardcodavam no topo. Nenhum dos dois produtores
reais do contrato os emite — `consolidate_baseline` na chave
`baseline_patrimonial`, e o E4 na chave `patrimonio` ([[ADR-427]] D3).

O conjunto proibido é **derivado do produtor**, não escrito à mão: roda-se
`consolidate` sobre um input real e mede-se o que ele emite. Fixture que
declara chave fora desse conjunto reprova — que é o controle negativo da lane:
reinserir `pipeline_stage` em qualquer fixture faz este teste falhar.

Segunda instância, na mesma sprint, do que a [[ADR-427]] §Consequências pegou
em `minimal-receitas-4_unified.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))

_FIXTURES = sorted((_RAIZ / "tests/fixtures/pipeline_golden/e2").glob("*1.5_consolidated.json"))
_EXTRACT_DOGFOOD = _RAIZ / "tests/fixtures/pipeline_golden/dogfood/baseline-1.5.json"

# Fósseis mortos em A40.l110. A lista não é o critério — é o registro do que já
# reprovou uma vez. O critério é a medição do produtor em
# `test_produtor_nao_emite_os_fosseis`, que falha primeiro se a premissa mudar.
_FOSSEIS = ("pipeline_stage", "data_processamento")


def _emitido_pelo_produtor() -> set[str]:
    """Chaves que `consolidate_baseline` **acrescenta** — medidas, não presumidas.

    `consolidate` copia as chaves do input para o output, então medir com o
    fóssil presente na entrada só provaria a passagem. A entrada é limpa antes,
    para que o resultado responda o que o produtor emite por conta própria.
    """
    from scripts.consolidate_baseline import consolidate

    entrada = json.loads(_EXTRACT_DOGFOOD.read_text(encoding="utf-8"))
    for fossil in _FOSSEIS:
        entrada.pop(fossil, None)
    return set(consolidate(entrada))


def test_produtor_nao_emite_os_fosseis():
    """A premissa do gate abaixo, medida no produtor real."""
    emitido = _emitido_pelo_produtor()
    assert emitido, "o produtor devolveu payload vazio — o gate abaixo seria vácuo"
    assert not (set(_FOSSEIS) & emitido), (
        f"`consolidate_baseline` voltou a emitir {sorted(set(_FOSSEIS) & emitido)} — "
        "se isso é intencional, o contrato mudou e o schema precisa declará-los de novo."
    )


def test_a_medicao_do_produtor_discrimina():
    """Não-inércia: com o fóssil na entrada, `consolidate` o repassa.

    Sem esta linha, `test_produtor_nao_emite_os_fosseis` passaria mesmo se o
    produtor tivesse voltado a emitir os campos — bastaria a entrada não os ter.
    Aqui se prova que o instrumento enxerga a presença quando ela existe.
    """
    from scripts.consolidate_baseline import consolidate

    entrada = json.loads(_EXTRACT_DOGFOOD.read_text(encoding="utf-8"))
    entrada["pipeline_stage"] = "carimbo-sintetico"
    assert "pipeline_stage" in set(consolidate(entrada))


@pytest.mark.parametrize("fixture", _FIXTURES + [_EXTRACT_DOGFOOD], ids=lambda p: p.name)
def test_fixture_nao_hardcoda_fossil(fixture: Path):
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    presentes = [k for k in _FOSSEIS if k in payload]
    assert presentes == [], (
        f"{fixture.name} declara {presentes}, que produtor nenhum emite. "
        "Fixture que finge um campo faz o teste concordar com a crença errada (A40.l110)."
    )


def test_o_corpus_de_fixtures_nao_esta_vazio():
    """Sem esta linha, um rename de pasta faria o parametrize acima passar vácuo."""
    assert len(_FIXTURES) >= 5
    assert _EXTRACT_DOGFOOD.exists()
