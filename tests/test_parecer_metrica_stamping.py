"""O alvo e o observado da métrica saem do catálogo, não do modelo (A40.l89 · ADR-399 D1).

Fixtures sintéticas PII-zero. O teste que importa é o de MUTAÇÃO: mudar uma folha do
E5 tem de virar a chave no catálogo REAL e apagar o comparador da métrica publicada.
Escrever ``{"procedencia": None}`` à mão — a leitura literal do critério de aceite —
mediria o dict do teste, não o produtor.
"""

from __future__ import annotations

from backend.app.services.parecer_orchestrator import (
    ParecerOrchestratorConfig,
    generate_parecer,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from pipeline.llm.schemas.parecer_planejador import Metrica
from tests.test_parecer_guardrails_pos_llm import (
    E5_COMPLETO,
    WS,
    _FakeLLMService,
    _generate,
    make_output,
)

# ---------------------------------------------------------------------------
# A40.l89 · ADR-399 D1 — o alvo publicado vem do catálogo, não do modelo
# ---------------------------------------------------------------------------


# Faz o CATÁLOGO REAL virar a chave, mudando UMA folha do E5. Escrever
# `{"procedencia": None}` à mão — a leitura literal do critério de aceite — seria
# fantasma: mediria o dict do teste, não o produtor. `reserva_cobertura_meses` é
# usada porque é uma das 3 chaves que flipam por payload; as 4 órfãs de domínio são
# inflexíveis e forçariam justamente o hand-edit que este desenho evita.
def _e5_com_reserva(meses_alvo):
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    e5 = {
        **E5_COMPLETO,
        "reserva_emergencia": {"meses_alvo": meses_alvo, "cobertura_meses": 42.8},
    }
    e5["kpi_targets"] = build_kpi_targets(
        e5, scoring={"thresholds_alertas": {"endividamento_maximo_pct": 20}}
    )
    return e5


def _metrica_reserva() -> Metrica:
    return Metrica(
        metrica_key="reserva_cobertura_meses", frequencia_revisao="trimestral", section_id="S3"
    )


def test_alvo_com_fonte_e_estampado_do_catalogo():
    """O par (rótulo, alvo, observado) sai do catálogo — o modelo emitiu só a chave."""
    result = _generate(make_output(metricas=[_metrica_reserva()]), _e5_com_reserva(18))

    metrica = result.output.metricas[0]
    assert metrica.target == "≥ 18 meses", "alvo tem de vir do `meses_alvo` declarado"
    assert metrica.nome == "Cobertura da reserva de emergência"
    assert metrica.valor_atual == "43 meses"
    assert metrica.target_motivo is None


def test_fonte_orfa_tira_o_comparador_e_mantem_a_metrica():
    """Prova por mutação: `meses_alvo` some ⇒ o catálogo vira órfão ⇒ o comparador
    some da métrica publicada, mas a linha sobrevive como observacional."""
    result = _generate(make_output(metricas=[_metrica_reserva()]), _e5_com_reserva(None))

    metrica = result.output.metricas[0]
    assert metrica.target is None, "KPI sem procedência não pode publicar alvo"
    assert metrica.target_motivo, "órfão sem motivo entrega célula vazia ao leitor"
    assert (
        metrica.valor_atual == "43 meses"
    ), "o observado permanece — órfão perde o alvo, não o sinal"
    assert result.status == "Gerado", "órfão é fato esperado, nunca needs_review"


def _gera(cache, e5):
    return generate_parecer(
        e5_data=e5,
        config=ParecerOrchestratorConfig(workspace_id=WS, tier="premium"),
        llm_service=_FakeLLMService(make_output(metricas=[_metrica_reserva()])),
        cache=cache,
    )


# Se o carimbo rodasse depois de `_write_cache`, o envelope guardaria o alvo do modelo
# por 7 dias de TTL e re-rodar o stage não repararia — cairia no mesmo cache hit.
def test_estampagem_precede_o_cache():
    """O alvo estampado sobrevive ao round-trip pelo cache."""
    cache, e5 = InMemoryLLMCache(), _e5_com_reserva(18)

    primeiro, segundo = _gera(cache, e5), _gera(cache, e5)

    assert segundo.cache_hit is True, "sem cache hit o mutante é vacuoso"
    assert primeiro.output.metricas[0].target == segundo.output.metricas[0].target == "≥ 18 meses"


# No produtor, `limiar is None` e `procedencia is None` colapsam em 1 bit — varridas
# as 108 combinações, zero divergem. Logo NENHUMA mutação de payload discrimina qual
# chave o estampador usou, e trocar uma pela outra passa em toda a suíte. Medido: o
# mutante sobrevive a 42 testes. O estampador lê um DICT (`kpi_targets` do payload),
# não um `KpiTarget`, então o bicondicional do construtor não o alcança — artefato de
# série anterior ou catálogo futuro podem trazer o estado divergente. A discriminação
# tem de ser feita aqui, no consumidor, com o estado injetado à mão de propósito.
_ALVO_BASE = {
    "observado_path": "$.reserva_emergencia.cobertura_meses",
    "base": "despesa_essencial_mensal",
    "unidade": "meses",
    "rotulo": "Cobertura da reserva de emergência",
    "procedencia": None,
    "ref": None,
    "motivo": None,
}


def test_numero_sem_procedencia_nao_vira_alvo_publicado():
    """`limiar` presente e `procedencia` ausente é número sem fonte auditável — o
    defeito exato que a ADR-399 fecha. O comparador tem de sumir mesmo assim."""
    from backend.app.services.parecer_finalization import stamp_metrica_targets
    from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

    alvos = {"reserva_cobertura_meses": {**_ALVO_BASE, "limiar": 42.0, "operador": ">="}}
    e5 = {**E5_COMPLETO, "reserva_emergencia": {"cobertura_meses": 42.8}}
    drill = PlannerDrillDown(e5_data=e5, section_whitelist=frozenset({"reserva_emergencia"}))

    saida = stamp_metrica_targets(make_output(metricas=[_metrica_reserva()]), drill, alvos)

    assert saida.metricas[0].target is None, "número sem procedência não pode ser publicado"
    assert saida.metricas[0].valor_atual == "43 meses", "o observado permanece"


# Fecha a CLASSE, não a instância: unidade nova no catálogo sem entrada no renderer
# cairia no ramo de "não sei renderizar" e a métrica sairia sem valor, calada. Mesma
# forma do `_BASE_POR_DENOMINADOR` da A40.l80 — o teste mede o produtor, não uma lista
# copiada para cá.
def test_toda_unidade_do_catalogo_tem_renderer():
    from backend.app.services.parecer_finalization import _UNIDADE_RENDER
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    alvos = build_kpi_targets(
        E5_COMPLETO, scoring={"thresholds_alertas": {"endividamento_maximo_pct": 20}}
    )
    unidades = {alvo["unidade"] for alvo in alvos.values()}

    sem_renderer = unidades - set(_UNIDADE_RENDER)
    assert not sem_renderer, f"unidade do catálogo sem renderer: {sorted(sem_renderer)}"
