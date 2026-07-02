"""Unit tests A17 L3 P1 (ADR-238) — InformeFinanceiroPFPayload + base polimórfico + Wise."""

from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.informe_base import InformeRendimentosBase
from pipeline.llm.schemas.informe_pf import (
    InformeFinanceiroPFPayload,
    QuadroEntry,
    SaldoProduto,
    TipoProduto,
    _coerce_decimal,
    has_conta_exterior,
)


def _quadro_dom(**overrides) -> dict:
    base = {
        "codigo_rfb": "12",
        "fonte_pagadora_cnpj": "60746948000112",
        "fonte_pagadora_nome": "Itaú Unibanco S.A.",
        "descricao": "Rendimentos de aplicação financeira",
        "valor": "1500.00",
    }
    base.update(overrides)
    return base


def _quadro_wise(**overrides) -> dict:
    base = {
        "codigo_rfb": "62",
        "fonte_pagadora_cnpj": "23945200000115",  # Wise Brasil placeholder
        "fonte_pagadora_nome": "Wise Brasil Corretora de Câmbio",
        "descricao": "Conta-corrente em moeda estrangeira",
        "valor": "1000.00",
        "moeda": "USD",
    }
    base.update(overrides)
    return base


def _saldo_dom(**overrides) -> dict:
    base = {
        "tipo": TipoProduto.cdb,
        "descricao": "CDB DI 100% Itaú 90 dias",
        "codigo_rfb": "70",
        "saldo": "5000.00",
        "fonte_pagadora_cnpj": "60746948000112",
    }
    base.update(overrides)
    return base


def _saldo_wise(**overrides) -> dict:
    base = {
        "tipo": TipoProduto.conta_exterior,
        "descricao": "Wise USD account",
        "codigo_rfb": "62",
        "saldo": "1000.00",
        "moeda": "USD",
        "fonte_pagadora_cnpj": "23945200000115",
    }
    base.update(overrides)
    return base


def _build_payload(**overrides) -> InformeFinanceiroPFPayload:
    base = {
        "cnpj_emissor": "60746948000112",
        "nome_emissor": "Itaú Unibanco S.A.",
        "rendimentos_tributaveis": [QuadroEntry(**_quadro_dom())],
        "saldos_31_12": [SaldoProduto(**_saldo_dom())],
    }
    base.update(overrides)
    return InformeFinanceiroPFPayload(**base)


def _build_base(**overrides) -> InformeRendimentosBase:
    base = {
        "ano_base": 2024,
        "tipo_informe": "financeiro_pf",
        "fonte_pagadora_cnpj": "60746948000112",
        "fonte_pagadora_nome": "Itaú Unibanco S.A.",
        "titular_cpf_masked": None,
        "confidence": 0.92,
        "source_artifact_id": "art_pf_001",
        "prompt_version": "1.0.0",
        "financeiro_pf": _build_payload(),
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


# ─────────────────────── QuadroEntry ────────────────────────────────────────


def test_quadro_entry_happy_path_doméstico_brl():
    q = QuadroEntry(**_quadro_dom(valor="1500.00", ir_retido="225.00"))
    assert q.codigo_rfb == "12"
    assert q.valor == Decimal("1500.00")
    assert q.ir_retido == Decimal("225.00")
    assert q.moeda == "BRL"  # default


def test_quadro_entry_wise_codigo_62_moeda_usd():
    """Wise: codigo_rfb=62 + moeda=USD em bens_direitos."""
    q = QuadroEntry(**_quadro_wise())
    assert q.codigo_rfb == "62"
    assert q.moeda == "USD"
    assert q.valor == Decimal("1000.00")


def test_quadro_entry_moeda_iso_4217_pattern():
    """Moeda deve ser 3 letras maiúsculas (ISO 4217)."""
    with pytest.raises(ValidationError):
        QuadroEntry(**_quadro_dom(moeda="usd"))  # lowercase
    with pytest.raises(ValidationError):
        QuadroEntry(**_quadro_dom(moeda="R$"))  # símbolo
    with pytest.raises(ValidationError):
        QuadroEntry(**_quadro_dom(moeda="REAIS"))  # 5 chars


def test_quadro_entry_ir_retido_default_zero():
    q = QuadroEntry(**_quadro_dom())
    assert q.ir_retido == Decimal("0")


def test_quadro_entry_recusa_field_desconhecido():
    """Strict extra='forbid'."""
    with pytest.raises(ValidationError):
        QuadroEntry(**_quadro_dom(campo_inexistente="x"))


def test_quadro_entry_cnpj_pattern_strict():
    with pytest.raises(ValidationError):
        QuadroEntry(**_quadro_dom(fonte_pagadora_cnpj="60.746.948/0001-12"))  # com máscara


# ─────────────────────── SaldoProduto ───────────────────────────────────────


def test_saldo_produto_happy_path_cdb_domestico():
    s = SaldoProduto(**_saldo_dom())
    assert s.tipo == TipoProduto.cdb
    assert s.codigo_rfb == "70"
    assert s.moeda == "BRL"


def test_saldo_produto_conta_exterior_wise_usd():
    s = SaldoProduto(**_saldo_wise())
    assert s.tipo == TipoProduto.conta_exterior
    assert s.codigo_rfb == "62"
    assert s.moeda == "USD"


def test_saldo_codigo_62_exige_tipo_conta_exterior():
    """Validator: codigo_rfb=62 + tipo doméstico = inconsistência."""
    with pytest.raises(ValidationError) as exc:
        SaldoProduto(**_saldo_wise(tipo=TipoProduto.cdb))
    assert "codigo_rfb=62" in str(exc.value) or "conta_exterior" in str(exc.value).lower()


def test_saldo_conta_exterior_exige_moeda_nao_brl():
    """Validator: tipo=conta_exterior + moeda=BRL = inconsistência."""
    with pytest.raises(ValidationError) as exc:
        SaldoProduto(**_saldo_wise(moeda="BRL"))
    assert "conta_exterior" in str(exc.value).lower() or "moeda" in str(exc.value).lower()


def test_saldo_dom_cdb_aceita_brl_default():
    """CDB doméstico com moeda BRL default → válido."""
    s = SaldoProduto(**_saldo_dom())
    assert s.moeda == "BRL"


def test_saldo_tipo_outros_aceito_quando_ambiguo():
    s = SaldoProduto(**_saldo_dom(tipo=TipoProduto.outros))
    assert s.tipo == TipoProduto.outros


# ─────────────────────── InformeFinanceiroPFPayload ─────────────────────────


def test_payload_happy_path_um_quadro_um_saldo():
    p = _build_payload()
    assert p.cnpj_emissor == "60746948000112"
    assert len(p.rendimentos_tributaveis) == 1
    assert len(p.saldos_31_12) == 1


def test_payload_recusa_quadros_todos_empty():
    """ao_menos_um_quadro_nao_vazio validator."""
    with pytest.raises(ValidationError) as exc:
        InformeFinanceiroPFPayload(
            cnpj_emissor="60746948000112",
            nome_emissor="Itaú",
            rendimentos_tributaveis=[],
            rendimentos_isentos=[],
            rendimentos_exclusiva=[],
            bens_direitos=[],
            saldos_31_12=[],
        )
    assert "vazio" in str(exc.value).lower() or "quadro" in str(exc.value).lower()


def test_payload_apenas_bens_direitos_aceito():
    """Wise pode emitir só bens_direitos + saldos, sem rendimentos."""
    p = InformeFinanceiroPFPayload(
        cnpj_emissor="23945200000115",
        nome_emissor="Wise",
        bens_direitos=[QuadroEntry(**_quadro_wise())],
        saldos_31_12=[SaldoProduto(**_saldo_wise())],
    )
    assert len(p.bens_direitos) == 1
    assert len(p.saldos_31_12) == 1


def test_payload_4_quadros_populados():
    p = InformeFinanceiroPFPayload(
        cnpj_emissor="60746948000112",
        nome_emissor="Itaú",
        rendimentos_tributaveis=[QuadroEntry(**_quadro_dom(codigo_rfb="12"))],
        rendimentos_isentos=[QuadroEntry(**_quadro_dom(codigo_rfb="01"))],
        rendimentos_exclusiva=[QuadroEntry(**_quadro_dom(codigo_rfb="06"))],
        bens_direitos=[QuadroEntry(**_quadro_dom(codigo_rfb="41"))],
        saldos_31_12=[SaldoProduto(**_saldo_dom())],
    )
    assert len(p.rendimentos_tributaveis) == 1
    assert len(p.rendimentos_isentos) == 1
    assert len(p.rendimentos_exclusiva) == 1
    assert len(p.bens_direitos) == 1


def test_payload_recusa_field_desconhecido():
    with pytest.raises(ValidationError):
        InformeFinanceiroPFPayload(
            cnpj_emissor="60746948000112",
            nome_emissor="Itaú",
            saldos_31_12=[SaldoProduto(**_saldo_dom())],
            campo_inexistente="x",
        )


# ─────────────────────── has_conta_exterior helper ──────────────────────────


def test_has_conta_exterior_true_para_wise():
    p = InformeFinanceiroPFPayload(
        cnpj_emissor="23945200000115",
        nome_emissor="Wise",
        bens_direitos=[QuadroEntry(**_quadro_wise())],
        saldos_31_12=[SaldoProduto(**_saldo_wise())],
    )
    assert has_conta_exterior(p) is True


def test_has_conta_exterior_false_para_dom():
    p = _build_payload()
    assert has_conta_exterior(p) is False


def test_has_conta_exterior_codigo_62_em_bens_sem_saldo():
    """Detecta exterior mesmo se só bens_direitos[] declarou (sem saldos_31_12 redundante)."""
    p = InformeFinanceiroPFPayload(
        cnpj_emissor="23945200000115",
        nome_emissor="Wise",
        bens_direitos=[QuadroEntry(**_quadro_wise())],
    )
    assert has_conta_exterior(p) is True


# ─────────────────────── Base polimórfico (L3) ──────────────────────────────


def test_base_happy_path_financeiro_pf():
    b = _build_base()
    assert b.tipo_informe == "financeiro_pf"
    assert b.financeiro_pf is not None
    assert b.financeiro_pf.cnpj_emissor == "60746948000112"
    assert b.previdencia is None
    assert b.financeiro_pj is None


def test_base_aceita_l1_l2_l3():
    """Literal aceita todos os tipos atuais."""
    b_pf = _build_base()
    assert b_pf.tipo_informe == "financeiro_pf"
    b_l1 = _build_base(tipo_informe="previdencia_privada", financeiro_pf=None, previdencia=None)
    assert b_l1.tipo_informe == "previdencia_privada"
    b_l2 = _build_base(tipo_informe="financeiro_pj", financeiro_pf=None, financeiro_pj=None)
    assert b_l2.tipo_informe == "financeiro_pj"


def test_base_lenient_top_level_aceita_extra():
    b = InformeRendimentosBase(
        ano_base=2024,
        tipo_informe="financeiro_pf",
        fonte_pagadora_cnpj="60746948000112",
        fonte_pagadora_nome="Itaú",
        confidence=0.9,
        prompt_version="1.0.0",
        financeiro_pf=_build_payload(),
        campo_futuro="ok",  # extra='allow' no base
    )
    assert b.tipo_informe == "financeiro_pf"


# ─────────────────────── JSON Schema sync ───────────────────────────────────


def test_json_schema_pf_exists_e_strict():
    repo_root = Path(__file__).resolve().parent.parent
    pf_schema = repo_root / "config" / "schemas" / "informe_pf.schema.json"
    assert pf_schema.exists()
    doc = json.loads(pf_schema.read_text())
    assert doc["$id"] == "informe_pf.schema.json"
    assert doc["additionalProperties"] is False
    assert set(doc["required"]) == {"cnpj_emissor", "nome_emissor"}


def test_json_schema_pf_moeda_iso_pattern():
    """Pattern ^[A-Z]{3}$ enforça ISO 4217."""
    repo_root = Path(__file__).resolve().parent.parent
    pf_schema = repo_root / "config" / "schemas" / "informe_pf.schema.json"
    doc = json.loads(pf_schema.read_text())
    moeda_def = doc["$defs"]["moedaISO"]
    assert moeda_def["pattern"] == "^[A-Z]{3}$"
    assert moeda_def["default"] == "BRL"


def test_prompt_version_bumpado():
    from pipeline.llm.prompts.informe_pf import PROMPT_VERSION

    assert re.fullmatch(r"\d+\.\d+\.\d+", PROMPT_VERSION)
    tail = PROMPT_VERSION
    assert all(part.isdigit() for part in tail.split("."))
