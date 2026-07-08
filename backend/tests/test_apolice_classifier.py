"""A18 L2 P2 (ADR-239 D9) — TypeRule apolice_seguro + mapping → DocumentType.comprovante_bem."""

from __future__ import annotations

import pytest

from backend.app.models.document import DocumentType
from backend.app.services.classification.type_classifier import (
    TYPE_RULES,
    compute_confidence,
    detect_type_by_content,
)
from backend.app.services.documents.document_classification import map_e0_doc_type_to_document_type

# ─────────────────────── TypeRule registrado ─────────────────────────────────


def test_type_rule_apolice_seguro_existe_com_prioridade_alta():
    """priority=2 (alinhado com crlv_eletronico + informe_previdencia_privada)."""
    by_code = {r.code: r for r in TYPE_RULES}
    assert "apolice_seguro" in by_code
    assert by_code["apolice_seguro"].dest_group == "comprovantes"
    assert by_code["apolice_seguro"].priority <= 3


# ─────────────────────── content-based detection ─────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        # Apólice auto simples (Tokio Marine)
        "Apólice de Seguro Auto\nTokio Marine\nSUSEP 202020138\n"
        "Segurado: Fulano\nVeículo: Yamaha NMAX 160 Placa ABC1D23\n"
        "Cobertura Casco LMI R$ 18.500\nVigência 01/03/2026 a 01/03/2027\n"
        "Prêmio Líquido R$ 1.480,50\nFranquia R$ 1.200,00\nCorretor: Bedoni",
        # Apólice residencial Bradesco
        "Apólice Residencial\nBradesco Seguros\nSUSEP 202020150\n"
        "Cobertura Incêndio LMI 400.000\nFranquia 500\n"
        "Vigência 15/02/2026 a 15/02/2027\nPrêmio Total 890,00",
        # Apólice combinada Porto (caso V1 obrigatório)
        "Apólice Porto Proteção Combinada\nPorto Seguro\nSUSEP 201008086\n"
        "Veículo: Fiat Toro Placa XYZ9A87\nResidência: Rua Test 61\n"
        "Cobertura Colisão LMI 100% FIPE\nCobertura Incêndio Residencial LMI 600.000\n"
        "Vigência 10/04/2026\nClasse de Bônus 4\nPrêmio Total 3.250,00",
        # Bilhete de seguro (variação)
        "Bilhete de Seguro\nZurich Brasil\nSUSEP 201234567\n"
        "Cobertura R$ 50.000\nPrêmio R$ 250,00\nVigência 2026",
    ],
)
def test_detect_apolice_em_textos_realistas(text):
    rule, req, sup = detect_type_by_content(text)
    assert rule is not None, "esperava match apolice_seguro"
    assert rule.code == "apolice_seguro"
    assert compute_confidence(rule, req, sup) >= 0.7


@pytest.mark.parametrize(
    "text,expected_code",
    [
        # CRLV-e — não deve casar apolice
        (
            "Certificado de Registro e Licenciamento de Veículo\nDENATRAN\n"
            "Placa: ABC1D23\nRENAVAM 12345678900\nMarca YAMAHA\nModelo NMAX 160\n"
            "Categoria Particular",
            "crlv_eletronico",
        ),
        # IRPF — não deve casar apolice
        (
            "Declaração IRPF 2024\nAno-Calendário 2023\nBens e Direitos\n"
            "Rendimentos Tributáveis",
            "irpfdeclaracao",
        ),
        # PGBL — pode mencionar "Apólice" mas marcadores fortes PGBL dominam
        (
            "Informe Anual de Rendimentos\nBrasilPrev\nPGBL\nRegime Regressivo\n"
            "Saldo em 31/12/2024\nNúmero da Apólice 99999",
            "informe_previdencia_privada",
        ),
    ],
)
def test_apolice_rule_nao_consome_documentos_de_outros_tipos(text, expected_code):
    """Apólice regex específico — não regride classifier existente."""
    rule, _, _ = detect_type_by_content(text)
    assert rule is not None
    assert rule.code == expected_code


# ─────────────────────── DocumentType mapping ────────────────────────────────


def test_apolice_seguro_mapeia_para_comprovante_bem():
    """ADR-239 D8: apólice usa mesmo stage extract_comprovantes_bens (dispatch por tipo_comprovante)."""
    assert map_e0_doc_type_to_document_type("apolice_seguro") == DocumentType.comprovante_bem
    # Variação curta também mapeia
    assert map_e0_doc_type_to_document_type("apolice") == DocumentType.comprovante_bem


def test_outros_tipos_continuam_inalterados():
    """Não-regressão dos mappings anteriores."""
    assert map_e0_doc_type_to_document_type("crlv_eletronico") == DocumentType.comprovante_bem
    assert map_e0_doc_type_to_document_type("irpfdeclaracao") == DocumentType.irpf
    assert (
        map_e0_doc_type_to_document_type("informe_previdencia_privada")
        == DocumentType.informe_rendimentos_anuais
    )
