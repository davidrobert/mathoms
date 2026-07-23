"""A38.l2 — unit tests do parser line-based do extrato Itaú layout 2026."""

from __future__ import annotations

from scripts.e2.banks.itau_extrato_2026 import (
    _drop_anchors_beyond_periodo,
    _drop_trailing_informational_anchor,
    is_itau_layout_2026,
    parse_extrato_2026_text,
    summarize_saldos,
)

_HEADER_2026 = (
    "FULANO DA SILVA 000.000.000-00 agência: 1234 conta: 56789-0\n"
    "extrato conta / lançamentos\n"
    "período de visualização: 01/01/2026 até 30/06/2026 emitido em: 22/07/2026 21:08:26\n"
    "data lançamentos valor (R$) saldo (R$)\n"
)

_HEADER_ANTIGO = (
    "Período: 01/04/2026 a 30/04/2026\n" "Conta: 56789-0\n" "Data Descrição Valor (R$) Saldo (R$)\n"
)

_CORPO = (
    "22/07/2026 SALDO DO DIA 1.550,00\n"
    "05/02/2026 REND PAGO APLIC AUT MAIS 10,00\n"
    "05/02/2026 SABESP 12345678 -60,00\n"
    "05/02/2026 SALDO DO DIA 1.550,00\n"
    "03/01/2026 APLICACAO CDB COFRINHOS -100,00\n"
    "03/01/2026 SISPAG EMPRESA LTDA 1.000,00\n"
    "03/01/2026 SALDO DO DIA 1.600,00\n"
)


def test_detecta_layout_2026_e_rejeita_antigo() -> None:
    assert is_itau_layout_2026(_HEADER_2026)
    assert is_itau_layout_2026(_HEADER_2026.upper())
    assert not is_itau_layout_2026(_HEADER_ANTIGO)


def test_extrai_todas_as_transacoes_com_sinal() -> None:
    txs, _ = parse_extrato_2026_text(_CORPO)
    assert len(txs) == 4
    assert [t["valor"] for t in txs] == [-100.0, 1000.0, 10.0, -60.0]
    assert txs[0]["data"] == "2026-01-03"
    assert txs[0]["descricao"] == "APLICACAO CDB COFRINHOS"


def test_saldo_do_dia_nunca_vira_transacao() -> None:
    txs, saldos = parse_extrato_2026_text(_CORPO)
    assert all("SALDO" not in t["descricao"].upper() for t in txs)
    assert len(saldos) == 3
    assert saldos[0] == ("2026-01-03", 1600.0)
    assert saldos[-1] == ("2026-07-22", 1550.0)


def test_saldo_inicial_desconta_txs_do_primeiro_dia() -> None:
    txs, saldos = parse_extrato_2026_text(_CORPO)
    saldo_inicial, saldo_final = summarize_saldos(txs, saldos)
    assert saldo_inicial == 700.0  # 1600 − (−100 + 1000)
    assert saldo_final == 1550.0


def test_conservacao_global_fecha_em_cents() -> None:
    txs, saldos = parse_extrato_2026_text(_CORPO)
    saldo_inicial, saldo_final = summarize_saldos(txs, saldos)
    soma = sum(t["valor"] for t in txs)
    assert abs((saldo_inicial + soma) - saldo_final) < 0.005


def test_conservacao_per_dia_entre_ancoras() -> None:
    txs, saldos = parse_extrato_2026_text(_CORPO)
    for (d_prev, s_prev), (d_next, s_next) in zip(saldos, saldos[1:]):
        delta = sum(t["valor"] for t in txs if d_prev < t["data"] <= d_next)
        assert abs((s_prev + delta) - s_next) < 0.005


def test_ancora_de_emissao_fora_do_periodo_descartada() -> None:
    """`SALDO DO DIA` da data de emissão (posterior ao fim do período) não pode
    virar saldo_final — movimentos entre o fim do período e a emissão não estão
    listados e a conservação quebraria por design."""
    _, saldos = parse_extrato_2026_text(_CORPO)
    kept = _drop_anchors_beyond_periodo(saldos, "2026-06-30")
    assert [d for d, _ in kept] == ["2026-01-03", "2026-02-05"]
    assert _drop_anchors_beyond_periodo(saldos, None) == saldos


def test_ancora_de_emissao_apos_ultima_tx_descartada() -> None:
    """Mesmo dentro do período, a âncora do dia da emissão (saldo atual) cai
    quando é posterior à última transação listada — o export não lista os
    movimentos dessa janela."""
    txs, saldos = parse_extrato_2026_text(_CORPO)
    kept = _drop_trailing_informational_anchor(saldos, txs)
    assert [d for d, _ in kept] == ["2026-01-03", "2026-02-05"]
    assert _drop_trailing_informational_anchor(saldos, []) == saldos


def test_linha_sem_valor_ou_sem_data_ignorada() -> None:
    txs, saldos = parse_extrato_2026_text("cabeçalho solto\n05/02/2026 PIX SEM VALOR\n")
    assert txs == [] and saldos == []


def _build_pdf_2026(path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    _, height = A4
    y = height - 2 * cm
    c.setFont("Helvetica", 9)
    for line in (_HEADER_2026 + _CORPO).splitlines():
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm
    c.save()


def test_parse_itau_despacha_layout_2026_end_to_end(tmp_path) -> None:
    """Fixture sintética do layout 2026 em CI (aceite A38.l2): dispatch +
    100% das linhas + conservação global em cents."""
    from scripts.e2.banks.itau import parse_itau

    pdf_path = tmp_path / "itau_extratoconta_202601_202606-0_original.pdf"
    _build_pdf_2026(pdf_path)
    result = parse_itau(pdf_path, pdf_path.name)

    assert len(result["transacoes"]) == 4
    assert result["periodo"] == {"inicio": "2026-01-01", "fim": "2026-06-30"}
    assert result["agencia"] == "1234"
    assert result["saldo_inicial"] == 700.0
    assert result["saldo_final"] == 1550.0
    soma = sum(t["valor"] for t in result["transacoes"])
    assert abs((result["saldo_inicial"] + soma) - result["saldo_final"]) < 0.005
