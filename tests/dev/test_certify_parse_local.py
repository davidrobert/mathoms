"""A38.l1 + harness ext — máscara PII, veredito e regras de comparação."""

from __future__ import annotations

import hashlib
from pathlib import Path

from dev.certify_parse_local import (
    _MONEY_RE,
    _fill_parse_metrics,
    _run_compare,
    compare_records,
    conservation_status,
    content_digest,
    file_digest,
    mask_text,
    stored_prefix,
)


def test_stored_prefix_extracts_adr084_identity() -> None:
    assert stored_prefix("29d69a0bb52b_c6bank_extratoconta_202606-0_original.csv") == "29d69a0bb52b"
    assert stored_prefix("sem_prefixo_valido.pdf") is None
    assert stored_prefix("29D69A0BB52B_uppercase.pdf") is None  # prefixo é lowercase hex


def test_content_digest_is_sha256_of_bytes(tmp_path) -> None:
    f = tmp_path / "extrato.pdf"
    f.write_bytes(b"conteudo-do-extrato")
    assert content_digest(f) == hashlib.sha256(b"conteudo-do-extrato").hexdigest()


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


def test_file_digest_is_pii_safe_and_stable() -> None:
    name = "extrato_joao_silva_2025.pdf"
    digest = file_digest(name)
    assert "joao" not in digest and "silva" not in digest
    assert digest == file_digest(name)  # estável
    assert len(digest) == 12


def _rec(**overrides):
    base = {"file": "doc.pdf", "n_tx": 10, "conservacao": True, "parser": "parse_x"}
    base.update(overrides)
    return base


def test_compare_flags_n_tx_decrease_as_regression() -> None:
    regressions, _ = compare_records([_rec(n_tx=5)], [_rec(n_tx=10)])
    assert len(regressions) == 1 and "n_tx" in regressions[0]


def test_compare_flags_conservation_and_parser_loss() -> None:
    # parser vira None (perda determinística por-doc) + conservação passa->falha
    current = [_rec(conservacao=False, parser=None)]
    regressions, _ = compare_records(current, [_rec()])
    assert any("conservação" in r for r in regressions)
    assert any("parser" in r for r in regressions)


def test_compare_flags_escalation_to_broken_conservation_as_silence() -> None:
    current = [_rec(escalated=False, conservacao=False)]
    baseline = [_rec(escalated=True, conservacao=True)]
    regressions, _ = compare_records(current, baseline)
    assert any("SILÊNCIO" in r for r in regressions)


def test_compare_accepts_improvement_and_reports_change() -> None:
    regressions, changes = compare_records(
        [_rec(n_tx=20, doc_type="extratoconta")], [_rec(n_tx=10, doc_type="cdbdetalhes")]
    )
    assert regressions == []
    assert any("doc_type" in c for c in changes)


# --- Ratchet do contrato de completude (#1080 · W0) ---


def test_compare_flags_fatura_checksum_downgrade() -> None:
    regs, _ = compare_records(
        [_rec(fatura_checksum_status="mismatch")], [_rec(fatura_checksum_status="passou")]
    )
    assert any("fatura_checksum" in r for r in regs)


def test_compare_flags_fatura_checksum_passou_to_faltando() -> None:
    regs, _ = compare_records(
        [_rec(fatura_checksum_status="faltando")], [_rec(fatura_checksum_status="passou")]
    )
    assert any("fatura_checksum" in r for r in regs)


def test_compare_flags_new_uncovered_scope_as_silence() -> None:
    regs, _ = compare_records([_rec(scopes_uncovered=["exterior"])], [_rec(scopes_uncovered=[])])
    assert any("SILÊNCIO" in r and "exterior" in r for r in regs)


def test_compare_flags_conservacao_verificavel_decertification() -> None:
    regs, _ = compare_records(
        [_rec(conservacao_verificavel=False)], [_rec(conservacao_verificavel=True)]
    )
    assert any("des-certificação" in r for r in regs)


def test_compare_accepts_faltando_to_passou_improvement() -> None:
    # faltando -> passou é melhoria (checksum passou a existir e fechar), não regressão.
    regs, _ = compare_records(
        [_rec(fatura_checksum_status="passou")], [_rec(fatura_checksum_status="faltando")]
    )
    assert regs == []


def test_run_compare_missing_baseline_errs_clean(tmp_path: Path) -> None:
    # baseline ausente não crasha (exit 2), não é falso "0 regressões"
    assert _run_compare([_rec()], tmp_path / "inexistente.json") == 2


def test_conservation_status_none_without_saldos() -> None:
    assert conservation_status({"transacoes": [{"valor": 1.0}]}) is None


def test_conservation_status_checks_sum_in_cents() -> None:
    ok = {"saldo_inicial": 10.0, "saldo_final": 15.5, "transacoes": [{"valor": 5.5}]}
    bad = {"saldo_inicial": 10.0, "saldo_final": 20.0, "transacoes": [{"valor": 5.5}]}
    assert conservation_status(ok) is True
    assert conservation_status(bad) is False


def test_fill_parse_metrics_emits_per_type_fields() -> None:
    result = {
        "tipo": "cdbresumo",
        "posicoes": [{"valor_atual": 1.0}, {"valor_atual": 2.0}],
        "itens": [],
        "transacoes": [],
        "raw_rows_detected": 7,
        "requires_llm_fallback": True,
        "escalation_reason": {"code": "extract.investment_sum_mismatch"},
        "saldo_atual": 3.0,
        "data_vencimento": "2025-01-10",
    }
    rec = _fill_parse_metrics({"file": "x"}, result)
    assert rec["tipo"] == "cdbresumo"
    assert rec["n_posicoes"] == 2 and rec["n_itens"] == 0
    assert rec["raw_rows_detected"] == 7
    assert rec["escalated"] is True
    assert rec["escalation_code"] == "extract.investment_sum_mismatch"
    assert rec["total_set"] is True and rec["vencimento_set"] is True
