"""Veredito dos baldes de imóvel ([[ADR-439]]): zero publicado só com evidência de zero.

A forma do run `U5`: a residência resolveu identidade, os quatro imóveis gravados como
`locado` não — e o relatório publicou que a família não tinha imóvel de renda.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.investimentos_cobertura import CoberturaStatus
from pipeline.domain.services.veredito_balde_imovel import (
    RESIDENCIA_ALUGADA,
    RESIDENCIA_NAO_DECLARADA,
    RESIDENCIA_PROPRIA,
    MotivoBaldeImovel,
    VereditoBalde,
    evidencia_de_imoveis,
    veredito_geradores,
    veredito_residencia,
    vereditos_de_imovel,
)

_CASA = {"property_id": "pid-casa", "valor": 500_000.0}
_SEM_ID_A = {"valor": 120_000.0}
_SEM_ID_B = {"valor": 230_000.0}
_OVERRIDES_U5 = {
    "pid-casa": "residencia_principal",
    "pid-sala": "locado",
    "pid-loja": "comercial",
}


def _vereditos(imoveis, overrides, *, status=RESIDENCIA_PROPRIA, residencia="0", geradores="0"):
    return vereditos_de_imovel(
        imoveis=imoveis,
        overrides=overrides,
        residencia_status=status,
        residencia=Decimal(residencia),
        geradores=Decimal(geradores),
    )


def test_forma_do_u5_residencia_e_numero_e_geradores_e_null() -> None:
    """Residência identificada sai número (piso); o gerador que perdeu o vínculo sai `null`."""
    v = _vereditos([_CASA, _SEM_ID_A, _SEM_ID_B], _OVERRIDES_U5, residencia="500000")

    assert v.residencia.status is CoberturaStatus.apurado
    assert v.residencia.piso is True
    assert v.geradores.status is CoberturaStatus.nao_apurado
    assert v.geradores.motivo is MotivoBaldeImovel.vinculo_perdido
    assert v.orfaos_geradores == 2
    assert v.geradores.publicavel is False


@pytest.mark.parametrize(
    ("status", "overrides", "imoveis", "motivo"),
    [
        (RESIDENCIA_PROPRIA, {"pid-casa": "residencia_principal"}, [_SEM_ID_A], "nao_localizada"),
        (RESIDENCIA_PROPRIA, {}, [_SEM_ID_A], "nao_classificada"),
        (RESIDENCIA_NAO_DECLARADA, {}, [_SEM_ID_A], "nao_declarada"),
        (None, {}, [], "nao_declarada"),
        (
            RESIDENCIA_PROPRIA,
            {"pid-casa": "residencia_principal"},
            [{"property_id": "pid-casa", "valor": 0.0}],
            "sem_valor",
        ),
        (
            RESIDENCIA_PROPRIA,
            {"pid-casa": "residencia_principal"},
            [{"property_id": "pid-casa", "valor_nao_apurado": {"anos": ["2025"]}}],
            "sem_valor",
        ),
    ],
)
def test_residencia_zero_sem_palavra_da_familia_e_null(status, overrides, imoveis, motivo) -> None:
    """Sem `rented`, zero de residência não é medida — é `null` com o motivo da ação."""
    ev = evidencia_de_imoveis(imoveis, overrides)
    v = veredito_residencia(Decimal("0"), ev, overrides, status)

    assert v.status is CoberturaStatus.nao_apurado
    assert v.motivo is MotivoBaldeImovel(motivo)
    assert v.publicavel is False


def test_residencia_alugada_publica_zero_mesmo_com_imovel_em_aberto() -> None:
    """A família disse que aluga: o zero é dela, não nosso."""
    ev = evidencia_de_imoveis([_SEM_ID_A], {})
    v = veredito_residencia(Decimal("0"), ev, {}, RESIDENCIA_ALUGADA)

    assert v.status is CoberturaStatus.zero_apurado
    assert v.publicavel is True


def test_residencia_identificada_sem_imovel_em_aberto_nao_e_piso() -> None:
    ev = evidencia_de_imoveis([_CASA], _OVERRIDES_U5)
    v = veredito_residencia(Decimal("500000"), ev, _OVERRIDES_U5, RESIDENCIA_PROPRIA)

    assert v.status is CoberturaStatus.apurado
    assert v.piso is False
    assert v.publicavel is True


# O falso-positivo que derrubou o gate literal da lane: trocar o imóvel de renda por FII
# deixa o `locado` órfão gravado, e o zero de geradores é verdadeiro.
def test_gerador_vendido_com_override_orfao_publica_zero() -> None:
    imoveis = [_CASA]
    overrides = {"pid-casa": "residencia_principal", "pid-vendido": "locado"}
    ev = evidencia_de_imoveis(imoveis, overrides)
    v = veredito_geradores(Decimal("0"), ev, overrides)

    assert v.status is CoberturaStatus.zero_apurado
    assert v.publicavel is True


def test_zero_declarado_e_venda_no_ano_e_nao_fica_em_aberto() -> None:
    ev = evidencia_de_imoveis([{"valor": 0.0}], {})
    assert ev.n_desconhecido_em_aberto == 0
    assert veredito_geradores(Decimal("0"), ev, {}).status is CoberturaStatus.zero_apurado


def test_desconhecido_sem_valor_apurado_fica_em_aberto() -> None:
    """Valor não apurado ([[ADR-431]]) não é zero: ninguém mediu."""
    ev = evidencia_de_imoveis([{"valor_nao_apurado": {"anos": ["2025"]}}], {})
    v = veredito_geradores(Decimal("0"), ev, {})

    assert ev.n_desconhecido_em_aberto == 1
    assert v.status is CoberturaStatus.nao_apurado
    assert v.motivo is MotivoBaldeImovel.nao_classificados


def test_gerador_identificado_com_imovel_em_aberto_e_piso() -> None:
    imoveis = [{"property_id": "pid-sala", "valor": 90_000.0}, _SEM_ID_A]
    ev = evidencia_de_imoveis(imoveis, _OVERRIDES_U5)
    v = veredito_geradores(Decimal("90000"), ev, _OVERRIDES_U5)

    assert v.status is CoberturaStatus.apurado
    assert v.piso is True


def test_gerador_presente_sem_valor_nao_publica_zero() -> None:
    imoveis = [{"property_id": "pid-sala", "valor_nao_apurado": {"anos": ["2025"]}}]
    ev = evidencia_de_imoveis(imoveis, _OVERRIDES_U5)
    v = veredito_geradores(Decimal("0"), ev, _OVERRIDES_U5)

    assert v.status is CoberturaStatus.nao_apurado
    assert v.motivo is MotivoBaldeImovel.sem_valor


def test_to_dict_publica_o_vocabulario_de_cobertura() -> None:
    v = _vereditos([_CASA, _SEM_ID_A], _OVERRIDES_U5, residencia="500000")
    payload = v.to_dict()

    assert payload["residencia"] == {"status": "apurado", "motivo": None, "piso": True}
    assert payload["imoveis_geradores"]["motivo"] == "vinculo_perdido"
    assert payload["overrides_sem_imovel"] == {"residencia_principal": 0, "geradores": 2}
    assert payload["n_desconhecido_em_aberto"] == 1
    assert VereditoBalde(CoberturaStatus.zero_apurado).to_dict()["motivo"] is None
