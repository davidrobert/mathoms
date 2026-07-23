"""A38.l5 — TypeRule cdbdetalhes não pode roubar extrato de conta com linha CDB."""

from __future__ import annotations

from backend.app.services.classification.type_classifier import detect_type_by_content

_EXTRATO_CONTA_COM_CDB = (
    "DAVID agência: 9652 conta: 12345-6\n"
    "extrato conta / lançamentos\n"
    "período de visualização: 01/07/2025 até 31/12/2025\n"
    "data lançamentos valor (R$) saldo (R$)\n"
    "03/07/2025 APLICACAO CDB COFRINHOS -100,00\n"
    "03/07/2025 SALDO DO DIA 1.600,00\n"
    "11/07/2025 SISPAG EMPRESA LTDA 1.000,00\n"
)

_CDB_MOVIMENTACAO_ITAU = (
    "Extrato de movimentação mensal - CDB-DI\n"
    "Dados da conta: Nome: DAVID  Agência:9652 Conta:12345-6\n"
    "Período: 01/07/2026 à 22/07/2026\n"
    "30/06/2026 SALDO ANTERIOR 10.000,00\n"
    "Rentab. no período(%) Data aplicação Data vencimento\n"
    "22/07/2026 SALDO FINAL 10.050,00\n"
)

_CDB_DETALHES_SANTANDER = (
    "DETALHES DO INVESTIMENTO\n"
    "CDB DI SANTANDER Valor Total : R$ 5.000,00 Disponível para Resgate : R$ 5.000,00\n"
    "Você possui 1 contrato neste investimento\n"
)


def test_extrato_conta_com_linha_cdb_nao_vira_cdbdetalhes() -> None:
    """Regressão A38.l5: 'APLICACAO CDB' num extrato de conta → extratoconta, não cdbdetalhes."""
    rule, _, _ = detect_type_by_content(_EXTRATO_CONTA_COM_CDB)
    assert rule is not None and rule.code == "extratoconta"


def test_cdb_movimentacao_itau_continua_cdbdetalhes() -> None:
    """Não regride: movimentação de CDB (SALDO ANTERIOR/FINAL, sem SALDO DO DIA) segue cdbdetalhes."""
    rule, _, _ = detect_type_by_content(_CDB_MOVIMENTACAO_ITAU)
    assert rule is not None and rule.code == "cdbdetalhes"


def test_cdb_detalhes_santander_continua_cdbdetalhes() -> None:
    rule, _, _ = detect_type_by_content(_CDB_DETALHES_SANTANDER)
    assert rule is not None and rule.code == "cdbdetalhes"
