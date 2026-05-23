"""Tests — propagação de ``source_doc_id`` + ``transaction_hash`` (ADR-255 Camada B)."""

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


class TestE2ProcessFilePopulatesArquivoOrigem:
    """Backfill de ``arquivo_origem`` no top-level do dict E2 (workspace 5@5.com, 2026-05)."""

    def _setup_mocks(self, monkeypatch, parser_result):
        from scripts import e2_extract

        monkeypatch.setattr(e2_extract, "route_to_parser", lambda fn: lambda fp, fn: parser_result)
        # validate_extrato_result lê o arquivo; vamos curto-circuitar para []
        monkeypatch.setattr(e2_extract, "validate_extrato_result", lambda r, fp, is_csv: [])

    def test_process_file_sets_arquivo_origem_when_parser_omits(self, tmp_path, monkeypatch):
        """Parser sem ``arquivo_origem`` no result — process_file adiciona."""
        parser_result = {"banco": "C6Bank", "tipo_conta": "corrente", "transacoes": []}
        self._setup_mocks(monkeypatch, parser_result)
        from scripts import e2_extract

        fake_file = tmp_path / "abc123_c6bank_extratoconta_202604-0_original.pdf"
        fake_file.write_bytes(b"x")
        result = e2_extract.process_file(fake_file)
        assert result is not None
        assert result["arquivo_origem"] == fake_file.name

    def test_process_file_preserves_arquivo_origem_when_parser_sets(self, tmp_path, monkeypatch):
        """Parser que setou ``arquivo_origem`` (ex.: E2-llm) — process_file preserva."""
        parser_result = {
            "banco": "C6Bank",
            "transacoes": [],
            "arquivo_origem": "explicit-set-by-parser.pdf",
        }
        self._setup_mocks(monkeypatch, parser_result)
        from scripts import e2_extract

        fake_file = tmp_path / "abc123_c6bank_extratoconta_202604-0_original.pdf"
        fake_file.write_bytes(b"x")
        result = e2_extract.process_file(fake_file)
        assert result["arquivo_origem"] == "explicit-set-by-parser.pdf"


class TestBankStatementFromE2DictPropagatesSource:
    """``BankStatement.from_e2_dict`` propaga ``arquivo_origem`` do top-level
    para cada ``Transaction.source_document``. Sem isso, o E3 grava txs sem
    rastreabilidade e o ClassifiedTransaction perde ``source_doc_id``."""

    def test_arquivo_origem_top_level_propagates_to_each_transaction(self):
        from pipeline.domain.models.document import BankStatement

        e2_dict = {
            "banco": "C6Bank",
            "tipo": "corrente",
            "moeda": "BRL",
            "periodo_inicio": "2026-01-01",
            "periodo_fim": "2026-01-31",
            "arquivo_origem": "abc123_c6bank_extratoconta_202601-0_original.pdf",
            "transacoes": [
                {"data": "2026-01-15", "descricao": "Pix", "valor": 100.0},
                {"data": "2026-01-20", "descricao": "TED", "valor": -50.0},
            ],
        }
        stmt = BankStatement.from_e2_dict(e2_dict)
        assert stmt.source_document == "abc123_c6bank_extratoconta_202601-0_original.pdf"
        assert len(stmt.transactions) == 2
        for tx in stmt.transactions:
            assert tx.source_document == "abc123_c6bank_extratoconta_202601-0_original.pdf"


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
