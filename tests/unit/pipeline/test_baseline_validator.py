"""Tests — ``BaselineValidator`` (Fase 6 foundation estendida)."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import BankCanonicalizer, BankStatement, Money  # noqa: E402
from pipeline.domain.services.baseline_validator import (  # noqa: E402
    BaselineAccountSaldo,
    BaselineDiffWarning,
    BaselineValidator,
    BaselineValidatorConfig,
)


INSTITUTIONS = {
    "banco_canonical": {
        "itau": "Itaú",
        "c6bank": "C6 Bank",
        "nubank": "Nubank",
    }
}


def _stmt(
    institution: str,
    period_end: date,
    closing: str | None,
    *,
    currency: str = "BRL",
    member: str | None = "david",
) -> BankStatement:
    period_start = date(period_end.year, 1, 1)
    return BankStatement(
        institution=institution,
        member_key=member,
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        transactions=[],
        opening_balance=None,
        closing_balance=(
            Money.of(closing, currency) if closing is not None else None
        ),
    )


def _bl_acct(
    bank: str,
    year: int,
    saldo: str,
    *,
    member: str = "David",
    tipo: str = "corrente",
) -> BaselineAccountSaldo:
    return BaselineAccountSaldo(
        bank=bank,
        year=year,
        saldo=Money.brl(saldo),
        member=member,
        account_type=tipo,
    )


# =============================================================================
# Config
# =============================================================================


class TestBaselineValidatorConfig:
    def test_default_tolerance(self):
        assert BaselineValidatorConfig().tolerance_amount == Decimal("1.00")

    def test_from_pipeline_config_defaults(self):
        cfg = BaselineValidatorConfig.from_pipeline_config({})
        assert cfg.tolerance_amount == Decimal("1.00")

    def test_from_pipeline_config_custom(self):
        cfg = BaselineValidatorConfig.from_pipeline_config(
            {"reconciliation": {"tolerances": {"baseline_irpf_diff": "10"}}}
        )
        assert cfg.tolerance_amount == Decimal("10")

    def test_from_pipeline_config_none_safe(self):
        cfg = BaselineValidatorConfig.from_pipeline_config(None)  # type: ignore[arg-type]
        assert cfg.tolerance_amount == Decimal("1.00")


# =============================================================================
# BaselineAccountSaldo.from_baseline_dict
# =============================================================================


class TestBaselineAccountSaldoExtraction:
    def test_empty_baseline(self):
        assert BaselineAccountSaldo.from_baseline_dict({}) == []

    def test_none_baseline(self):
        assert BaselineAccountSaldo.from_baseline_dict(None) == []  # type: ignore[arg-type]

    def test_members_dict_format(self):
        baseline = {
            "members": {
                "David": {
                    "contas_bancarias": [
                        {
                            "banco": "Itaú",
                            "saldo_31_12": 1000.0,
                            "ano_base": 2025,
                            "tipo": "corrente",
                        }
                    ]
                }
            }
        }
        out = BaselineAccountSaldo.from_baseline_dict(baseline)
        assert len(out) == 1
        assert out[0].bank == "Itaú"
        assert out[0].year == 2025
        assert out[0].saldo == Money.brl("1000")
        assert out[0].member == "David"
        assert out[0].account_type == "corrente"

    def test_members_list_format(self):
        baseline = {
            "membros": [
                {
                    "nome": "David",
                    "contas_bancarias": [
                        {"banco": "Itaú", "saldo_31_12": 500, "ano_base": 2024},
                    ],
                }
            ]
        }
        out = BaselineAccountSaldo.from_baseline_dict(baseline)
        assert len(out) == 1
        assert out[0].member == "David"
        assert out[0].year == 2024

    def test_pt_member_key_membros(self):
        """Aceita ``membros`` (PT) como alias de ``members``."""
        baseline = {
            "membros": {
                "David": {
                    "contas_bancarias": [
                        {"banco": "C6", "saldo_31_12": 100, "ano_base": 2023},
                    ]
                }
            }
        }
        out = BaselineAccountSaldo.from_baseline_dict(baseline)
        assert len(out) == 1

    def test_alternative_field_names(self):
        """Aceita ``banco_origem`` e ``saldo_31_12_ano_base`` (aliases)."""
        baseline = {
            "members": {
                "David": {
                    "contas_bancarias": [
                        {
                            "banco_origem": "Nubank",
                            "saldo_31_12_ano_base": 250,
                            "ano_base": 2025,
                        }
                    ]
                }
            }
        }
        out = BaselineAccountSaldo.from_baseline_dict(baseline)
        assert len(out) == 1
        assert out[0].bank == "Nubank"
        assert out[0].saldo == Money.brl("250")

    def test_skips_missing_saldo(self):
        baseline = {
            "members": {
                "David": {
                    "contas_bancarias": [
                        {"banco": "Itaú", "ano_base": 2025},  # sem saldo
                    ]
                }
            }
        }
        assert BaselineAccountSaldo.from_baseline_dict(baseline) == []

    def test_skips_missing_bank(self):
        baseline = {
            "members": {
                "David": {
                    "contas_bancarias": [
                        {"saldo_31_12": 100, "ano_base": 2025},  # sem banco
                    ]
                }
            }
        }
        assert BaselineAccountSaldo.from_baseline_dict(baseline) == []

    def test_skips_invalid_ano(self):
        baseline = {
            "members": {
                "David": {
                    "contas_bancarias": [
                        {"banco": "Itaú", "saldo_31_12": 100, "ano_base": "invalid"},
                    ]
                }
            }
        }
        assert BaselineAccountSaldo.from_baseline_dict(baseline) == []

    def test_multiple_members_multiple_accounts(self):
        baseline = {
            "members": {
                "David": {
                    "contas_bancarias": [
                        {"banco": "Itaú", "saldo_31_12": 100, "ano_base": 2025},
                        {"banco": "C6", "saldo_31_12": 200, "ano_base": 2025},
                    ]
                },
                "Carol": {
                    "contas_bancarias": [
                        {"banco": "Nubank", "saldo_31_12": 300, "ano_base": 2025},
                    ]
                },
            }
        }
        out = BaselineAccountSaldo.from_baseline_dict(baseline)
        assert len(out) == 3
        members = {e.member for e in out}
        assert members == {"David", "Carol"}

    def test_member_without_accounts_is_skipped(self):
        baseline = {
            "members": {
                "David": {"contas_bancarias": []},
                "Carol": {},  # nenhuma conta
            }
        }
        assert BaselineAccountSaldo.from_baseline_dict(baseline) == []

    def test_reference_date_is_31_12(self):
        acct = _bl_acct("Itaú", 2025, "100")
        assert acct.reference_date == date(2025, 12, 31)


# =============================================================================
# BaselineValidator — sem warnings
# =============================================================================


class TestBaselineValidatorNoWarnings:
    def _svc(self) -> BaselineValidator:
        return BaselineValidator(
            BaselineValidatorConfig(tolerance_amount=Decimal("1.00")),
            BankCanonicalizer.from_institutions(INSTITUTIONS),
        )

    def test_empty_inputs(self):
        assert self._svc().validate([], []) == []

    def test_no_baseline_no_warnings(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "1000")]
        assert self._svc().validate(stmts, []) == []

    def test_no_statements_no_warnings(self):
        bl = [_bl_acct("Itaú", 2025, "1000")]
        assert self._svc().validate([], bl) == []

    def test_matching_saldos_no_warning(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "1000")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        assert self._svc().validate(stmts, bl) == []

    def test_diff_within_tolerance_no_warning(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "1000.50")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        # diff = 0.50 ≤ 1.00 → no warning
        assert self._svc().validate(stmts, bl) == []

    def test_statement_not_on_31_12(self):
        """Extrato termina em outra data — não compara."""
        stmts = [_stmt("Itaú", date(2025, 11, 30), "1000")]
        bl = [_bl_acct("Itaú", 2025, "9999")]
        assert self._svc().validate(stmts, bl) == []

    def test_missing_closing_balance_skipped(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), None)]
        bl = [_bl_acct("Itaú", 2025, "9999")]
        assert self._svc().validate(stmts, bl) == []

    def test_different_bank_no_compare(self):
        stmts = [_stmt("Nubank", date(2025, 12, 31), "1000")]
        bl = [_bl_acct("Itaú", 2025, "5000")]
        assert self._svc().validate(stmts, bl) == []


# =============================================================================
# BaselineValidator — com warnings
# =============================================================================


class TestBaselineValidatorWarnings:
    def _svc(self, tol: str = "1.00") -> BaselineValidator:
        return BaselineValidator(
            BaselineValidatorConfig(tolerance_amount=Decimal(tol)),
            BankCanonicalizer.from_institutions(INSTITUTIONS),
        )

    def test_diff_above_tolerance_generates_warning(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "900")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        warns = self._svc().validate(stmts, bl)
        assert len(warns) == 1
        assert warns[0].diff == Money.brl("100")
        assert warns[0].baseline_saldo == Money.brl("1000")
        assert warns[0].statement_closing == Money.brl("900")

    def test_warning_has_reference_date(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "900")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        warns = self._svc().validate(stmts, bl)
        assert warns[0].reference_date == date(2025, 12, 31)

    def test_warning_account_key_uses_lowercase_institution(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "900")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        warns = self._svc().validate(stmts, bl)
        inst, member, currency = warns[0].account_key
        assert inst == "itaú"
        assert currency == "BRL"

    def test_percent_diff_calc(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "900")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        warns = self._svc().validate(stmts, bl)
        # 100 / 1000 = 10%
        assert warns[0].percent_diff == Decimal("10")

    def test_percent_diff_zero_baseline_is_infinity(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "5")]
        bl = [_bl_acct("Itaú", 2025, "0")]
        warns = self._svc().validate(stmts, bl)
        assert warns[0].percent_diff.is_infinite()

    def test_format_contains_key_fields(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "900")]
        bl = [_bl_acct("Itaú", 2025, "1000", member="David")]
        warns = self._svc().validate(stmts, bl)
        msg = warns[0].format()
        assert "2025-12-31" in msg
        assert "David" in msg
        assert "900.00" in msg
        assert "1000.00" in msg

    def test_canonical_match_display_vs_code(self):
        """Baseline diz "Itaú", extrato diz "itau" — canonicalização junta."""
        stmts = [_stmt("itau", date(2025, 12, 31), "900")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        warns = self._svc().validate(stmts, bl)
        assert len(warns) == 1

    def test_avoids_substring_false_positive(self):
        """Fix 4.4: sem canonicalizer, ``"c6"`` poderia casar com strings
        contendo ``"c6"``. Com canonicalizer, bate apenas ``"c6bank"``.
        """
        stmts = [_stmt("C6 Bank", date(2025, 12, 31), "500")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        warns = self._svc().validate(stmts, bl)
        assert warns == []

    def test_multiple_diffs(self):
        stmts = [
            _stmt("Itaú", date(2025, 12, 31), "900"),
            _stmt("C6 Bank", date(2025, 12, 31), "100", member="carol"),
        ]
        bl = [
            _bl_acct("Itaú", 2025, "1000", member="David"),
            _bl_acct("C6 Bank", 2025, "200", member="Carol"),
        ]
        warns = self._svc().validate(stmts, bl)
        assert len(warns) == 2

    def test_custom_tolerance_suppresses_warning(self):
        stmts = [_stmt("Itaú", date(2025, 12, 31), "900")]
        bl = [_bl_acct("Itaú", 2025, "1000")]
        # diff = 100 ≤ 200 → no warning
        assert self._svc(tol="200").validate(stmts, bl) == []


# =============================================================================
# validate_grouped
# =============================================================================


class TestBaselineValidatorGrouped:
    def _svc(self) -> BaselineValidator:
        return BaselineValidator(
            BaselineValidatorConfig(tolerance_amount=Decimal("1.00")),
            BankCanonicalizer.from_institutions(INSTITUTIONS),
        )

    def test_grouped_by_account_key(self):
        stmts = [
            _stmt("Itaú", date(2025, 12, 31), "900", member="david"),
            _stmt("Itaú", date(2024, 12, 31), "400", member="david"),
        ]
        bl = [
            _bl_acct("Itaú", 2025, "1000"),
            _bl_acct("Itaú", 2024, "500"),
        ]
        grouped = self._svc().validate_grouped(stmts, bl)
        # Mesma conta (itau/david/BRL) → 2 warnings sob a mesma chave.
        assert len(grouped) == 1
        (only_key,) = grouped.keys()
        assert only_key == ("itaú", "david", "BRL")
        assert len(grouped[only_key]) == 2

    def test_grouped_empty_when_no_warnings(self):
        assert self._svc().validate_grouped([], []) == {}


# =============================================================================
# ISP / Zero I/O contracts
# =============================================================================


class TestISPContract:
    def test_accepts_none_canonicalizer_degrades_gracefully(self):
        """Sem canonicalizer, ``BankCanonicalizer.empty()`` é usado — match
        estrito por forma normalizada.
        """
        svc = BaselineValidator()  # default config + empty canonicalizer
        stmts = [_stmt("itau", date(2025, 12, 31), "900")]
        bl = [_bl_acct("itau", 2025, "1000")]
        # Mesma forma normalizada → casa mesmo sem canonicalizer.
        assert len(svc.validate(stmts, bl)) == 1

    def test_empty_canonicalizer_misses_display_variant(self):
        """Sem canonicalizer, "Itaú" ≠ "itau" após normalização.

        Normalização é idêntica nos dois (``itau``), então casa. Esse é o
        fallback — pior caso é "banco X" ≠ "banco y" (capitalização
        extrema + typo).
        """
        svc = BaselineValidator()
        stmts = [_stmt("Itaú", date(2025, 12, 31), "900")]
        bl = [_bl_acct("itau", 2025, "1000")]
        # ``_normalize("Itaú") == _normalize("itau") == "itau"`` → match.
        assert len(svc.validate(stmts, bl)) == 1

    def test_no_path_in_public_api(self):
        import inspect

        sig = inspect.signature(BaselineValidator.validate)
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            assert "Path" not in str(param.annotation)
