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
    drill = PlannerDrillDown(e5_data=e5, section_whitelist=_SECOES)
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
    assert m.valor_atual == "12,0%", "a linha segue observacional"


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
