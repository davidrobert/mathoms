"""Telemetria do orçamento do exec context ([[ADR-341]] §Emenda 2026-10-09 · [[A40.l124]]).

A eviction por seção funcionava e era muda: o marcador só existia dentro do prompt. O
orçamento publicado tem de dizer a MESMA coisa que o marcador diz ao modelo — por isso
os testes comparam o publicado com o texto montado, não com uma constante.
"""

from __future__ import annotations

import dataclasses
import re

from backend.app.services.parecer_distiller import (
    distill_exec_context,
    distill_exec_context_with_budget,
)
from backend.app.services.parecer_manifest import load_manifest
from tests.test_parecer_distiller_exec_context import make_dogfood_like_e5

_HINTS_HEADER = "### Diretrizes de leitura por seção (hints)"
_MARKER_IDS = re.compile(r"seções removidas por prioridade: ([a-z0-9_, ]+)\.")


def _com_cap(cap: int):
    return dataclasses.replace(load_manifest(), max_exec_context_bytes=cap)


def _corpo(texto: str) -> str:
    return texto.partition(_HINTS_HEADER)[0].rstrip("\n")


def _ids_do_marcador(corpo: str) -> tuple[str, ...]:
    achado = _MARKER_IDS.search(corpo)
    return tuple(i.strip() for i in achado.group(1).split(",")) if achado else ()


def test_orcamento_nomeia_as_mesmas_secoes_que_o_marcador():
    texto, orcamento = distill_exec_context_with_budget(_com_cap(3500), make_dogfood_like_e5())
    assert orcamento.evicted_section_ids, "o cap de 3500 B tem de evictar — senão o teste é vácuo"
    assert orcamento.evicted_section_ids == _ids_do_marcador(_corpo(texto))


def test_bytes_do_corpo_sao_os_do_texto_enviado():
    texto, orcamento = distill_exec_context_with_budget(_com_cap(3500), make_dogfood_like_e5())
    assert orcamento.body_bytes == len(_corpo(texto).encode("utf-8"))
    assert orcamento.body_bytes <= orcamento.cap_bytes < orcamento.demand_bytes


def test_demanda_e_a_soma_das_secoes_inteiras():
    _texto, orcamento = distill_exec_context_with_budget(load_manifest(), make_dogfood_like_e5())
    secoes = dict(orcamento.section_bytes)
    assert set(secoes) == {s["id"] for s in load_manifest().sections}
    assert orcamento.demand_bytes == sum(secoes.values()) + len(secoes) - 1


def test_sem_eviction_o_orcamento_diz_vazio_e_a_demanda_e_o_corpo():
    _texto, orcamento = distill_exec_context_with_budget(load_manifest(), make_dogfood_like_e5())
    assert orcamento.evicted_section_ids == ()
    assert orcamento.demand_bytes == orcamento.body_bytes
    assert not orcamento.hard_cut


def test_corte_degenerado_e_declarado():
    """Sobra uma seção e ela sozinha excede o cap — o único corte intra-seção (D2)."""
    _texto, orcamento = distill_exec_context_with_budget(_com_cap(300), make_dogfood_like_e5())
    assert orcamento.hard_cut
    assert len(orcamento.evicted_section_ids) == len(load_manifest().sections) - 1


def test_fora_do_orcamento_e_medido_a_parte():
    texto, orcamento = distill_exec_context_with_budget(load_manifest(), make_dogfood_like_e5())
    hints_e_catalogo = texto.partition(_HINTS_HEADER)[1] + texto.partition(_HINTS_HEADER)[2]
    assert orcamento.hints_bytes + orcamento.catalog_bytes + 2 == len(
        hints_e_catalogo.encode("utf-8")
    )


def test_publicado_e_so_inteiro_e_id_do_manifest():
    """Postura de PII: granularidade de SEÇÃO, nunca valor, nome ou rótulo de bloco."""
    _texto, orcamento = distill_exec_context_with_budget(_com_cap(3500), make_dogfood_like_e5())
    publicado = orcamento.as_dict()
    ids = {s["id"] for s in load_manifest().sections}
    assert set(publicado["section_bytes"]) <= ids
    assert set(publicado["evicted_section_ids"]) <= ids
    escalares = [
        v for k, v in publicado.items() if k not in ("section_bytes", "evicted_section_ids")
    ]
    assert all(isinstance(v, (int, bool)) for v in escalares)
    assert all(isinstance(v, int) for v in publicado["section_bytes"].values())


def test_o_wrapper_publico_devolve_o_mesmo_texto():
    e5 = make_dogfood_like_e5()
    for cap in (load_manifest().max_exec_context_bytes, 3500):
        manifest = _com_cap(cap)
        assert (
            distill_exec_context(manifest, e5) == distill_exec_context_with_budget(manifest, e5)[0]
        )
