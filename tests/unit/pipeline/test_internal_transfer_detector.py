"""Tests — ``InternalTransferDetector`` (Sessão A3a · Fase 7 foundation).

Cobre paridade com ``is_internal_transfer`` (e4_categorize.py:144).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.internal_transfer_detector import (  # noqa: E402
    InternalTransferConfig,
    InternalTransferDetector,
)


# =============================================================================
# Config
# =============================================================================


class TestConfig:
    def test_from_categorization_collects_all_lists(self):
        cat = {
            "internal_transfer_patterns": ["TRANSF MARIANA"],
            "internal_transfer_recipients": ["David Cliente"],
            "bank_specific_transfer_patterns": {"c6": ["Pagamento"]},
            "global_transfer_patterns": ["PIX SAQUE"],
        }
        cfg = InternalTransferConfig.from_categorization(cat)

        assert cfg.internal_patterns == ("TRANSF MARIANA",)
        assert cfg.internal_recipients == ("David Cliente",)
        assert cfg.bank_specific_patterns == {"c6": ("Pagamento",)}
        assert cfg.global_transfer_patterns == ("PIX SAQUE",)

    def test_from_categorization_skips_underscore_keys_in_bank_specific(self):
        cat = {
            "bank_specific_transfer_patterns": {
                "_comment": "ignore me",
                "c6": ["P"],
            }
        }
        cfg = InternalTransferConfig.from_categorization(cat)

        assert "_comment" not in cfg.bank_specific_patterns
        assert "c6" in cfg.bank_specific_patterns

    def test_from_categorization_handles_empty(self):
        cfg = InternalTransferConfig.from_categorization({})

        assert cfg.internal_patterns == ()
        assert cfg.internal_recipients == ()
        assert cfg.bank_specific_patterns == {}
        assert cfg.global_transfer_patterns == ()

    def test_from_categorization_handles_none(self):
        cfg = InternalTransferConfig.from_categorization(None)

        assert cfg.internal_patterns == ()


# =============================================================================
# Detector
# =============================================================================


class TestInternalPatterns:
    def test_matches_substring(self):
        cfg = InternalTransferConfig(internal_patterns=("TRANSF MARIANA",))
        detector = InternalTransferDetector(cfg)

        assert detector.is_internal_transfer("PIX TRANSF MARIANA 100") is True

    def test_normalizes_accents(self):
        cfg = InternalTransferConfig(internal_patterns=("Transferência",))
        detector = InternalTransferDetector(cfg)

        assert detector.is_internal_transfer("TRANSFERENCIA INTERNA") is True

    def test_no_match_returns_false(self):
        cfg = InternalTransferConfig(internal_patterns=("TRANSF X",))
        detector = InternalTransferDetector(cfg)

        assert detector.is_internal_transfer("compra mercado") is False


class TestInternalRecipients:
    def test_matches_recipient_name(self):
        cfg = InternalTransferConfig(internal_recipients=("Mariana Silva",))
        detector = InternalTransferDetector(cfg)

        assert detector.is_internal_transfer("PIX para MARIANA SILVA") is True


class TestBankSpecificPatterns:
    def test_match_only_when_banco_matches(self):
        cfg = InternalTransferConfig(
            bank_specific_patterns={"c6": ("Pagamento",)}
        )
        detector = InternalTransferDetector(cfg)

        # Match com banco correto + descrição exata.
        assert detector.is_internal_transfer("Pagamento", banco="C6 Bank") is True
        # Banco diferente — não match.
        assert detector.is_internal_transfer("Pagamento", banco="Itaú") is False

    def test_requires_exact_match_not_substring(self):
        """Bank-specific exige igualdade exata (após normalize) para evitar
        falsos positivos com keywords muito genéricas."""
        cfg = InternalTransferConfig(
            bank_specific_patterns={"c6": ("Pagamento",)}
        )
        detector = InternalTransferDetector(cfg)

        # Substring "Pagamento" dentro de outra descrição NÃO deve match.
        assert (
            detector.is_internal_transfer(
                "Pagamento boleto luz", banco="C6 Bank"
            )
            is False
        )


class TestGlobalPatterns:
    def test_matches_substring(self):
        cfg = InternalTransferConfig(global_transfer_patterns=("PIX SAQUE",))
        detector = InternalTransferDetector(cfg)

        assert detector.is_internal_transfer("PIX SAQUE 200,00") is True


class TestEmptyConfig:
    def test_no_config_means_no_internal_match(self):
        detector = InternalTransferDetector()

        assert detector.is_internal_transfer("qualquer coisa") is False

    def test_empty_description_returns_false(self):
        cfg = InternalTransferConfig(internal_patterns=("X",))
        detector = InternalTransferDetector(cfg)

        assert detector.is_internal_transfer("") is False
        assert detector.is_internal_transfer("   ") is False


class TestPriorityOrder:
    def test_internal_pattern_wins_before_recipient(self):
        """Se alguma camada anterior já marcou como interna, a função
        retorna ``True`` na primeira ocorrência (curto-circuito). Cobertura
        defensiva."""
        cfg = InternalTransferConfig(
            internal_patterns=("FOO",),
            internal_recipients=("BAR",),
        )
        detector = InternalTransferDetector(cfg)

        # Match no internal_pattern — recipient nunca é avaliado.
        assert detector.is_internal_transfer("compra FOO") is True
