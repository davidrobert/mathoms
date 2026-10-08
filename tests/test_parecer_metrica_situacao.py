"""A situação da métrica sai do finalize como dado (A40.l92).

O caso de origem: `taxa_endividamento` 45% contra `≤ 20%` desenhava trilha 100% cheia,
porque o front re-derivava os dois números por regex sobre a string renderizada e a regex
comia o glifo. Os alvos aqui saem do catálogo REAL (`build_kpi_targets`) sobre um E5
sintético PII-zero — escrever o dict à mão mediria o teste, não o produtor.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from backend.app.services.parecer_finalization import stamp_metrica_targets
from pipeline.domain.services.kpi_target_catalog import build_kpi_targets
from pipeline.llm.schemas.parecer_comparador import Comparador
from pipeline.llm.schemas.parecer_planejador import Metrica
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown
from tests.test_parecer_guardrails_pos_llm import E5_COMPLETO, make_output

_SCHEMA = (
    Path(__file__).resolve().parents[1] / "config" / "schemas" / "parecer_planejador.schema.json"
)
_SECOES = frozenset({"ratios", "reserva_emergencia", "diagnostico_confianca"})


# O resolver de PRODUÇÃO aplica os `format_hints` do manifest: o observado da concentração
# chega como "62,50%", não 62.5. Montar o drill sem eles era a crença que o teste
# compartilhava com o código — e o veredito da concentração nunca saía em produção.
def _drill(e5: dict) -> PlannerDrillDown:
    from backend.app.services.parecer_manifest import load_manifest

    manifest = load_manifest()
    return PlannerDrillDown(
        e5_data=e5,
        section_whitelist=manifest.tools_section_whitelist,
        format_hints=manifest.format_hints,
    )


def _e5(*, endividamento=45.0, concentracao=34.86, cobertura=5.6, nivel="parcial") -> dict:
    e5 = {
        **E5_COMPLETO,
        "ratios": {
            "taxa_endividamento_pct": endividamento,
            "concentracao_imobiliaria": concentracao,
        },
        "reserva_emergencia": {"meses_alvo": 6, "cobertura_meses": cobertura},
        "diagnostico_confianca": {"nivel": nivel, "share_nao_identificado_pct": 12.0},
    }
    e5["kpi_targets"] = build_kpi_targets(
        e5, scoring={"thresholds_alertas": {"endividamento_maximo_pct": 20}}
    )
    return e5


def _estampa(chave: str, e5: dict, alvos: dict | None = None) -> Metrica:
    drill = _drill(e5)
    metrica = Metrica(metrica_key=chave, frequencia_revisao="trimestral")
    saida = stamp_metrica_targets(
        make_output(metricas=[metrica]), drill, alvos or e5["kpi_targets"]
    )
    return saida.metricas[0]


def test_teto_violado_publica_veredito_e_nenhum_progresso():
    """45% contra ≤ 20%: o caso medido. Violação, e teto não tem trilha."""
    m = _estampa("taxa_endividamento", _e5())

    assert m.comparador == Comparador(operador="<=", conforme=False, progresso_pct=None)
    assert (m.valor_atual, m.target) == ("45,0%", "≤ 20,0%")


def test_o_mesmo_payload_com_operador_de_piso_faz_a_barra_aparecer():
    """O gate discrimina a DIREÇÃO: trocar só o operador da fixture muda a forma do veredito."""
    e5 = _e5()
    alvos = {**e5["kpi_targets"]}
    alvos["taxa_endividamento"] = {**alvos["taxa_endividamento"], "operador": ">="}

    m = _estampa("taxa_endividamento", e5, alvos)

    assert m.comparador == Comparador(operador=">=", conforme=True, progresso_pct=100)


def test_piso_abaixo_do_minimo_publica_progresso_e_violacao():
    """5,6 contra ≥ 6 meses: a barra a 93% lia "atingido" — o status existe por isso."""
    m = _estampa("reserva_cobertura_meses", _e5(cobertura=5.6))

    assert m.comparador == Comparador(operador=">=", conforme=False, progresso_pct=93)
    assert m.valor_atual == "5,6 meses"


@pytest.mark.parametrize(
    "chave,campo,observado",
    [
        ("taxa_endividamento", "endividamento", 20.0),
        ("concentracao_imobiliaria", "concentracao", 50.0),
    ],
)
def test_limiar_exato_e_conforme(chave, campo, observado):
    """O limiar é o último valor conforme ([[ADR-399]] §Emenda 2026-10-08)."""
    m = _estampa(chave, _e5(**{campo: observado}))

    assert m.comparador.conforme is True


def test_numero_e_status_nao_se_contradizem_na_mesma_linha():
    """Bruto 20,04 com 1 casa seria "20,0%" sob "≤ 20,0%" e "Acima do limite"."""
    m = _estampa("taxa_endividamento", _e5(endividamento=20.04))

    assert m.comparador.conforme is False
    assert m.valor_atual == "20,04%"


def test_precisao_extra_so_quando_uma_casa_contradiz():
    m = _estampa("taxa_endividamento", _e5(endividamento=21.36))

    assert m.valor_atual == "21,4%"


def test_despesas_publica_o_nivel_do_produtor_e_nunca_veredito():
    """Fala da leitura do relatório, não da família: sem alvo e sem conformidade."""
    m = _estampa("despesas_nao_categorizadas", _e5(nivel="parcial"))

    assert m.nivel_confianca == "parcial"
    assert m.comparador is None and m.target is None
    assert "relatório" in m.target_motivo
    assert m.valor_atual == "12,00%", "a linha segue observacional (hint `percent2`)"


def test_nivel_fora_do_vocabulario_do_produtor_nao_e_publicado():
    m = _estampa("despesas_nao_categorizadas", _e5(nivel="otimo"))

    assert m.nivel_confianca is None


def test_metrica_com_alvo_nao_publica_nivel():
    assert _estampa("taxa_endividamento", _e5()).nivel_confianca is None


def test_orfa_por_dominio_nao_tem_comparador():
    e5 = _e5()
    e5["ratios"]["rentabilidade"] = {"valor_pct": 1.7}

    assert _estampa("carteira_trs", e5).comparador is None


def test_observado_ausente_nao_tem_comparador():
    """Comparador com um lado fabricado pela ausência é o defeito da [[ADR-399]]."""
    e5 = _e5()
    del e5["ratios"]["taxa_endividamento_pct"]

    m = _estampa("taxa_endividamento", e5)

    assert m.comparador is None and m.target is None


def test_artefato_estampado_valida_contra_o_schema():
    """`exclude_none` faz `progresso_pct` sumir no teto — o schema não pode exigi-lo."""
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    e5 = _e5()
    drill = PlannerDrillDown(e5_data=e5, section_whitelist=_SECOES)
    chaves = ("taxa_endividamento", "reserva_cobertura_meses", "despesas_nao_categorizadas")
    metricas = [Metrica(metrica_key=c, frequencia_revisao="trimestral") for c in chaves]
    saida = stamp_metrica_targets(make_output(metricas=metricas), drill, e5["kpi_targets"])

    artefato = saida.model_dump(mode="json", exclude_none=True)

    jsonschema.validate(artefato, schema)
    assert "progresso_pct" not in artefato["metricas"][0]["comparador"]


# Número sem procedência é o estado que a ADR-399 recusa publicar como alvo; ganhar
# veredito por baixo seria o mesmo número entrando pela outra porta. O dict é injetado à
# mão DE PROPÓSITO: o catálogo nunca o produz (o construtor recusa), mas E5 de série
# anterior ou artefato antigo podem trazê-lo.
def test_numero_sem_procedencia_nao_ganha_veredito():
    e5 = _e5()
    alvos = {**e5["kpi_targets"]}
    alvos["taxa_endividamento"] = {**alvos["taxa_endividamento"], "procedencia": None}

    m = _estampa("taxa_endividamento", e5, alvos)

    assert m.target is None and m.comparador is None


def test_hint_de_formato_de_producao_nao_cala_o_veredito():
    """`percent2` formata o observado da concentração para quem lê; o veredito julga o cru."""
    from backend.app.services.parecer_manifest import load_manifest

    assert load_manifest().format_hints.get(
        "$.ratios.concentracao_imobiliaria"
    ), "o caso exige o hint de produção — sem ele o teste é vácuo"
    m = _estampa("concentracao_imobiliaria", _e5(concentracao=62.5))

    assert m.comparador == Comparador(operador="<=", conforme=False, progresso_pct=None)


def _e5_de_era_anterior(nivel: str) -> dict:
    """E5 anterior à A40.l92: despesas ainda publicava alvo `< 10`."""
    e5 = _e5(nivel=nivel)
    e5["kpi_targets"] = {
        **e5["kpi_targets"],
        "despesas_nao_categorizadas": {
            **e5["kpi_targets"]["despesas_nao_categorizadas"],
            "limiar": 10.0,
            "operador": "<",
            "procedencia": "limiar_canonico",
            "ref": "diagnostico_comportamental_analyzer.NAO_IDENTIFICADO_PARCIAL_PCT",
            "motivo": None,
        },
    }
    return e5


def test_despesas_em_e5_de_era_anterior_nao_ganha_alvo_nem_veredito():
    """Regenerado sobre E5 antigo (ADR-291), o alvo que a decisão removeu não volta."""
    m = _estampa("despesas_nao_categorizadas", _e5_de_era_anterior("parcial"))

    assert m.target is None and m.comparador is None
    assert m.nivel_confianca == "parcial"
    assert "relatório" in m.target_motivo


def test_nivel_que_nao_e_string_nao_derruba_o_stage():
    e5 = _e5()
    e5["diagnostico_confianca"]["nivel"] = ["parcial"]

    assert _estampa("despesas_nao_categorizadas", e5).nivel_confianca is None


def test_limiar_com_virgula_nao_derruba_o_stage():
    e5 = _e5(endividamento=20.04)
    alvos = {**e5["kpi_targets"]}
    alvos["taxa_endividamento"] = {**alvos["taxa_endividamento"], "limiar": "20,0"}

    m = _estampa("taxa_endividamento", e5, alvos)

    assert m.comparador.conforme is False and m.valor_atual == "20,04%"


@pytest.mark.parametrize(
    "emitido",
    [
        {"nivel_confianca": "media"},
        {"nivel_confianca": ["alta"]},
        {"comparador": {"operador": "<=", "conforme": False, "progresso_pct": 50}},
        {"comparador": "acima"},
    ],
)
def test_campo_estampado_invalido_vindo_do_modelo_vira_none_nunca_reask(emitido):
    """[[ADR-294]]: raise no boundary do LLM vira reask storm; coerce para None."""
    m = Metrica.model_validate(
        {"metrica_key": "taxa_endividamento", "frequencia_revisao": "trimestral", **emitido}
    )

    assert m.comparador is None and m.nivel_confianca is None


def test_estampado_valido_sobrevive_ao_round_trip_do_cache():
    m = _estampa("taxa_endividamento", _e5())

    relido = Metrica.model_validate(m.model_dump(mode="json"))

    assert relido.comparador == m.comparador


def test_artefato_sem_exclude_none_tambem_valida_contra_o_schema():
    """`comparador: null` e `progresso_pct: null` são valores que o modelo permite."""
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    metrica_schema = {"$defs": schema["$defs"], **schema["$defs"]["metrica"]}
    e5 = _e5()
    chaves = ("taxa_endividamento", "carteira_trs", "despesas_nao_categorizadas")
    metricas = [Metrica(metrica_key=c, frequencia_revisao="trimestral") for c in chaves]
    saida = stamp_metrica_targets(make_output(metricas=metricas), _drill(e5), e5["kpi_targets"])

    # Nulos EXPLÍCITOS só nos campos desta lane — outros campos opcionais do schema
    # (`tema_canonico`) não aceitam null por razões que não são desta lane.
    for metrica in saida.metricas:
        dump = metrica.model_dump(mode="json", exclude_none=True)
        dump.setdefault("comparador", None)
        dump.setdefault("nivel_confianca", None)
        if dump["comparador"] is not None:
            dump["comparador"].setdefault("progresso_pct", None)
        jsonschema.validate(dump, metrica_schema)
