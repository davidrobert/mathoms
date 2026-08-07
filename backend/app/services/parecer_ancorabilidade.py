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

from backend.app.services.parecer_citation_catalog import (
    build_citation_catalog,
    select_catalog_entries,
)
from backend.app.services.parecer_distiller import render_block, surviving_sections, walk_path
from backend.app.services.parecer_manifest import ManifestData
from pipeline.llm.value_formatter import format_value

# Só `brl` emite token R$ no corpo. `raw` devolve o valor cru, `pct`/`int`/`string`
# formatam sem prefixo, e `format_value(None, "brl")` → "—" (sem R$).
_MONEY_FORMAT = "brl"
_MONEY_PREFIX = "R$"
_LIST_WILDCARD = "[*]"


@dataclass(frozen=True)
class VisibleMoneyLeaf:
    """Folha monetária que o modelo VÊ no corpo, com a seção que a projeta."""

    path: str
    section_id: str


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


def _renders_money(value: Any) -> bool:
    """Pergunta ao MESMO formatter do renderer se a folha imprime "R$ ...". `None` vira
    "—" e sentinela ("N/D"/""/"nan") volta como string crua — nenhuma dá token R$.
    Reusar `format_value` em vez de reimplementar a coerção evita que o instrumento
    derive do renderer sem ninguém notar."""
    return str(format_value(value, _MONEY_FORMAT)).lstrip("-").startswith(_MONEY_PREFIX)


def _format_key(block: Mapping[str, Any]) -> str:
    """`scalar` declara `value_format`; `key_value`/`table` declaram `format` por campo."""
    return "value_format" if block.get("format") == "scalar" else "format"


def _field_money_paths(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> Iterator[str]:
    """Folhas R$ de bloco `key_value`/`scalar`. Campo cujo valor é dict/list NÃO conta:
    `_render_field` achata em folhas cruas e o format é ignorado (sem prefixo R$)."""
    on_null_skips = block.get("on_null", "skip") == "skip"
    format_key = _format_key(block)
    for field in _declared_fields(block):
        if field.get(format_key) != _MONEY_FORMAT:
            continue
        value = walk_path(e5_data, field["path"])
        if value is None and on_null_skips:
            continue
        if isinstance(value, (Mapping, list)) or not _renders_money(value):
            continue
        yield field["path"]


def _declared_fields(block: Mapping[str, Any]) -> list[dict]:
    if block.get("format") == "scalar":
        return [dict(block)] if block.get("path") else []
    return list(block.get("fields", []) or [])


def _list_root(path: str) -> str:
    """`$.a.b[*]` → `$.a.b`. O manifest declara a lista com wildcard; o catálogo indexa
    (`$.a.b[5].valor`, via `_iter_list_money_leaf_paths`). Sem normalizar o sufixo,
    path↔path nunca casa e TODA linha de tabela apareceria inancorável — FP de 100%."""
    return path[: -len(_LIST_WILDCARD)] if path.endswith(_LIST_WILDCARD) else path


def _row_money_paths(row: Mapping[str, Any], root: str, index: int, cols: list[dict]):
    for col in cols:
        if _renders_money(row.get(col["path"])):
            yield f"{root}[{index}].{col['path']}"


# Fonte de inancorabilidade ESTRUTURAL, não de bytes: o corpo renderiza `max_rows` (10 em
# `tabela_classes`, 15 em `top_ativos`) e o catálogo pega `_MAX_LIST_ITEMS = 5` — e pega
# **por maior valor** (`_top_money_indices`), não por posição. Logo há linha visível sem
# rota por *ranking*, que nenhum ajuste de `max_bytes` resolve.
def _table_money_paths(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> Iterator[str]:
    """Folhas R$ de bloco `table` — o path efetivo é `{block.path}[i].{col.path}`."""
    path = block.get("path")
    rows = walk_path(e5_data, path) if path else None
    if not isinstance(rows, list):
        return
    cols = [c for c in block.get("columns", []) if c.get("format") == _MONEY_FORMAT]
    root = _list_root(path)
    for i, row in enumerate(rows[: int(block.get("max_rows", 10))]):
        if isinstance(row, Mapping):
            yield from _row_money_paths(row, root, i, cols)


def _block_money_paths(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> Iterator[str]:
    if block.get("format") == "table":
        yield from _table_money_paths(block, e5_data)
        return
    yield from _field_money_paths(block, e5_data)


def _leaves_of(sections: list[dict], e5_data: Mapping[str, Any]) -> list[VisibleMoneyLeaf]:
    return [
        VisibleMoneyLeaf(path=path, section_id=str(section.get("id", "")))
        for section in sections
        for block in section.get("blocks", []) or []
        for path in _block_money_paths(block, e5_data)
    ]


def iter_visible_money_paths(
    manifest: ManifestData, e5_data: Mapping[str, Any]
) -> list[VisibleMoneyLeaf]:
    """Folhas R$ que o modelo vê no CORPO (pré-catálogo, pós-eviction), em ordem."""
    sections, _hard_cut = surviving_sections(manifest, e5_data)
    return _leaves_of(sections, e5_data)


def measure_anchorability(
    manifest: ManifestData, e5_data: Mapping[str, Any]
) -> AnchorabilityReport:
    """Ancorabilidade de um E5 sob um manifest — determinística, in-process, US$ 0."""
    sections, hard_cut = surviving_sections(manifest, e5_data)
    visiveis = _unique(leaf.path for leaf in _leaves_of(sections, e5_data))
    cfg = manifest.citation_catalog
    construido = build_citation_catalog(
        e5_data, section_whitelist=manifest.tools_section_whitelist, max_entries=cfg.max_entries
    )
    renderizado = select_catalog_entries(construido, max_bytes=cfg.max_bytes) if cfg.emit else []
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
    return [f["path"] for f in _declared_fields(block) if f.get("path")]


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


__all__ = [
    "AnchorabilityReport",
    "BlockCoverage",
    "VisibleMoneyLeaf",
    "iter_uncovered_paths",
    "iter_visible_money_paths",
    "measure_anchorability",
    "measure_block_coverage",
]
