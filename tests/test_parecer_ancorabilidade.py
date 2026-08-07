"""Ancorabilidade do exec context — invariante + paridade corpus↔manifest (A40.l30 item 2/5).

Dois artefatos, e a distinção entre eles é o que mantém a lane honesta (co-design
`senior-cto` 2026-08-07): **hard sobre predicado que o HEAD já satisfaz**, soft sobre
predicado que o HEAD viola.

- Hard: os ratchets do *instrumento* (o conjunto cresce quando eu projeto R$ fora do
  catálogo? limpa quando removo?) e o change-detector do snapshot. Nenhum é vermelho
  no HEAD, logo nenhum bloqueia trabalho alheio.
- Soft: o alvo `inancoraveis == 0`. É vermelho hoje (16 paths) e gateá-lo aqui violaria
  o §Escopo item 2 da lane ("**não** instalar gate hard no mesmo PR que introduz a
  métrica"). O flip converge sozinho: quando a l31 esvaziar o conjunto, "snapshot
  inalterado" e `== 0` passam a ser o mesmo predicado — não há decisão a drenar.

Rebaseline do snapshot: ``MATHOMS_UPDATE_SNAPSHOT=1 pytest tests/test_parecer_ancorabilidade.py``.
Custa **US$ 0** e roda in-process — é essa condição que separa snapshot-que-funciona de
snapshot-que-apodrece (contra-precedente vivo: ``dev/snapshots/lineage_eval_baseline.json``
está ``pending_first_real_run`` porque preenchê-lo exige run owner-gated).
"""

from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.services.parecer_ancorabilidade import (
    iter_uncovered_paths,
    iter_visible_money_paths,
    measure_anchorability,
    measure_block_coverage,
)
from backend.app.services.parecer_citation_catalog import _MAX_LIST_ITEMS, _PRIORITY_ROOTS
from backend.app.services.parecer_distiller import _render_section_body, surviving_sections
from backend.app.services.parecer_manifest import load_manifest
from tests.test_parecer_planejador_golden import make_workspace_e5

_REPO = Path(__file__).resolve().parents[1]
_SNAPSHOT = _REPO / "dev" / "snapshots" / "parecer_ancorabilidade.json"

# Os 3 blocos que #1004 acrescentou ao corpo e que o holdout NÃO tinha — a razão pela
# qual um run do eval de US$ 26 responderia "os gates ainda passam?" e não "o #1004
# causou a queda?". A paridade abaixo falhava nestes 3 antes de a fixture ganhá-los.
_BLOCOS_DO_1004 = ("janela_12m", "receita_por_natureza", "protecao_patrimonial")


@pytest.fixture
def manifest():
    return load_manifest()


@pytest.fixture
def e5():
    return make_workspace_e5()


# -----------------------------------------------------------------------
# Item 5 — paridade corpus ↔ manifest
# -----------------------------------------------------------------------


class TestParidadeCorpusManifest:
    def test_os_tres_blocos_do_1004_estao_no_corpus(self, manifest, e5):
        """Vermelho antes da fixture ganhar os 3 blocos; verde depois. É o item 5."""
        descobertos = iter_uncovered_paths(manifest, e5)
        ausentes = [b for b in _BLOCOS_DO_1004 if any(b in p for p in descobertos)]
        assert ausentes == [], f"o corpus não exercita {ausentes} — o eval fica cego a eles"

    def test_presenca_de_bloco_nao_basta_como_criterio(self, manifest, e5):
        """`receita_por_natureza` são 4 campos DENTRO de um bloco que fica `com_dado`
        pelos outros campos. Só a granularidade de path revela a ausência — medir por
        bloco daria verde com o buraco intacto."""
        por_bloco = measure_block_coverage(manifest, e5)
        fluxo = [c for c in por_bloco if "Fluxo do período completo" in c.block_title]
        assert fluxo and fluxo[0].covered
        sem_natureza = copy.deepcopy(e5)
        sem_natureza["fluxo_caixa"].pop("receita_por_natureza")
        ainda_coberto = measure_block_coverage(manifest, sem_natureza)
        fluxo_sem = [c for c in ainda_coberto if "Fluxo do período completo" in c.block_title]
        assert fluxo_sem[0].covered  # o bloco MENTE que está coberto
        assert any(
            "receita_por_natureza" in p for p in iter_uncovered_paths(manifest, sem_natureza)
        )

    def test_cabecalho_orfao_e_nomeado_e_nao_conta_como_cobertura(self, manifest, e5):
        """`_render_table` com `rows == []` emite `**Top ativos (até 15)** (top 0):` —
        cabeçalho sem linha. `_render_key_value` se protege disso (`:174`), `_render_table`
        não. É esse estado que fazia o corpus PARECER coberto. Fix é do dono do distiller
        (l31); aqui o instrumento se recusa a contá-lo como cobertura."""
        orfaos = [c for c in measure_block_coverage(manifest, e5) if c.header_orfao]
        assert orfaos, "nenhum cabeçalho órfão — se o distiller foi corrigido, remova este teste"
        assert all(not c.covered for c in orfaos)
        assert all(c.cardinalidade == 0 for c in orfaos)


# -----------------------------------------------------------------------
# Item 2 — o instrumento mede o observável, não o teto
# -----------------------------------------------------------------------


def _body_of(manifest, e5) -> str:
    sections, _ = surviving_sections(manifest, e5)
    return "\n".join(_render_section_body(s, e5) for s in sections)


class TestInstrumentoMedeOObservavel:
    def test_conjunto_derivado_do_manifest_bate_com_o_renderer(self, manifest, e5):
        """Oráculo de drift instrumento↔renderer. Se o distiller ganhar caminho novo de
        R$ que o manifest não declara, os dois números divergem e este teste conta."""
        visiveis = iter_visible_money_paths(manifest, e5)
        tokens = len(re.findall(r"R\$", _body_of(manifest, e5)))
        assert len(visiveis) == tokens

    def test_varrer_o_exec_context_inteiro_seria_verde_falso(self, manifest, e5):
        """O bloco do catálogo imprime `path → R$ valor`: são tokens R$ ancoráveis POR
        CONSTRUÇÃO. Um check sobre o exec context inteiro ficaria quase-sempre verde
        medindo a camada errada — daí a pinagem "corpo pré-catálogo"."""
        from backend.app.services.parecer_distiller import distill_exec_context

        no_corpo = len(re.findall(r"R\$", _body_of(manifest, e5)))
        no_contexto = len(re.findall(r"R\$", distill_exec_context(manifest, e5)))
        assert no_contexto > no_corpo

    def test_catalogo_renderizado_e_menor_que_o_construido(self, manifest, e5):
        """94% vs 78% no corpus original: `max_bytes` corta entries antes de o modelo
        ver. Medir contra o construído é o verde-falso nº 2."""
        report = measure_anchorability(manifest, e5)
        assert report.catalogo_renderizado < report.catalogo_construido

    def test_medicao_nao_esta_degradada_por_hard_cut(self, manifest, e5):
        """Sob `_hard_cut` a atribuição por seção deixa de ser exata. O corpus sintético
        não chega lá; se chegar, o instrumento tem de se declarar degradado."""
        assert measure_anchorability(manifest, e5).hard_cut is False


# -----------------------------------------------------------------------
# Ratchets do instrumento — mutação em 4 sentidos (hard, verde no HEAD)
# -----------------------------------------------------------------------


_PATH_ORFAO = "$.raiz_sintetica_sem_rota.valor_orfao"


def _secao_com_rs_sem_rota() -> dict:
    """Seção sintética projetando `brl` numa raiz que `_PRIORITY_ROOTS` não conhece."""
    campo = {"path": _PATH_ORFAO, "label": "Órfão", "format": "brl"}
    return {
        "id": "sintetica",
        "title": "Sintética",
        "eviction_priority": 1,
        "blocks": [{"format": "key_value", "title": "Órfã", "fields": [campo]}],
    }


def _sem_nenhum_brl(sections: list[dict]) -> list[dict]:
    """Todo campo/coluna `brl` → `raw`: nenhuma folha monetária chega ao corpo."""
    mutadas = copy.deepcopy(sections)
    blocos = [b for s in mutadas for b in (s.get("blocks") or [])]
    declarados = [d for b in blocos for d in (b.get("fields") or []) + (b.get("columns") or [])]
    for declared in declarados:
        if declared.get("format") == "brl":
            declared["format"] = "raw"
    return mutadas


class TestRatchetDeMutacao:
    def test_projetar_rs_fora_do_catalogo_gera_sinal(self, manifest, e5):
        """Sentido 1 — a mutação que #1004 fez: bloco novo com `format: brl` numa raiz
        que o catálogo não prioriza."""
        antes = measure_anchorability(manifest, e5)
        mutado = copy.deepcopy(e5)
        mutado["raiz_sintetica_sem_rota"] = {"valor_orfao": 123_456.0}
        sections = [*copy.deepcopy(manifest.sections), _secao_com_rs_sem_rota()]
        depois = measure_anchorability(replace(manifest, sections=sections), mutado)
        assert _PATH_ORFAO in depois.inancoraveis
        assert len(depois.inancoraveis) == len(antes.inancoraveis) + 1

    def test_remover_a_projecao_limpa_o_sinal(self, manifest, e5):
        """Sentido 2 — manifest sem nenhum campo `brl` ⇒ conjunto vazio. Prova que o
        sinal vem da projeção e não de ruído do instrumento."""
        sections = _sem_nenhum_brl(manifest.sections)
        report = measure_anchorability(replace(manifest, sections=sections), e5)
        assert report.visiveis == ()
        assert report.inancoraveis == ()

    def test_encolher_max_bytes_do_catalogo_faz_o_conjunto_crescer(self, manifest, e5):
        """Sentido 3 — o binding constraint medido: o catálogo é cortado por bytes, e
        `_PRIORITY_ROOTS` decide quem sobra. Dois parâmetros, dois arquivos, nenhum
        invariante os ligando."""
        antes = measure_anchorability(manifest, e5)
        apertado = replace(
            manifest, citation_catalog=replace(manifest.citation_catalog, max_bytes=200)
        )
        depois = measure_anchorability(apertado, e5)
        assert len(depois.inancoraveis) > len(antes.inancoraveis)
        assert depois.catalogo_renderizado < antes.catalogo_renderizado

    def test_evictar_secao_faz_o_conjunto_encolher(self, manifest, e5):
        """Sentido 4 — seção evictada não é visível. Sem isto o instrumento mediria o
        teto (`manifest.sections` inteiro) e a baseline seria otimista."""
        antes = measure_anchorability(manifest, e5)
        # Budget minúsculo ⇒ eviction agressiva ⇒ menos folha visível.
        depois = measure_anchorability(replace(manifest, max_exec_context_bytes=1200), e5)
        assert len(depois.visiveis) < len(antes.visiveis)
        assert len(depois.inancoraveis) <= len(antes.inancoraveis)

    def test_linha_de_tabela_fora_do_top_k_e_inancoravel_por_ranking(self, manifest, e5):
        """Inancorabilidade ESTRUTURAL, não de bytes: o corpo renderiza `max_rows` (10)
        e o catálogo pega `_MAX_LIST_ITEMS` (5) **por maior valor**, não por posição.
        Nenhum ajuste de `max_bytes` resolve — e é por isso que o flip a hard não pode
        acontecer nesta lane."""
        assert _MAX_LIST_ITEMS == 5
        report = measure_anchorability(manifest, e5)
        linhas = [p for p in report.inancoraveis if "tabela_classes[" in p]
        assert linhas, "nenhuma linha de tabela inancorável — o mecanismo mudou, remeça a medição"


# -----------------------------------------------------------------------
# Snapshot — gate por DIFF de conjunto, não por threshold
# -----------------------------------------------------------------------


_SNAPSHOT_COMMENT = (
    "A40.l30 item 2 — folhas R$ visíveis no corpo do exec context sem rota de citação no "
    "catálogo RENDERIZADO. Gate por diff de conjunto: um #1004 futuro aparece aqui. "
    "Rebaseline: MATHOMS_UPDATE_SNAPSHOT=1 pytest tests/test_parecer_ancorabilidade.py "
    "— US$ 0, in-process."
)


# Os parâmetros geradores são obrigatórios: sem eles o diff não distingue "manifest
# cresceu" de "budget encolheu" — e são remediações OPOSTAS.
def _parametros_geradores(manifest) -> dict:
    return {
        "manifest_version": manifest.version,
        "max_exec_context_bytes": manifest.max_exec_context_bytes,
        "catalogo_max_bytes": manifest.citation_catalog.max_bytes,
        "catalogo_max_entries": manifest.citation_catalog.max_entries,
        "max_list_items": _MAX_LIST_ITEMS,
        "priority_roots": list(_PRIORITY_ROOTS),
    }


# Paths legíveis, nunca hash: aqui a legibilidade É o produto (um #1004 futuro tem de ser
# lido em 5 segundos no diff do PR).
def _snapshot_payload(manifest, e5) -> dict:
    """Conjunto ordenado de paths inancoráveis + os parâmetros que o geraram."""
    report = measure_anchorability(manifest, e5)
    return {
        "_comment": _SNAPSHOT_COMMENT,
        "corpus": "make_workspace_e5 (sintético, PII-zero)",
        "parametros_geradores": _parametros_geradores(manifest),
        "medicao": {
            "visiveis": len(report.visiveis),
            "ancoraveis": len(report.ancoraveis),
            "catalogo_construido": report.catalogo_construido,
            "catalogo_renderizado": report.catalogo_renderizado,
            "hard_cut": report.hard_cut,
        },
        "inancoraveis": sorted(report.inancoraveis),
        "paths_projetados_sem_dado_no_corpus": sorted(iter_uncovered_paths(manifest, e5)),
    }


class TestSnapshotDeAncorabilidade:
    def test_conjunto_inancoravel_bate_com_o_snapshot(self, manifest, e5):
        actual = json.dumps(_snapshot_payload(manifest, e5), ensure_ascii=False, indent=2) + "\n"
        if os.environ.get("MATHOMS_UPDATE_SNAPSHOT") == "1" or not _SNAPSHOT.exists():
            _SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            _SNAPSHOT.write_text(actual, encoding="utf-8")
        assert actual == _SNAPSHOT.read_text(encoding="utf-8"), (
            "ancorabilidade do exec context mudou — se foi intencional, rebaseline via "
            "MATHOMS_UPDATE_SNAPSHOT=1 e explique no PR qual parâmetro se moveu"
        )

    def test_snapshot_e_deterministico(self, manifest, e5):
        primeiro = _snapshot_payload(manifest, e5)
        segundo = _snapshot_payload(load_manifest(), make_workspace_e5())
        assert primeiro == segundo

    def test_snapshot_guarda_paths_e_nunca_valores(self):
        """PII-zero por construção: o arquivo carrega JSONPath e contagens. Um valor R$
        aqui seria dado de cliente num arquivo versionado."""
        raw = _SNAPSHOT.read_text(encoding="utf-8")
        # `R$` seguido de dígito é VALOR; o símbolo solto na prosa do `_comment` não é.
        assert not re.search(r"R\$\s*\d", raw)
        assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", raw)  # CPF
        assert not re.search(r"\d{1,3}(\.\d{3})+,\d{2}", raw)  # monetário BR formatado

    def test_alvo_de_zero_inancoravel_e_soft(self, manifest, e5, caplog):
        """O alvo da lane (`inancoraveis == 0`) é REPORTADO, não gateado — a lane proíbe
        gate hard no mesmo PR da métrica. Este teste falha se alguém o transformar em
        assert duro sem passar pelo PR próprio exigido."""
        report = measure_anchorability(manifest, e5)
        if report.inancoraveis:
            pytest.skip(
                f"alvo ainda não atingido: {len(report.inancoraveis)} folhas R$ sem rota "
                f"({report.cobertura_pct}% de cobertura) — flip a hard é da A40.l31"
            )
        assert report.inancoraveis == ()
