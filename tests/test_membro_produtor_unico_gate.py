"""Gates do produtor único de membro, no PAYLOAD ([[ADR-410]] §Gate · [[A40.l77]] PR3).

Segunda testemunha dos unit tests: aqui o predicado roda sobre o E5 que o
pipeline realmente publica, não sobre o retorno do resolver.

**A fixture sozinha não basta.** Sem `papel: conjuge` no `family_members`, a
identidade sai com `conjuge_key=""`, todo item cai no titular e o caso não
existe — medido em 2026-08-24: `total_financeiro` 900.000 em vez de 1.010.000, e
as instituições dela atribuídas a ele. O gate declara a família junto da
fixture por isso.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import load_fixture, run_e3_e4_e5, write_e5_config

_FIX = Path(__file__).resolve().parent / "fixtures" / "pipeline_golden"
_E3 = _FIX / "e3" / "minimal-conta-3_reconciled.json"
_BASELINE = _FIX / "e2" / "dois-membros-anos-disjuntos-1.5_consolidated.json"

#: Identidade com cônjuge — sem ela o baseline de dois membros vira um.
_FAMILIA_COM_CONJUGE = {
    "titular": "david",
    "membros": {
        "david": {"nome_curto": "David", "data_nascimento": "1985-06-15"},
        "mariana": {"nome_curto": "Mariana", "papel": "conjuge", "data_nascimento": "1987-03-10"},
    },
}
_STATUS_COM_MEDICAO = frozenset({"apurado", "zero_apurado"})


def _cents(value) -> int:
    return int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@pytest.fixture(scope="module")
def payload(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("gate_produtor_unico")
    write_e5_config(tmp_path, family=_FAMILIA_COM_CONJUGE)
    return run_e3_e4_e5(
        tmp_path,
        e3_payloads={"minimal-conta": load_fixture(_E3)},
        baseline=load_fixture(_BASELINE),
    )


# =============================================================================
# Denominador — o gate não pode passar por vazio
# =============================================================================


def test_o_caso_de_dois_membros_existe_no_payload(payload: dict):
    """Sem este assert os três gates abaixo passam sobre lista vazia."""
    cobertura = payload["patrimonio"]["cobertura_investimentos"]
    instituicoes = payload["investimentos"]["instituicoes_por_membro"]

    assert {c["membro"] for c in cobertura} == {"titular", "conjuge"}
    assert len(instituicoes) == 2, "a identidade colapsou os dois membros em um"


# =============================================================================
# Conservação — o D1 unifica o produtor do ITEM, não o da AGREGAÇÃO
# =============================================================================


def test_o_total_financeiro_soma_os_dois_baldes_de_membro(payload: dict):
    pat, inv = payload["patrimonio"], payload["investimentos"]
    soma = _cents(pat["investimentos_titular"]) + _cents(pat["investimentos_conjuge"])
    assert _cents(inv["total_financeiro"]) == soma


def test_a_tabela_de_classes_fecha_com_o_total(payload: dict):
    inv = payload["investimentos"]
    soma_classes = sum(_cents(c["valor"]) for c in inv["tabela_classes"])
    assert soma_classes == _cents(inv["total"])


def test_nenhum_membro_some_do_total(payload: dict):
    """O defeito original: o cônjuge valia 0,00 dentro de `total_financeiro`."""
    assert _cents(payload["patrimonio"]["investimentos_conjuge"]) > 0


# =============================================================================
# Contradição — posição contada exige veredito que admita medição
# =============================================================================


def test_membro_com_posicao_tem_status_que_admite_medicao(payload: dict):
    """`n_posicoes>0` com status fora de {apurado, zero_apurado} é a assinatura do RV6-04.

    Resolve o §Critério 2 da lane sem inventar um campo `valor` em
    `MembroInstituicoes` — seria um quarto lugar afirmando dinheiro de membro.
    """
    por_papel = {c["membro"]: c for c in payload["patrimonio"]["cobertura_investimentos"]}
    nome_para_papel = {"David": "titular", "Mariana": "conjuge"}

    avaliados = 0
    for linha in payload["investimentos"]["instituicoes_por_membro"]:
        papel = nome_para_papel.get(linha["membro"])
        if papel is None or linha["n_posicoes"] <= 0:
            continue
        avaliados += 1
        assert por_papel[papel]["status"] in _STATUS_COM_MEDICAO, (
            f"{linha['membro']}: {linha['n_posicoes']} posições com status "
            f"{por_papel[papel]['status']!r}"
        )
    assert avaliados == 2, "denominador vazio — o predicado não olhou ninguém"


def test_frescor_carrega_o_ano_de_cada_membro(payload: dict):
    """Primeira vez que `frescor` fica não-nulo E não-uniforme entre membros (DE-9)."""
    por_papel = {c["membro"]: c for c in payload["patrimonio"]["cobertura_investimentos"]}
    assert por_papel["titular"]["frescor"] == "2025"
    assert por_papel["conjuge"]["frescor"] == "2023"
