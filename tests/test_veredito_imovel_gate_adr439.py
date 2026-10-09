"""Gate da [[ADR-439]] D7: zero publicado só com evidência de zero, em toda a matriz de regimes.

O oráculo NÃO chama o veredito: ele relê o estado de DB da fixture (overrides + status) e
os itens do run. Se o produtor e o gate compartilhassem a função, a mutação do produtor
mudaria os dois lados e o gate seria tautológico.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from pipeline.domain.services import veredito_balde_imovel
from pipeline.domain.services.carteira_por_papel import build_carteira_por_papel
from pipeline.domain.services.investimentos_cobertura import CoberturaStatus
from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
)

_IDENT = MemberIdentity(
    titular_key="alex", conjuge_key="bia", titular_nome="Alex", conjuge_nome="Bia"
)
_GERADORAS = {"locado", "comercial"}


@dataclass(frozen=True)
class Regime:
    nome: str
    imoveis: list[dict]
    overrides: dict[str, str] = field(default_factory=dict)
    status: str | None = None


_CASA = {"descricao": "Casa", "valor": 500_000.0, "property_id": "pid-casa"}
_SALA = {"descricao": "Sala", "valor": 120_000.0, "property_id": "pid-sala"}
_SEM_ID = {"descricao": "Loja", "valor": 230_000.0}

REGIMES = [
    Regime(
        "u5_vinculo_perdido",
        [_CASA, _SEM_ID],
        {"pid-casa": "residencia_principal", "pid-x": "locado"},
        "owned",
    ),
    Regime("nada_classificado", [_SEM_ID], {}, None),
    Regime("aluga", [_SEM_ID], {}, "rented"),
    Regime(
        "vendeu_o_imovel_de_renda",
        [_CASA],
        {"pid-casa": "residencia_principal", "pid-x": "locado"},
        "owned",
    ),
    Regime(
        "tudo_classificado",
        [_CASA, _SALA],
        {"pid-casa": "residencia_principal", "pid-sala": "locado"},
        "owned",
    ),
    Regime(
        "residencia_orfa",
        [_SALA, _SEM_ID],
        {"pid-casa": "residencia_principal", "pid-sala": "locado"},
        "owned",
    ),
    Regime("sem_imovel", [], {}, "undeclared"),
]


def _publicar(r: Regime) -> dict:
    baseline = {
        "members": {
            "alex": {
                "total_bens": sum(i["valor"] for i in r.imoveis),
                "bens": {"imoveis": r.imoveis},
            },
            "bia": {"total_bens": 0, "bens": {}},
        }
    }
    config = PatrimonioConfig(
        members=_IDENT, property_classification_overrides=r.overrides, residencia_status=r.status
    )
    inputs = PatrimonioInputs(
        baseline=baseline,
        members=resolve_members(baseline, _IDENT),
        carteira=build_carteira_por_papel(None, titular_key="alex", conjuge_key="bia"),
    )
    return PatrimonioCalculator(config).calculate(inputs)


# ── oráculo: estado de DB da fixture, nunca o veredito ──────────────────────────
def _classe(r: Regime, imovel: dict) -> str | None:
    pid = imovel.get("property_id")
    return r.overrides.get(pid) if pid else None


def _em_aberto(r: Regime) -> bool:
    return any(_classe(r, im) is None and im["valor"] > 0 for im in r.imoveis)


def violacoes(r: Regime, p: dict) -> list[str]:
    """Zero numérico sem evidência de zero — o defeito da [[A40.l113]]."""
    achados = []
    if p["residencia"] == 0 and r.status != "rented":
        achados.append(f"{r.nome}: residência 0 sem `rented`")
    if p["imoveis_geradores"] is not None and _em_aberto(r):
        achados.append(f"{r.nome}: geradores numérico com imóvel em aberto")
    if (p["imoveis_geradores"] is None) != (p["imoveis_nao_geradores"] is None):
        achados.append(f"{r.nome}: par de geradores misto")
    return achados


@pytest.mark.parametrize("regime", REGIMES, ids=lambda r: r.nome)
def test_zero_publicado_so_com_evidencia_de_zero(regime: Regime) -> None:
    assert violacoes(regime, _publicar(regime)) == []


def test_o_imovel_de_renda_vendido_publica_zero_e_nao_reprova() -> None:
    """O falso-positivo que derrubou o gate literal: override órfão + tudo identificado."""
    p = _publicar(next(r for r in REGIMES if r.nome == "vendeu_o_imovel_de_renda"))
    assert p["imoveis_geradores"] == 0.0


# Não-inércia: com o veredito trocado por "sempre apurado", o gate tem de morder.
def test_mutacao_do_produtor_deixa_o_gate_vermelho(monkeypatch) -> None:
    sempre = veredito_balde_imovel.VereditoBalde(CoberturaStatus.apurado)
    monkeypatch.setattr(veredito_balde_imovel, "veredito_residencia", lambda *a, **k: sempre)
    monkeypatch.setattr(veredito_balde_imovel, "veredito_geradores", lambda *a, **k: sempre)

    todas = [v for r in REGIMES for v in violacoes(r, _publicar(r))]
    assert todas, "o gate não mordeu a mutação — seria inerte"
