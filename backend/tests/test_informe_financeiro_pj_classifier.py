"""A17 L2 P2 (ADR-238) — TypeRule informe_financeiro_pj + DocumentType mapping."""

from __future__ import annotations

import pytest

from backend.app.models.document import DocumentType
from backend.app.services.classification.type_classifier import (
    TYPE_RULES,
    compute_confidence,
    detect_type_by_content,
)
from backend.app.services.document_classification import map_e0_doc_type_to_document_type


def test_type_rule_informe_financeiro_pj_existe_com_prioridade_2():
    """Mais específico que informerendimentos genérico; ao mesmo nível de previdencia."""
    by_code = {r.code: r for r in TYPE_RULES}
    assert "informe_financeiro_pj" in by_code
    assert by_code["informe_financeiro_pj"].priority == 2
    assert by_code["informe_financeiro_pj"].priority < by_code["informerendimentos"].priority
    assert by_code["informe_financeiro_pj"].dest_group == "income_tax_br"


@pytest.mark.parametrize(
    "text",
    [
        # Stone-style saldo PJ (Demonstrativo de saldo PJ + tributação exclusiva)
        "Informe de rendimentos\nAno-calendário 2024\n"
        "Pessoa Jurídica beneficiária dos rendimentos\n"
        "Fonte pagadora: Stone Instituição de Pagamentos S.A.\n"
        "SALDO EM CONTA\nSaldo em 31/12/2023\nSaldo em 31/12/2024\n"
        "Rendimentos sujeitos à tributação exclusiva\nAPLICAÇÃO DE RENDA FIXA",
        # Comprovante Lei 9.249/95 — adquirente Cielo
        "Comprovante de Rendimentos Pagos e de Retenção\n"
        "Cielo\nFonte pagadora\nIRRF retido\nCSLL retida\n"
        "PIS retido\nCOFINS retida\nLucro Presumido",
        # C6 PJ saldo
        "Pessoa Jurídica beneficiária dos rendimentos\n"
        "C6 Bank\nSaldo em 31/12/2024\nTributação Exclusiva\n"
        "Simples Nacional",
        # Adquirente Rede com vendas brutas
        "Lei 9.249\nRedecred\nVendas brutas\nTPV\n"
        "MDR\nAntecipação de recebíveis\nEstabelecimento aderente",
    ],
)
def test_detect_informe_financeiro_pj_em_textos_realistas(text):
    rule, req, sup = detect_type_by_content(text)
    assert rule is not None, "esperava match informe_financeiro_pj"
    assert rule.code == "informe_financeiro_pj"
    assert compute_confidence(rule, req, sup) >= 0.7


@pytest.mark.parametrize(
    "text,expected_code",
    [
        # Previdência PGBL — deve casar previdencia, NÃO PJ
        (
            "BrasilPrev\nPGBL\nRegime Regressivo\nContribuições no ano\n"
            "Saldo em 31/12/2024\nCertificado 12345",
            "informe_previdencia_privada",
        ),
        # Extrato bancário PURO — não casa PJ
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
        # Informe PF genérico (sem marker PJ) — cai em informerendimentos
        (
            "Informe de Rendimentos Financeiros\nFonte Pagadora: Banco X\n"
            "Ano-Calendário 2024\nRendimentos Tributáveis\nIsentos e Não Tributáveis",
            "informerendimentos",
        ),
    ],
)
def test_pj_rule_nao_consome_documentos_de_outros_tipos(text, expected_code):
    rule, _, _ = detect_type_by_content(text)
    assert rule is not None
    assert rule.code == expected_code


def test_pessoa_juridica_isolada_sem_supporting_classifica_pj_com_07():
    """Marcador forte (Pessoa Jurídica beneficiária) sozinho → 0.7."""
    rule, req, sup = detect_type_by_content("Pessoa Jurídica beneficiária dos rendimentos.")
    assert rule is not None and rule.code == "informe_financeiro_pj"
    assert req == 1
    assert sup == 0
    assert compute_confidence(rule, req, sup) == 0.7


def test_comprovante_lei_9249_sem_supporting_classifica_pj():
    """Marcador forte (Lei 9.249) sozinho → 0.7."""
    rule, req, sup = detect_type_by_content("Documento referente a Lei 9.249/95.")
    assert rule is not None and rule.code == "informe_financeiro_pj"
    assert compute_confidence(rule, req, sup) == 0.7


def test_informe_financeiro_pj_mapeia_para_document_type_enum_unificado():
    """Bug histórico ADR-238 §Contexto: informe* não pode cair em .irpf."""
    assert (
        map_e0_doc_type_to_document_type("informe_financeiro_pj")
        == DocumentType.informe_rendimentos_anuais
    )


def test_pj_rule_e_previdencia_rule_nao_disputam_priority():
    """Tie em priority=2: garantir que required regex são exclusivos (não há sobreposição)."""
    by_code = {r.code: r for r in TYPE_RULES}
    prev_text = "BrasilPrev\nPGBL\nRegime Regressivo"
    pj_text = "Pessoa Jurídica beneficiária"

    # Previdência text → casa previdencia, NÃO pj
    rule_prev, _, _ = detect_type_by_content(prev_text)
    assert rule_prev.code == "informe_previdencia_privada"

    # PJ text → casa pj, NÃO previdencia
    rule_pj, _, _ = detect_type_by_content(pj_text)
    assert rule_pj.code == "informe_financeiro_pj"

    # Sanity: ambas registradas como priority=2.
    assert by_code["informe_previdencia_privada"].priority == 2
    assert by_code["informe_financeiro_pj"].priority == 2
