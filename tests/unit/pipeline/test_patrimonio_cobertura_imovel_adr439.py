"""O calculator publica o veredito dos baldes de imóvel ([[ADR-439]] D1/D2/D5).

A forma do run `U5`: a residência resolveu identidade; os imóveis gravados como renda
não. Valores sintéticos — nenhum vem do dogfood.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import jsonschema
import pytest

from pipeline.domain.services.carteira_por_papel import build_carteira_por_papel
from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_composicao import ROTULO_RESIDENCIA, build_composicao
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
)

_IDENT = MemberIdentity(
    titular_key="alex", conjuge_key="bia", titular_nome="Alex", conjuge_nome="Bia"
)
_SCHEMA = Path(__file__).resolve().parents[3] / "config" / "schemas" / "e5_analysis.schema.json"
_OVERRIDES_U5 = {
    "pid-casa": "residencia_principal",
    "pid-sala": "locado",
    "pid-loja": "comercial",
}


def _cents(valor) -> int:
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _calcular(imoveis: list[dict], *, overrides=None, status=None) -> dict:
    baseline = {
        "members": {
            "alex": {"total_bens": sum(i["valor"] for i in imoveis), "bens": {"imoveis": imoveis}},
            "bia": {"total_bens": 0, "bens": {}},
        }
    }
    config = PatrimonioConfig(
        members=_IDENT,
        property_classification_overrides=overrides or {},
        residencia_status=status,
    )
    inputs = PatrimonioInputs(
        baseline=baseline,
        members=resolve_members(baseline, _IDENT),
        carteira=build_carteira_por_papel(None, titular_key="alex", conjuge_key="bia"),
    )
    return PatrimonioCalculator(config).calculate(inputs)


_CASA = {"descricao": "Casa", "valor": 500_000.0, "property_id": "pid-casa"}
_SEM_ID = [{"descricao": "Sala", "valor": 120_000.0}, {"descricao": "Loja", "valor": 230_000.0}]


def test_forma_do_u5_publica_o_veredito_ao_lado_dos_baldes() -> None:
    p = _calcular([_CASA, *_SEM_ID], overrides=_OVERRIDES_U5, status="owned")
    bloco = p["cobertura_classificacao_imovel"]

    assert p["residencia"] == 500_000.0
    assert bloco["residencia"] == {"status": "apurado", "motivo": None, "piso": True}
    assert bloco["imoveis_geradores"]["status"] == "nao_apurado"
    assert bloco["imoveis_geradores"]["motivo"] == "vinculo_perdido"
    assert bloco["overrides_sem_imovel"] == {"residencia_principal": 0, "geradores": 2}
    assert bloco["n_desconhecido_em_aberto"] == 2
    assert bloco["residencia_status"] == "owned"


def test_a_particao_do_bloco_fecha_com_os_baldes_ao_centavo() -> None:
    """Mesmo laço: a soma do bloco é o estoque, e a fatia de cat_2 é `imoveis_investimento`."""
    p = _calcular([_CASA, *_SEM_ID], overrides=_OVERRIDES_U5, status="owned")
    b = p["cobertura_classificacao_imovel"]
    cat2 = b["geradores_identificados"] + b["nao_geradores_identificados"] + b["valor_desconhecido"]

    assert _cents(b["residencia_identificada"] + cat2) == _cents(b["valor_total"])
    assert _cents(cat2) == _cents(p["imoveis_investimento"])
    assert _cents(b["residencia_identificada"]) == _cents(p["residencia"])


def test_residencia_nao_apurada_marca_a_linha_e_a_soma_da_composicao_fica() -> None:
    p = _calcular(_SEM_ID)  # status ausente ≡ `undeclared` ([[ADR-215]])
    linha = next(c for c in p["composicao"] if c["categoria"] == ROTULO_RESIDENCIA)

    assert p["cobertura_classificacao_imovel"]["residencia"]["motivo"] == "nao_declarada"
    assert linha["valor"] == 0.0
    assert linha["estado"] == "nao_apurado"
    assert linha["motivo"] == "nao_declarada"
    assert _cents(sum(c["valor"] for c in p["composicao"])) == _cents(p["bruto"])


def test_quem_aluga_tem_zero_declarado_e_a_linha_segue_sem_estado() -> None:
    p = _calcular(_SEM_ID, status="rented")
    linha = next(c for c in p["composicao"] if c["categoria"] == ROTULO_RESIDENCIA)

    assert p["cobertura_classificacao_imovel"]["residencia"]["status"] == "zero_apurado"
    assert "estado" not in linha


def test_rotulo_da_residencia_e_o_da_linha_literal_da_composicao() -> None:
    """`ROTULO_RESIDENCIA` marca a linha; divergir da literal desligaria a marcação calada."""
    composicao = build_composicao(
        identity=_IDENT,
        residencia=1.0,
        imoveis_investimento=0.0,
        investimentos_titular=0.0,
        investimentos_conjuge=0.0,
        caixa=0.0,
        veiculos=0.0,
    )

    assert ROTULO_RESIDENCIA in {c["categoria"] for c in composicao}


@pytest.fixture(scope="module")
def schema_do_patrimonio() -> dict:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return {**schema["properties"]["patrimonio"], "$defs": schema["$defs"]}


@pytest.mark.parametrize("flip", [False, True], ids=["expand", "flip"])
def test_o_patrimonio_publicado_valida_no_contrato_e5(schema_do_patrimonio, flip) -> None:
    """O bloco é fechado, e os três baldes aceitam `null` antes de o produtor emiti-lo."""
    p = _calcular([_CASA, *_SEM_ID], overrides=_OVERRIDES_U5, status="owned")
    if flip:
        p.update(residencia=None, imoveis_geradores=None, imoveis_nao_geradores=None)

    jsonschema.validate(p, schema_do_patrimonio)
