"""A40.l58 §Escopo 4 — tripwire do flip órfão: a suíte valida contrato em `strict`."""

from __future__ import annotations

import os

import scripts.pipeline_common as pc


def test_suite_roda_em_strict_sem_depender_do_ci():
    """O gate de contrato não pode depender de o workflow lembrar de exportar a env — foi assim que `tests/` passou anos validando em `warn` enquanto um único passo do CI cobria 1 arquivo."""
    assert os.environ.get("MATHOMS_PIPELINE_SCHEMA_MODE") == "strict"


def test_modo_efetivo_e_strict_para_schema_sem_override():
    """Prova o efeito, não só a env: é `_effective_schema_validation_mode` que o hook de write consulta."""
    assert pc._effective_schema_validation_mode("e3_reconciled.schema.json") == "strict"


def test_payload_invalido_e_REJEITADO_e_nao_logado_e_passado():
    """A diferença que a chave compra: em `warn` isto devolvia `True` e o drift passava calado."""
    assert pc.validate_dict({"shape": "invalido"}, "e3_reconciled.schema.json") is False
