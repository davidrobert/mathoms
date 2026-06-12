"""Goldens de paridade de colapso v1↔v2 atrás de ``dedup_natural_key_v2`` (ADR-287 · A25.l2).
Slice 1 — flag DEFAULT OFF, zero mudança de comportamento sem flag. Cravam:
(a) pernas entrada/saída de mesmo valor → 2 linhas sob v2 vs 1 sob v1
    (v1 usa ``abs(valor)`` sem direction e funde as pernas);
(b) drift de sufixo PIX → 1 linha sob v2. NOTA: v1 TAMBÉM colapsa — o strip
    de sufixo vive no ``normalize_descricao`` compartilhado desde ADR-255 it.2
    (PR #478); o diferencial "2 sob v1" citado na ADR-287 não se aplica ao
    shim atual. O golden trava que o flip PRESERVA o colapso do drift;
(c) BRL 100 ≠ USD 100 sob v2 (v1 não discrimina moeda e funde).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services._tx_identity import compute_transaction_hash  # noqa: E402
from pipeline.domain.services.cash_flow_builder import CashFlowBuilder  # noqa: E402
from pipeline.domain.services.transaction_classifier import (  # noqa: E402
    ClassifierConfig,
    TransactionClassifier,
)

_TRANSFER_CAT = {"internal_transfer_patterns": ["TRANSFERENCIA ENTRE CONTAS"]}


def _classifier(*, v2: bool, categorization: dict | None = None) -> TransactionClassifier:
    cfg = ClassifierConfig.from_configs(categorization=categorization or {}, family={})
    return TransactionClassifier(replace(cfg, dedup_natural_key_v2=v2))


def _account(transacoes: list[dict], *, moeda: str = "BRL") -> dict:
    return {
        "banco": "C6Bank",
        "titular": "david",
        "tipo_conta": "extratoconta",
        "moeda": moeda,
        "transacoes": transacoes,
    }


def _transfer_legs() -> list[dict]:
    return [
        {"data": "2026-03-30", "descricao": "TRANSFERENCIA ENTRE CONTAS", "valor": 500.0},
        {"data": "2026-03-30", "descricao": "TRANSFERENCIA ENTRE CONTAS", "valor": -500.0},
    ]


class TestFlagOffZeroBehavior:
    def test_default_config_is_off(self):
        assert ClassifierConfig().dedup_natural_key_v2 is False

    def test_flag_off_hash_matches_v1_shim(self):
        # Byte-idêntico ao atual: hash do classifier == shim v1.
        account = _account([{"data": "2026-03-30", "descricao": "Pix recebido", "valor": 100.0}])
        txs = _classifier(v2=False).classify_account(account)
        assert txs[0].transaction_hash == compute_transaction_hash(
            data="2026-03-30",
            banco="C6Bank",
            titular="david",
            tipo_conta="extratoconta",
            valor=100.0,
            descricao="Pix recebido",
        )


class TestGoldenEntradaSaidaMesmoValor:
    """(a) v1 funde as pernas (abs sem direction); v2 separa por direction."""

    def test_v1_hashes_collide_for_opposite_signs(self):
        txs = _classifier(v2=False, categorization=_TRANSFER_CAT).classify_account(
            _account(_transfer_legs())
        )
        assert [t.kind for t in txs] == ["transferencia", "transferencia"]
        assert txs[0].transaction_hash == txs[1].transaction_hash

    def test_v2_hashes_differ_for_opposite_signs(self):
        txs = _classifier(v2=True, categorization=_TRANSFER_CAT).classify_account(
            _account(_transfer_legs())
        )
        assert txs[0].transaction_hash != txs[1].transaction_hash

    def test_v1_collapses_to_one_line(self):
        txs = _classifier(v2=False, categorization=_TRANSFER_CAT).classify_account(
            _account(_transfer_legs())
        )
        cf = CashFlowBuilder().build(txs)
        assert cf.transferencias_count == 1
        assert cf.dedup_report.collapsed_count == 1

    def test_v2_keeps_two_lines(self):
        txs = _classifier(v2=True, categorization=_TRANSFER_CAT).classify_account(
            _account(_transfer_legs())
        )
        cf = CashFlowBuilder(dedup_natural_key_v2=True).build(txs)
        assert cf.transferencias_count == 2
        assert cf.dedup_report.collapsed_count == 0


class TestGoldenDriftSufixoPix:
    """(b) v2 colapsa drift de sufixo de roteamento — e v1 idem (ADR-255 it.2)."""

    def _despesas_com_drift(self) -> list[dict]:
        return [
            {"data": "2026-03-30", "descricao": "PAGTO CONDOMINIO EDIF X", "valor": -120.5},
            {
                "data": "2026-03-30",
                "descricao": "PAGTO CONDOMINIO EDIF X — Boleto",
                "valor": -120.5,
            },
        ]

    def test_v2_collapses_drift_to_one_line(self):
        txs = _classifier(v2=True).classify_account(_account(self._despesas_com_drift()))
        cf = CashFlowBuilder(dedup_natural_key_v2=True).build(txs)
        assert cf.despesas.total_transacoes == 1
        assert cf.dedup_report.collapsed_count == 1

    def test_v1_also_collapses_drift(self):
        # Paridade documentada: strip de sufixo é compartilhado entre v1 e v2
        # (normalize_descricao, ADR-255 it.2) — o flip não regride esse colapso.
        txs = _classifier(v2=False).classify_account(_account(self._despesas_com_drift()))
        cf = CashFlowBuilder().build(txs)
        assert cf.despesas.total_transacoes == 1


class TestGoldenMoedaDiscrimina:
    """(c) BRL 100 ≠ USD 100 sob v2; v1 funde (hash sem moeda)."""

    def _accounts(self) -> list[dict]:
        tx = {"data": "2026-03-30", "descricao": "Pix recebido arvo", "valor": 100.0}
        return [_account([dict(tx)], moeda="BRL"), _account([dict(tx)], moeda="USD")]

    def test_v1_fuses_brl_and_usd(self):
        txs = _classifier(v2=False).classify_all(self._accounts())
        cf = CashFlowBuilder().build(txs)
        assert cf.receitas.total_transacoes == 1
        assert cf.dedup_report.collapsed_count == 1

    def test_v2_keeps_brl_and_usd_apart(self):
        txs = _classifier(v2=True).classify_all(self._accounts())
        assert txs[0].transaction_hash != txs[1].transaction_hash
        cf = CashFlowBuilder(dedup_natural_key_v2=True).build(txs)
        assert cf.receitas.total_transacoes == 2
        assert cf.dedup_report.collapsed_count == 0


class TestBuilderFallbackRespectsFlag:
    """Sem ``transaction_hash`` estampado, o fallback do builder segue a flag."""

    def _bare_tx(self, valor, tipo):
        from pipeline.domain.services.transaction_classifier import ClassifiedTransaction

        return ClassifiedTransaction(
            kind="transferencia",
            data="2026-03-30",
            descricao="TRANSFERENCIA ENTRE CONTAS",
            valor=valor,
            banco="C6Bank",
            moeda="BRL",
            tipo_conta="extratoconta",
            titular="david",
            tipo=tipo,
        )

    def test_fallback_v1_collapses_legs(self):
        cf = CashFlowBuilder().build(
            [self._bare_tx(500.0, "credito"), self._bare_tx(-500.0, "debito")]
        )
        assert cf.transferencias_count == 1

    def test_fallback_v2_keeps_legs(self):
        cf = CashFlowBuilder(dedup_natural_key_v2=True).build(
            [self._bare_tx(500.0, "credito"), self._bare_tx(-500.0, "debito")]
        )
        assert cf.transferencias_count == 2
