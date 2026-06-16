"""member_hashes K4 full no nó de despesa via fixture E3 com titular (A25.l6B · ADR-279/ADR-287): E4 recomputa natural_key (gate classe-c), par dedup-colapsável prova sobreviventes pós-dedup v2; complementa a dogfood (classe-c/partial, PII-zero)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.context import WorkspaceContext  # noqa: E402
from pipeline.domain.services.e5_lineage import despesa_member_hashes  # noqa: E402

_E3_K4 = {
    "banco": "itau",
    "tipo_conta": "extratoconta",
    "titular": "TITULAR EXEMPLO",
    "moeda": "BRL",
    "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-01-31"},
    "saldo_inicial": 0.0,
    "saldo_inicial_unknown": False,
    "saldo_final": -350.0,
    "saldo_final_unknown": False,
    "fontes": ["itau_extratoconta_202601-2_extract.json"],
    "transacoes_total": 4,
    "transacoes_duplicadas_removidas": 0,
    "transacoes": [
        {"data": "2026-01-10", "descricao": "PAGAMENTO MERCADO FICTICIO", "valor": -100.0},
        {"data": "2026-01-12", "descricao": "PAGAMENTO FARMACIA EXEMPLO", "valor": -50.0},
        {"data": "2026-01-15", "descricao": "PAGAMENTO CONDOMINIO EDIF X", "valor": -200.0},
        # drift de sufixo do mesmo lançamento → colapsa no dedup (ADR-255 it.2)
        {
            "data": "2026-01-15",
            "descricao": "PAGAMENTO CONDOMINIO EDIF X — Boleto",
            "valor": -200.0,
        },
    ],
}


@pytest.fixture
def despesas_e4_v2(monkeypatch, tmp_path):
    monkeypatch.setenv("MATHOMS_DEDUP_NATURAL_KEY_V2", "1")
    from scripts.e4_categorize import main_with_store as e4

    store = InMemoryArtifactStore()
    store.seed("E3", "itau_extratoconta_202601", copy.deepcopy(_E3_K4))
    ctx = WorkspaceContext(root=tmp_path, artifact_store=store)
    e4(ctx)
    return store.read("E4", "despesas")


def test_coverage_is_full(despesas_e4_v2):
    _hashes, signals = despesa_member_hashes(despesas_e4_v2)
    assert signals == {}  # dict vazio = full, sem inline_cap


def test_member_hashes_non_empty_and_unique(despesas_e4_v2):
    hashes, _signals = despesa_member_hashes(despesas_e4_v2)
    assert hashes
    assert len(hashes) == len(set(hashes))


def test_member_hashes_are_post_dedup_survivors(despesas_e4_v2):
    # 4 itens brutos, par CONDOMINIO colapsa sob v2 → 3 despesas sobreviventes.
    hashes, _signals = despesa_member_hashes(despesas_e4_v2)
    assert len(hashes) == 3


def test_lineage_sum_matches_despesa_total(despesas_e4_v2):
    # check_lineage_sum: Σ amount[member_hashes] == despesa_total (cents int, tolerância zero).
    hashes, _signals = despesa_member_hashes(despesas_e4_v2)
    all_txs = [tx for cat in (despesas_e4_v2.get("dados") or {}).values() for tx in cat]
    by_hash = {
        nk: round(abs(float(tx["valor"])) * 100)
        for tx in all_txs
        if (nk := (tx.get("natural_key") or {}).get("hash")) is not None
    }
    soma_cents = sum(by_hash[h] for h in hashes)
    assert soma_cents == round(float(despesas_e4_v2["total_geral"]) * 100)
