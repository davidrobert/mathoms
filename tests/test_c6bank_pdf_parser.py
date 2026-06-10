"""Unit tests para `_parse_c6_extrato_text` — helper line-based do parser C6 PDF."""

from __future__ import annotations

from scripts.e2.banks.c6bank import _parse_c6_extrato_text

_REGRESSION_TEXT = (
    "22/04 22/04 Pagamento Itau Unibanco S/A -R$ 194.886,65\n"
    "22/04 22/04 Saída PIX Pix enviado para Eliane Costa Goncalves -R$ 230,00\n"
    "Saldo do dia 22/04/26 R$ 10.052,70\n"
)


def test_duas_transacoes_mesmo_dia_nao_se_misturam():
    """Regressão: 2 txs no mesmo dia viravam 1 franquenstein com `extract_tables()`."""
    txs, _ = _parse_c6_extrato_text(_REGRESSION_TEXT, "2026-04-01", "2026-04-30")
    assert len(txs) == 2
    assert txs[0] == {
        "data": "2026-04-22",
        "descricao": "Itau Unibanco S/A",
        "valor": -194886.65,
    }
    assert txs[1] == {
        "data": "2026-04-22",
        "descricao": "Pix enviado para Eliane Costa Goncalves",
        "valor": -230.00,
    }


def test_saldo_acompanha_transacoes_do_mesmo_dia():
    _, saldos = _parse_c6_extrato_text(_REGRESSION_TEXT, "2026-04-01", "2026-04-30")
    assert saldos == [("22/04/26", 10052.70)]


def test_entrada_pix_valor_positivo():
    text = "22/04 22/04 Entrada PIX Pix recebido de DAVID CAMPOS R$ 50.000,00\n"
    txs, _ = _parse_c6_extrato_text(text, "2026-04-01", "2026-04-30")

    assert len(txs) == 1
    assert txs[0]["valor"] == 50000.0
    assert txs[0]["descricao"] == "Pix recebido de DAVID CAMPOS"
    assert "tipo_lancamento" not in txs[0]


def test_global_usd_valores_assinados():
    text = (
        "31/07 29/07 Débito de cartão Bass Pro Store Orlando -US$ 17,56\n"
        "30/07 28/07 Débito de cartão Walgreens -US$ 10,18\n"
    )
    txs, _ = _parse_c6_extrato_text(text, "2025-07-01", "2025-07-31")

    assert len(txs) == 2
    assert all(t["valor"] is not None and t["valor"] < 0 for t in txs)
    assert txs[0]["valor"] == -17.56


def test_descricao_vazia_ok():
    """`04/05 04/05 Saída PIX -R$ 1.950,00` — sem destinatário visível."""
    text = "04/05 04/05 Saída PIX -R$ 1.950,00\n"
    txs, _ = _parse_c6_extrato_text(text, "2026-05-01", "2026-05-31")

    assert len(txs) == 1
    assert txs[0]["descricao"] == ""
    assert txs[0]["valor"] == -1950.0


def test_saldo_do_dia_isolado():
    text = "Saldo do dia 22/04/26 R$ 10.052,70\nSaldo do dia 23/04/26 R$ 11.702,70\n"
    txs, saldos = _parse_c6_extrato_text(text, "2026-04-01", "2026-04-30")

    assert txs == []
    assert saldos == [("22/04/26", 10052.70), ("23/04/26", 11702.70)]


def test_linhas_ruido_ignoradas():
    text = (
        "Banco C6 S.A. CNPJ: 31.872.495/0001-72\n"
        "Período • 1 de abril de 2026 até 30 de abril de 2026\n"
        "22/04 22/04 Pagamento Itau Unibanco S/A -R$ 194.886,65\n"
        "Pagina 1 de 16\n"
    )
    txs, _ = _parse_c6_extrato_text(text, "2026-04-01", "2026-04-30")
    assert len(txs) == 1


def test_descricao_multilinha_wrap_concat():
    """Linha tail (não-data, não-saldo, não-ruído) concatena na descrição anterior."""
    text = (
        "22/04 22/04 Pagamento BOLETO RECEITA FEDERAL DARF -R$ 5.173,85\n"
        "REF NUMERO 12345-67 EXERCICIO 2026\n"
    )
    txs, _ = _parse_c6_extrato_text(text, "2026-04-01", "2026-04-30")
    assert len(txs) == 1
    assert txs[0]["descricao"] == ("BOLETO RECEITA FEDERAL DARF REF NUMERO 12345-67 EXERCICIO 2026")
    assert txs[0]["valor"] == -5173.85


def test_descricao_nao_concatena_cabecalho_pagina():
    """Linha de cabeçalho/rodapé não vira tail da descrição da transação
    anterior — protege contra concat de ruído (Pagina X de Y, etc.)."""
    text = (
        "22/04 22/04 Pagamento Itau Unibanco S/A -R$ 194.886,65\n"
        "Pagina 14 de 16\n"
        "Banco C6 S.A.\n"
        "CNPJ: 31.872.495/0001-72\n"
    )
    txs, _ = _parse_c6_extrato_text(text, "2026-04-01", "2026-04-30")
    assert len(txs) == 1
    assert txs[0]["descricao"] == "Itau Unibanco S/A"


# Header `"Data Data Tipo Descrição Valor lançamento contábil"` repete no topo
# de cada página do extrato PDF C6 conta-corrente. Não pode vazar como wrap da
# descrição da transação anterior (bug observado em prod 2026-05-24, workspace
# 1b9f2cf5: 5 PIXes Arvo R$ 46k+ duplicados quebrando dedup K4 ADR-255).
_TABLE_HEADER_TEXT = (
    "28/11 28/11 Entrada PIX Pix recebido de ARVO SAUDE LTDA R$ 46.624,29\n"
    "Data Data Tipo Descrição Valor lançamento contábil\n"
    "29/12 29/12 Entrada PIX Pix recebido de ARVO SAUDE LTDA R$ 46.624,29\n"
)


def test_descricao_nao_concatena_cabecalho_tabela():
    txs, _ = _parse_c6_extrato_text(_TABLE_HEADER_TEXT, "2025-11-01", "2025-12-31")
    assert len(txs) == 2
    for tx in txs:
        assert "Data Data" not in tx["descricao"], tx["descricao"]
        assert "lançamento contábil" not in tx["descricao"]
    assert txs[0]["descricao"] == "Pix recebido de ARVO SAUDE LTDA"
    assert txs[1]["descricao"] == "Pix recebido de ARVO SAUDE LTDA"


def test_outros_gastos_e_resgate():
    """Tipos menos comuns precisam ser reconhecidos via prefix match — o split
    tipo/descrição segue interno ao parser (limpa a descrição); o campo
    `tipo_lancamento` não é mais emitido (de-leak ADR-280, A24.l3)."""
    text = (
        "26/04 27/04 Outros gastos C6TAG ESTACIONAMENTO -R$ 22,00\n"
        "22/04 22/04 Entradas RESGATE DE CDB R$ 2.587,91\n"
    )
    txs, _ = _parse_c6_extrato_text(text, "2026-04-01", "2026-04-30")
    assert len(txs) == 2
    assert txs[0]["descricao"] == "C6TAG ESTACIONAMENTO"
    assert txs[1]["descricao"] == "RESGATE DE CDB"
    assert all("tipo_lancamento" not in tx for tx in txs)
