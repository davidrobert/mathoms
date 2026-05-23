"""A17 L3 P2 (ADR-238) — TypeRule informe_financeiro_pf + DocumentType mapping + Wise."""

from __future__ import annotations

import pytest

from backend.app.models.document import DocumentType
from backend.app.services.classification.type_classifier import (
    TYPE_RULES,
    compute_confidence,
    detect_type_by_content,
)
from backend.app.services.document_classification import map_e0_doc_type_to_document_type


def test_type_rule_informe_financeiro_pf_existe_com_prioridade_2():
    """Specific PF rule (priority=2); legacy `informerendimentos` deletado em L3 P2 (subsumido)."""
    by_code = {r.code: r for r in TYPE_RULES}
    assert "informe_financeiro_pf" in by_code
    assert by_code["informe_financeiro_pf"].priority == 2
    assert by_code["informe_financeiro_pf"].dest_group == "income_tax_br"
    assert "informerendimentos" not in by_code  # legacy removido em L3 P2


@pytest.mark.parametrize(
    "text",
    [
        # Itaú PF layout completo (4 quadros + CPF)
        "Informe de Rendimentos Financeiros\nItaú Unibanco S.A.\n"
        "Pessoa Física\nCPF: ***.***.789-**\n"
        "Quadro 1 - Rendimentos Tributáveis\n"
        "Quadro 2 - Rendimentos Isentos e Não Tributáveis\n"
        "Quadro 3 - Tributação Exclusiva\n"
        "Quadro 4 - Bens e Direitos",
        # Santander layout
        "Informe Anual de Rendimentos\nSantander\nPessoa Física\n"
        "Rendimentos Tributáveis\nIsentos e Não Tributáveis\n"
        "Tributação Exclusiva\nBens e Direitos",
        # Nubank
        "Informe de Rendimentos Financeiros\nNubank\nCPF 987.***.456-**\n"
        "Quadro 1\nQuadro 2\nFonte Pagadora",
        # Wise (caso especial — sem 4 quadros estritos mas com moeda estrangeira)
        "Wise Brasil\nsaldo em moeda estrangeira\nUSD\nconta no exterior\nPessoa Física\nPTAX",
        # XP Investimentos
        "Informe de Rendimentos Financeiros\nXP Investimentos\n"
        "Pessoa Física\nTributação Exclusiva\nBens e Direitos",
    ],
)
def test_detect_informe_financeiro_pf_em_textos_realistas(text):
    rule, req, sup = detect_type_by_content(text)
    assert rule is not None, "esperava match informe_financeiro_pf"
    assert rule.code == "informe_financeiro_pf"
    assert compute_confidence(rule, req, sup) >= 0.7


@pytest.mark.parametrize(
    "text,expected_code",
    [
        # Previdência PGBL — deve casar previdencia (priority=2 antes na lista)
        (
            "BrasilPrev\nPGBL\nRegime Regressivo\nContribuições no ano\n"
            "Saldo em 31/12/2024\nCertificado 12345",
            "informe_previdencia_privada",
        ),
        # PJ (Stone) — deve casar PJ (priority=2 antes na lista)
        (
            "Informe de rendimentos\nPessoa Jurídica beneficiária dos rendimentos\n"
            "Stone Pagamentos S.A.\nSALDO EM CONTA\nSaldo em 31/12/2024",
            "informe_financeiro_pj",
        ),
        # Extrato bancário puro — não casa
        (
            "EXTRATO DA CONTA CORRENTE\nAgência: 1234 Conta: 56789-0\n"
            "SALDO ANTERIOR\nPeríodo: 01/01/2024",
            "extratoconta",
        ),
        # IRPF declaração — não casa
        (
            "Declaração IRPF 2024\nAno-Calendário 2023\nBens e Direitos\n"
            "Rendimentos Tributáveis\nResumo da Declaração",
            "irpfdeclaracao",
        ),
    ],
)
def test_pf_rule_nao_consome_documentos_de_outros_tipos(text, expected_code):
    rule, _, _ = detect_type_by_content(text)
    assert rule is not None
    assert rule.code == expected_code


def test_wise_isolado_classifica_como_pf():
    """Wise sem 4 quadros RFB ainda classifica PF (required: 'Wise Brasil' OR moeda estrangeira)."""
    rule, req, sup = detect_type_by_content(
        "Wise Brasil\nsaldo em moeda estrangeira em 31/12/2024\nUSD"
    )
    assert rule is not None and rule.code == "informe_financeiro_pf"
    assert compute_confidence(rule, req, sup) >= 0.7


def test_informe_rendimentos_generico_legado_compat_via_pf():
    """Informe genérico sem PF/Wise/Wise markers cai em PF se tiver 4 quadros."""
    rule, req, sup = detect_type_by_content(
        "Informe de Rendimentos Financeiros\nQuadro 1 - Tributáveis\n"
        "Quadro 4 - Bens e Direitos\nPessoa Física"
    )
    assert rule is not None and rule.code == "informe_financeiro_pf"


def test_informe_pf_mapeia_para_document_type_enum_unificado():
    """Bug histórico ADR-238 §Contexto: informe* não pode cair em .irpf."""
    assert (
        map_e0_doc_type_to_document_type("informe_financeiro_pf")
        == DocumentType.informe_rendimentos_anuais
    )


def test_pf_e_pj_e_previdencia_tie_breaking_priority_2():
    """3 rules em priority=2: ordem no TYPE_RULES define quem casa quando required overlapping."""
    by_code = {r.code: r for r in TYPE_RULES}
    assert by_code["informe_previdencia_privada"].priority == 2
    assert by_code["informe_financeiro_pj"].priority == 2
    assert by_code["informe_financeiro_pf"].priority == 2

    # Required exclusivos garantem desambiguação:
    # PGBL/VGBL → previdencia
    # Pessoa Jurídica beneficiária → PJ
    # Informe Rendimentos Financeiros + Pessoa Física → PF
    # Wise Brasil → PF
    prev = detect_type_by_content("BrasilPrev\nPGBL")[0]
    assert prev and prev.code == "informe_previdencia_privada"
    pj = detect_type_by_content("Pessoa Jurídica beneficiária\nStone")[0]
    assert pj and pj.code == "informe_financeiro_pj"
    pf = detect_type_by_content("Informe Anual de Rendimentos\nItaú\nPessoa Física")[0]
    assert pf and pf.code == "informe_financeiro_pf"
