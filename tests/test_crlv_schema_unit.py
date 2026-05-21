"""A18 L1 P2 (ADR-239) — schema CRLVPayload + normalização de placa + LGPD."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.crlv import (
    PROMPT_VERSION,
    CRLVPayload,
)


def _build(**overrides) -> CRLVPayload:
    base = {
        "placa": "ABC1D23",
        "renavam": "12345678900",
        "marca": "Yamaha",
        "modelo": "NMAX 160 ABS",
        "ano_modelo": 2024,
        "ano_fabricacao": 2024,
        "cor": "preta",
        "combustivel": "gasolina",
        "exercicio": 2026,
        "categoria": "particular",
        "uf_emplacamento": "SP",
        "data_emissao": date(2026, 3, 15),
        "confidence": 0.95,
    }
    base.update(overrides)
    return CRLVPayload(**base)


# ─────────────────────── Placa: Mercosul + legado ──────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ABC1D23", "ABC1D23"),  # Mercosul já normalizada
        ("abc1d23", "ABC1D23"),  # lowercase → upper
        ("ABC-1234", "ABC1234"),  # legado com hífen
        ("ABC 1234", "ABC1234"),  # com espaço
    ],
)
def test_placa_normalizada(raw, expected):
    p = _build(placa=raw)
    assert p.placa == expected


@pytest.mark.parametrize(
    "invalida",
    [
        "AB1D23",  # 2 letras
        "ABCD123",  # 4 letras
        "123ABCD",  # ordem invertida
        "",
    ],
)
def test_placa_recusa_formato_invalido(invalida):
    with pytest.raises(ValidationError):
        _build(placa=invalida)


# ─────────────────────── RENAVAM ──────────────────────────────────────────


@pytest.mark.parametrize("raw", ["123456789", "12345678900", "12345678901"])
def test_renavam_aceita_9_a_11_digitos(raw):
    p = _build(renavam=raw)
    assert p.renavam == raw


@pytest.mark.parametrize(
    "invalido",
    ["12345678", "123456789012", "abc456789", "1234-5678", ""],
)
def test_renavam_recusa_formato_invalido(invalido):
    with pytest.raises(ValidationError):
        _build(renavam=invalido)


# ─────────────────────── CPF do proprietário (LGPD) ────────────────────────


def test_cpf_masked_default_none():
    """LGPD ADR-231: SYSTEM_PROMPT força null; Python pós-LLM extrai e mascara."""
    p = _build()
    assert p.proprietario_cpf_masked is None


def test_cpf_masked_aceita_padrao():
    p = _build(proprietario_cpf_masked="***.456.789-**")
    assert p.proprietario_cpf_masked == "***.456.789-**"


def test_cpf_masked_recusa_cpf_completo():
    with pytest.raises(ValidationError):
        _build(proprietario_cpf_masked="12345678900")


# ─────────────────────── UF + ano ranges ───────────────────────────────────


def test_uf_dois_caracteres_maiusculos():
    p = _build(uf_emplacamento="RJ")
    assert p.uf_emplacamento == "RJ"
    with pytest.raises(ValidationError):
        _build(uf_emplacamento="rj")  # lowercase
    with pytest.raises(ValidationError):
        _build(uf_emplacamento="SAO")  # 3 letras


def test_ano_modelo_range():
    with pytest.raises(ValidationError):
        _build(ano_modelo=1899)
    with pytest.raises(ValidationError):
        _build(ano_modelo=2101)


def test_exercicio_apenas_2000_em_diante():
    with pytest.raises(ValidationError):
        _build(exercicio=1999)


# ─────────────────────── PROMPT_VERSION default ────────────────────────────


def test_prompt_version_default_alinhado_ao_modulo():
    p = _build()
    assert p.prompt_version == PROMPT_VERSION
    assert PROMPT_VERSION == "crlv-v1.0.0"


# ─────────────────────── Strict (extra='forbid') ───────────────────────────


def test_recusa_campo_desconhecido():
    """Strict — protege contra schema drift do LLM (futuro: drift de versão DENATRAN)."""
    with pytest.raises(ValidationError):
        CRLVPayload(
            placa="ABC1D23",
            renavam="12345678900",
            marca="Yamaha",
            modelo="NMAX",
            ano_modelo=2024,
            ano_fabricacao=2024,
            exercicio=2026,
            categoria="particular",
            confidence=0.9,
            campo_inexistente="drift",
        )


# ─────────────────────── JSON Schema sync ─────────────────────────────────


def test_json_schema_arquivo_existe_e_parseia():
    repo_root = Path(__file__).resolve().parent.parent
    schema_path = repo_root / "config" / "schemas" / "crlv.schema.json"
    assert schema_path.exists()
    doc = json.loads(schema_path.read_text())
    assert doc["$id"] == "crlv.schema.json"
    # required deve cobrir os campos obrigatórios do Pydantic
    required = set(doc["required"])
    assert {"placa", "renavam", "marca", "modelo", "ano_modelo", "exercicio"} <= required


def test_db_artifact_store_registra_schema():
    from backend.app.services.db_artifact_store import SCHEMA_BY_STAGE

    assert SCHEMA_BY_STAGE["extract_comprovantes_bens"] == "crlv.schema.json"


def test_db_artifact_store_workspace_scoped():
    from backend.app.services.db_artifact_store import _WORKSPACE_SCOPED_STAGES

    assert "extract_comprovantes_bens" in _WORKSPACE_SCOPED_STAGES
