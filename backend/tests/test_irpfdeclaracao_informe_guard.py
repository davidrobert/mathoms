"""Negative guard de `irpfdeclaracao` — informes e recibos não são a declaração.

Regressão do incidente workspace 5@5.com (2026-05): um "Informe de Rendimentos
Financeiros" PJ do C6 era classificado como `irpfdeclaracao` porque continha a
âncora "Declaração de Ajuste Anual" (referência ao destino do informe). Como
`irpfdeclaracao` tem priority=1 e é definido antes de `irpfrecibo` e das rules
de informe (priority=2), roubava a classificação. O doc chegava a E1.6
(`extract_irpf_full`) e quebrava o validator PF/PJ (ADR-268) — `IRPFFullOutput`
rejeita `contribuinte.nome` com sufixo "LTDA" → 4 retries → pipeline abortado.
"""

from __future__ import annotations

import pytest

from backend.app.services.classification.type_classifier import detect_type_by_content
from backend.app.services.documents.content_classifier import classify_text

# Trechos reais (PII redigida) dos docs que estavam mal-classificados em 5@5.com.
_C6_INFORME_PJ = (
    "ANO-CALENDÁRIO DE 2025\nINFORME DE RENDIMENTOS FINANCEIROS\n"
    "IMPOSTO DE RENDA – PESSOA JURÍDICA\n"
    "1. IDENTIFICAÇÃO DA FONTE PAGADORA\nBANCO C6 S.A. 31.872.495/0001-72\n"
    "2. PESSOA JURIDICA BENEFICIÁRIA DOS RENDIMENTOS\n"
    "NOME COMPLETO CNPJ\n<RAZAO SOCIAL> LTDA 48.***.***/0001-87\n"
    "3. RENDIMENTOS TRIBUTÁVEIS NA DECLARAÇÃO DE AJUSTE ANUAL (Valores em Reais)\n"
    "3.1 APLICAÇÕES DE RENDA FIXA\nSALDOS EM 31/12/2024 SALDOS EM 31/12/2025"
)
_C6_INFORME_PF = (
    "Ano Calendário de 2025\n<NOME PF>\nCPF: ***.***.***-36\n"
    "Informe de Rendimentos Financeiros\n1. Rendimentos Isentos\n"
    "BANCO C6 S.A. 31.872.495/0001-72 Aplicações em Renda Fixa\n"
    "2. Rendimentos Sujeitos a Tributação Exclusiva"
)
_CAIXA_INFORME_PF = (
    "Informe IRPF\nInforme de Rendimentos Financeiros\nAno-Calendário de 2025\n"
    "Imposto de Renda - Pessoa Física\n1 - Identificação da Fonte Pagadora\n"
    "Nome Empresarial: CAIXA ECONÔMICA FEDERAL\n"
    "3 - Rendimentos Tributáveis na Declaração de Ajuste Anual - Valores em Reais"
)
_RECIBO_DAA = (
    "MINISTÉRIO DA FAZENDA IMPOSTO SOBRE A RENDA - PESSOA FÍSICA\n"
    "SECRETARIA ESPECIAL DA RECEITA FEDERAL DO BRASIL EXERCÍCIO 2025 ANO-CALENDÁRIO 2024\n"
    "RECIBO DE ENTREGA DA DECLARAÇÃO DE AJUSTE ANUAL - OPÇÃO PELO DESCONTO SIMPLIFICADO\n"
    "DECLARAÇÃO ORIGINAL\nIDENTIFICAÇÃO DO DECLARANTE\n"
    "CPF do declarante Nome do declarante\nTOTAL RENDIMENTOS TRIBUTÁVEIS"
)
_DAA_GENUINA = (
    "NOME: <NOME PF>\nCPF: ***.***.***-36 IMPOSTO SOBRE A RENDA - PESSOA FÍSICA\n"
    "DECLARAÇÃO DE AJUSTE ANUAL EXERCÍCIO 2025 ANO-CALENDÁRIO 2024\n"
    "IDENTIFICAÇÃO DO CONTRIBUINTE\nTipo de declaração: Declaração de Ajuste Anual Original\n"
    "DEPENDENTES\nRENDIMENTOS TRIBUTÁVEIS RECEBIDOS DE PESSOA JURÍDICA PELO TITULAR\n"
    "Bens e Direitos\nResumo da Declaração"
)


@pytest.mark.parametrize(
    "text,expected",
    [
        (_C6_INFORME_PJ, "informe_financeiro_pj"),
        (_C6_INFORME_PF, "informe_financeiro_pf"),
        (_CAIXA_INFORME_PF, "informe_financeiro_pf"),
        (_RECIBO_DAA, "irpfrecibo"),
    ],
)
def test_informe_e_recibo_nao_sao_irpfdeclaracao(text, expected):
    rule, _, _ = detect_type_by_content(text)
    assert rule is not None
    assert rule.code == expected, f"esperava {expected}, veio {rule.code}"


def test_declaracao_genuina_ainda_classifica_como_irpfdeclaracao():
    rule, _, _ = detect_type_by_content(_DAA_GENUINA)
    assert rule is not None and rule.code == "irpfdeclaracao"


def test_informe_pj_preserva_instituicao_real_nao_receitafederal():
    """Com o type correto, `_resolve_institution` não força receitafederal."""
    result = classify_text(_C6_INFORME_PJ)
    assert result.doc_type == "informe_financeiro_pj"
    assert result.institution != "receitafederal"
