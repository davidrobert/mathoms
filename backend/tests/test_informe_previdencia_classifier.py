"""A17 L1 P3 (ADR-238) — TypeRule informe_previdencia_privada + DocumentType mapping."""

from __future__ import annotations

import pytest

from backend.app.models.document import DocumentType
from backend.app.services.classification.type_classifier import (
    TYPE_RULES,
    compute_confidence,
    detect_type_by_content,
)
from backend.app.services.documents.document_classification import (
    _DOCUMENT_TYPE_TO_E0_DEST,
    map_e0_doc_type_to_document_type,
)

# ─────────────────────── TypeRule registrado ─────────────────────────────────


def test_type_rule_informe_previdencia_existe_com_prioridade_2():
    """Previdência priority=2; legacy `informerendimentos` deletado em L3 P2."""
    by_code = {r.code: r for r in TYPE_RULES}
    assert "informe_previdencia_privada" in by_code
    assert by_code["informe_previdencia_privada"].priority == 2
    assert by_code["informe_previdencia_privada"].dest_group == "income_tax_br"


# ─────────────────────── content-based detection ─────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        # BrasilPrev layout típico
        "Informe Anual de Rendimentos\nBrasilPrev\nPGBL\nRegime Regressivo\n"
        "Contribuições no ano: R$ 12.000,00\nSaldo em 31/12/2024: R$ 85.420,00\n"
        "Número do Plano: 12345678",
        # Bradesco Vida — sem PGBL/VGBL explícito mas com "Previdência Privada"
        "Bradesco Vida e Previdência\nPlano de Previdência Privada Complementar\n"
        "Contribuições anuais\nSaldo acumulado em 31/12\nCertificado: 9988",
        # VGBL Icatu
        "Icatu Seguros\nVGBL\nRegime Progressivo\nTributação Compensável\n"
        "Saldo de reserva em 31-12-2024\nApólice 4567890",
    ],
)
def test_detect_informe_previdencia_em_textos_realistas(text):
    rule, req, sup = detect_type_by_content(text)
    assert rule is not None, "esperava match informe_previdencia_privada"
    assert rule.code == "informe_previdencia_privada"
    assert compute_confidence(rule, req, sup) >= 0.7


@pytest.mark.parametrize(
    "text,expected_code",
    [
        # Extrato bancário PURO — não deve casar previdência
        (
            "EXTRATO DA CONTA CORRENTE\nAgência: 1234 Conta: 56789-0\n"
            "SALDO ANTERIOR\nPeríodo: 01/01/2024",
            "extratoconta",
        ),
        # Declaração IRPF — continua mapeando para irpfdeclaracao
        (
            "Declaração IRPF 2024\nAno-Calendário 2023\nBens e Direitos\n"
            "Rendimentos Tributáveis\nResumo da Declaração",
            "irpfdeclaracao",
        ),
        # Informe de rendimentos sem produto previdenciário — agora vai para PF
        # (ADR-238 L3 P2: priority=2 mais específico que informerendimentos legado).
        (
            "Informe de Rendimentos Financeiros\nFonte Pagadora: Banco X\n"
            "Ano-Calendário 2024\nRendimentos Tributáveis",
            "informe_financeiro_pf",
        ),
    ],
)
def test_previdencia_rule_nao_consome_documentos_de_outros_tipos(text, expected_code):
    """Garante que regex de previdência é específico (não há regressão em outros tipos)."""
    rule, _, _ = detect_type_by_content(text)
    assert rule is not None
    assert rule.code == expected_code


def test_pgbl_isolado_sem_supporting_ainda_classifica_como_previdencia():
    """Marcador forte (PGBL) sozinho — sem supporting — ainda detecta a regra."""
    # Texto enxuto: só PGBL, sem regime / saldo / certificado / seguradora.
    rule, req, sup = detect_type_by_content("Documento referente a PGBL do titular.")
    assert rule is not None and rule.code == "informe_previdencia_privada"
    assert req == 1
    assert sup == 0
    # 1 required + 0 supporting → 0.7 (regra com required único)
    assert compute_confidence(rule, req, sup) == 0.7


# ─────────────────────── DocumentType mapping (ADR-238 chave) ────────────────


def test_informe_previdencia_NAO_cai_em_irpf_doctype():
    """Bug histórico ADR-238 §Contexto: ``informerendimento*`` virava ``.irpf`` → quebrava pipeline."""
    assert map_e0_doc_type_to_document_type("informe_previdencia_privada") == (
        DocumentType.informe_rendimentos_anuais
    )
    # Forms futuros L2-L4 também caem no novo enum, não em irpf:
    assert map_e0_doc_type_to_document_type("informe_financeiro_pj") == (
        DocumentType.informe_rendimentos_anuais
    )
    assert map_e0_doc_type_to_document_type("informe_proventos_acoes") == (
        DocumentType.informe_rendimentos_anuais
    )


def test_irpf_declaracao_mantem_mapping():
    """IRPF declaração continua disparando extract_irpf_full (não regride)."""
    assert map_e0_doc_type_to_document_type("irpfdeclaracao") == DocumentType.irpf
    assert map_e0_doc_type_to_document_type("irpfrecibo") == DocumentType.irpf


def test_informerendimentos_generico_legado_compat():
    """Genérico legado ``informerendimentos`` (sem tipo específico) mantém compat."""
    # L2-L4 cobrirão tipos específicos; até lá, o genérico segue mapeando como
    # informe legado IRPF.
    assert map_e0_doc_type_to_document_type("informerendimentos") == DocumentType.irpf
    # Aluguel: ADR-216 cutover separado → other temporariamente.
    assert map_e0_doc_type_to_document_type("informerendimentosaluguel") == DocumentType.other


def test_reverse_mapping_informe_anuais():
    """Override via PATCH cai em canonical PGBL (P1 default; L2-L4 ramificam)."""
    assert _DOCUMENT_TYPE_TO_E0_DEST[DocumentType.informe_rendimentos_anuais] == (
        "informe_previdencia_privada",
        "income_tax_br",
    )
