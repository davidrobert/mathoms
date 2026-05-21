"""Unit tests A17 L1 P1 (ADR-238) — InformePrevidenciaPayload + InformeRendimentosBase."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.informe_base import InformeRendimentosBase
from pipeline.llm.schemas.informe_previdencia import (
    InformePrevidenciaPayload,
    PlanoTipo,
    RegimeTributacao,
    _coerce_decimal,
)


def _build_payload(**overrides) -> InformePrevidenciaPayload:
    base = {
        "numero_certificado": "BR12345678",
        "plano_tipo": PlanoTipo.pgbl,
        "regime_tributacao": RegimeTributacao.regressivo,
        "data_adesao": "2018-06",
        "contribuicoes_anuais": "12000.00",
        "rendimentos_anuais": "850.00",
        "saldo_31_12": "85420.00",
        "resgates_anuais": "0",
        "ir_retido_anual": "0",
    }
    base.update(overrides)
    return InformePrevidenciaPayload(**base)


def _build_base(**overrides) -> InformeRendimentosBase:
    base = {
        "ano_base": 2024,
        "tipo_informe": "previdencia_privada",
        "fonte_pagadora_cnpj": "16404287000167",
        "fonte_pagadora_nome": "BrasilPrev Seguros e Previdencia S.A.",
        "titular_cpf_masked": "***.456.789-**",
        "confidence": 0.92,
        "source_artifact_id": "art_abc123",
        "prompt_version": "informe-prev-v1.0.0",
        "previdencia": _build_payload(),
    }
    base.update(overrides)
    return InformeRendimentosBase(**base)


# ─────────────────────── _coerce_decimal (ADR-090) ──────────────────────────


def test_coerce_decimal_aceita_string_int_decimal_e_float():
    assert _coerce_decimal("1234.56") == Decimal("1234.56")
    assert _coerce_decimal(1234) == Decimal("1234")
    assert _coerce_decimal(None) is None
    assert _coerce_decimal(Decimal("9.99")) == Decimal("9.99")
    # ADR-090: float é coercido no boundary do LLM (não há Decimal nativo em JSON).
    assert _coerce_decimal(7424.71) == Decimal("7424.71")
    assert _coerce_decimal(0.0) == Decimal("0")


# ─────────────────────── Payload Previdência ────────────────────────────────


def test_payload_happy_path_pgbl_regressivo():
    p = _build_payload()
    assert p.plano_tipo == PlanoTipo.pgbl
    assert p.regime_tributacao == RegimeTributacao.regressivo
    assert p.contribuicoes_anuais == Decimal("12000.00")
    assert p.saldo_31_12 == Decimal("85420.00")
    assert p.resgates_anuais == Decimal("0")


def test_payload_vgbl_progressivo_aceito():
    p = _build_payload(plano_tipo=PlanoTipo.vgbl, regime_tributacao=RegimeTributacao.progressivo)
    assert p.plano_tipo == PlanoTipo.vgbl
    assert p.regime_tributacao == RegimeTributacao.progressivo


def test_payload_saldo_obrigatorio():
    with pytest.raises(ValidationError) as exc:
        InformePrevidenciaPayload(
            plano_tipo=PlanoTipo.pgbl,
            regime_tributacao=RegimeTributacao.regressivo,
            contribuicoes_anuais="100",
            # falta saldo_31_12
        )
    assert "saldo_31_12" in str(exc.value)


def test_payload_recusa_field_desconhecido():
    """Sub-payload é strict (extra='forbid') — protege contra schema drift do LLM."""
    with pytest.raises(ValidationError) as exc:
        InformePrevidenciaPayload(
            plano_tipo=PlanoTipo.pgbl,
            regime_tributacao=RegimeTributacao.regressivo,
            contribuicoes_anuais="100",
            saldo_31_12="500",
            campo_inexistente="ruim",
        )
    assert "campo_inexistente" in str(exc.value).lower() or "extra" in str(exc.value).lower()


def test_payload_data_adesao_pattern():
    """YYYY-MM ou YYYY-MM-DD; outros formatos recusados."""
    p = _build_payload(data_adesao="2020-03-15")
    assert p.data_adesao == "2020-03-15"
    with pytest.raises(ValidationError):
        _build_payload(data_adesao="03/2020")


def test_payload_resgates_e_ir_retido_default_zero():
    p = InformePrevidenciaPayload(
        plano_tipo=PlanoTipo.pgbl,
        regime_tributacao=RegimeTributacao.regressivo,
        contribuicoes_anuais="100",
        saldo_31_12="500",
    )
    assert p.resgates_anuais == Decimal("0")
    assert p.ir_retido_anual == Decimal("0")
    assert p.rendimentos_anuais == Decimal("0")


def test_payload_lgpd_nao_persiste_beneficiarios_pii():
    """Beneficiarios persistem apenas como contagem — nomes/CPFs proibidos."""
    p = _build_payload(beneficiarios_count=2)
    assert p.beneficiarios_count == 2
    dumped = p.model_dump()
    # Verifica que nem o schema permite campo "beneficiarios" (lista de nomes).
    assert "beneficiarios" not in dumped
    assert "beneficiarios_cpfs" not in dumped


# ─────────────────────── Base polimórfico ───────────────────────────────────


def test_base_happy_path_previdencia():
    b = _build_base()
    assert b.tipo_informe == "previdencia_privada"
    assert b.previdencia is not None
    assert b.previdencia.plano_tipo == PlanoTipo.pgbl
    assert b.source_priority == 2  # default
    assert b.needs_review is False


def test_base_recusa_outros_tipos_em_p1():
    """L1 só aceita 'previdencia_privada'. L2-L4 expandem o Literal."""
    with pytest.raises(ValidationError) as exc:
        _build_base(tipo_informe="financeiro_pj")
    assert "tipo_informe" in str(exc.value)


def test_base_lenient_top_level():
    """ADR-238 D2: top-level lenient (extra='allow') sobrevive shape novo."""
    b = InformeRendimentosBase(
        ano_base=2024,
        tipo_informe="previdencia_privada",
        fonte_pagadora_cnpj="16404287000167",
        fonte_pagadora_nome="BrasilPrev",
        confidence=0.9,
        prompt_version="informe-prev-v1.0.0",
        previdencia=_build_payload(),
        campo_futuro="ok",  # não rejeita
    )
    assert b.tipo_informe == "previdencia_privada"


def test_base_cnpj_pattern_strict():
    with pytest.raises(ValidationError):
        _build_base(fonte_pagadora_cnpj="16.404.287/0001-67")  # com máscara
    with pytest.raises(ValidationError):
        _build_base(fonte_pagadora_cnpj="123")  # incompleto


def test_base_cpf_masked_pattern_strict():
    """LGPD: CPF completo nunca; só máscara parcial."""
    with pytest.raises(ValidationError):
        _build_base(titular_cpf_masked="98765432100")
    # Máscara válida
    b = _build_base(titular_cpf_masked="***.***.789-**")
    assert b.titular_cpf_masked == "***.***.789-**"


def test_base_confidence_range():
    with pytest.raises(ValidationError):
        _build_base(confidence=1.5)
    with pytest.raises(ValidationError):
        _build_base(confidence=-0.1)


def test_base_source_priority_range_e_default():
    b = _build_base()
    assert b.source_priority == 2  # default 'declaração vence'
    b1 = _build_base(source_priority=1)
    assert b1.source_priority == 1
    with pytest.raises(ValidationError):
        _build_base(source_priority=0)
    with pytest.raises(ValidationError):
        _build_base(source_priority=4)


def test_base_ano_base_range():
    with pytest.raises(ValidationError):
        _build_base(ano_base=1999)
    with pytest.raises(ValidationError):
        _build_base(ano_base=2101)


# ─────────────────────── JSON Schema sync ───────────────────────────────────


def test_json_schema_files_exist_e_sao_validos():
    """Schemas JSON devem existir e parsear como JSON válido."""
    repo_root = Path(__file__).resolve().parent.parent
    base_schema = repo_root / "config" / "schemas" / "informe_base.schema.json"
    prev_schema = repo_root / "config" / "schemas" / "informe_previdencia.schema.json"
    assert base_schema.exists(), f"falta {base_schema}"
    assert prev_schema.exists(), f"falta {prev_schema}"
    base_doc = json.loads(base_schema.read_text())
    prev_doc = json.loads(prev_schema.read_text())
    assert base_doc["$id"] == "informe_base.schema.json"
    assert prev_doc["$id"] == "informe_previdencia.schema.json"
    # JSON Schema deve restringir tipo_informe ao mesmo conjunto do Pydantic em P1.
    enum_jsonschema = set(base_doc["properties"]["tipo_informe"]["enum"])
    assert enum_jsonschema == {"previdencia_privada"}, (
        f"L1: JSON Schema deve aceitar somente previdencia_privada — encontrou {enum_jsonschema}. "
        f"L2-L4 expandem o enum."
    )
