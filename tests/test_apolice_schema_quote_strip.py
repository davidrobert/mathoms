"""Regressão prod 2026-05-22 — Haiku gera ``'"4509.98"'`` (aspas literais no valor) determinístico em todas apólices. Schema agora descasca via model_validator antes do Pydantic strict-parse; prompt instrui formato sem aspas internas (apolice-v1.1.0)."""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.prompts import apolice as prompt_mod
from pipeline.llm.schemas.apolice import (
    PROMPT_VERSION,
    ApolicePayload,
    _strip_spurious_quotes,
)

# ─────────────────────── helper puro ─────────────────────────────────────


def test_strip_quotes_idempotente_em_string_sem_aspas():
    assert _strip_spurious_quotes("4509.98") == "4509.98"
    assert _strip_spurious_quotes("cartao") == "cartao"


def test_strip_quotes_remove_aspas_duplas_e_simples_nas_pontas():
    assert _strip_spurious_quotes('"4509.98"') == "4509.98"
    assert _strip_spurious_quotes("'4509.98'") == "4509.98"


def test_strip_quotes_nao_remove_aspas_no_meio():
    """Aspa no meio (improvável mas possível em nome) não é tocada."""
    assert _strip_spurious_quotes('4"509.98') == '4"509.98'
    assert _strip_spurious_quotes('Foo "Bar" Baz') == 'Foo "Bar" Baz'


def test_strip_quotes_cascata_recursiva_em_dict():
    """Strip cobre sub-models e listas aninhadas (Cobertura* dentro de BemSegurado*)."""
    payload = {
        "premio_total_brl": '"100.00"',
        "bens": [{"premio_brl": '"50.00"', "tipo": '"veiculo"'}],
    }
    out = _strip_spurious_quotes(payload)
    assert out["premio_total_brl"] == "100.00"
    assert out["bens"][0]["premio_brl"] == "50.00"
    assert out["bens"][0]["tipo"] == "veiculo"


def test_strip_quotes_passthrough_para_tipos_nao_string():
    """Int/float/bool/None passam intactos (defesa em profundidade)."""
    assert _strip_spurious_quotes(42) == 42
    assert _strip_spurious_quotes(0.95) == 0.95
    assert _strip_spurious_quotes(None) is None
    assert _strip_spurious_quotes(True) is True


# ─────────────────────── ApolicePayload end-to-end ───────────────────────


_BASE_COBERTURA = {
    "tipo": "material",
    "nome": "Casco",
    "lmi_modo": "valor_fixo",
    "lmi_brl": "50000.00",
    "premio_brl": "2000.00",
}
_BASE_CORRETOR = {
    "susep_code": "123456",
    "nome": "Corretora ABC",
    "cpf_or_cnpj": "12345678000190",
    "cnpj_or_cpf_kind": "cnpj",
}


def _bem_veiculo(tipo_bem="veiculo"):
    return {
        "tipo": tipo_bem,
        "placa": "ABC1D23",
        "marca": "Toyota",
        "modelo": "Corolla",
        "ano_modelo": 2024,
        "coberturas": [dict(_BASE_COBERTURA)],
    }


def _apolice_minima(*, premio_total_brl="4509.98", forma_pagamento="cartao", tipo_bem="veiculo"):
    """Payload mínimo válido — caller injeta aspas spurious onde precisar."""
    return {
        "apolice_numero": "ABC-1",
        "seguradora": "porto",
        "vigencia_inicio": "2026-03-01",
        "vigencia_fim": "2027-03-01",
        "premio_total_brl": premio_total_brl,
        "forma_pagamento": forma_pagamento,
        "corretor": dict(_BASE_CORRETOR),
        "bens_segurados": [_bem_veiculo(tipo_bem)],
        "confidence": 0.95,
    }


def test_payload_aceita_premio_com_aspas_spurious():
    """Reproduce do bug prod: ``premio_total_brl='"4509.98"'`` deve virar Decimal('4509.98')."""
    p = ApolicePayload.model_validate(_apolice_minima(premio_total_brl='"4509.98"'))
    assert p.premio_total_brl == Decimal("4509.98")


def test_payload_aceita_literal_com_aspas_spurious():
    """``forma_pagamento='"cartao"'`` deve descascar antes de Literal validation."""
    p = ApolicePayload.model_validate(_apolice_minima(forma_pagamento='"cartao"'))
    assert p.forma_pagamento == "cartao"


def test_payload_aceita_discriminator_com_aspas_spurious():
    """``tipo='"veiculo"'`` ainda deve resolver BemSeguradoVeiculo do Union."""
    p = ApolicePayload.model_validate(_apolice_minima(tipo_bem='"veiculo"'))
    assert p.bens_segurados[0].tipo == "veiculo"


def test_payload_aceita_aspas_em_subfield_cobertura():
    """Sub-models (CoberturaMaterial.premio_brl) também limpos via recursão."""
    data = _apolice_minima()
    data["bens_segurados"][0]["coberturas"][0]["premio_brl"] = '"2000.00"'
    data["bens_segurados"][0]["coberturas"][0]["lmi_brl"] = '"50000.00"'
    p = ApolicePayload.model_validate(data)
    cov = p.bens_segurados[0].coberturas[0]
    assert cov.premio_brl == Decimal("2000.00")
    assert cov.lmi_brl == Decimal("50000.00")


# ─────────────────────── Strict-mode regression (incidente 2026-05-22 v2) ───
# Instructor TOOLS mode chama ``model_validate_json(strict=True)`` (default
# ``strict=True`` no client). O ``model_validator(mode="before")`` de v1.1.0
# quebrava a coerção JSON-nativa de Pydantic strict — strings ISO/decimal
# eram rejeitadas com ``type=date_type``/``type=is_instance_of``. v1.1.1
# acrescentou ``BeforeValidator`` por campo restaurando aceitação.


def test_strict_json_aceita_iso_dates():
    """Path Instructor: ``model_validate_json(strict=True)`` aceita ISO dates."""
    import json

    data = _apolice_minima()
    p = ApolicePayload.model_validate_json(json.dumps(data), strict=True)
    assert str(p.vigencia_inicio) == "2026-03-01"
    assert str(p.vigencia_fim) == "2027-03-01"


def test_strict_json_aceita_decimal_strings():
    """Path Instructor: strings decimais (formato ADR-090 wire) viram Decimal."""
    import json

    data = _apolice_minima(premio_total_brl="4509.98")
    p = ApolicePayload.model_validate_json(json.dumps(data), strict=True)
    assert p.premio_total_brl == Decimal("4509.98")
    assert p.bens_segurados[0].coberturas[0].premio_brl == Decimal("2000.00")
    assert p.bens_segurados[0].coberturas[0].lmi_brl == Decimal("50000.00")


def test_strict_json_aceita_decimal_quoted():
    """Path Instructor + Haiku quote-wrap (combinado v1.1.0 + v1.1.1)."""
    import json

    data = _apolice_minima(premio_total_brl='"4509.98"')
    p = ApolicePayload.model_validate_json(json.dumps(data), strict=True)
    assert p.premio_total_brl == Decimal("4509.98")


def test_strict_dict_aceita_iso_e_decimal():
    """Path alternativo de Instructor: ``model_validate(dict, strict=True)``."""
    data = _apolice_minima()
    p = ApolicePayload.model_validate(data, strict=True)
    assert str(p.vigencia_inicio) == "2026-03-01"
    assert p.premio_total_brl == Decimal("4509.98")


# ─────────────────────── prompt smoke (anti-regressão) ───────────────────


def test_prompt_version_aligned():
    """Schema + prompt mod usam mesma versão (bump pareado, ADR-144)."""
    assert PROMPT_VERSION == prompt_mod.PROMPT_VERSION == "1.1.1"


_EX_DECIMAL_QUOTED = re.compile(r"Ex\.:\s*`\"[\d\.]+\"`")


def test_prompt_evita_padrao_Ex_aspas_decimal():
    """Prompt não deve conter ``Ex.: `"<digits>"``` — esse era o padrão que induzia o
    Haiku a copiar as aspas literalmente para o valor JSON (causa raiz prod 2026-05-22).
    Aspas em demonstração do JSON serializado completo (linha §JSON format) continuam
    permitidas — elas mostram contexto, não conteúdo de campo."""
    matches = _EX_DECIMAL_QUOTED.findall(prompt_mod.SYSTEM_PROMPT)
    assert not matches, (
        f"Prompt apolice contém exemplo numérico com aspas: {matches}. "
        f"Use 'Conteúdo: 1500.00' (sem aspas) em vez de 'Ex.: \"1500.00\"'."
    )
