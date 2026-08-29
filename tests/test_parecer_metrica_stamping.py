"""O alvo e o observado da métrica saem do catálogo, não do modelo (A40.l89 · ADR-399 D1).

Fixtures sintéticas PII-zero. O teste que importa é o de MUTAÇÃO: mudar uma folha do
E5 tem de virar a chave no catálogo REAL e apagar o comparador da métrica publicada.
Escrever ``{"procedencia": None}`` à mão — a leitura literal do critério de aceite —
mediria o dict do teste, não o produtor.
"""

from __future__ import annotations

import pytest

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
def _estampa(e5, alvos):
    from backend.app.services.parecer_finalization import stamp_metrica_targets
    from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

    if alvos is None:
        alvos = e5["kpi_targets"]
    drill = PlannerDrillDown(e5_data=e5, section_whitelist=frozenset({"reserva_emergencia"}))
    return stamp_metrica_targets(make_output(metricas=[_metrica_reserva()]), drill, alvos)


def _e5_com_reserva(meses_alvo, cobertura=42.8):
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    e5 = {
        **E5_COMPLETO,
        "reserva_emergencia": {"meses_alvo": meses_alvo, "cobertura_meses": cobertura},
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
    assert metrica.target == "≥ 18,0 meses", "alvo tem de vir do `meses_alvo` declarado"
    assert metrica.nome == "Cobertura da reserva de emergência"
    assert metrica.valor_atual == "42,8 meses"
    assert metrica.target_motivo is None


def test_fonte_orfa_tira_o_comparador_e_mantem_a_metrica():
    """Prova por mutação: `meses_alvo` some ⇒ o catálogo vira órfão ⇒ o comparador
    some da métrica publicada, mas a linha sobrevive como observacional."""
    result = _generate(make_output(metricas=[_metrica_reserva()]), _e5_com_reserva(None))

    metrica = result.output.metricas[0]
    assert metrica.target is None, "KPI sem procedência não pode publicar alvo"
    assert metrica.target_motivo, "órfão sem motivo entrega célula vazia ao leitor"
    assert (
        metrica.valor_atual == "42,8 meses"
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
    assert primeiro.output.metricas[0].target == segundo.output.metricas[0].target == "≥ 18,0 meses"


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
    assert saida.metricas[0].valor_atual == "42,8 meses", "o observado permanece"


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


def _enum_do_schema(campo: str) -> set:
    import json
    from pathlib import Path as _P

    raiz = _P(__file__).resolve().parents[1]
    schema = json.loads((raiz / "config" / "schemas" / "e5_analysis.schema.json").read_text())
    props = schema["properties"]["kpi_targets"]["additionalProperties"]["properties"]
    return set(props[campo]["enum"])


# A40.l93 fechou `unidade` e `operador` como enum no schema E5, e enum é uma TERCEIRA
# cópia do vocabulário — o teste acima cobria só a ponta esquerda. A cadeia inteira:
# produzidas ⊆ enum == renderer. Igualdade no meio de propósito: enum que declarasse
# unidade sem renderer prometeria contrato que o consumidor não honra, e renderer sem
# enum seria capacidade morta que ninguém pode declarar.
def test_enum_de_unidade_casa_o_renderer_e_cobre_o_produzido():
    from backend.app.services.parecer_finalization import _UNIDADE_RENDER
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    alvos = build_kpi_targets(
        E5_COMPLETO, scoring={"thresholds_alertas": {"endividamento_maximo_pct": 20}}
    )
    enum = _enum_do_schema("unidade")

    assert enum == set(_UNIDADE_RENDER)
    assert {alvo["unidade"] for alvo in alvos.values()} <= enum


# Assimetria deliberada com a unidade: o enum de operador é subconjunto ESTRITO do
# glifo. `>` existe no renderer e não no contrato — ampliar é ato do produtor que
# precisar, e consumidor mais permissivo que o contrato é a direção segura.
def test_enum_de_operador_e_subconjunto_do_glifo_e_cobre_o_produzido():
    from backend.app.services.parecer_finalization import _OPERADOR_GLIFO
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    alvos = build_kpi_targets(
        E5_COMPLETO, scoring={"thresholds_alertas": {"endividamento_maximo_pct": 20}}
    )
    enum = _enum_do_schema("operador") - {None}

    assert enum < set(_OPERADOR_GLIFO), "enum de operador tem símbolo que o renderer não sabe"
    assert {a["operador"] for a in alvos.values() if a["operador"]} <= enum


# O observado de `protecao_custo_premio` chega do payload como STRING ("0.005686") e a
# unidade é razão 0–1. Um guard por `isinstance(float)` na escala deixaria o fator sem
# aplicar e publicaria 0,0% no lugar de 0,6% — o erro de 100× que a renomeação da chave
# existe para fechar, reintroduzido no renderer. Foi assim que ele passou despercebido
# na primeira escrita: os testes de unidade usavam float.
@pytest.mark.parametrize(
    "valor,unidade,esperado",
    [
        ("0.005686", "ratio_0_1", "0,6%"),
        (0.005686, "ratio_0_1", "0,6%"),
        ("16.37", "pct", "16,4%"),
        (2036, "ano", "2036"),
        (1.74, "pct_aa", "1,7%"),
        ("N/D", "ratio_0_1", None),
        (None, "pct", None),
    ],
)
def test_escala_de_unidade_independe_do_tipo_que_veio_do_payload(valor, unidade, esperado):
    from backend.app.services.parecer_finalization import _render_valor

    assert _render_valor(valor, unidade) == esperado


# `kpi_targets` existe desde o #1591; `rotulo` nasceu no #1770. Há uma janela de E5
# persistidos cujas entradas têm 8 campos e nenhum `rotulo` — e regenerar SÓ o parecer
# sobre o E5 do run base (ADR-291) é operação normal. Indexar com `[]` derrubava o stage
# com KeyError DEPOIS de pagar o LLM e ANTES de `_write_cache`: cada retry pagava de novo.
#
# A forma da era anterior é reproduzida REMOVENDO do produtor atual o campo que o #1770
# acrescentou — não escrevendo o dict à mão (que codificaria a minha suposição sobre a
# forma) e não via `git show` do commit daquela era: `actions/checkout@v4` clona raso, o
# commit não existe no runner, e o teste morria de `CalledProcessError` só no CI.
def _alvos_da_era_sem_rotulo(e5: dict) -> dict:
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    atuais = build_kpi_targets(e5, scoring=SCORING_STAMP)
    return {
        chave: {k: v for k, v in alvo.items() if k != "rotulo"} for chave, alvo in atuais.items()
    }


SCORING_STAMP = {"thresholds_alertas": {"endividamento_maximo_pct": 20}}


def test_e5_de_era_sem_rotulo_nao_derruba_o_stage():
    """Campo ausente DENTRO da entrada do catálogo — não a entrada ausente."""
    e5 = _e5_com_reserva(6)
    alvos = _alvos_da_era_sem_rotulo(e5)
    assert "rotulo" not in alvos["reserva_cobertura_meses"], "fixture não reproduz a era antiga"

    saida = _estampa(e5, alvos)

    assert saida.metricas[0].nome, "linha sem identidade é pior que nome técnico"
    assert saida.metricas[0].target == "≥ 6,0 meses"


def test_payload_sem_kpi_targets_publica_linha_com_identidade():
    """67 E5 do dogfood não têm `kpi_targets`: todo parecer regenerado sobre eles caía
    no ramo órfão com `nome=""` — até 10 linhas anônimas na tabela."""
    saida = _estampa(_e5_com_reserva(6), {})

    assert saida.metricas[0].nome, "coluna Métrica em branco"
    assert saida.metricas[0].target is None
    assert saida.metricas[0].target_motivo


# 5,6 meses contra alvo 6 renderizava "6 meses ≥ 6 meses": violação lida como
# conformidade, que é a primeira linha do que a ADR-399 existe para impedir.
def test_meses_preserva_a_casa_que_decide_o_veredito():
    saida = _estampa(_e5_com_reserva(6, cobertura=5.6), None)

    assert saida.metricas[0].valor_atual == "5,6 meses"
    assert saida.metricas[0].target == "≥ 6,0 meses"


# `limiar` está isento do classificador monetário do `golden_diff` (A40.l93) porque a
# unidade mora no irmão `unidade`, e nenhum membro do enum é dinheiro. No dia em que um
# KPI publicar alvo em R$, a isenção vira o bug de volta EM SILÊNCIO — este teste o
# transforma em vermelho no commit que o introduz. É a asserção mais barata do pacote.
def _golden_diff_module():
    """Carrega `dev/golden_diff.py` fora de pacote, como o snapshot do view-model faz."""
    import importlib.util
    import sys
    from pathlib import Path as _P

    raiz = _P(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("golden_diff", raiz / "dev" / "golden_diff.py")
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: os `@dataclass` do módulo resolvem anotações via
    # `sys.modules[cls.__module__]`. Mesmo padrão de test_report_view_model_snapshot.py.
    sys.modules["golden_diff"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# Escrito À MÃO, nunca derivado do enum que ele testa: allowlist que se deriva da
# própria fonte que deveria julgar fabrica a precondição e nunca reprova. Unidade nova
# entra aqui por decisão humana — e é esse o ponto do gate.
#
# A prosa antiga prometia universal ("enquanto TODA unidade for adimensional") e o código
# testava existencial (não-interseção com denylist fechada de 5: brl/usd/eur/reais/moeda).
# `gbp`, `dolar`, `centavos` e `currency` passavam livres. Achado da sessão da A40.l90.
_ADIMENSIONAIS = frozenset({"pct", "pct_aa", "meses", "ano", "ratio_0_1"})


def test_isencao_de_limiar_no_golden_diff_exige_enum_de_unidade_nao_monetario():
    golden_diff = _golden_diff_module()

    assert not golden_diff.is_monetary("kpi_targets.reserva_cobertura_meses.limiar")
    fora = _enum_do_schema("unidade") - _ADIMENSIONAIS
    assert not fora, (
        f"unidade não declarada adimensional no enum: {sorted(fora)}. `limiar` é isento "
        "no golden_diff, então alvo nessa unidade sairia lido como número puro sem "
        "ninguém acusar. Se a unidade nova É adimensional, adicione-a a _ADIMENSIONAIS "
        "aqui — deliberadamente à mão. Se for monetária, `limiar` não pode seguir isento."
    )
