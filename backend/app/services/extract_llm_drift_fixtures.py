"""Fixtures sintéticas PII-zero do drift nightly de ``extract_with_llm`` (A33.l5 · ADR-307 F2).

Mesma convenção de dado 100% inventado de ``tests/fixtures/pipeline_golden/``
(sem CPF, sem nome real, valores redondos fictícios). Vivem em módulo — não
em ``tests/`` — porque a imagem backend só embarca ``config/``, ``pipeline/``
e ``backend/`` e o job Celery precisa delas em runtime.

Expectativas são ESTRUTURAIS (shape/campos/contagem), não bit-exact:
drift de temperatura ≠ drift de contrato. Asserção de ``institution`` exata
só onde o código canônico consta do vocabulário do prompt (``e2_llm.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StructuralExpectation:
    """Contrato estrutural esperado do output LLM para uma fixture."""

    institution: Optional[str] = None  # None = exige apenas não-vazia (invariante A28.l8)
    currency: str = "BRL"
    min_transactions: int = 0
    max_transactions: Optional[int] = None
    min_investments: int = 0


@dataclass(frozen=True)
class DriftFixture:
    """Documento sintético + expectativa estrutural — 1 trial por noite."""

    fixture_id: str
    filename: str
    document_text: str
    expect: StructuralExpectation


_EXTRATO_C6BANK = """\
C6 BANK S.A. — EXTRATO DE CONTA CORRENTE
Titular: CLIENTE SINTETICO EXEMPLO
Agência 0001 · Conta 12345-6
Período: 01/03/2026 a 31/03/2026

Data        Descrição                              Valor        Saldo
05/03/2026  TED RECEBIDA EMPRESA EXEMPLO LTDA    +5.000,00    6.234,56
10/03/2026  PIX ENVIADO SUPERMERCADO MODELO        -350,25    5.884,31
15/03/2026  PAGAMENTO CONTA DE LUZ ENERGIA SA      -180,00    5.704,31
22/03/2026  COMPRA CARTAO DEBITO FARMACIA ABC       -75,90    5.628,41
28/03/2026  RENDIMENTO CDB LIQUIDEZ DIARIA          +12,34    5.640,75
"""

_POSICAO_BTG = """\
BTG PACTUAL — POSIÇÃO CONSOLIDADA DE INVESTIMENTOS
Cliente: INVESTIDOR SINTETICO EXEMPLO
Data-base: 31/03/2026

Produto                        Aplicação    Vencimento   Taxa       Valor Bruto
CDB BTG PACTUAL 102% CDI       10/01/2025   10/01/2027   102% CDI   R$ 25.000,00
LCI BTG IMOBILIARIA            15/06/2025   15/06/2026   95% CDI    R$ 15.500,00
FUNDO BTG ABSOLUTO LS FIC FIM  01/02/2024   —            —          R$ 8.750,00

Total consolidado: R$ 49.250,00
"""

_INFORME_ITAU = """\
BANCO ITAU UNIBANCO S.A.
INFORME DE RENDIMENTOS FINANCEIROS
Ano-Calendário 2025
Beneficiário: CONTRIBUINTE SINTETICO EXEMPLO

RENDIMENTOS SUJEITOS À TRIBUTAÇÃO EXCLUSIVA
Saldo em 31/12/2024: R$ 10.000,00
Saldo em 31/12/2025: R$ 11.000,00
Rendimentos líquidos no ano: R$ 1.000,00
Imposto de renda retido na fonte: R$ 150,00
"""

_EXTRATO_USD = """\
GLOBAL SAMPLE BANK — CHECKING ACCOUNT STATEMENT
Account holder: SYNTHETIC SAMPLE CUSTOMER
Statement period: 03/01/2026 - 03/31/2026
Currency: USD

Date        Description                       Amount       Balance
03/07/2026  WIRE TRANSFER IN - SAMPLE CO     +2,000.00     3,150.00
03/14/2026  DEBIT CARD PURCHASE GROCERY        -120.50     3,029.50
03/25/2026  MONTHLY MAINTENANCE FEE             -25.00     3,004.50
"""

#: 4 fixtures, 1 trial cada (lane pede 3-5). Ordem estável — o runner itera
#: nesta sequência e o fake de teste consome outputs na mesma ordem.
EXTRACT_LLM_DRIFT_FIXTURES: tuple[DriftFixture, ...] = (
    DriftFixture(
        fixture_id="extrato_c6bank_brl",
        filename="c6bank_extratoconta_202603_sintetico.pdf",
        document_text=_EXTRATO_C6BANK,
        expect=StructuralExpectation(
            institution="c6bank",
            currency="BRL",
            min_transactions=3,
            max_transactions=7,
        ),
    ),
    DriftFixture(
        fixture_id="posicao_investimentos_btg",
        filename="btgpactual_posicao_202603_sintetico.pdf",
        document_text=_POSICAO_BTG,
        expect=StructuralExpectation(
            institution="btgpactual",
            currency="BRL",
            min_investments=2,
        ),
    ),
    # Regra explícita do PROMPT_VERSION 1.2.0: informe IR anual NÃO vira
    # extrato fantasma — transacoes deve voltar vazio.
    DriftFixture(
        fixture_id="informe_rendimentos_itau",
        filename="itau_informerendimentos_2025_sintetico.pdf",
        document_text=_INFORME_ITAU,
        expect=StructuralExpectation(
            institution="itau",
            currency="BRL",
            max_transactions=0,
        ),
    ),
    # Banco fora do vocabulário canônico do prompt: asserta apenas
    # institution não-vazia (A28.l8) + propagação de currency=USD.
    DriftFixture(
        fixture_id="extrato_global_usd",
        filename="globalbank_extratoconta_202603_sintetico.pdf",
        document_text=_EXTRATO_USD,
        expect=StructuralExpectation(
            currency="USD",
            min_transactions=2,
            max_transactions=5,
        ),
    ),
)
