"""Tests — ``BankCanonicalizer`` e ``canonicalize_bank`` (Fase 6 foundation)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import BankCanonicalizer, canonicalize_bank  # noqa: E402
from pipeline.domain.models.bank import _normalize  # noqa: E402

INSTITUTIONS = {
    "banco_canonical": {
        "itau": "Itaú",
        "c6bank": "C6 Bank",
        "bankofamerica": "Bank of America",
        "btgpactual": "BTG Pactual",
        "bradesco": "Bradesco",
        "nubank": "Nubank",
    }
}


class TestNormalize:
    def test_removes_accents(self):
        assert _normalize("Itaú") == "itau"

    def test_removes_spaces(self):
        assert _normalize("C6 Bank") == "c6bank"

    def test_removes_punctuation(self):
        assert _normalize("Bank-of/America") == "bankofamerica"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_none_safe(self):
        assert _normalize(None) == ""  # type: ignore[arg-type]

    def test_idempotent(self):
        once = _normalize("Itaú Unibanco")
        twice = _normalize(once)
        assert once == twice


class TestCanonicalizerIndex:
    def test_from_institutions_indexes_codes(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert canon.canonicalize("itau") == "itau"
        assert canon.canonicalize("c6bank") == "c6bank"

    def test_from_institutions_indexes_display_names(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert canon.canonicalize("Itaú") == "itau"
        assert canon.canonicalize("C6 Bank") == "c6bank"
        assert canon.canonicalize("Bank of America") == "bankofamerica"

    def test_case_insensitive(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert canon.canonicalize("ITAÚ") == "itau"
        assert canon.canonicalize("c6 BANK") == "c6bank"

    def test_missing_banco_canonical_section_is_safe(self):
        canon = BankCanonicalizer.from_institutions({})
        assert canon.canonicalize("itau") == "itau"  # fallback normalizado

    def test_none_institutions_is_safe(self):
        canon = BankCanonicalizer.from_institutions(None)  # type: ignore[arg-type]
        assert canon.canonicalize("itau") == "itau"

    def test_empty_factory(self):
        canon = BankCanonicalizer.empty()
        assert canon.canonicalize("qualquer") == "qualquer"


class TestCanonicalizeFallback:
    def test_unknown_bank_returns_normalized_form(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        # Bank not in map — returns normalized input (no invented canonical).
        assert canon.canonicalize("Banco Desconhecido") == "bancodesconhecido"

    def test_empty_input_returns_empty(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert canon.canonicalize("") == ""


class TestAreSameBank:
    def test_same_code(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert canon.are_same_bank("itau", "Itaú")

    def test_same_code_variations(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert canon.are_same_bank("c6bank", "C6 Bank")
        assert canon.are_same_bank("c6bank", "c6 BANK")

    def test_different_codes(self):
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert not canon.are_same_bank("itau", "nubank")

    def test_avoids_substring_false_positive(self):
        """Fix 4.4 regression test: ``"c6"`` não deve bater com ``"abc6xyz"``.

        Antes: comparação por substring produzia match espúrio. Agora,
        canonicalização garante que ``"c6"`` vira ``"c6"`` (fallback) e
        ``"abc6xyz"`` vira ``"abc6xyz"`` — diferentes.
        """
        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        assert not canon.are_same_bank("c6", "abc6xyz")


class TestCanonicalizeBankFreeFunction:
    def test_delegates_to_class(self):
        assert canonicalize_bank("Itaú", INSTITUTIONS) == "itau"

    def test_fallback_on_empty_mapping(self):
        assert canonicalize_bank("Itaú", {}) == "itau"


class TestImmutability:
    def test_canonicalizer_is_frozen(self):
        import pytest

        canon = BankCanonicalizer.from_institutions(INSTITUTIONS)
        with pytest.raises((AttributeError, Exception)):
            canon._index = {}  # type: ignore[misc]
