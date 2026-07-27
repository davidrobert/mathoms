"""A39.l3 + ADR-342 emenda 2026-07-27 — _apply_fatura_checksum é escopo-aware E
valida COBERTURA de escopo: soma só as tx cujo `escopo` casa `signal.escopo`, e
exige que todo escopo presente nas tx (exceto `pagamento`, transferência interna)
seja coberto por algum sinal declarado. Sem a cobertura, tx num escopo sem sinal
(ex.: exterior não-lido, `escopo=None`) escapava de TODA soma e o checksum passava
verde parcial (falso-verde) — o modo de falha que o gate existe para matar."""

from __future__ import annotations

from scripts.e2.validation import _apply_fatura_checksum


def _fatura(transacoes, valor_cents, escopo="despesa_brasil"):
    return {
        "transacoes": transacoes,
        "total_lancamentos_conferivel": {"valor_cents": valor_cents, "escopo": escopo},
    }


def test_soma_so_o_subconjunto_do_escopo() -> None:
    # Cada escopo tem seu sinal; pagamento é isento → todos cobertos, sem WARN.
    r = {
        "transacoes": [
            {"valor": 100.0, "escopo": "despesa_brasil"},
            {"valor": 50.0, "escopo": "despesa_brasil"},
            {"valor": -200.0, "escopo": "pagamento"},
            {"valor": 300.0, "escopo": "exterior"},
        ],
        "total_lancamentos_conferivel": [
            {"valor_cents": 15000, "escopo": "despesa_brasil"},
            {"valor_cents": 30000, "escopo": "exterior"},
        ],
    }
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert issues == []
    assert r["fatura_checksum"]["status"] == "passou"
    assert r["fatura_checksum"]["scopes_uncovered"] == []


def test_mismatch_no_escopo_dispara_warn() -> None:
    r = _fatura([{"valor": 100.0, "escopo": "despesa_brasil"}], valor_cents=20000)
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert any("Σ lançamentos" in i for i in issues)
    assert r["fatura_checksum"]["status"] == "mismatch"


def test_sem_signal_status_faltando() -> None:
    r = {"transacoes": [{"valor": 100.0, "escopo": "despesa_brasil"}]}
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert issues == []
    assert r["fatura_checksum"]["status"] == "faltando"
    assert r["fatura_checksum"]["scopes_uncovered"] == []


# --- Invariante de cobertura de escopo (F6, emenda ADR-342 2026-07-27) ---


def test_escopo_exterior_sem_sinal_dispara_scope_uncovered() -> None:
    # despesa_brasil fecha, MAS há tx exterior sem sinal exterior → falso-verde que
    # o invariante mata: WARN de cobertura + escopo listado em scopes_uncovered.
    r = _fatura(
        [
            {"valor": 100.0, "escopo": "despesa_brasil"},
            {"valor": 300.0, "escopo": "exterior"},
        ],
        valor_cents=10000,  # só despesa_brasil declarada — e ela fecha
    )
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert any("cobertura de checksum incompleta" in i for i in issues)
    assert r["fatura_checksum"]["scopes_uncovered"] == ["exterior"]
    # Σ despesa_brasil casa → status "passou", mas cobertura incompleta ⇒ NÃO completo.
    codes = [rr["code"] for rr in r.get("warn_reasons", [])]
    assert "extract.fatura_scope_uncovered" in codes


def test_escopo_none_conta_como_uncovered() -> None:
    r = _fatura(
        [{"valor": 100.0, "escopo": "despesa_brasil"}, {"valor": 50.0}],
        valor_cents=10000,
    )
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert "None" in r["fatura_checksum"]["scopes_uncovered"]


def test_pagamento_isento_nao_dispara_uncovered() -> None:
    r = _fatura(
        [
            {"valor": 100.0, "escopo": "despesa_brasil"},
            {"valor": -200.0, "escopo": "pagamento"},
        ],
        valor_cents=10000,
    )
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert issues == []
    assert r["fatura_checksum"]["scopes_uncovered"] == []
    assert r["fatura_checksum"]["status"] == "passou"
