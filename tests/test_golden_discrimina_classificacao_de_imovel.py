"""A fixture do dogfood discrimina o destino de cat_2 ([[ADR-420]] §Critério de aceite 2)."""

# Até 2026-08-31 **nenhuma** fixture end-to-end do repo tinha `imoveis_geradores > 0`:
# o golden do dogfood punha 100% de cat_2 em não-geradores, então as duas leituras da
# concentração imobiliária eram extremos degenerados ali e verde depois de um conserto
# provaria só que geradores é zero. A fixture era o gate, e estava cega.
#
# O split que a corrigiu CONSERVA o bruto — cinco imóveis com destino declarado somando
# os mesmos R$600.000 do imóvel opaco que substituíram —, então o que se move é o eixo
# de classificação e nada mais. O apartamento fica DE PROPÓSITO sem override: o regime
# default (imóvel sem classificação nenhuma) é classe de defeito distinta, viva no
# §Follow-up da [[A40.l95]].

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import (
    CLASSIFICACOES_DO_DOGFOOD,
    load_fixture,
    run_dogfood_pipeline,
    write_e5_config,
)

_REPO = Path(__file__).resolve().parents[1]
_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"
_FAMILY = {
    "titular": "alex",
    "membros": {
        "alex": {"nome_curto": "Alex", "data_nascimento": "1985-03-10"},
        "bia": {"nome_curto": "Bia", "data_nascimento": "1987-07-22"},
    },
}


def _cents(valor) -> int:
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _extratos() -> dict[str, dict]:
    return {
        "extrato-a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
        "extrato-b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
    }


def _rodar(root: Path, classificacoes: dict[str, str] | None) -> dict:
    write_e5_config(root, family=_FAMILY)
    return run_dogfood_pipeline(
        root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts=_extratos(),
        property_classifications=classificacoes,
    )


@pytest.fixture(scope="module")
def com_classificacao(tmp_path_factory) -> dict:
    return _rodar(tmp_path_factory.mktemp("com"), None)["patrimonio"]


# O contrafactual roda o MESMO baseline sem override nenhum: é ele que separa
# "a fixture declara classificação" de "o motor lê a classificação declarada".
@pytest.fixture(scope="module")
def sem_classificacao(tmp_path_factory) -> dict:
    return _rodar(tmp_path_factory.mktemp("sem"), {})["patrimonio"]


def _imoveis_da_fixture() -> list[dict]:
    baseline = load_fixture(_DOGFOOD / "baseline-1.5.json")
    return [i for i in baseline["itens"] if i.get("categoria") == "imovel"]


def test_a_fixture_declara_locado_E_especulacao() -> None:
    """Os dois que a [[ADR-420]] §D1 nomeia — sem eles o corte não é observável."""
    declaradas = set(CLASSIFICACOES_DO_DOGFOOD.values())

    assert {"locado", "especulacao"} <= declaradas, f"faltam destinos: {declaradas}"
    assert {
        "nu_proprietario",
        "uso_pessoal",
    } <= declaradas, "sem um membro de fora-da-alocação o corte de §D1 não move nada na fixture"


def test_um_imovel_fica_sem_override(com_classificacao: dict) -> None:
    """Regime default preservado: é classe de defeito distinta, não a desta lane."""
    assert len(_imoveis_da_fixture()) == len(CLASSIFICACOES_DO_DOGFOOD) + 1


# Sem isto o teste de conservação abaixo é cego a troca de destino: dois imóveis de
# mesmo valor podem trocar de lado e as somas não se mexem.
def test_os_valores_sao_dois_a_dois_distintos() -> None:
    """Valor repetido torna invisível o imóvel que foi para o balde errado."""
    valores = [i["valor_brl"] for i in _imoveis_da_fixture()]

    assert len(set(valores)) == len(valores), f"valores repetidos na fixture: {valores}"
    assert all(v > 0 for v in valores), f"valor nulo na fixture: {valores}"


def test_cat2_conserva_ao_cent(com_classificacao: dict) -> None:
    """Tolerância zero: identidade algébrica no mesmo payload, não paridade."""
    assert _cents(com_classificacao["imoveis_geradores"]) + _cents(
        com_classificacao["imoveis_nao_geradores"]
    ) == _cents(com_classificacao["imoveis_investimento"])


# A prova de não-inércia. Sem ela, "a fixture declara classificação" e "o motor a lê"
# são indistinguíveis — e era exatamente essa a cegueira do golden anterior.
def test_a_classificacao_declarada_e_LOAD_BEARING(
    com_classificacao: dict, sem_classificacao: dict
) -> None:
    """Sem override, cat_2 inteiro colapsa em não-gerador — o extremo degenerado."""
    assert _cents(sem_classificacao["imoveis_geradores"]) == 0
    assert _cents(sem_classificacao["imoveis_nao_geradores"]) == _cents(
        sem_classificacao["imoveis_investimento"]
    )

    assert _cents(com_classificacao["imoveis_geradores"]) > 0
    assert _cents(com_classificacao["cat2_efetivo"]) > 0


def test_o_split_da_fixture_NAO_move_dinheiro(
    com_classificacao: dict, sem_classificacao: dict
) -> None:
    """O eixo que se move é o de classificação; bruto, líquido e cat_2 ficam parados."""
    for campo in ("bruto", "liquido", "imoveis_investimento", "residencia"):
        assert _cents(com_classificacao[campo]) == _cents(sem_classificacao[campo]), campo
