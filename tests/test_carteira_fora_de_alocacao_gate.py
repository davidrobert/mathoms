"""Gate da [[ADR-444]] D9: carteira de investimentos é o que o próximo aporte move.

Uso pessoal e nu-propriedade saem da tabela, do total e do ranking pela MESMA lista do
numerador da concentração ([[ADR-420]] §D1), e seguem no patrimônio. Caminho de produção
inteiro (`E5AnalyzerAdapter.analyze_via_store`); o oráculo relê os overrides da fixture,
nunca o roteador. Critério do `financial-planner`: em centavos, os imóveis da carteira somam
o `imoveis_alocacao` do patrimônio, e o patrimônio não depende do roteador.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.services import imovel_na_carteira
from pipeline.domain.services.e5_analyzer_adapter import E5AnalyzerAdapter
from tests.unit.pipeline.test_e5_analyzer_adapter import _seed_minimal

_FORA = {"uso_pessoal", "nu_proprietario"}

_CASA = {"descricao": "Casa", "valor_31_12_ano_base": 800_000.0, "property_id": "pid-casa"}
_PRAIA = {"descricao": "Praia", "valor_31_12_ano_base": 350_000.0, "property_id": "pid-praia"}
_NUA = {"descricao": "Apto", "valor_31_12_ano_base": 250_000.0, "property_id": "pid-nua"}
_TERRENO = {"descricao": "Terreno", "valor_31_12_ano_base": 150_000.0, "property_id": "pid-ter"}
_SALA = {"descricao": "Sala", "valor_31_12_ano_base": 300_000.0, "property_id": "pid-sala"}
_LOJA = {"descricao": "Loja", "valor_31_12_ano_base": 200_000.0}
_USOS = {
    "pid-praia": "uso_pessoal",
    "pid-nua": "nu_proprietario",
    "pid-ter": "especulacao",
    "pid-sala": "locado",
}

REGIMES = {
    # Residência identificada: o desconhecido fica na carteira por eliminação ([[ADR-444]] D6).
    "residencia_identificada": (
        [_CASA, _PRAIA, _NUA, _TERRENO, _SALA, _LOJA],
        {"pid-casa": "residencia_principal", **_USOS},
    ),
    # Residência não apurada: o desconhecido vai à linha sem peso ([[ADR-444]] D3).
    "residencia_nao_apurada": ([_PRAIA, _NUA, _TERRENO, _SALA, _LOJA], _USOS),
}


def _rodar(imoveis: list[dict], overrides: dict[str, str]):
    store = InMemoryArtifactStore()
    _seed_minimal(store)
    store.seed("E4", "patrimonio", {"members": {"david": {"bens": {"imoveis": imoveis}}}})
    adapter = E5AnalyzerAdapter.from_configs(
        property_classification_overrides=overrides, residencia_status="owned"
    )
    return adapter.analyze_via_store(store)


def _cents(valor) -> int:
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1")))


def _valor_declarado_fora(imoveis: list[dict], overrides: dict[str, str]) -> int:
    """Oráculo: estado de DB da fixture (override gravado), não o roteador."""
    return sum(
        _cents(im["valor_31_12_ano_base"])
        for im in imoveis
        if overrides.get(im.get("property_id") or "") in _FORA
    )


def violacoes(nome: str, imoveis: list[dict], overrides: dict[str, str], resultado) -> list[str]:
    carteira = resultado.investimentos_classes
    patrimonio = resultado.patrimonio_full
    achados = [
        f"{nome}: o ranking lista {item.classificacao_imovel} como ativo da carteira"
        for item in resultado.top_ativos.top_ativos
        if item.classificacao_imovel in _FORA
    ]
    imoveis_da_carteira = _cents(carteira.total_imoveis_investimento) + _cents(
        carteira.total_imoveis_uso_nao_apurado
    )
    if imoveis_da_carteira != _cents(patrimonio["imoveis_alocacao"]):
        achados.append(f"{nome}: imóveis da carteira != imoveis_alocacao do patrimônio")
    if _cents(patrimonio["imoveis_fora_alocacao"]) != _valor_declarado_fora(imoveis, overrides):
        achados.append(f"{nome}: o patrimônio perdeu o imóvel que saiu da carteira")
    return achados


@pytest.mark.parametrize("nome", REGIMES)
def test_carteira_corta_pela_lista_da_concentracao(nome: str) -> None:
    imoveis, overrides = REGIMES[nome]
    assert violacoes(nome, imoveis, overrides, _rodar(imoveis, overrides)) == []


def test_roteador_antigo_deixa_o_gate_vermelho_e_o_patrimonio_igual(monkeypatch) -> None:
    """Não-inércia, e o corte é só da carteira: o patrimônio sai byte-idêntico."""
    antes = {nome: _rodar(*REGIMES[nome]) for nome in REGIMES}
    monkeypatch.setattr(
        imovel_na_carteira, "_FORA_DA_CARTEIRA", frozenset({"residencia_principal"})
    )
    depois = {nome: _rodar(*REGIMES[nome]) for nome in REGIMES}
    assert [v for n in REGIMES for v in violacoes(n, *REGIMES[n], depois[n])]
    for nome in REGIMES:
        assert json.dumps(antes[nome].patrimonio_full, sort_keys=True, default=str) == (
            json.dumps(depois[nome].patrimonio_full, sort_keys=True, default=str)
        )
