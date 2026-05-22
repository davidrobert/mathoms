"""Unit tests A17 L2 P1 (ADR-238) — InformeFinanceiroPJPayload + base polimórfico."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.informe_base import InformeRendimentosBase
from pipeline.llm.schemas.informe_pj import (
    InformeFinanceiroPJPayload,
    RegimeTributarioPJ,
    _coerce_decimal,
)


def _build_payload(**overrides) -> InformeFinanceiroPJPayload:
    base = {
        "regime_tributario": RegimeTributarioPJ.lucro_presumido,
        "cnpj_pagador": "16501555000157",  # Stone (anonimizado para teste)
        "nome_pagador": "Stone Pagamentos S.A.",
        "cnpj_beneficiario": "12345678000190",
        "periodo_inicio": "2024-01",
        "periodo_fim": "2024-12",
        "receita_bruta_anual": "240000.00",
    }
    base.update(overrides)
    return InformeFinanceiroPJPayload(**base)


def _build_base(**overrides) -> InformeRendimentosBase:
    base = {
        "ano_base": 2024,
        "tipo_informe": "financeiro_pj",
        "fonte_pagadora_cnpj": "16501555000157",
        "fonte_pagadora_nome": "Stone Pagamentos S.A.",
        "titular_cpf_masked": None,
        "confidence": 0.92,
        "source_artifact_id": "art_pj_001",
        "prompt_version": "informe-pj-v1.0.0",
        "financeiro_pj": _build_payload(),
    }
    base.update(overrides)
    return InformeRendimentosBase(**base)


# ─────────────────────── _coerce_decimal (ADR-090) ──────────────────────────


def test_coerce_decimal_aceita_string_int_decimal_e_float():
    assert _coerce_decimal("1234.56") == Decimal("1234.56")
    assert _coerce_decimal(1234) == Decimal("1234")
    assert _coerce_decimal(None) is None
    assert _coerce_decimal(Decimal("9.99")) == Decimal("9.99")
    assert _coerce_decimal(7424.71) == Decimal("7424.71")
    assert _coerce_decimal(0.0) == Decimal("0")


# ─────────────────────── Payload PJ ────────────────────────────────────────


def test_payload_happy_path_lucro_presumido_servicos():
    """LP típico: 1% CSLL + 0,65% PIS + 3% COFINS + 1,5% IRRF sobre serviços."""
    p = _build_payload(
        receita_bruta_anual="240000.00",
        irrf_anual="3600.00",
        csll_anual="2400.00",
        pis_anual="1560.00",
        cofins_anual="7200.00",
    )
    assert p.regime_tributario == RegimeTributarioPJ.lucro_presumido
    assert p.receita_bruta_anual == Decimal("240000.00")
    assert p.irrf_anual == Decimal("3600.00")
    assert p.csll_anual == Decimal("2400.00")


def test_payload_happy_path_simples_nacional_sem_retencoes():
    """SN típico: sem retenção CSLL/PIS/COFINS (DAS unificada)."""
    p = _build_payload(
        regime_tributario=RegimeTributarioPJ.simples_nacional,
        receita_bruta_anual="180000.00",
    )
    assert p.regime_tributario == RegimeTributarioPJ.simples_nacional
    assert p.csll_anual == Decimal("0")
    assert p.pis_anual == Decimal("0")
    assert p.cofins_anual == Decimal("0")


def test_payload_adquirente_stone_com_mdr_e_estornos():
    """Adquirente: receita = TPV - estornos; MDR é despesa, não retenção."""
    p = _build_payload(
        regime_tributario=RegimeTributarioPJ.simples_nacional,
        receita_bruta_anual="300000.00",
        estornos_anuais="5000.00",
        mdr_anual="12000.00",
    )
    assert p.receita_bruta_anual == Decimal("300000.00")
    assert p.estornos_anuais == Decimal("5000.00")
    assert p.mdr_anual == Decimal("12000.00")
    assert p.irrf_anual == Decimal("0")  # MDR não é retenção


def test_payload_recusa_lucro_real():
    """LR fora de escopo V1 (ADR-238 §Não-objetivos). Schema só aceita SN/LP."""
    with pytest.raises(ValidationError) as exc:
        _build_payload(regime_tributario="lucro_real")
    assert (
        "regime_tributario" in str(exc.value).lower() or "literal_error" in str(exc.value).lower()
    )


def test_payload_receita_bruta_obrigatoria():
    with pytest.raises(ValidationError) as exc:
        InformeFinanceiroPJPayload(
            regime_tributario=RegimeTributarioPJ.lucro_presumido,
            cnpj_pagador="16501555000157",
            nome_pagador="Stone",
            cnpj_beneficiario="12345678000190",
            periodo_inicio="2024-01",
            periodo_fim="2024-12",
            # falta receita_bruta_anual
        )
    assert "receita_bruta_anual" in str(exc.value)


def test_payload_cnpj_pagador_pattern_strict():
    with pytest.raises(ValidationError):
        _build_payload(cnpj_pagador="16.501.555/0001-57")  # com máscara
    with pytest.raises(ValidationError):
        _build_payload(cnpj_pagador="123")  # incompleto
    with pytest.raises(ValidationError):
        _build_payload(cnpj_pagador="1650155500015a")  # com letra


def test_payload_cnpj_beneficiario_pattern_strict():
    with pytest.raises(ValidationError):
        _build_payload(cnpj_beneficiario="12.345.678/0001-90")
    with pytest.raises(ValidationError):
        _build_payload(cnpj_beneficiario="abc")


def test_payload_periodo_consistente():
    """periodo_fim deve ser >= periodo_inicio."""
    with pytest.raises(ValidationError) as exc:
        _build_payload(periodo_inicio="2024-12", periodo_fim="2024-01")
    assert "periodo" in str(exc.value).lower()


def test_payload_periodo_pattern_yyyy_mm():
    with pytest.raises(ValidationError):
        _build_payload(periodo_inicio="2024-1")  # mês sem zero-pad
    with pytest.raises(ValidationError):
        _build_payload(periodo_inicio="01/2024")  # formato BR


def test_payload_recusa_field_desconhecido():
    """Sub-payload é strict (extra='forbid') — protege contra schema drift do LLM."""
    with pytest.raises(ValidationError) as exc:
        _build_payload(campo_inexistente="ruim")
    assert "campo_inexistente" in str(exc.value).lower() or "extra" in str(exc.value).lower()


def test_payload_retencoes_default_zero():
    """Retenções não informadas defaultam para Decimal('0')."""
    p = _build_payload()
    assert p.irrf_anual == Decimal("0")
    assert p.csll_anual == Decimal("0")
    assert p.pis_anual == Decimal("0")
    assert p.cofins_anual == Decimal("0")
    assert p.inss_anual == Decimal("0")
    assert p.iss_anual == Decimal("0")
    assert p.estornos_anuais == Decimal("0")
    assert p.mdr_anual is None


def test_payload_sn_com_retencao_csll_marca_anomalia_em_notas():
    """SN raramente sofre retenção CSLL/PIS/COFINS (LC 123 §6 IV-A). Quando ocorre, notas captura."""
    p = _build_payload(
        regime_tributario=RegimeTributarioPJ.simples_nacional,
        csll_anual="2400.00",
    )
    assert p.csll_anual == Decimal("2400.00")  # schema não rejeita (anomalia legítima rara)
    assert p.notas is not None
    assert "SN com retenção" in p.notas


def test_payload_lp_com_retencoes_sem_anomalia_em_notas():
    """LP com retenções CSLL/PIS/COFINS é normal — sem warning em notas."""
    p = _build_payload(
        regime_tributario=RegimeTributarioPJ.lucro_presumido,
        csll_anual="2400.00",
        pis_anual="1560.00",
        cofins_anual="7200.00",
    )
    assert p.notas is None  # sem anomalia


def test_payload_inss_iss_independem_do_regime():
    """INSS (11% serviços com MOL) e ISS (variável município) podem aparecer em qualquer regime."""
    p_sn = _build_payload(
        regime_tributario=RegimeTributarioPJ.simples_nacional,
        inss_anual="13200.00",
        iss_anual="6000.00",
    )
    assert p_sn.inss_anual == Decimal("13200.00")
    assert p_sn.iss_anual == Decimal("6000.00")


def test_payload_lgpd_nao_persiste_cpf_socio_pj():
    """Schema NÃO modela CPF de sócio nem informações pessoais — só CNPJs."""
    p = _build_payload()
    dumped = p.model_dump()
    assert "cpf_socio" not in dumped
    assert "cpfs_socios" not in dumped
    # Apenas CNPJs canônicos
    assert "cnpj_pagador" in dumped
    assert "cnpj_beneficiario" in dumped


# ─────────────────────── Base polimórfico ───────────────────────────────────


def test_base_happy_path_financeiro_pj():
    b = _build_base()
    assert b.tipo_informe == "financeiro_pj"
    assert b.financeiro_pj is not None
    assert b.financeiro_pj.regime_tributario == RegimeTributarioPJ.lucro_presumido
    assert b.source_priority == 1
    assert b.needs_review is False
    assert b.previdencia is None  # sub-payload de outro tipo não populado


def test_base_aceita_l1_e_l2():
    """Após L2, tipo_informe Literal aceita previdencia_privada E financeiro_pj."""
    b_l1 = _build_base(
        tipo_informe="previdencia_privada",
        financeiro_pj=None,
        previdencia=None,  # smoke — não exige sub-payload aqui pois validator é só do schema JSON
    )
    # Pydantic não bloqueia (validator está no JSON Schema allOf, não no Pydantic)
    assert b_l1.tipo_informe == "previdencia_privada"
    b_l2 = _build_base()
    assert b_l2.tipo_informe == "financeiro_pj"


def test_base_lenient_top_level():
    """ADR-238 D2: top-level lenient (extra='allow') sobrevive shape novo."""
    b = InformeRendimentosBase(
        ano_base=2024,
        tipo_informe="financeiro_pj",
        fonte_pagadora_cnpj="16501555000157",
        fonte_pagadora_nome="Stone",
        confidence=0.9,
        prompt_version="informe-pj-v1.0.0",
        financeiro_pj=_build_payload(),
        campo_futuro="ok",
    )
    assert b.tipo_informe == "financeiro_pj"


def test_base_titular_cpf_null_em_pj():
    """Informe PJ não tem CPF titular — sempre null."""
    b = _build_base(titular_cpf_masked=None)
    assert b.titular_cpf_masked is None


# ─────────────────────── JSON Schema sync ───────────────────────────────────


_PJ_REQUIRED = {
    "regime_tributario",
    "cnpj_pagador",
    "nome_pagador",
    "cnpj_beneficiario",
    "periodo_inicio",
    "periodo_fim",
    "receita_bruta_anual",
}


def _load_pj_schema() -> dict:
    repo_root = Path(__file__).resolve().parent.parent
    pj_schema = repo_root / "config" / "schemas" / "informe_pj.schema.json"
    assert pj_schema.exists(), f"falta {pj_schema}"
    return json.loads(pj_schema.read_text())


def test_json_schema_pj_required_sync_com_pydantic():
    """JSON Schema PJ deve listar mesmas required do Pydantic."""
    doc = _load_pj_schema()
    assert doc["$id"] == "informe_pj.schema.json"
    assert set(doc["required"]) == _PJ_REQUIRED


def test_json_schema_pj_enum_regime_exclui_lucro_real():
    """Enum regime_tributario sincronizado com RegimeTributarioPJ (LR fora V1)."""
    doc = _load_pj_schema()
    assert set(doc["properties"]["regime_tributario"]["enum"]) == {
        "simples_nacional",
        "lucro_presumido",
    }


def test_json_schema_base_enum_inclui_financeiro_pj():
    """Após L2, JSON Schema base deve aceitar previdencia_privada E financeiro_pj."""
    repo_root = Path(__file__).resolve().parent.parent
    base_schema = repo_root / "config" / "schemas" / "informe_base.schema.json"
    doc = json.loads(base_schema.read_text())
    enum_atual = set(doc["properties"]["tipo_informe"]["enum"])
    assert "financeiro_pj" in enum_atual
    assert "previdencia_privada" in enum_atual


def test_prompt_version_bumpado():
    """PROMPT_VERSION deve ter prefixo informe-pj-v* e sufixo semver."""
    from pipeline.llm.prompts.informe_pj import PROMPT_VERSION

    assert PROMPT_VERSION.startswith("informe-pj-v"), f"PROMPT_VERSION={PROMPT_VERSION!r}"
    # semver tail
    tail = PROMPT_VERSION.replace("informe-pj-v", "")
    assert all(part.isdigit() for part in tail.split(".")), f"semver inválido: {tail}"
