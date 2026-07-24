#!/usr/bin/env python3
"""A39.l4 — C6 PDF BRL: saldo_inicial vinha da âncora bruta `Saldo do dia` do 1º
dia (que já inclui as tx do dia) → conservação nunca fechava. `_c6_summarize_saldos`
subtrai o Σ do 1º dia (semântica do Itaú 2026), recuperando a abertura real,
sem ser tautológico (usa a âncora observada, não saldo_final − Σtx)."""

from __future__ import annotations

from scripts.e2.banks.c6bank import (
    _c6_anchor_date_to_iso,
    _c6_summarize_saldos,
    _parse_c6_extrato_text,
)

# Abertura real = 10.000; dia 05 fecha em 9.550 (−450); dia 20 fecha em 14.550 (+5.000).
_TEXT = (
    "05/01 05/01 Saída PIX Mercado -R$ 450,00\n"
    "Saldo do dia 05/01/25 R$ 9.550,00\n"
    "20/01 20/01 Entrada PIX Salario R$ 5.000,00\n"
    "Saldo do dia 20/01/25 R$ 14.550,00\n"
)


def test_anchor_date_para_iso():
    assert _c6_anchor_date_to_iso("05/01/25") == "2025-01-05"
    assert _c6_anchor_date_to_iso("22/04/26") == "2026-04-22"
    assert _c6_anchor_date_to_iso("lixo") is None


def test_summarize_recupera_abertura_e_conserva():
    txs, saldos = _parse_c6_extrato_text(_TEXT, "2025-01-01", "2025-01-31")
    si, sf = _c6_summarize_saldos(txs, saldos)
    assert si == 10000.0  # âncora 9550 − (−450) do 1º dia
    assert sf == 14550.0
    # conservação fecha em cents
    soma = sum(t["valor"] for t in txs)
    assert round(si + soma, 2) == sf


def test_summarize_sem_saldos_retorna_none():
    assert _c6_summarize_saldos([], []) == (None, None)
