"""Tests — ``AccountGrouper`` (Fase 6 foundation · Sessão A1).

Cobre paridade com ``scripts/e3_reconcile.py::should_skip_extract`` (linha 219)
e ``get_account_key`` (linha 245).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.account_grouper import (  # noqa: E402
    AccountGrouper,
    AccountGrouperConfig,
    AccountKey,
)


# =============================================================================
# Helpers
# =============================================================================


def _conta(banco: str = "Itaú", tipo: str = "extratoconta", **extras) -> dict:
    base = {"banco": banco, "tipo": tipo, "moeda": "BRL"}
    base.update(extras)
    return base


# =============================================================================
# AccountKey
# =============================================================================


class TestAccountKey:
    def test_is_fatura_true_for_fatura_type(self) -> None:
        key = AccountKey(bank="Nubank", account_type="faturacarbon", currency=None)
        assert key.is_fatura is True

    def test_is_fatura_false_for_conta(self) -> None:
        key = AccountKey(bank="Itaú", account_type="extratoconta", currency="BRL")
        assert key.is_fatura is False

    def test_to_tuple_conta_includes_currency(self) -> None:
        key = AccountKey(bank="Itaú", account_type="extratoconta", currency="BRL")
        assert key.to_tuple() == ("Itaú", "extratoconta", "BRL")

    def test_to_tuple_fatura_excludes_currency(self) -> None:
        key = AccountKey(bank="Nubank", account_type="faturacarbon", currency=None)
        assert key.to_tuple() == ("Nubank", "faturacarbon")

    def test_account_key_is_hashable_for_dict_keys(self) -> None:
        a = AccountKey("Itaú", "extratoconta", "BRL")
        b = AccountKey("Itaú", "extratoconta", "BRL")
        d = {a: 1}
        assert d[b] == 1


# =============================================================================
# AccountGrouperConfig
# =============================================================================


class TestConfig:
    def test_from_pipeline_config_strips_comment_keys(self) -> None:
        family = {
            "account_type_equivalences": {
                "_comment": "comentário",
                "extratocontapersonnalite": "extratoconta",
            }
        }
        cfg = AccountGrouperConfig.from_pipeline_config(family=family)

        assert cfg.account_type_equivalences == {
            "extratocontapersonnalite": "extratoconta"
        }

    def test_from_pipeline_config_overrides_skip_types_when_present(self) -> None:
        pipeline = {"reconciliation": {"skip_types": ["custom_skip"]}}
        cfg = AccountGrouperConfig.from_pipeline_config(pipeline=pipeline)

        assert cfg.skip_types == frozenset({"custom_skip"})

    def test_from_pipeline_config_uses_defaults_when_absent(self) -> None:
        cfg = AccountGrouperConfig.from_pipeline_config()

        assert "investimentosposicao" in cfg.skip_types
        assert "irpf" in cfg.skip_types
        assert cfg.default_currency == "BRL"


# =============================================================================
# AccountGrouper.should_skip
# =============================================================================


class TestShouldSkip:
    def test_skips_non_dict(self) -> None:
        grouper = AccountGrouper()
        assert grouper.should_skip(None) is True
        assert grouper.should_skip("not a dict") is True
        assert grouper.should_skip([]) is True

    def test_skips_irpf(self) -> None:
        grouper = AccountGrouper()
        assert grouper.should_skip({"tipo": "irpf"}) is True

    def test_skips_investimentos(self) -> None:
        grouper = AccountGrouper()
        assert grouper.should_skip({"tipo": "investimentosposicao"}) is True
        assert grouper.should_skip({"tipo": "cdbdetalhes"}) is True

    def test_skips_disallowed_fatura(self) -> None:
        grouper = AccountGrouper()
        # "faturasecundaria" não está em fatura_allowed
        assert grouper.should_skip({"tipo": "faturasecundaria"}) is True

    def test_does_not_skip_allowed_fatura(self) -> None:
        grouper = AccountGrouper()
        for tipo in ("faturacarbon", "faturaunique", "faturapaoacucar"):
            assert grouper.should_skip({"tipo": tipo}) is False

    def test_does_not_skip_extratoconta(self) -> None:
        grouper = AccountGrouper()
        assert grouper.should_skip({"tipo": "extratoconta"}) is False

    def test_skips_via_equivalence(self) -> None:
        cfg = AccountGrouperConfig(
            account_type_equivalences={"alias_tipo": "irpf"},
        )
        grouper = AccountGrouper(cfg)
        # alias_tipo aponta para irpf que está em skip_types
        assert grouper.should_skip({"tipo": "alias_tipo"}) is True


# =============================================================================
# AccountGrouper.key
# =============================================================================


class TestKey:
    def test_returns_none_when_banco_missing(self) -> None:
        grouper = AccountGrouper()
        assert grouper.key({"tipo": "extratoconta"}) is None

    def test_returns_none_when_tipo_missing(self) -> None:
        grouper = AccountGrouper()
        assert grouper.key({"banco": "Itaú"}) is None

    def test_conta_uses_moeda_field(self) -> None:
        grouper = AccountGrouper()
        key = grouper.key(_conta(moeda="USD"))

        assert key == AccountKey("Itaú", "extratoconta", "USD")

    def test_conta_falls_back_to_nested_conta_moeda(self) -> None:
        grouper = AccountGrouper()
        data = {"banco": "Wise", "tipo": "extratoconta", "conta": {"moeda": "EUR"}}

        key = grouper.key(data)

        assert key == AccountKey("Wise", "extratoconta", "EUR")

    def test_conta_defaults_to_brl_when_moeda_absent(self) -> None:
        grouper = AccountGrouper()
        data = {"banco": "Itaú", "tipo": "extratoconta"}

        key = grouper.key(data)

        assert key == AccountKey("Itaú", "extratoconta", "BRL")

    def test_fatura_currency_is_none(self) -> None:
        grouper = AccountGrouper()
        data = {"banco": "Nubank", "tipo": "faturacarbon"}

        key = grouper.key(data)

        assert key == AccountKey("Nubank", "faturacarbon", None)
        assert key.is_fatura is True

    def test_normalizes_via_equivalences(self) -> None:
        cfg = AccountGrouperConfig(
            account_type_equivalences={"extratocontapersonnalite": "extratoconta"}
        )
        grouper = AccountGrouper(cfg)
        data = {"banco": "Itaú", "tipo": "extratocontapersonnalite", "moeda": "BRL"}

        key = grouper.key(data)

        # Mesmo banco + tipo equivalente devem agrupar com extratoconta normal.
        assert key == AccountKey("Itaú", "extratoconta", "BRL")

    def test_uses_instituicao_when_banco_absent(self) -> None:
        grouper = AccountGrouper()
        data = {"instituicao": "Bradesco", "tipo": "extratoconta", "moeda": "BRL"}

        key = grouper.key(data)

        assert key == AccountKey("Bradesco", "extratoconta", "BRL")

    def test_currency_normalized_to_uppercase(self) -> None:
        grouper = AccountGrouper()
        data = {"banco": "Wise", "tipo": "extratoconta", "moeda": "usd"}

        key = grouper.key(data)

        assert key.currency == "USD"

    def test_normalize_account_type_helper(self) -> None:
        cfg = AccountGrouperConfig(
            account_type_equivalences={"extratocontapersonnalite": "extratoconta"}
        )
        grouper = AccountGrouper(cfg)

        assert grouper.normalize_account_type("extratocontapersonnalite") == "extratoconta"
        assert grouper.normalize_account_type("unknown") == "unknown"
