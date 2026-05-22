"""Tests — propagação de ``source_doc_id`` + ``transaction_hash`` (ADR-248 Camada B)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services._tx_identity import compute_transaction_hash  # noqa: E402
from pipeline.domain.services.cash_flow_builder import CashFlowBuilder  # noqa: E402
from pipeline.domain.services.transaction_classifier import (  # noqa: E402
    ClassifiedTransaction,
    ClassifierConfig,
    TransactionClassifier,
)


def _classifier() -> TransactionClassifier:
    return TransactionClassifier(ClassifierConfig.from_configs(categorization={}, family={}))


def _account(transacoes: list[dict]) -> dict:
    return {
        "banco": "C6Bank",
        "titular": "david",
        "tipo_conta": "extratoconta",
        "moeda": "BRL",
        "transacoes": transacoes,
    }


class TestHashPopulated:
    def test_classifier_populates_transaction_hash(self):
        # Após Camada B, toda tx classificada tem `transaction_hash` não-None.
        account = _account([{"data": "2026-03-30", "descricao": "Pix recebido", "valor": 100.0}])
        txs = _classifier().classify_account(account)
        assert len(txs) == 1
        assert txs[0].transaction_hash is not None
        assert len(txs[0].transaction_hash) == 16

    def test_hash_matches_inline_compute(self):
        # Paridade com Camada A: hash do classifier == hash computado inline.
        account = _account([{"data": "2026-03-30", "descricao": "Pix recebido", "valor": 100.0}])
        txs = _classifier().classify_account(account)
        expected = compute_transaction_hash(
            data="2026-03-30",
            banco="C6Bank",
            titular="david",
            tipo_conta="extratoconta",
            valor=100.0,
            descricao="Pix recebido",
        )
        assert txs[0].transaction_hash == expected

    def test_source_doc_id_propagated_from_arquivo_origem(self):
        account = _account(
            [
                {
                    "data": "2026-03-30",
                    "descricao": "Pix recebido",
                    "valor": 100.0,
                    "arquivo_origem": "abc123_extratoconta-0_original.pdf",
                }
            ]
        )
        txs = _classifier().classify_account(account)
        assert txs[0].source_doc_id == "abc123_extratoconta-0_original.pdf"

    def test_source_doc_id_none_when_arquivo_origem_absent(self):
        account = _account([{"data": "2026-03-30", "descricao": "Pix recebido", "valor": 100.0}])
        txs = _classifier().classify_account(account)
        assert txs[0].source_doc_id is None


class TestLegacyDictSurfacesIdentity:
    def test_to_legacy_dict_includes_hash_and_source(self):
        tx = ClassifiedTransaction(
            kind="receita",
            data="2026-03-30",
            descricao="X",
            valor=100.0,
            banco="C6Bank",
            moeda="BRL",
            tipo_conta="extratoconta",
            titular="david",
            tipo="credito",
            categoria="rec",
            origem="O",
            source_doc_id="doc-uuid",
            transaction_hash="a1b2c3d4e5f6a7b8",
        )
        d = tx.to_legacy_dict()
        assert d["source_doc_id"] == "doc-uuid"
        assert d["transaction_hash"] == "a1b2c3d4e5f6a7b8"

    def test_to_legacy_dict_omits_hash_when_none(self):
        # Compat com payloads pré-Camada B: campos só aparecem quando populados.
        tx = ClassifiedTransaction(
            kind="receita",
            data="2026-03-30",
            descricao="X",
            valor=100.0,
            banco="C6Bank",
            moeda="BRL",
            tipo_conta="extratoconta",
            titular="david",
            tipo="credito",
            categoria="rec",
            origem="O",
        )
        d = tx.to_legacy_dict()
        assert "source_doc_id" not in d
        assert "transaction_hash" not in d


def _force_hash_tx(descricao: str, forced_hash: str) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="receita",
        data="2026-03-30",
        descricao=descricao,
        valor=100.0,
        banco="C6Bank",
        moeda="BRL",
        tipo_conta="extratoconta",
        titular="david",
        tipo="credito",
        categoria="rec",
        origem="O",
        transaction_hash=forced_hash,
    )


class TestCashFlowPrefersTxHash:
    def test_cash_flow_uses_tx_hash_when_present(self):
        # Descrições diferentes → hash inline diferente, mas forçamos
        # `transaction_hash` igual. Se builder usar o campo (Camada B),
        # colapsa; se recomputar inline (Camada A pura), preserva ambas.
        tx_a = _force_hash_tx("ALPHA", "forced_same_hash")
        tx_b = _force_hash_tx("BETA", "forced_same_hash")
        cf = CashFlowBuilder().build([tx_a, tx_b])
        assert cf.receitas.total_transacoes == 1
        assert cf.dedup_report.collapsed_count == 1
