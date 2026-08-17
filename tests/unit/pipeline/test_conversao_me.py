"""A40.l63 · ADR-390 — conversão ME→BRL carrega proveniência."""

from __future__ import annotations

import logging
from decimal import Decimal

from pipeline.domain.services.conversao_me import (
    FxQuote,
    HardcodedFxDefault,
    apply_fx,
    convert_me_brl,
    from_informe_entry,
    identity_already_brl,
    missing_rate,
    resolve_fx_input,
    warn_hardcoded,
)


def test_convert_stamps_quote():
    quote = FxQuote(rate=Decimal("6.00"), fonte="market_rate_corrente", observed_at="2026-04-27")
    conv = convert_me_brl(Decimal("1000"), "USD", quote)
    assert conv.valor_brl == Decimal("6000")
    assert conv.to_wire() == {
        "taxa": "6.00",
        "taxa_data": "2026-04-27",
        "taxa_fonte": "market_rate_corrente",
        "status": "converted",
    }


def test_irpf_identity_is_brl():
    conv = identity_already_brl("34433.67")
    assert conv.moeda == "BRL"
    assert conv.status == "identity"
    assert conv.taxa_fonte == "irpf_ja_em_brl"
    assert conv.taxa is None
    assert conv.valor_brl == Decimal("34433.67")


def test_gbp_without_quote_is_missing_rate():
    conv = apply_fx(Decimal("100"), "GBP", None)
    assert conv.status == "missing_rate"
    assert conv.valor_brl is None
    assert conv.moeda == "GBP"


def test_hardcoded_is_named_not_silent():
    default = HardcodedFxDefault.usd_brl()
    conv = apply_fx(Decimal("1000"), "USD", default)
    assert conv.taxa_fonte == "default_hardcoded"
    assert conv.valor_brl == Decimal("5800.00")
    assert conv.taxa == Decimal("5.80")


def test_seed_rate_is_market_not_hardcoded():
    resolved = resolve_fx_input(
        "USD", typed_usd=None, typed_eur=None, taxas={"cambio_usd_brl": Decimal("5.80")}
    )
    assert isinstance(resolved, FxQuote)
    assert resolved.fonte == "market_rate_corrente"
    assert resolved.rate == Decimal("5.80")


def test_empty_config_resolves_to_named_hardcoded():
    resolved = resolve_fx_input("USD", typed_usd=None, typed_eur=None, taxas={})
    assert isinstance(resolved, HardcodedFxDefault)
    assert resolved.pair == "USD/BRL"


def test_gbp_has_no_hardcoded_default():
    assert HardcodedFxDefault.for_moeda("GBP") is None
    assert resolve_fx_input("GBP", typed_usd=None, typed_eur=None, taxas={}) is None


def test_informe_copy_does_not_remultiply():
    entry = {
        "moeda": "USD",
        "saldo_original": "5210.55",
        "saldo_brl": "32262.16",
        "taxa_ptax_aplicada": "6.1917",
        "ptax_data": "2024-12-31",
        "ptax_status": "applied",
    }
    conv = from_informe_entry(entry)
    assert conv.valor_brl == Decimal("32262.16")
    assert conv.taxa == Decimal("6.1917")
    assert conv.taxa_fonte == "ptax_31_12"
    assert conv.status == "converted"


def test_warn_hardcoded_has_no_money_in_extra(caplog):
    caplog.set_level(logging.WARNING, logger="mathoms.pipeline.conversao_me")
    warn_hardcoded("USD/BRL", 3)
    assert "fx_default_hardcoded" in caplog.text
    record = caplog.records[-1]
    assert record.par == "USD/BRL"
    assert record.n_linhas == 3
    assert not hasattr(record, "valor")
    assert not hasattr(record, "valor_brl")
