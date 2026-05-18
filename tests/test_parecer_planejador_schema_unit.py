"""Unit tests do schema do parecer planejador — boundary do LLM (ADR-202/207)."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from pipeline.llm.schemas.parecer_planejador import Confianca, Risco, Sugestao

_CONFIANCA = TypeAdapter(Confianca)


def _risco(**overrides) -> dict:
    base = dict(
        severidade="Alta",
        titulo="Titulo de teste",
        descricao="Descricao curta de teste sem ticker nem sigilo.",
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        section_id="S1",
        confianca="alta",
    )
    base.update(overrides)
    return base


def _sugestao(**overrides) -> dict:
    base = dict(
        prioridade="P1",
        acao="Acao sugerida de teste com pelo menos dez caracteres.",
        impacto_qualitativo="Impacto qualitativo de teste com pelo menos dez caracteres.",
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        confianca="alta",
        section_id="S1",
        suggestion_dedup_key="0" * 64,
    )
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("alta", "alta"),
        ("media", "media"),
        ("baixa", "baixa"),
        ("média", "media"),  # PT natural — regressão prod 2026-05-18 run 98e60bef
        ("Média", "media"),
        ("MÉDIA", "media"),
        ("Alta", "alta"),
        ("BAIXA", "baixa"),
    ],
)
def test_confianca_normaliza_acento_e_caixa(raw, expected):
    """Boundary do LLM aceita acento + caixa, canoniza para lowercase ASCII."""
    assert _CONFIANCA.validate_python(raw) == expected


def test_confianca_rejeita_valor_invalido():
    with pytest.raises(ValueError):
        _CONFIANCA.validate_python("provavelmente alta")


def test_risco_aceita_confianca_com_acento_regressao_prod_2026_05_18():
    """Regressão run 98e60bef: LLM emitia `\"confianca\": \"média\"` (acento PT natural) e 4 retries falhavam contra Literal['alta','media','baixa']."""
    r = Risco(**_risco(confianca="média"))
    assert r.confianca == "media"


def test_sugestao_aceita_confianca_com_acento():
    s = Sugestao(**_sugestao(confianca="média"))
    assert s.confianca == "media"


def test_sugestao_normaliza_antes_de_checar_impacto_estimado_so_alta():
    """ADR-202 §D6: impacto_estimado só permitido com confianca='alta'. Coerção
    'Alta' → 'alta' deve preservar a invariante."""
    payload = _sugestao(confianca="Alta")
    payload["impacto_estimado"] = {
        "valor_estimado_brl": 1000.0,
        "unidade": "ano",
        "caveat": "Estimativa indicativa baseada em premissas conservadoras.",
    }
    s = Sugestao(**payload)
    assert s.confianca == "alta"
    assert s.impacto_estimado is not None
