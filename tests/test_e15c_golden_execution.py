"""Golden de execução E1.5c (`consolidate_baseline`): run canônico + contrato.

Distinto da suíte INV-1..9 (propriedades) e do golden anotado de l2 (fn/fp
rates): este golden roda um baseline sintético **realista** (imóvel + série
cross-year + conta conjunta + dívida + zero-PII) pelo caminho real
`main_with_store` e afirma o **contrato de saída** que o E5 consome. Fixture
mínima — l2 endurece com o golden multi-ano anotado.

Plano: [[PLAN-launch-trust]] §F1-O0. Lane A21.l1.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext

# Chaves que o E5 (`analyze_finances`) lê do artifact E1.5c — o contrato.
_E5_CONSUMED_KEYS = (
    "imoveis_consolidados",
    "veiculos_consolidados",
    "investimentos_consolidados",
    "dividas",
    "patrimonio_por_ano",
)


def _canonical_baseline() -> dict:
    return {
        "itens": [
            {
                "codigo": "11",
                "descricao": "APT RUA EXEMPLO 100, SAO PAULO/SP",
                "categoria": "imovel",
                "valor_brl": 600000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
            {
                "codigo": "04",
                "descricao": "TESOURO SELIC 2029",
                "instituicao": "tesouro",
                "categoria": "investimento",
                "valor_brl": 80000.0,
                "membro": "david_robert",
                "ano": 2023,
            },
            {
                "codigo": "04",
                "descricao": "TESOURO SELIC 2029",
                "instituicao": "tesouro",
                "categoria": "investimento",
                "valor_brl": 100000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
            {
                "codigo": "04",
                "descricao": "CDB BANCO EXEMPLO",
                "instituicao": "banco_exemplo",
                "categoria": "investimento",
                "valor_brl": 50000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
            {
                "codigo": "04",
                "descricao": "CDB BANCO EXEMPLO",
                "instituicao": "banco_exemplo",
                "categoria": "investimento",
                "valor_brl": 50000.0,
                "membro": "mariana_silva",
                "ano": 2024,
            },
            {
                "codigo": "00",
                "descricao": "FINANCIAMENTO IMOVEL",
                "categoria": "outros",
                "valor_brl": -200000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
        ],
        "resumo": {
            "total_ativos": 0.0,
            "total_passivos": 0.0,
            "patrimonio_liquido": 0.0,
            "ano_referencia": 2024,
        },
    }


def _run(tmp_path: Path) -> dict:
    from scripts.e15_consolidate import main_with_store

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", _canonical_baseline())
    ctx = WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-golden",
        property_identity_resolver=InMemoryPropertyIdentityResolver(),
    )
    result = main_with_store(ctx)
    assert result["success"] is True
    return store.read("E1.5c", "baseline_patrimonial")


def test_e15c_golden_output_contract(tmp_path: Path) -> None:
    """Run canônico produz todas as chaves que o E5 consome, com tipos certos."""
    out = _run(tmp_path)
    for key in _E5_CONSUMED_KEYS:
        assert key in out, f"contrato E5 quebrado: falta {key!r}"
    assert isinstance(out["investimentos_consolidados"], list)
    assert isinstance(out["dividas"], list)
    assert isinstance(out["patrimonio_por_ano"], dict)


def test_e15c_golden_dedup_e_serie(tmp_path: Path) -> None:
    """Conta conjunta funde (1), série cross-year preserva 2 anos, dívida fica."""
    out = _run(tmp_path)
    invs = out["investimentos_consolidados"]
    # CDB conjunto idêntico → 1; Tesouro série cross-year → 1: total 2.
    assert len(invs) == 2
    serie = [e for e in invs if e["descricao"] == "TESOURO SELIC 2029"]
    assert len(serie) == 1
    assert set(serie[0]["valores_31_12"]) == {"2023", "2024"}
    assert len(out["dividas"]) == 1
    assert out["dividas"][0]["saldo_31_12"]["2024"] == 200000.0
