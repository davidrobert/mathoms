"""Unit tests do schema do parecer planejador — boundary do LLM (ADR-202/207)."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from pipeline.llm.schemas.parecer_planejador import (
    Ancora,
    CampoFaltante,
    Confianca,
    Risco,
    Sugestao,
)

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


# -----------------------------------------------------------------------
# ADR-292 — coerção de evidencia_path/field_path inválido → None.
# Regressão do incidente parecer 2026-06-16 (workspace 5@5.com): claude-sonnet-4-6
# emitia JSONPath com filtros → pattern hard-fail → reask storm (~243s/needs_review).
# -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_path",
    [
        "$.alocacao_por_classe[?(@.classe=='Caixa')].valor",  # filtro — incidente real
        "$.ativos[?(@.descricao=~'.*Gisele.*')].valor",  # filtro + regex match
        "$..total_liquida",  # recursive descent
        "$.reserva emergencia.total",  # espaço (segmento inválido)
    ],
)
def test_ancora_path_invalido_coerce_para_none(bad_path):
    """ADR-296 reusa o coerce do ADR-292 em Ancora.path."""
    assert Ancora(path=bad_path).path is None


@pytest.mark.parametrize(
    "good_path",
    [
        "$.reserva_emergencia.total_liquida",
        "$.patrimonio.composicao.imoveis_residencia",
        "$.ativos[0].valor",
        "$.alocacao_por_classe[*]",
    ],
)
def test_ancora_path_valido_passa(good_path):
    assert Ancora(path=good_path).path == good_path


@pytest.mark.parametrize(
    "bad_rotulo",
    [
        "tem espaço",  # não-identifier
        "$.reserva_emergencia",  # path, não root
        "x" * 65,  # > 64 chars
        "com-hifen",  # não-identifier
    ],
)
def test_ancora_rotulo_invalido_coerce_para_none(bad_rotulo):
    """ADR-296: rótulo fora da FORMA (não-identifier/>64) → None, nunca reask.
    Pertinência (rótulo == root) é do verificador, não do schema."""
    assert Ancora(rotulo=bad_rotulo).rotulo is None


@pytest.mark.parametrize("good_rotulo", ["reserva_emergencia", "patrimonio", "if_monte_carlo"])
def test_ancora_rotulo_valido_passa(good_rotulo):
    assert Ancora(rotulo=good_rotulo).rotulo == good_rotulo


def test_risco_aceita_ate_3_ancoras():
    r = Risco(
        **_risco(
            ancoras=[{"path": "$.reserva_emergencia.total_liquida", "rotulo": "reserva_emergencia"}]
        )
    )
    assert len(r.ancoras) == 1 and r.ancoras[0].rotulo == "reserva_emergencia"


def test_campo_faltante_field_path_filtro_coerce_para_none_preserva_motivo():
    """Regra 3 do prompt manda registrar paths NÃO-whitelistados aqui — i.e. os
    que falham o regex. Coerção → None com motivo intacto, sem reask."""
    cf = CampoFaltante(
        field_path="$.ativos[?(@.descricao=~'.*imovel.*')].valor",
        motivo="Sem path escalar para o imóvel específico citado.",
    )
    assert cf.field_path is None
    assert cf.motivo.startswith("Sem path escalar")


def test_caps_de_prosa_elevados_adr292():
    """Caps subiram (sign-off product-designer) — texto no novo teto valida."""
    Risco(**_risco(descricao="d" * 650))
    Sugestao(**_sugestao(acao="a" * 340, impacto_qualitativo="i" * 420))


# -----------------------------------------------------------------------
# ADR-294 — coerção dos reask triggers remanescentes (incidente 5@5.com
# 2026-06-17, run 2d555c7f): prosa acima do teto é truncada no boundary e
# impacto_estimado com confianca != 'alta' é dropado, em vez de hard-fail → reask.
# -----------------------------------------------------------------------


@pytest.mark.parametrize("cap,field", [(650, "descricao"), (140, "titulo")])
def test_risco_prosa_acima_do_teto_trunca_em_vez_de_falhar(cap, field):
    """Prosa > cap não dá hard-fail (que viraria reask): trunca no boundary ≤ cap."""
    long = "Frase de teste sem ticker nem sigilo. " * 60
    r = Risco(**_risco(**{field: long}))
    assert len(getattr(r, field)) <= cap


def test_diagnostico_geral_acima_do_teto_trunca_em_frase():
    """diagnostico_geral > 750 (incidente: 699 vs cap stale 500) trunca limpo ≤ 750."""
    from pipeline.llm.schemas.parecer_planejador import _cut_at_sentence

    long = "Diagnostico denso da familia. " * 40  # ~1200 chars, sem ticker/sigilo
    cut = _cut_at_sentence(long, 750)
    assert 50 <= len(cut) <= 750
    assert cut.endswith(".")  # corte em fim de frase, sem reticências


def test_sugestao_impacto_estimado_com_confianca_baixa_dropa_sem_falhar():
    """ADR-294: impacto_estimado + confianca != 'alta' → dropa (None), não raise.
    Era reask trigger no run 2d555c7f (sugestoes_estrategicas[1])."""
    payload = _sugestao(confianca="media")
    payload["impacto_estimado"] = {
        "valor_estimado_brl": 250000.0,
        "unidade": "ano",
        "caveat": "Estimativa indicativa baseada em premissas conservadoras.",
    }
    s = Sugestao(**payload)
    assert s.impacto_estimado is None
    assert s.confianca == "media"  # confianca preservada — não promovida


def test_sugestao_impacto_estimado_com_alta_preservado():
    """Invariante ADR-202 §D6 mantida: com confianca='alta' o impacto sobrevive."""
    payload = _sugestao(confianca="alta")
    payload["impacto_estimado"] = {
        "valor_estimado_brl": 1000.0,
        "unidade": "ano",
        "caveat": "Estimativa indicativa baseada em premissas conservadoras.",
    }
    s = Sugestao(**payload)
    assert s.impacto_estimado is not None
