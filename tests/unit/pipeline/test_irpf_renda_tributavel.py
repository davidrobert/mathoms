"""Tests — `extract_renda_tributavel_pf` aplicado ao artifact `extract_irpf_full` (ADR-236 §D2)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.transaction import Money  # noqa: E402
from pipeline.domain.services.tributario.irpf_renda_tributavel import (  # noqa: E402
    RendaTributavelPF,
    extract_renda_tributavel_pf,
)


def _artifact(*, pj: list[dict] | None = None, pf: list[dict] | None = None) -> dict:
    """Skeleton de artifact `extract_irpf_full`."""
    return {
        "contribuinte": {"cpf_masked": "***.***.***-12"},
        "rendimentos_pj": pj or [],
        "rendimentos_pf": pf or [],
        "imposto_apurado": {"imposto_devido_brl": "0.00"},
        "confidence": 0.95,
    }


# =============================================================================
# Agregação básica
# =============================================================================


def test_extract_agrega_pj_e_pf_em_total():
    artifact = _artifact(
        pj=[
            {
                "cnpj": "11.222.333/0001-44",
                "nome": "Arvo",
                "rendimentos_tributaveis_brl": "96000.00",
                "contrib_previdenciaria_brl": "8000.00",
                "ir_retido_brl": "12000.00",
            },
            {
                "cnpj": "55.666.777/0001-88",
                "nome": "BrandLovers",
                "rendimentos_tributaveis_brl": "48000.00",
                "contrib_previdenciaria_brl": "4000.00",
                "ir_retido_brl": "5000.00",
            },
        ],
        pf=[
            {
                "pagador_nome": "Inquilino Aluguel",
                "valor_brl": "36000.00",
                "ir_recolhido_brl": "0.00",
            },
        ],
    )

    result = extract_renda_tributavel_pf(artifact)

    assert isinstance(result, RendaTributavelPF)
    # PJ: 96000 + 48000 = 144000
    assert result.rendimentos_pj_total == Money.brl("144000.00")
    assert result.fontes_pj == 2
    # PF: 36000
    assert result.rendimentos_pf_total == Money.brl("36000.00")
    assert result.fontes_pf == 1
    # Total: 180000
    assert result.total == Money.brl("180000.00")
    assert result.has_renda_tributavel is True


def test_extract_handles_decimal_precision():
    """Valores com 2 casas decimais preservam precisão (ADR-090)."""
    artifact = _artifact(
        pj=[
            {
                "cnpj": "11.222.333/0001-44",
                "nome": "PJ",
                "rendimentos_tributaveis_brl": "0.01",
                "contrib_previdenciaria_brl": "0.00",
                "ir_retido_brl": "0.00",
            },
        ],
        pf=[
            {
                "pagador_nome": "PF",
                "valor_brl": "0.02",
                "ir_recolhido_brl": "0.00",
            },
        ],
    )
    result = extract_renda_tributavel_pf(artifact)
    assert result.total.amount == Decimal("0.03")


# =============================================================================
# Casos vazios / parciais (workspace dogfood sem IRPF processado)
# =============================================================================


def test_extract_none_artifact_returns_zeros():
    result = extract_renda_tributavel_pf(None)
    assert result.total == Money.brl("0.00")
    assert result.fontes_pj == 0
    assert result.fontes_pf == 0
    assert result.has_renda_tributavel is False


def test_extract_empty_artifact_returns_zeros():
    result = extract_renda_tributavel_pf({})
    assert result.total == Money.brl("0.00")
    assert result.has_renda_tributavel is False


def test_extract_only_pj_no_pf():
    """Sócio sem aluguel/CLT — só pró-labore PJ."""
    artifact = _artifact(
        pj=[
            {
                "cnpj": "11.222.333/0001-44",
                "nome": "PJ Single",
                "rendimentos_tributaveis_brl": "60000.00",
                "contrib_previdenciaria_brl": "5000.00",
                "ir_retido_brl": "7000.00",
            },
        ]
    )
    result = extract_renda_tributavel_pf(artifact)
    assert result.rendimentos_pj_total == Money.brl("60000.00")
    assert result.rendimentos_pf_total == Money.brl("0.00")
    assert result.total == Money.brl("60000.00")
    assert result.fontes_pj == 1
    assert result.fontes_pf == 0


def test_extract_only_pf_no_pj():
    """Workspace sem PJ — só aluguéis e CLT."""
    artifact = _artifact(
        pf=[
            {"pagador_nome": "Inquilino A", "valor_brl": "12000.00", "ir_recolhido_brl": "0.00"},
            {"pagador_nome": "Inquilino B", "valor_brl": "18000.00", "ir_recolhido_brl": "0.00"},
        ]
    )
    result = extract_renda_tributavel_pf(artifact)
    assert result.rendimentos_pj_total == Money.brl("0.00")
    assert result.rendimentos_pf_total == Money.brl("30000.00")
    assert result.fontes_pj == 0
    assert result.fontes_pf == 2


# =============================================================================
# Robustez: campos malformados (workspace dogfood parcialmente parsed)
# =============================================================================


def test_extract_skips_items_with_missing_money_field():
    artifact = _artifact(
        pj=[
            {"cnpj": "11.222.333/0001-44", "nome": "OK"},  # sem rendimentos_tributaveis_brl
            {
                "cnpj": "55.666.777/0001-88",
                "nome": "OK",
                "rendimentos_tributaveis_brl": "60000.00",
                "contrib_previdenciaria_brl": "0.00",
                "ir_retido_brl": "0.00",
            },
        ]
    )
    result = extract_renda_tributavel_pf(artifact)
    # Só o segundo item conta.
    assert result.rendimentos_pj_total == Money.brl("60000.00")
    assert result.fontes_pj == 1


def test_extract_rejects_float_per_adr_090():
    """ADR-090: float em campo monetário rejeitado silenciosamente (item ignorado, não raise)."""
    artifact = _artifact(
        pj=[
            {
                "cnpj": "11.222.333/0001-44",
                "nome": "Float Bad",
                "rendimentos_tributaveis_brl": 60000.50,  # float — rejeitado
                "contrib_previdenciaria_brl": "0.00",
                "ir_retido_brl": "0.00",
            },
        ]
    )
    result = extract_renda_tributavel_pf(artifact)
    assert result.rendimentos_pj_total == Money.brl("0.00")
    assert result.fontes_pj == 0


def test_extract_handles_non_dict_items_gracefully():
    """Itens corrompidos (string, None, list) são pulados."""
    artifact = {
        "rendimentos_pj": ["not a dict", None, 42],
        "rendimentos_pf": [
            {"pagador_nome": "OK", "valor_brl": "1000.00", "ir_recolhido_brl": "0.00"}
        ],
    }
    result = extract_renda_tributavel_pf(artifact)
    assert result.fontes_pj == 0
    assert result.fontes_pf == 1
    assert result.total == Money.brl("1000.00")


def test_extract_does_not_include_decimo_terceiro_or_isentos():
    """Base PGBL canônica exclui 13º (tributação exclusiva) e lucros isentos."""
    artifact = {
        "rendimentos_pj": [
            {
                "cnpj": "11.222.333/0001-44",
                "nome": "Arvo",
                "rendimentos_tributaveis_brl": "96000.00",
                "contrib_previdenciaria_brl": "8000.00",
                "ir_retido_brl": "12000.00",
                "decimo_terceiro_bruto_brl": "8000.00",  # NÃO entra
                "decimo_terceiro_ir_retido_brl": "1500.00",
            }
        ],
        "rendimentos_isentos": [
            {"codigo_rfb": "09", "descricao": "Lucros distribuídos", "valor_brl": "240000.00"}
        ],
        "rendimentos_tributacao_exclusiva": [
            {"codigo_rfb": "06", "descricao": "13º salário", "valor_brl": "8000.00"}
        ],
        "rendimentos_exterior": [
            {
                "pais": "EUA",
                "pagador": "X",
                "valor_origem": "10000.00",
                "moeda_origem": "USD",
                "taxa_conversao": "5.00",
                "data_conversao": "2025-12-31",
                "valor_brl": "50000.00",
            }
        ],
    }
    result = extract_renda_tributavel_pf(artifact)
    # Só rendimentos_tributaveis_brl entra na base canônica V1.
    assert result.total == Money.brl("96000.00")
