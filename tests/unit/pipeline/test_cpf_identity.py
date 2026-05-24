"""Tests — ``_cpf_identity.normalize_cpf`` (ADR-267)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services._cpf_identity import normalize_cpf  # noqa: E402


class TestNormalizeCpf:
    def test_masked_cpf_normalizes_to_11_digits(self):
        # Placeholder LGPD-safe (allowlist do lint anti-PII).
        assert normalize_cpf("123.456.789-09") == "12345678909"
        assert normalize_cpf("000.000.000-00") == "00000000000"

    def test_unmasked_cpf_passthrough(self):
        assert normalize_cpf("12345678909") == "12345678909"

    def test_with_spaces_and_dashes(self):
        assert normalize_cpf("123 456 789-09") == "12345678909"
        assert normalize_cpf("  123.456.789-09  ") == "12345678909"

    def test_cnpj_14_digits_rejected(self):
        """CNPJ tem 14 dígitos — não é CPF, rejeitar."""
        assert normalize_cpf("12.345.678/0001-99") == ""
        assert normalize_cpf("12345678000199") == ""

    def test_partial_cpf_rejected(self):
        """CPF mascarado parcialmente (<11 dígitos) é inválido."""
        assert normalize_cpf("12345") == ""
        assert normalize_cpf("123.456") == ""

    def test_empty_and_none(self):
        assert normalize_cpf("") == ""
        assert normalize_cpf(None) == ""
        assert normalize_cpf("   ") == ""

    def test_only_punctuation(self):
        assert normalize_cpf("...---") == ""
        assert normalize_cpf("/-.") == ""

    def test_alphanumeric_strips_letters(self):
        """Letras são strippadas — pega só dígitos."""
        assert normalize_cpf("CPF 123.456.789-09") == "12345678909"

    def test_cpf_with_extra_digits_rejected(self):
        """12 dígitos (CPF + 1 sobrando) não é CPF válido — rejeitar."""
        assert normalize_cpf("123456789091") == ""
