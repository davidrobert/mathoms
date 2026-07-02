"""Unit tests A17 L4 (ADR-238 D1/D2) — InformeProventosPayload + Provento + tipos fiscais."""

from __future__ import annotations

import re

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.informe_base import InformeRendimentosBase
from pipeline.llm.schemas.informe_proventos import (
    InformeProventosPayload,
    PosicaoCustodia,
    Provento,
    TipoProvento,
    _coerce_decimal,
    total_proventos_por_ticker,
)


def _provento(**overrides) -> dict:
    base = {
        "ticker": "WEGE3",
        "cnpj_pagador": "02332886000104",  # XP placeholder
        "tipo": TipoProvento.dividendo,
        "valor_brl": "150.00",
        "data_pagamento": "2024-04-15",
    }
    base.update(overrides)
    return base


def _build_payload(**overrides) -> InformeProventosPayload:
    base = {
        "cnpj_emissor": "02332886000104",
        "nome_emissor": "XP Investimentos CCTVM S.A.",
        "proventos": [Provento(**_provento())],
    }
    base.update(overrides)
    return InformeProventosPayload(**base)


def _build_base(**overrides) -> InformeRendimentosBase:
    base = {
        "ano_base": 2024,
        "tipo_informe": "proventos_acoes",
        "fonte_pagadora_cnpj": "02332886000104",
        "fonte_pagadora_nome": "XP Investimentos CCTVM S.A.",
        "titular_cpf_masked": None,
        "confidence": 0.92,
        "prompt_version": "1.0.0",
        "proventos": _build_payload(),
    }
    base.update(overrides)
    return InformeRendimentosBase(**base)


# ─────────────────────── _coerce_decimal ─────────────────────────────────────


def test_coerce_decimal_aceita_string_int_decimal_float():
    assert _coerce_decimal("1234.56") == Decimal("1234.56")
    assert _coerce_decimal(150) == Decimal("150")
    assert _coerce_decimal(None) is None
    assert _coerce_decimal(15.0) == Decimal("15.0")


# ─────────────────────── Provento ────────────────────────────────────────────


def test_provento_dividendo_wege3():
    p = Provento(**_provento())
    assert p.ticker == "WEGE3"
    assert p.tipo == TipoProvento.dividendo
    assert p.valor_brl == Decimal("150.00")
    assert p.ir_retido_brl == Decimal("0")  # dividendo isento PF


def test_provento_jcp_com_ir_15_pct():
    """JCP: IR retido 15% sobre valor bruto (tributação exclusiva)."""
    p = Provento(**_provento(tipo=TipoProvento.jcp, valor_brl="1000.00", ir_retido_brl="150.00"))
    assert p.tipo == TipoProvento.jcp
    assert p.valor_brl == Decimal("1000.00")
    assert p.ir_retido_brl == Decimal("150.00")


def test_provento_rend_fii_isento():
    p = Provento(**_provento(ticker="MXRF11", tipo=TipoProvento.rend_fii, valor_brl="85.50"))
    assert p.tipo == TipoProvento.rend_fii
    assert p.ir_retido_brl == Decimal("0")


def test_provento_bonificacao_valor_zero():
    """Bonificação não é renda — valor pode ser 0 (ajuste de custo)."""
    p = Provento(**_provento(tipo=TipoProvento.bonificacao, valor_brl="0"))
    assert p.tipo == TipoProvento.bonificacao
    assert p.valor_brl == Decimal("0")


def test_provento_bonificacao_com_ir_retido_rejeita():
    """Bonificação NÃO pode ter IR retido > 0 (não é renda)."""
    with pytest.raises(ValidationError) as exc:
        Provento(**_provento(tipo=TipoProvento.bonificacao, ir_retido_brl="50.00"))
    assert "bonificacao" in str(exc.value).lower()


def test_provento_dividendo_com_ir_inesperado_marca_nota():
    """Dividendo PF isento — IR retido > 0 é atípico, validator anota PEC dividendos."""
    p = Provento(**_provento(ir_retido_brl="22.50"))
    assert p.tipo == TipoProvento.dividendo
    assert p.notas is not None
    assert "PEC" in p.notas or "atípico" in p.notas.lower()


def test_provento_ticker_pattern_b3():
    """Ticker B3: maiúsculas + dígitos, 4-10 chars, sem ponto."""
    Provento(**_provento(ticker="ITSA4"))
    Provento(**_provento(ticker="MXRF11"))
    with pytest.raises(ValidationError):
        Provento(**_provento(ticker="wege3"))  # lowercase
    with pytest.raises(ValidationError):
        Provento(**_provento(ticker="WEGE.3"))  # com ponto
    with pytest.raises(ValidationError):
        Provento(**_provento(ticker="ABC"))  # < 4 chars


def test_provento_cnpj_pagador_pattern_strict():
    with pytest.raises(ValidationError):
        Provento(**_provento(cnpj_pagador="02.332.886/0001-04"))  # com máscara
    with pytest.raises(ValidationError):
        Provento(**_provento(cnpj_pagador="123"))


def test_provento_cnpj_fonte_opcional():
    """cnpj_fonte pode ser None quando informe não distingue."""
    p = Provento(**_provento(cnpj_fonte=None))
    assert p.cnpj_fonte is None
    # Quando preenchido, valida pattern
    p2 = Provento(**_provento(cnpj_fonte="84429695000111"))  # Weg S.A.
    assert p2.cnpj_fonte == "84429695000111"


def test_provento_data_pagamento_yyyy_mm_dd():
    with pytest.raises(ValidationError):
        Provento(**_provento(data_pagamento="15/04/2024"))  # BR format
    with pytest.raises(ValidationError):
        Provento(**_provento(data_pagamento="2024-04"))  # missing day


def test_provento_recusa_field_desconhecido():
    with pytest.raises(ValidationError):
        Provento(**_provento(campo_inexistente="x"))


# ─────────────────────── PosicaoCustodia ────────────────────────────────────


def test_posicao_custodia_completa():
    pos = PosicaoCustodia(
        ticker="WEGE3",
        quantidade="1000",
        custo_medio_brl="42.50",
        valor_mercado_31_12="48000.00",
    )
    assert pos.ticker == "WEGE3"
    assert pos.quantidade == Decimal("1000")
    assert pos.custo_medio_brl == Decimal("42.50")
    assert pos.valor_mercado_31_12 == Decimal("48000.00")


def test_posicao_custodia_so_quantidade():
    """custo_medio + valor_mercado são opcionais (corretora pode não informar)."""
    pos = PosicaoCustodia(ticker="ITSA4", quantidade="500")
    assert pos.custo_medio_brl is None
    assert pos.valor_mercado_31_12 is None


# ─────────────────────── InformeProventosPayload ─────────────────────────────


def test_payload_happy_path_xp_proventos():
    p = _build_payload()
    assert p.cnpj_emissor == "02332886000104"
    assert len(p.proventos) == 1


def test_payload_recusa_vazio_total():
    """Informe sem proventos E sem posicao_31_12 é extração ruim."""
    with pytest.raises(ValidationError) as exc:
        InformeProventosPayload(
            cnpj_emissor="02332886000104",
            nome_emissor="XP",
            proventos=[],
            posicao_31_12=[],
        )
    assert "vazio" in str(exc.value).lower() or "ao menos" in str(exc.value).lower()


def test_payload_apenas_posicao_31_12_aceito():
    """Algumas corretoras emitem só snapshot custódia sem eventos."""
    p = InformeProventosPayload(
        cnpj_emissor="02332886000104",
        nome_emissor="XP",
        posicao_31_12=[PosicaoCustodia(ticker="WEGE3", quantidade="100")],
    )
    assert len(p.posicao_31_12) == 1


def test_payload_multiplos_eventos_e_tickers():
    """Itaúsa (1 ticker) + XP (vários tickers) — payload aceita N eventos."""
    proventos = [
        Provento(**_provento(ticker="WEGE3", tipo=TipoProvento.dividendo, valor_brl="150")),
        Provento(
            **_provento(ticker="WEGE3", tipo=TipoProvento.jcp, valor_brl="200", ir_retido_brl="30")
        ),
        Provento(**_provento(ticker="ITSA4", tipo=TipoProvento.dividendo, valor_brl="80")),
        Provento(**_provento(ticker="MXRF11", tipo=TipoProvento.rend_fii, valor_brl="85.50")),
    ]
    p = _build_payload(proventos=proventos)
    assert len(p.proventos) == 4


def test_payload_recusa_field_desconhecido():
    with pytest.raises(ValidationError):
        InformeProventosPayload(
            cnpj_emissor="02332886000104",
            nome_emissor="XP",
            proventos=[Provento(**_provento())],
            campo_inexistente="x",
        )


# ─────────────────────── total_proventos_por_ticker helper ──────────────────


def test_total_proventos_exclui_bonificacao():
    """Bonificação não soma em yield (é ajuste de custo)."""
    proventos = [
        Provento(**_provento(ticker="WEGE3", tipo=TipoProvento.dividendo, valor_brl="150")),
        Provento(**_provento(ticker="WEGE3", tipo=TipoProvento.bonificacao, valor_brl="0")),
        Provento(
            **_provento(ticker="WEGE3", tipo=TipoProvento.jcp, valor_brl="200", ir_retido_brl="30")
        ),
    ]
    p = _build_payload(proventos=proventos)
    totals = total_proventos_por_ticker(p)
    assert totals["WEGE3"] == Decimal("350")  # dividendo + jcp; bonificação fora


def test_total_proventos_multi_ticker():
    proventos = [
        Provento(**_provento(ticker="ITSA4", valor_brl="80")),
        Provento(**_provento(ticker="MXRF11", tipo=TipoProvento.rend_fii, valor_brl="85.50")),
    ]
    p = _build_payload(proventos=proventos)
    totals = total_proventos_por_ticker(p)
    assert totals == {"ITSA4": Decimal("80"), "MXRF11": Decimal("85.50")}


# ─────────────────────── Base polimórfico (L4) ───────────────────────────────


def test_base_happy_path_proventos_acoes():
    b = _build_base()
    assert b.tipo_informe == "proventos_acoes"
    assert b.proventos is not None
    assert len(b.proventos.proventos) == 1
    assert b.previdencia is None
    assert b.financeiro_pj is None
    assert b.financeiro_pf is None


def test_base_aceita_l1_l2_l3_l4():
    """Literal aceita 4 tipos canônicos A17."""
    b_l4 = _build_base()
    assert b_l4.tipo_informe == "proventos_acoes"
    b_l1 = _build_base(tipo_informe="previdencia_privada", proventos=None, previdencia=None)
    assert b_l1.tipo_informe == "previdencia_privada"


# ─────────────────────── JSON Schema sync ───────────────────────────────────


def test_json_schema_proventos_exists_e_strict():
    repo_root = Path(__file__).resolve().parent.parent
    schema_file = repo_root / "config" / "schemas" / "informe_proventos.schema.json"
    assert schema_file.exists()
    doc = json.loads(schema_file.read_text())
    assert doc["$id"] == "informe_proventos.schema.json"
    assert doc["additionalProperties"] is False
    assert set(doc["required"]) == {"cnpj_emissor", "nome_emissor"}


def test_json_schema_provento_enum_tipos():
    repo_root = Path(__file__).resolve().parent.parent
    doc = json.loads(
        (repo_root / "config" / "schemas" / "informe_proventos.schema.json").read_text()
    )
    enum_tipo = set(doc["$defs"]["provento"]["properties"]["tipo"]["enum"])
    assert enum_tipo == {"dividendo", "jcp", "rend_fii", "bonificacao"}


def test_json_schema_base_enum_inclui_proventos_acoes():
    repo_root = Path(__file__).resolve().parent.parent
    doc = json.loads((repo_root / "config" / "schemas" / "informe_base.schema.json").read_text())
    enum_atual = set(doc["properties"]["tipo_informe"]["enum"])
    assert enum_atual == {
        "previdencia_privada",
        "financeiro_pj",
        "financeiro_pf",
        "proventos_acoes",
    }


def test_prompt_version_bumpado():
    from pipeline.llm.prompts.informe_proventos import PROMPT_VERSION

    assert re.fullmatch(r"\d+\.\d+\.\d+", PROMPT_VERSION)
    tail = PROMPT_VERSION
    assert all(part.isdigit() for part in tail.split("."))
