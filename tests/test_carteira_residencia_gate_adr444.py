"""Gate da [[ADR-444]]: a carteira de investimentos não afirma investimento sobre o que pode
ser a residência, nem silencia imóvel sabidamente não-residência.

Caminho de produção inteiro: `E5AnalyzerAdapter.analyze_via_store` — o veredito sai do
`PatrimonioCalculator` e chega aos analyzers pela fiação do adapter. O oráculo NÃO chama o
veredito: relê o estado de DB da fixture (overrides + `residencia_status`) e os itens
([[ADR-439]] D7). Se gate e produtor compartilhassem a função, a mutação mudaria os dois.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.services import e5_analyzer_adapter
from pipeline.domain.services.e5_analyzer_adapter import E5AnalyzerAdapter
from tests.unit.pipeline.test_e5_analyzer_adapter import _seed_minimal

SEM_PESO = "Imóveis com uso não apurado"
INVESTIMENTO = "Imóveis Investimento"


@dataclass(frozen=True)
class Regime:
    nome: str
    imoveis: list[dict]
    overrides: dict[str, str] = field(default_factory=dict)
    status: str | None = None


_CASA = {"descricao": "Casa", "valor_31_12_ano_base": 800_000.0, "property_id": "pid-casa"}
_CASA_SEM_ID = {"descricao": "Casa", "valor_31_12_ano_base": 800_000.0}
_CASA_VENDIDA = {"descricao": "Casa", "valor_31_12_ano_base": 0.0, "property_id": "pid-casa"}
_SALA = {"descricao": "Sala", "valor_31_12_ano_base": 300_000.0, "property_id": "pid-sala"}
_LOJA = {"descricao": "Loja", "valor_31_12_ano_base": 200_000.0}
_RES = {"pid-casa": "residencia_principal"}
_RES_E_SALA = {"pid-casa": "residencia_principal", "pid-sala": "locado"}

REGIMES = [
    # O caso da lane: a residência perdeu o id no run e o override segue gravado.
    Regime("residencia_sem_id", [_CASA_SEM_ID, _SALA], _RES_E_SALA, "owned"),
    Regime("nada_classificado", [_CASA_SEM_ID, _LOJA], {}, None),
    Regime("owned_sem_override", [_CASA_SEM_ID, _LOJA], {}, "owned"),
    # Mudança de casa: a marcada foi vendida (zero em 31/12) e a nova veio sem override.
    Regime("vendeu_a_casa_marcada", [_CASA_VENDIDA, _LOJA], _RES, "owned"),
    Regime("aluga", [_LOJA, _SALA], {"pid-sala": "locado"}, "rented"),
    # Resíduo declarado (D6): residência identificada, desconhecido por eliminação.
    Regime("identificada_com_desconhecido", [_CASA, _LOJA], _RES, "owned"),
    Regime("tudo_classificado", [_CASA, _SALA], _RES_E_SALA, "owned"),
    Regime("sem_imovel", [], {}, "undeclared"),
]


def _rodar(r: Regime):
    store = InMemoryArtifactStore()
    _seed_minimal(store)
    store.seed("E4", "patrimonio", {"members": {"david": {"bens": {"imoveis": r.imoveis}}}})
    adapter = E5AnalyzerAdapter.from_configs(
        property_classification_overrides=r.overrides, residencia_status=r.status
    )
    return adapter.analyze_via_store(store)


# ── oráculo: estado de DB da fixture, nunca o veredito ──────────────────────────
def _pid(im: dict) -> str | None:
    return im.get("property_id") or None


def _desconhecido(r: Regime, im: dict) -> bool:
    return not _pid(im) or _pid(im) not in r.overrides


def _residencia_pode_estar_no_desconhecido(r: Regime) -> bool:
    localizada = any(
        r.overrides.get(_pid(im) or "") == "residencia_principal" and im["valor_31_12_ano_base"] > 0
        for im in r.imoveis
    )
    return not localizada and r.status != "rented"


def violacoes(r: Regime, resultado) -> list[str]:
    tabela = {c.categoria: c for c in resultado.investimentos_classes.tabela_classes}
    em_aberto = sum(
        Decimal(str(im["valor_31_12_ano_base"]))
        for im in r.imoveis
        if _desconhecido(r, im) and im["valor_31_12_ano_base"] > 0
    )
    sem_peso = Decimal(str(tabela[SEM_PESO].valor)) if SEM_PESO in tabela else Decimal("0")
    achados = []
    if _residencia_pode_estar_no_desconhecido(r) and sem_peso != em_aberto:
        achados.append(f"{r.nome}: afirma investimento sobre o que pode ser a residência")
    if not _residencia_pode_estar_no_desconhecido(r) and sem_peso:
        achados.append(f"{r.nome}: tira o peso de imóvel sabidamente não-residência")
    return achados + _contrato(r, resultado)


def _contrato(r: Regime, resultado) -> list[str]:
    a = resultado.investimentos_classes
    linhas = {c.categoria: c for c in a.tabela_classes}
    achados = []
    if SEM_PESO in linhas and linhas[SEM_PESO].pct is not None:
        achados.append(f"{r.nome}: linha sem peso publica percentual")
    soma = sum(Decimal(str(c.valor)) for c in a.tabela_classes)
    if round(Decimal(str(a.total)) + a.total_imoveis_uso_nao_apurado, 2) != round(soma, 2):
        achados.append(f"{r.nome}: total + sem peso != Σ tabela")
    for item in resultado.top_ativos.top_ativos:
        if (item.classe == SEM_PESO) != (item.pct_carteira is None):
            achados.append(f"{r.nome}: peso do item não segue a classe ({item.classe})")
    return achados


@pytest.mark.parametrize("regime", REGIMES, ids=lambda r: r.nome)
def test_carteira_so_afirma_investimento_com_evidencia(regime: Regime) -> None:
    assert violacoes(regime, _rodar(regime)) == []


def test_a_residencia_sem_id_nao_e_contada_como_investimento() -> None:
    """O critério 1 da lane, literal: hoje a casa sem id entrava em Imóveis Investimento."""
    resultado = _rodar(REGIMES[0])
    tabela = {c.categoria: c.valor for c in resultado.investimentos_classes.tabela_classes}
    assert tabela.get(INVESTIMENTO) == 300_000.0
    assert tabela.get(SEM_PESO) == 800_000.0
    topo = resultado.top_ativos.top_ativos[0]
    assert (topo.classe, topo.pct_carteira) == (SEM_PESO, None)


# Não-inércia: o predicado preso em qualquer valor fixo tem de morder.
@pytest.mark.parametrize("fixo", [True, False])
def test_predicado_fixo_deixa_o_gate_vermelho(monkeypatch, fixo: bool) -> None:
    monkeypatch.setattr(
        e5_analyzer_adapter,
        "residencia_pode_estar_no_desconhecido",
        lambda *a, **k: fixo,
    )
    todas = [v for r in REGIMES for v in violacoes(r, _rodar(r))]
    assert todas, f"predicado sempre {fixo} passou — o gate seria inerte"
