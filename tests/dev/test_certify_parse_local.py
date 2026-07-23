"""A38.l1 — máscara PII e regras de comparação do harness de certificação local."""

from __future__ import annotations

from dev.certify_parse_local import (
    _MONEY_RE,
    compare_records,
    conservation_status,
    mask_text,
)


def test_mask_removes_monetary_cpf_and_long_numbers() -> None:
    raw = "saldo 1.234,56 conta 1234567890 cpf 123.456.789-01 e -12,34"
    masked = mask_text(raw)
    assert "1.234,56" not in masked
    assert "1234567890" not in masked
    assert "123.456.789-01" not in masked
    assert not _MONEY_RE.search(masked)
    assert "<VAL>" in masked and "<NUM>" in masked and "<CPF>" in masked


def test_mask_filename_hides_account_ids() -> None:
    assert "119327445" not in mask_text("statement_119327445_USD_2025.pdf")


def _rec(**overrides):
    base = {"file": "doc.pdf", "n_tx": 10, "conservacao": True, "parser": "parse_x"}
    base.update(overrides)
    return base


def test_compare_flags_n_tx_decrease_as_regression() -> None:
    regressions, _ = compare_records([_rec(n_tx=5)], [_rec(n_tx=10)])
    assert len(regressions) == 1 and "n_tx" in regressions[0]


def test_compare_flags_conservation_and_parser_loss() -> None:
    current = [_rec(conservacao=False, parser=None)]
    regressions, _ = compare_records(current, [_rec()])
    assert len(regressions) == 2


def test_compare_accepts_improvement_and_reports_change() -> None:
    regressions, changes = compare_records(
        [_rec(n_tx=20, doc_type="extratoconta")], [_rec(n_tx=10, doc_type="cdbdetalhes")]
    )
    assert regressions == []
    assert any("doc_type" in c for c in changes)


def test_conservation_status_none_without_saldos() -> None:
    assert conservation_status({"transacoes": [{"valor": 1.0}]}) is None


def test_conservation_status_checks_sum_in_cents() -> None:
    ok = {"saldo_inicial": 10.0, "saldo_final": 15.5, "transacoes": [{"valor": 5.5}]}
    bad = {"saldo_inicial": 10.0, "saldo_final": 20.0, "transacoes": [{"valor": 5.5}]}
    assert conservation_status(ok) is True
    assert conservation_status(bad) is False
