"""Tests — ``_tx_identity`` (ADR-248 Camada A)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services._tx_identity import (  # noqa: E402
    cents_int,
    compute_transaction_hash,
    normalize_banco,
    normalize_descricao,
    normalize_tipo_conta,
    normalize_titular,
)


class TestNormalizeBanco:
    def test_collapses_spacing_and_casing(self):
        assert normalize_banco("C6Bank") == normalize_banco("C6 Bank")
        assert normalize_banco("C6Bank") == normalize_banco("c6bank")

    def test_strips_accent(self):
        assert normalize_banco("Itaú") == normalize_banco("Itau")

    def test_empty_and_none(self):
        assert normalize_banco("") == ""
        assert normalize_banco(None) == ""


class TestNormalizeDescricao:
    def test_preserves_accent_and_digits(self):
        # Crítico para distinguir "FAÇA" vs "FACA" e tokens N/M legítimos.
        assert "ç" in normalize_descricao("FAÇA O X")
        assert "3/12" in normalize_descricao("PARC 3/12 LOJA")

    def test_collapses_whitespace_and_casing(self):
        assert normalize_descricao("  pix  recebido  arvo  ") == "pix recebido arvo"

    def test_empty_and_none(self):
        assert normalize_descricao("") == ""
        assert normalize_descricao(None) == ""


class TestCentsInt:
    def test_avoids_float_drift(self):
        # 47208.77 * 100 em float = 4720876.999... — int(round(...)) salva.
        assert cents_int(47208.77) == 4720877

    def test_negative(self):
        assert cents_int(-100.5) == -10050


class TestComputeTransactionHash:
    def _base(self) -> dict:
        return dict(
            data="2026-03-30",
            banco="C6Bank",
            titular="david",
            tipo_conta="extratoconta",
            valor=47208.77,
            descricao="Pix recebido de ARVO SAUDE LTDA",
        )

    def test_deterministic_across_bank_casing_drift(self):
        h1 = compute_transaction_hash(**{**self._base(), "banco": "C6Bank"})
        h2 = compute_transaction_hash(**{**self._base(), "banco": "C6 Bank"})
        h3 = compute_transaction_hash(**{**self._base(), "banco": "c6bank"})
        assert h1 == h2 == h3

    def test_changes_with_data(self):
        h1 = compute_transaction_hash(**self._base())
        h2 = compute_transaction_hash(**{**self._base(), "data": "2026-03-31"})
        assert h1 != h2

    def test_changes_with_titular(self):
        # K4: titular separa casal mesmo banco.
        h1 = compute_transaction_hash(**self._base())
        h2 = compute_transaction_hash(**{**self._base(), "titular": "mariana"})
        assert h1 != h2

    def test_changes_with_tipo_conta(self):
        # K4: tipo_conta separa CC vs poupança do mesmo titular.
        h1 = compute_transaction_hash(**self._base())
        h2 = compute_transaction_hash(**{**self._base(), "tipo_conta": "extratopoupanca"})
        assert h1 != h2

    def test_changes_with_valor(self):
        h1 = compute_transaction_hash(**self._base())
        h2 = compute_transaction_hash(**{**self._base(), "valor": 47208.78})
        assert h1 != h2

    def test_changes_with_descricao(self):
        h1 = compute_transaction_hash(**self._base())
        h2 = compute_transaction_hash(
            **{**self._base(), "descricao": "Pix recebido de ARVO SAUDE LTDA — Salários PJ"}
        )
        assert h1 != h2

    def test_preserves_distinct_parcelas(self):
        # PARC 3/12 vs PARC 4/12 — mesmo dia, mesmo valor, mas diferentes
        # lançamentos contábeis. Hash deve separar.
        h_p3 = compute_transaction_hash(
            data="2026-01-15",
            banco="Santander",
            titular="david",
            tipo_conta="faturaunique",
            valor=199.90,
            descricao="LOJA X PARC 3/12",
        )
        h_p4 = compute_transaction_hash(
            data="2026-01-15",
            banco="Santander",
            titular="david",
            tipo_conta="faturaunique",
            valor=199.90,
            descricao="LOJA X PARC 4/12",
        )
        assert h_p3 != h_p4

    def test_abs_value_collapses_sign(self):
        # Hash usa abs() para robustez se caller passar valor com sinal.
        kw = dict(data="2026-01-01", banco="X", titular="y", tipo_conta="z", descricao="abc")
        h_pos = compute_transaction_hash(valor=100.0, **kw)
        h_neg = compute_transaction_hash(valor=-100.0, **kw)
        assert h_pos == h_neg

    def test_hash_is_16_lowercase_hex(self):
        h = compute_transaction_hash(**self._base())
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)


class TestNormalizeTitular:
    def test_handles_strip_and_accent(self):
        assert normalize_titular(" David ") == normalize_titular("david")
        assert normalize_titular("Davíd") == normalize_titular("david")


class TestNormalizeTipoConta:
    def test_collapses_spaces(self):
        assert normalize_tipo_conta("Conta Corrente") == "contacorrente"

    def test_none(self):
        assert normalize_tipo_conta(None) == ""
