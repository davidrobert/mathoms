"""Ancorabilidade do exec context: toda folha R$ que o modelo vê tem rota de citação?

O invariante que faltava (A40.l30 item 2). #1004 dobrou os valores monetários visíveis
no corpo (9→18 tokens médios) sem mexer no conjunto ancorável, e a suíte inteira ficou
verde — porque nada assere *"valor R$ renderizado no corpo ⇒ path no catálogo"*.
Enquanto isso `_CATALOG_INSTRUCTION` manda literalmente "Conceito ausente daqui → não
ancore", então digitar o número na prosa é o comportamento que sobra.

Três pinagens de definição, todas necessárias para o instrumento medir o observável e
não o teto (co-design `prompt-engineer` + `senior-cto`, 2026-08-07):

1. **Catálogo RENDERIZADO, não construído.** `build_citation_catalog` devolve 29 entries
   no corpus sintético; `max_bytes` deixa 20 passar. Medir contra o construído dá 94% de
   cobertura; o que o modelo tem é 78%.
2. **Corpo PRÉ-catálogo.** O próprio bloco do catálogo imprime `path → R$ valor` — se a
   varredura incluísse o exec context inteiro, ~20 tokens R$ ancoráveis-por-construção
   entrariam na conta e o check ficaria quase-sempre verde. Verde-falso estrutural.
3. **Seções sobreviventes à eviction.** Seção evictada não é visível.

Respostas de tool (`get_e5_section`) ficam **fora de escopo**: são ancoráveis por
construção (ADR-341 D5) e imensuráveis in-process.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from backend.app.services.parecer_distiller import (
    VisibleMoneyLeaf,
    citation_catalog_for,
    declared_fields,
    iter_visible_money_paths,
    render_block,
    surviving_sections,
    walk_path,
)
from backend.app.services.parecer_manifest import ManifestData
from pipeline.llm.value_formatter import format_value


@dataclass(frozen=True)
class AnchorabilityReport:
    """Medição de ancorabilidade de um corpus. `inancoraveis` é o produto — o conjunto
    ordenado de paths, não um percentual: percentual se move por dois motivos ao mesmo
    tempo quando a fixture ganha bloco, e um #1004 futuro aparece como DIFF do conjunto."""

    visiveis: tuple[str, ...]
    ancoraveis: tuple[str, ...]
    inancoraveis: tuple[str, ...]
    catalogo_renderizado: int
    catalogo_construido: int
    hard_cut: bool

    @property
    def cobertura_pct(self) -> float:
        """Legibilidade apenas — nunca o gate (ver docstring da classe)."""
        if not self.visiveis:
            return 100.0
        return round(100.0 * len(self.ancoraveis) / len(self.visiveis), 1)


def measure_anchorability(
    manifest: ManifestData, e5_data: Mapping[str, Any]
) -> AnchorabilityReport:
    """Ancorabilidade de um E5 sob um manifest — determinística, in-process, US$ 0."""
    _sections, hard_cut = surviving_sections(manifest, e5_data)
    visiveis = _unique(leaf.path for leaf in iter_visible_money_paths(manifest, e5_data))
    construido, renderizado = citation_catalog_for(manifest, e5_data)
    rotas = {entry.path for entry in renderizado}
    return AnchorabilityReport(
        visiveis=visiveis,
        ancoraveis=tuple(p for p in visiveis if p in rotas),
        inancoraveis=tuple(p for p in visiveis if p not in rotas),
        catalogo_renderizado=len(renderizado),
        catalogo_construido=len(construido),
        hard_cut=hard_cut,
    )


def _unique(paths: Iterator[str]) -> tuple[str, ...]:
    """Dedupe preservando ordem — o mesmo path pode ser projetado por 2 blocos."""
    return tuple(dict.fromkeys(paths))


# ----------------------------------------------------------------------
# Paridade corpus ↔ manifest (A40.l30 item 5)
# ----------------------------------------------------------------------
# O eval de US$ 26 é CEGO ao mecanismo desta lane porque 3 dos blocos que #1004
# acrescentou ao corpo não existem no holdout: sem `janela_12m`,
# `receita_por_natureza` e `protecao_patrimonial`, um run responde "os gates ainda
# passam?" e não "o #1004 causou a queda?". Presença de bloco não basta como
# critério — `_render_table` com `rows == []` emite o cabeçalho sem nenhuma linha
# (`**Top ativos (até 15)** (top 0):`), e é esse estado que faz o corpus PARECER
# coberto. Daí 3 estados + a cardinalidade.

_STATE_WITH_DATA = "com_dado"
_STATE_EMPTY = "vazio"
_STATE_ABSENT = "ausente"


@dataclass(frozen=True)
class BlockCoverage:
    """Cobertura de um bloco do manifest por um corpus."""

    section_id: str
    block_title: str
    state: str
    cardinalidade: int
    # `_render_table` não se protege de lista vazia como `_render_key_value` se protege
    # de campo ausente — o cabeçalho órfão promete dado que não existe. Fix é do dono do
    # distiller (l31); aqui o instrumento apenas o NOMEIA em vez de contá-lo como cobertura.
    header_orfao: bool

    @property
    def covered(self) -> bool:
        return self.state == _STATE_WITH_DATA


def _declared_paths(block: Mapping[str, Any]) -> list[str]:
    if block.get("format") == "table":
        return [block["path"]] if block.get("path") else []
    return [f["path"] for f in declared_fields(block) if f.get("path")]


def _any_path_resolves(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> bool:
    return any(walk_path(e5_data, p) is not None for p in _declared_paths(block))


def _block_state(
    block: Mapping[str, Any], e5_data: Mapping[str, Any], *, section_id: str
) -> BlockCoverage:
    rendered = render_block(block, e5_data)
    data_lines = [line for line in rendered.splitlines() if line.lstrip().startswith("- ")]
    if data_lines:
        state = _STATE_WITH_DATA
    elif _any_path_resolves(block, e5_data):
        state = _STATE_EMPTY
    else:
        state = _STATE_ABSENT
    return BlockCoverage(
        section_id=section_id,
        block_title=str(block.get("title", block.get("path", ""))),
        state=state,
        cardinalidade=len(data_lines),
        header_orfao=bool(rendered) and not data_lines,
    )


def measure_block_coverage(
    manifest: ManifestData, e5_data: Mapping[str, Any]
) -> list[BlockCoverage]:
    """Cobertura de cada bloco projetado pelo manifest sobre um corpus."""
    # Sobre `manifest.sections` INTEIRO (não pós-eviction, ao contrário de
    # `measure_anchorability`): a pergunta aqui é "o corpus exercita o que o manifest
    # projeta?", e bloco evictado por budget continua sendo bloco que o eval deveria
    # poder exercitar.
    return [
        _block_state(block, e5_data, section_id=str(section.get("id", "")))
        for section in manifest.sections
        for block in section.get("blocks", []) or []
    ]


def iter_uncovered_paths(manifest: ManifestData, e5_data: Mapping[str, Any]) -> tuple[str, ...]:
    """Paths que o manifest projeta e o corpus NÃO fornece."""
    # Granularidade de path, não de bloco, e por razão medida: `receita_por_natureza.*`
    # são 4 campos DENTRO do bloco "Fluxo do período completo", que fica `com_dado`
    # porque os outros campos dele resolvem. Só o path revela a ausência — e é
    # exatamente um dos 3 buracos que tornam o eval cego ao mecanismo do #1004.
    # Colunas de tabela ficam fora: são paths relativos à linha, cobertos pela
    # cardinalidade do bloco.
    declared = _unique(
        p
        for section in manifest.sections
        for block in section.get("blocks", []) or []
        for p in _declared_paths(block)
    )
    return tuple(p for p in declared if walk_path(e5_data, p) is None)


# `VisibleMoneyLeaf`/`iter_visible_money_paths` moraram aqui até a A40.l83 e hoje
# vivem no distiller (quem renderiza é quem sabe o que renderizou). Re-exportados
# para não quebrar quem importa do instrumento.
__all__ = [
    "AnchorabilityReport",
    "BlockCoverage",
    "VisibleMoneyLeaf",
    "iter_uncovered_paths",
    "iter_visible_money_paths",
    "measure_anchorability",
    "measure_block_coverage",
]
