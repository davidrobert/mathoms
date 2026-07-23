"""A38.l15 — extração do extrato C6 Global (USD/EUR); layout distinto do BRL."""

from __future__ import annotations

from scripts.e2.banks.c6bank import _C6_GLOBAL_TX_RE, _parse_c6_global_text

# Fixture sintética PII-zero (USD): dois formatos de linha coexistem —
# débito de cartão com data de compra no fim, e entrada/saída sem data final.
_USD_TEXT = (
    "Extrato Período • 01 de julho de 2025 até 31 de julho de 2025\n"
    "Saldo do dia • 29 de março de 2026 • US$ 91,59\n"
    "Resumo das movimentações Entradas • US$ 137,33 • Saidas • US$ 39,12\n"
    "31/07 Débito de cartão -US$ 17,56 29/07\n"
    "30/07 Débito de cartão -US$ 21,56 28/07\n"
    "15/07 Entrada Outros US$ 10,73\n"
    "16/07 Entrada Transf C6 Conta Global Líquido US$ 126,60\n"
    "10/07 Saída Transf. Internacional -US$ 0,00\n"
    "cabeçalho sem transação\n"
)

_EUR_TEXT = (
    "Extrato Período • 01 de março de 2026 até 31 de março de 2026\n"
    "05/03 Débito de cartão -€ 12,00 03/03\n"
    "10/03 Entrada Outros € 500,00\n"
)


def test_c6_global_usd_extrai_debitos_e_entradas() -> None:
    txs = _parse_c6_global_text(_USD_TEXT, "2025-07-01", "2025-07-31")
    assert len(txs) == 5  # 2 débitos + 2 entradas + 1 saída; header ignorado
    negativos = [t for t in txs if t["valor"] < 0]
    positivos = [t for t in txs if t["valor"] > 0]
    assert len(negativos) == 2 and len(positivos) == 2  # a "Saída ... 0,00" não é <0
    assert round(sum(t["valor"] for t in positivos), 2) == 137.33  # bate o resumo Entradas
    assert txs[0]["data"] == "2025-07-31"
    assert "Débito de cartão" in txs[0]["descricao"]


def test_c6_global_eur() -> None:
    txs = _parse_c6_global_text(_EUR_TEXT, "2026-03-01", "2026-03-31")
    assert len(txs) == 2
    assert any(t["valor"] == 500.0 for t in txs)
    assert any(t["valor"] == -12.0 for t in txs)


def test_c6_global_locale_br_mesmo_em_usd() -> None:
    """`US$ 7.196,37` é 7196.37 (BR), não 7,196.37 → sem inversão de locale."""
    txs = _parse_c6_global_text("20/05 Entrada Outros US$ 7.196,37\n", "2025-05-01", "2025-05-31")
    assert txs[0]["valor"] == 7196.37


def test_c6_global_pattern_ignora_saldo_e_resumo() -> None:
    assert not _C6_GLOBAL_TX_RE.match("Saldo do dia • 29 de março de 2026 • US$ 91,59")
    assert not _C6_GLOBAL_TX_RE.match("Resumo das movimentações Entradas • US$ 137,33 • Saidas")
