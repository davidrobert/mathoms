"""Gate de produtor único de membro ([[ADR-410]] §Gate).

Substitui a comparação entre superfícies que a [[A40.l77]] pedia: com um produtor,
duas superfícies não podem discordar do **item** — mas sobrevivem dois caminhos de
**agregação**, e é conservação que os prende.

A fixture de dois membros em anos disjuntos é precondição: a golden solo/mono-ano
não consegue exibir o caso, e foi por isso que 98 testes verdes não viram o defeito
nem o fix do #1578.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.domain.services.instituicoes_por_membro_analyzer import (
    InstituicoesPorMembroAnalyzer,
)
from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesAnalyzer,
)
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import MemberIdentity

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests/fixtures/pipeline_golden/e2/dois-membros-anos-disjuntos-1.5_consolidated.json"
)
_IDENTITY = MemberIdentity(
    titular_key="david", conjuge_key="mariana", titular_nome="David", conjuge_nome="Mariana"
)
_TITULAR_BRL = 900_000.0
_CONJUGE_BRL = 110_000.0


@pytest.fixture
def baseline() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _bens(data: dict) -> dict:
    return data.get("bens") or data


def test_cada_membro_e_valorado_no_ano_que_ele_declarou(baseline: dict):
    """O defeito original: o ano do domicílio zerava quem não declarou nele."""
    titular, conjuge = resolve_members(baseline, _IDENTITY).as_tuple()
    assert titular["bens"]["investimentos"][0]["valor_31_12_ano_base"] == _TITULAR_BRL
    assert conjuge["bens"]["investimentos"][0]["valor_31_12_ano_base"] == _CONJUGE_BRL


def test_conservacao_o_total_soma_os_dois_membros(baseline: dict):
    """`Σ tabela_classes == total` — identidade no mesmo payload, cents exatos."""
    titular, conjuge = resolve_members(baseline, _IDENTITY).as_tuple()
    r = InvestimentosClassesAnalyzer().analyze([_bens(titular), _bens(conjuge)])

    assert round(r.total * 100) == round((_TITULAR_BRL + _CONJUGE_BRL) * 100)
    assert round(sum(c.valor for c in r.tabela_classes) * 100) == round(r.total * 100)


def test_nenhum_membro_publica_posicao_com_valor_zero(baseline: dict):
    """A assinatura do RV6-04: `n_posicoes>0` somando 0,00 no balde do membro."""
    titular, conjuge = resolve_members(baseline, _IDENTITY).as_tuple()
    inst = InstituicoesPorMembroAnalyzer().analyze(
        [("David", _bens(titular)), ("Mariana", _bens(conjuge))]
    )
    for linha in inst.por_membro:
        bens = _bens(titular) if linha.membro == "David" else _bens(conjuge)
        soma = sum(i.get("valor_31_12_ano_base", 0) for i in bens["investimentos"])
        assert not (
            linha.n_posicoes > 0 and soma == 0
        ), f"{linha.membro}: {linha.n_posicoes} posições somando 0,00"


def test_instituicao_sobrevive_ao_produtor_unico(baseline: dict):
    """Se o canônico não propagar `instituicao`, toda posição vira lacuna falsa ([[ADR-406]])."""
    titular, conjuge = resolve_members(baseline, _IDENTITY).as_tuple()
    inst = InstituicoesPorMembroAnalyzer().analyze(
        [("David", _bens(titular)), ("Mariana", _bens(conjuge))]
    )
    por_membro = {linha.membro: linha for linha in inst.por_membro}
    assert len(por_membro["Mariana"].instituicoes) == 1  # o analyzer normaliza a caixa
    assert por_membro["Mariana"].posicoes_sem_identidade == ()
    assert por_membro["David"].posicoes_sem_identidade == ()


def test_tipo_sobrevive_e_a_classe_nao_cai_na_catch_all(baseline: dict):
    """Sem `tipo`, o classificador só tem a descrição livre ([[ADR-406]] §D2)."""
    titular, conjuge = resolve_members(baseline, _IDENTITY).as_tuple()
    r = InvestimentosClassesAnalyzer().analyze([_bens(titular), _bens(conjuge)])
    baldes = {c.categoria: c.valor for c in r.tabela_classes if c.valor}

    assert baldes.get("Renda Fixa") == _TITULAR_BRL
    assert baldes.get("FIIs") == _CONJUGE_BRL
    assert float(r.nao_classificado_brl) == 0.0
