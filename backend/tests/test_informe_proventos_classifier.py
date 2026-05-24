"""A17 L4 (ADR-238) — TypeRule informe_proventos_acoes + DocumentType mapping."""

from __future__ import annotations

import pytest

from backend.app.models.document import DocumentType
from backend.app.services.classification.type_classifier import (
    TYPE_RULES,
    compute_confidence,
    detect_type_by_content,
)
from backend.app.services.document_classification import map_e0_doc_type_to_document_type


def test_type_rule_informe_proventos_acoes_existe_priority_2():
    by_code = {r.code: r for r in TYPE_RULES}
    assert "informe_proventos_acoes" in by_code
    assert by_code["informe_proventos_acoes"].priority == 2
    assert by_code["informe_proventos_acoes"].dest_group == "income_tax_br"


@pytest.mark.parametrize(
    "text",
    [
        # XP Proventos típico
        "Relatório de Proventos\nXP Investimentos CCTVM S.A.\n"
        "Dividendo\nJCP\nBonificação\nWEGE3\nITSA4\n"
        "CNPJ do Pagador\nData do Pagamento",
        # Itaúsa holding (1 ativo)
        "Aviso aos Acionistas\nItaúsa Investimentos S.A.\n"
        "Dividendo\nITSA4\nData Com\nData Ex\nFonte Pagadora",
        # FII apenas
        "Informe de Proventos\nRendimento de FII\nMXRF11\nHGLG11\n"
        "Fundo Imobiliário\nData do Pagamento",
        # BTG Pactual
        "Proventos de Ações\nBTG Pactual\nJCP\nJuros sobre Capital Próprio\nWEGE3\nCustodiante",
    ],
)
def test_detect_informe_proventos_em_textos_realistas(text):
    rule, req, sup = detect_type_by_content(text)
    assert rule is not None, "esperava match informe_proventos_acoes"
    assert rule.code == "informe_proventos_acoes"
    assert compute_confidence(rule, req, sup) >= 0.7


@pytest.mark.parametrize(
    "text,expected_code",
    [
        # Previdência PGBL — não casa proventos
        (
            "BrasilPrev\nPGBL\nRegime Regressivo\nContribuições no ano\n"
            "Saldo em 31/12/2024\nCertificado 12345",
            "informe_previdencia_privada",
        ),
        # PJ Stone — não casa proventos
        (
            "Informe de rendimentos\nPessoa Jurídica beneficiária dos rendimentos\n"
            "Stone Pagamentos S.A.\nSALDO EM CONTA\nSaldo em 31/12/2024",
            "informe_financeiro_pj",
        ),
        # Informe PF bancário — não casa proventos (sem markers de Dividendo/JCP/FII)
        (
            "Informe de Rendimentos Financeiros\nItaú Unibanco S.A.\n"
            "Pessoa Física\nQuadro 1 - Rendimentos Tributáveis\n"
            "Quadro 4 - Bens e Direitos",
            "informe_financeiro_pf",
        ),
        # Extrato bancário puro
        (
            "EXTRATO DA CONTA CORRENTE\nAgência: 1234 Conta: 56789-0\n"
            "SALDO ANTERIOR\nPeríodo: 01/01/2024",
            "extratoconta",
        ),
        # IRPF declaração
        (
            "Declaração IRPF 2024\nAno-Calendário 2023\nBens e Direitos\n"
            "Rendimentos Tributáveis\nResumo da Declaração",
            "irpfdeclaracao",
        ),
    ],
)
def test_proventos_rule_nao_consome_outros_tipos(text, expected_code):
    rule, _, _ = detect_type_by_content(text)
    assert rule is not None
    assert rule.code == expected_code


def test_relatorio_proventos_isolado_classifica():
    """Required mínimo: 'Relatório de Proventos' sozinho."""
    rule, req, sup = detect_type_by_content("Relatório de Proventos 2024")
    assert rule is not None and rule.code == "informe_proventos_acoes"


def test_aviso_acionistas_isolado_classifica():
    rule, req, sup = detect_type_by_content("Aviso aos Acionistas — Itaúsa S.A.")
    assert rule is not None and rule.code == "informe_proventos_acoes"


def test_informe_proventos_mapeia_para_document_type_unificado():
    """Bug histórico ADR-238 §Contexto: informe_* não cai em .irpf."""
    assert (
        map_e0_doc_type_to_document_type("informe_proventos_acoes")
        == DocumentType.informe_rendimentos_anuais
    )


_A17_PRIORITY_2_CODES = (
    "informe_previdencia_privada",
    "informe_financeiro_pj",
    "informe_financeiro_pf",
    "informe_proventos_acoes",
)

_A17_DISAMBIGUATION_FIXTURES = [
    ("BrasilPrev\nPGBL", "informe_previdencia_privada"),
    ("Pessoa Jurídica beneficiária\nStone", "informe_financeiro_pj"),
    ("Informe Anual de Rendimentos\nItaú\nPessoa Física", "informe_financeiro_pf"),
    ("Relatório de Proventos\nXP\nDividendo", "informe_proventos_acoes"),
]


def test_quatro_priority_2_rules_canonicos_a17():
    """L1-L4 todas em priority=2 com required exclusivo."""
    by_code = {r.code: r for r in TYPE_RULES}
    for code in _A17_PRIORITY_2_CODES:
        assert by_code[code].priority == 2
    for text, expected in _A17_DISAMBIGUATION_FIXTURES:
        assert detect_type_by_content(text)[0].code == expected
