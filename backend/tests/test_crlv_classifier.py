"""A18 L1 P3 (ADR-239) — TypeRule crlv_eletronico + DocumentType.comprovante_bem."""

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


def test_type_rule_crlv_eletronico_existe_com_prioridade_alta():
    """priority=2 (igual a informe_previdencia_privada); ambos antes do informerendimentos."""
    by_code = {r.code: r for r in TYPE_RULES}
    assert "crlv_eletronico" in by_code
    assert by_code["crlv_eletronico"].dest_group == "comprovantes"
    assert by_code["crlv_eletronico"].priority <= 3


# ─────────────────────── content-based detection ─────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        # CRLV-e moderno padrão DENATRAN
        "Certificado de Registro e Licenciamento de Veículo\nDENATRAN\n"
        "Placa: ABC1D23\nRENAVAM: 12345678900\nMarca: YAMAHA\nModelo: NMAX 160\n"
        "Categoria: Particular\nCombustível: Gasolina\nAno Fabricação: 2024\n"
        "Município de Emplacamento: São Paulo - SP",
        # CRLV-e abreviado mas com âncoras fortes
        "CRLV-e\nPlaca ABC1234\nRENAVAM 98765432100\nExercício 2026\n"
        "Categoria Particular\nCombustível Flex",
        # Variação: "Licenciamento de Veículo" sem "CRLV-e" literal
        "Licenciamento de Veículo 2026\nPlaca XYZ9A87\nRENAVAM 11111111111\n"
        "Ano Modelo 2023\nAno Fabricação 2023\nCategoria Particular",
    ],
)
def test_detect_crlv_em_textos_realistas(text):
    rule, req, sup = detect_type_by_content(text)
    assert rule is not None, "esperava match crlv_eletronico"
    assert rule.code == "crlv_eletronico"
    assert compute_confidence(rule, req, sup) >= 0.7


@pytest.mark.parametrize(
    "text,expected_code",
    [
        # Apólice de seguro auto — não deve casar CRLV (separação L2)
        (
            "Apólice de Seguro Auto\nTokio Marine\nSegurado: Fulano\n"
            "Veículo: Yamaha NMAX 160\nLMI Casco R$ 18.500\nVigência 2026-2027",
            None,  # nenhuma TypeRule existente casa apólice; cai em LLM ou .other
        ),
        # IRPF declaração — continua mapeando para irpfdeclaracao
        (
            "Declaração IRPF 2024\nAno-Calendário 2023\nBens e Direitos\n"
            "Rendimentos Tributáveis\nResumo da Declaração\n"
            "Grupo 02 (Veículos)\nMarca/Modelo Yamaha NMAX",
            "irpfdeclaracao",
        ),
        # PGBL (A17 L1) — não deve casar CRLV
        (
            "Informe Anual de Rendimentos\nBrasilPrev\nPGBL\nRegime Regressivo\n"
            "Saldo em 31/12/2024",
            "informe_previdencia_privada",
        ),
    ],
)
def test_crlv_rule_nao_consome_documentos_de_outros_tipos(text, expected_code):
    """Garante que regex de CRLV é específico (não há regressão em outros tipos)."""
    rule, _, _ = detect_type_by_content(text)
    if expected_code is None:
        # Aceita None (nenhuma rule casa) ou qualquer non-CRLV
        if rule is not None:
            assert rule.code != "crlv_eletronico"
    else:
        assert rule is not None
        assert rule.code == expected_code


# ─────────────────────── DocumentType mapping ────────────────────────────────


def test_crlv_eletronico_mapeia_para_comprovante_bem():
    """ADR-239 D8: CRLV-e dispara extract_comprovantes_bens, não cai em other."""
    assert map_e0_doc_type_to_document_type("crlv_eletronico") == DocumentType.comprovante_bem
    # Variação curta também mapeia (compat futuro)
    assert map_e0_doc_type_to_document_type("crlv") == DocumentType.comprovante_bem


def test_outros_tipos_continuam_inalterados():
    """Não-regressão dos mappings anteriores."""
    assert map_e0_doc_type_to_document_type("irpfdeclaracao") == DocumentType.irpf
    assert (
        map_e0_doc_type_to_document_type("informe_previdencia_privada")
        == DocumentType.informe_rendimentos_anuais
    )
    assert map_e0_doc_type_to_document_type("extratoconta") == DocumentType.bank_statement
    assert map_e0_doc_type_to_document_type("fatura") == DocumentType.credit_card_bill


def test_reverse_mapping_comprovante_bem():
    """Override via PATCH cai em canonical CRLV (V1 default; V2 imóveis ramifica)."""
    assert _DOCUMENT_TYPE_TO_E0_DEST[DocumentType.comprovante_bem] == (
        "crlv_eletronico",
        "comprovantes",
    )
