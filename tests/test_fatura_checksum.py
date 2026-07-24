"""ADR-342 §Emenda 2026-07-23 — checksum de fatura (WARN-first, opt-in por sinal)."""

from __future__ import annotations

from pathlib import Path

from scripts.e2.validation import validate_fatura_result


def _fatura(transacoes, signal=None):
    r = {
        "saldo_atual": 500.0,
        "data_vencimento": "2026-04-10",
        "transacoes": transacoes,
        "itens": [],
    }
    if signal is not None:
        r["total_lancamentos_conferivel"] = signal
    return r


def test_no_signal_is_noop() -> None:
    # sem total_lancamentos_conferivel, o gate de fatura não roda (mecanismo dormente)
    r = validate_fatura_result(_fatura([{"valor": 100.0}]), "itau_fatura_202604.pdf")
    assert not any("checksum de fatura" in n for n in r["notas"])
    assert not r.get("requires_llm_fallback")


def test_signal_match_no_warn() -> None:
    # A39.l3: gate escopo-aware — as tx carregam o mesmo `escopo` do signal.
    r = validate_fatura_result(
        _fatura(
            [
                {"valor": 100.0, "escopo": "brl_compras"},
                {"valor": 50.5, "escopo": "brl_compras"},
            ],
            {"valor_cents": 15050, "escopo": "brl_compras"},
        ),
        "itau_fatura_202604.pdf",
    )
    assert not any("checksum de fatura" in n for n in r["notas"])


def test_signal_mismatch_warns_but_does_not_escalate() -> None:
    r = validate_fatura_result(
        _fatura([{"valor": 100.0}], {"valor_cents": 20000, "escopo": "brl_compras"}),
        "itau_fatura_202604.pdf",
    )
    assert any("checksum de fatura" in n for n in r["notas"])
    assert any(wr["code"] == "extract.fatura_total_mismatch" for wr in r.get("warn_reasons", []))
    # WARN-first: NÃO escala (não flippa requires_llm_fallback)
    assert not r.get("requires_llm_fallback")


def test_never_compares_against_saldo_atual() -> None:
    # saldo_atual=500 mas total_compras declarado=100 e Σ=100 ⇒ fecha (não usa saldo_atual)
    r = validate_fatura_result(
        _fatura(
            [{"valor": 100.0, "escopo": "brl_compras"}],
            {"valor_cents": 10000, "escopo": "brl_compras"},
        ),
        "itau_fatura_202604.pdf",
    )
    assert not any("checksum de fatura" in n for n in r["notas"])
