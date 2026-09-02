"""Destilação do exec context (manifest F5 → texto compactado, ADR-200)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from backend.app.services.parecer_citation_catalog import (
    CatalogEntry,
    build_citation_catalog,
    render_grouped_entries,
    select_catalog_entries,
)
from backend.app.services.parecer_manifest import ManifestData
from pipeline.llm.prompts._sanitization import contains_injection_pattern
from pipeline.llm.value_formatter import format_value

# Anti-injection de **saída** (ADR-203 §D9): redação de narrativas E5 destiladas
# no exec context do parecer. Fonte única de "o que é injeção" reconciliada com
# Layer 1 (ADR-175): consome ``contains_injection_pattern`` em vez de regex local.
# Distingue-se da entrada (Layer 1 stripa); aqui redata com marcador.
_MAX_NARRATIVA_CHARS = 500
_TRUNCATION_MARKER = "\n…[exec context truncado em max_exec_context_bytes]"

# ADR-341 D2: seção sem eviction_priority declarada é a primeira candidata a
# eviction — o schema do manifest exige o campo no arquivo canônico; o default
# só protege manifests sintéticos de teste de virar corte intra-seção silencioso.
_EVICT_FIRST_DEFAULT = 10_000

# Vocabulário de ausência do E5 (espelho de ``value_formatter._coerce_number``;
# A37.l4 + ADR-341): sentinela não é dado — folha "N/D"/""/"nan" é pulada no
# flatten como se fosse ``None`` (paridade com on_null:skip escalar).
_ABSENT_LEAF_SENTINELS = frozenset({"", "N/D", "nan"})


def _walk_indices(current: Any, indices: list[str]) -> Any:
    """Aplica indices [*] ou [n] sobre current. Wildcard terminal retorna lista."""
    for idx in indices:
        if idx == "*":
            if not isinstance(current, list):
                return None
            return current  # caller pára aqui — wildcard é terminal por convenção
        try:
            current = current[int(idx)]
        except (IndexError, TypeError, ValueError):
            return None
    return current


def tokenize_path_part(part: str) -> tuple[str, list[str]]:
    """Tokeniza ``foo[*][0]`` em ``("foo", ["*", "0"])``. Público: o guardrail
    pós-LLM classifica os mesmos paths e um segundo tokenizer divergiria."""
    base = part
    idxs: list[str] = []
    while "[" in base:
        head, _, tail = base.partition("[")
        idx, _, rest = tail.partition("]")
        idxs.append(idx)
        base = head + rest
    return base, idxs


def walk_path(data: Mapping[str, Any], path: str) -> Any:
    """Resolve JSONPath subset ``$.a.b[*].c`` sobre dict. Retorna None se ausente."""
    if not path.startswith("$."):
        return None
    current: Any = data
    for part in path[2:].split("."):
        base, idxs = tokenize_path_part(part)
        if not isinstance(current, Mapping):
            return None
        current = current.get(base)
        current = _walk_indices(current, idxs)
        if isinstance(current, list) and idxs and "*" in idxs:
            return current  # terminou em wildcard
        if current is None:
            return None
    return current


def redact_narrativas_inline(s: Any) -> Any:
    """Sanitiza strings de narrativas (truncate + redact se padrão hostil)."""
    if isinstance(s, str):
        s = s[:_MAX_NARRATIVA_CHARS] + ("…" if len(s) > _MAX_NARRATIVA_CHARS else "")
        if contains_injection_pattern(s):
            return "[REDACTED_SUSPECT_PATTERN]"
        return s
    if isinstance(s, Mapping):
        return {k: redact_narrativas_inline(v) for k, v in s.items()}
    if isinstance(s, list):
        return [redact_narrativas_inline(v) for v in s]
    return s


def _short(value: Any, *, limit: int = 300) -> str:
    """Stringify defensivo — limita tamanho por linha do exec context."""
    if isinstance(value, str):
        s = value
    elif isinstance(value, (int, float, bool)) or value is None:
        s = str(value)
    else:
        s = json.dumps(value, ensure_ascii=False, default=str)
    return s[:limit] + "…" if len(s) > limit else s


def _block_limit(block: Mapping[str, Any]) -> int:
    """Safety-net por bloco (ADR-341 D3): quem decide o que o LLM vê é o
    manifest; ``_short`` é rede de segurança com limite declarável via
    ``max_chars`` no bloco."""
    return int(block.get("max_chars", 300))


def _leaf_is_absent(value: Any) -> bool:
    """``None`` ou sentinela de ausência (A37.l4) — nunca renderizado como dado."""
    if value is None:
        return True
    return isinstance(value, str) and value.strip() in _ABSENT_LEAF_SENTINELS


def _render_scalar(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    path = block.get("path")
    if not path:
        return ""
    value = walk_path(e5_data, path)
    label = block.get("label", path)
    on_null = block.get("on_null", "skip")
    if value is None:
        if on_null == "skip":
            return ""
        return f"- **{label}**: —" if on_null == "placeholder" else f"- **{label}**: (ausente)"
    if path == "$.narrativas":
        value = redact_narrativas_inline(value)
    formatted = format_value(value, block.get("value_format", "raw"))
    return f"- **{label}**: {_short(formatted, limit=_block_limit(block))}"


def _flatten_leaves(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Achata dict/list em pares (chave_pontilhada, folha escalar). Cada folha é
    curta e sobrevive ao ``_short(300)`` individualmente — evita a truncação do
    dump raw que cortava os zeros estruturais no fim (PE-01)."""
    if not isinstance(value, (Mapping, list)):
        yield (prefix or "valor", value)
        return
    is_list = isinstance(value, list)
    items = enumerate(value) if is_list else value.items()
    for k, v in items:
        child = f"{prefix}[{k}]" if is_list else (f"{prefix}.{k}" if prefix else str(k))
        yield from _flatten_leaves(v, child)


def _render_field(field: Mapping[str, Any], value: Any, *, limit: int = 300) -> list[str]:
    """Uma linha por folha; dict/list é achatado (PE-01), escalar mantém o label.
    Folha None ou sentinela "N/D"/""/"nan" é ausência (A37.l4) — pulada,
    paridade com on_null:skip escalar."""
    if isinstance(value, (Mapping, list)):
        return [
            f"  - {leaf}: {_short(val, limit=limit)}"
            for leaf, val in _flatten_leaves(value)
            if not _leaf_is_absent(val)
        ]
    formatted = format_value(value, field.get("format", "raw"))
    return [f"  - {field.get('label', field['path'])}: {_short(formatted, limit=limit)}"]


def _render_key_value(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    on_null = block.get("on_null", "skip")
    limit = _block_limit(block)
    field_lines: list[str] = []
    for f in block.get("fields", []):
        v = walk_path(e5_data, f["path"])
        if v is None and on_null == "skip":
            continue
        field_lines.extend(_render_field(f, v, limit=limit))
    # Seção ausente (ex.: $.irpf_kpis num workspace sem IRPF, ADR-157) → NENHUM
    # campo sobrevive: omite o bloco inteiro (preserva a semântica on_null:skip do
    # scalar antigo; sem cabeçalho órfão prometendo dado inexistente).
    if not field_lines:
        return ""
    title = block.get("title", "")
    return "\n".join(([f"**{title}**:"] if title else []) + field_lines)


def _render_row(row: Mapping[str, Any], cols: list[dict]) -> str:
    cells = []
    for col in cols:
        v = row.get(col["path"])
        fv = format_value(v, col.get("format", "raw"))
        cells.append(f"{col.get('label', col['path'])}={_short(fv)}")
    return "  - " + " · ".join(cells)


def _render_table(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    path = block.get("path")
    rows = walk_path(e5_data, path) if path else None
    if not isinstance(rows, list):
        return ""
    max_rows = int(block.get("max_rows", 10))
    cols = block.get("columns", [])
    title = block.get("title", "")
    out = [f"**{title}** (top {min(len(rows), max_rows)}):"] if title else []
    for row in rows[:max_rows]:
        if isinstance(row, Mapping):
            out.append(_render_row(row, cols))
    return "\n".join(out)


def render_block(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    """Renderiza um block do manifest para texto plano (despacha por format)."""
    fmt = block.get("format")
    if fmt == "scalar":
        return _render_scalar(block, e5_data)
    if fmt == "key_value":
        return _render_key_value(block, e5_data)
    if fmt == "table":
        return _render_table(block, e5_data)
    return ""


def _render_section_body(section: dict, e5_data: Mapping[str, Any]) -> str:
    """Renderiza header + blocks de uma seção (hints ficam fora do corpo — ADR-341 D4)."""
    parts: list[str] = [f"### {section.get('title', section.get('id', ''))}"]
    for block in section.get("blocks", []):
        rendered = render_block(block, e5_data)
        if rendered:
            parts.append(rendered)
    parts.append("")
    return "\n".join(parts)


_HINTS_HEADER = "### Diretrizes de leitura por seção (hints)"


def _render_hints_block(sections: list[dict]) -> str:
    """Hints fora do corpo orçado (ADR-341 D4) — guidance não compete com dado
    por budget. Inclui hints de seções evictadas: a diretriz continua valendo se
    a seção voltar ao corpo num run com outro perfil de eviction."""
    lines = [
        f"_hint ({section.get('id', '')}):_ {hint}"
        for section in sections
        for hint in section.get("narrative_hints", []) or []
    ]
    return "\n".join([_HINTS_HEADER, *lines]) if lines else ""


def _eviction_marker(evicted: list[dict]) -> str:
    """Marcador nomeando as seções removidas (ADR-341 D2). Sem rota de recovery: o
    modelo é single-shot (A40.l117), e prometer `get_e5_section` aqui era o único convite
    morto que caía DENTRO do corpo orçado."""
    ids = ", ".join(str(s.get("id", "?")) for s in evicted)
    return (
        f"\n…[exec context truncado em max_exec_context_bytes — seções removidas "
        f"por prioridade: {ids}. Não-mostradas, não inexistentes: registre o "
        f"conceito em campos_faltantes em vez de afirmar ausência.]"
    )


def _eviction_order(sections: list[dict]) -> list[int]:
    """Índices na ordem de remoção (ADR-341 D2): maior ``eviction_priority`` sai
    primeiro (1 = mais importante, última a sair); empate → seção mais abaixo no
    manifest sai primeiro. Determinístico por construção."""
    return sorted(
        range(len(sections)),
        key=lambda i: (int(sections[i].get("eviction_priority", _EVICT_FIRST_DEFAULT)), i),
        reverse=True,
    )


def _join_body(bodies: list[str], kept: list[int], evicted: list[dict]) -> str:
    body = "\n".join(bodies[i] for i in kept)
    return body + (_eviction_marker(evicted) if evicted else "")


def _hard_cut(bodies: list[str], kept: list[int], evicted: list[dict], cap: int) -> str:
    """Safety-net degenerado: a única seção restante sozinha excede o cap — corte
    por bytes preservando o marcador no fim (único ponto onde corte intra-seção
    sobrevive; o caso geral é coberto pela eviction por seção, ADR-341 D2)."""
    marker = _eviction_marker(evicted) if evicted else _TRUNCATION_MARKER
    budget = max(cap - len(marker.encode("utf-8")), 0)
    body = "\n".join(bodies[i] for i in kept)
    return body.encode("utf-8")[:budget].decode("utf-8", errors="ignore") + marker


def _evict_to_budget(
    sections: list[dict], bodies: list[str], cap: int
) -> tuple[list[int], list[dict]]:
    """Índices mantidos + seções evictadas (ADR-341 D2): corpo excede o budget →
    remove seções INTEIRAS de menor prioridade até caber (marcador incluso no
    orçamento). Nunca corta no meio de seção enquanto houver seção a evictar."""
    kept = list(range(len(sections)))
    evicted: list[dict] = []
    victims = iter(_eviction_order(sections))
    while len(_join_body(bodies, kept, evicted).encode("utf-8")) > cap and len(kept) > 1:
        victim = next(victims)
        kept.remove(victim)
        evicted.append(sections[victim])
    return kept, evicted


def _fit_body_to_budget(sections: list[dict], bodies: list[str], cap: int) -> str:
    kept, evicted = _evict_to_budget(sections, bodies, cap)
    body = _join_body(bodies, kept, evicted)
    if len(body.encode("utf-8")) <= cap:
        return body
    return _hard_cut(bodies, kept, evicted, cap)


# Existe para o instrumento de ancorabilidade (A40.l30 item 2) medir o **observável** e
# não o teto: seção evictada não é visível, e medir sobre `manifest.sections` inteiro
# produziria baseline otimista — o espelho exato do "piso lido como medida" que a lane
# fecha. O flag de hard cut é necessário porque aí a atribuição por seção deixa de ser
# exata (o corte é no meio de uma seção) e o instrumento tem de se declarar degradado em
# vez de reportar número que não pode sustentar.
def surviving_sections(
    manifest: ManifestData, e5_data: Mapping[str, Any]
) -> tuple[list[dict], bool]:
    """Seções que o modelo de fato vê, + se o corpo sofreu ``_hard_cut``."""
    bodies = [_render_section_body(section, e5_data) for section in manifest.sections]
    cap = manifest.max_exec_context_bytes
    kept, evicted = _evict_to_budget(manifest.sections, bodies, cap)
    hard_cut = len(_join_body(bodies, kept, evicted).encode("utf-8")) > cap
    return [manifest.sections[i] for i in kept], hard_cut


# ----------------------------------------------------------------------
# Folhas R$ que o corpo renderizado contém (movido da A40.l30 pela A40.l83)
# ----------------------------------------------------------------------
# Mora AQUI, e não no instrumento de ancorabilidade, porque quem sabe o que o
# corpo contém é quem o renderiza. Enquanto morava lá, produção precisava
# importar um módulo de medição para semear o catálogo — dependência invertida,
# e a classe exata de drift que a l83 fecha: instrumento e produção respondendo
# "o que o modelo vê?" por caminhos diferentes.

_MONEY_FORMAT = "brl"
_MONEY_PREFIX = "R$"
_LIST_WILDCARD = "[*]"


@dataclass(frozen=True)
class VisibleMoneyLeaf:
    """Folha monetária que o modelo VÊ no corpo, com a seção que a projeta."""

    path: str
    section_id: str


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
    for field in declared_fields(block):
        if field.get(format_key) != _MONEY_FORMAT:
            continue
        value = walk_path(e5_data, field["path"])
        if value is None and on_null_skips:
            continue
        if isinstance(value, (Mapping, list)) or not _renders_money(value):
            continue
        yield field["path"]


def declared_fields(block: Mapping[str, Any]) -> list[dict]:
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


# Produção renderiza o segundo; o instrumento de ancorabilidade mede os dois. Ter
# dois produtores era o que deixava a medição divergir do que o modelo de fato
# recebe — o par que a lane mediu como 30 construídas vs 16 renderizadas.
def citation_catalog_for(
    manifest: ManifestData, e5_data: Mapping[str, Any]
) -> tuple[list[CatalogEntry], list[CatalogEntry]]:
    """``(construído, renderizado)`` — produtor ÚNICO do catálogo (A40.l83)."""
    cfg = manifest.citation_catalog
    if not cfg.emit:
        return [], []
    seed = [leaf.path for leaf in iter_visible_money_paths(manifest, e5_data)]
    construido = build_citation_catalog(
        e5_data,
        section_whitelist=manifest.tools_section_whitelist,
        max_entries=cfg.max_entries,
        seed_paths=seed,
    )
    return construido, select_catalog_entries(construido, max_bytes=cfg.max_bytes)


def _render_catalog_block(manifest: ManifestData, e5_data: Mapping[str, Any]) -> str:
    """Catálogo de citação (A26.l1) — vazio se emit desligado."""
    _construido, renderizado = citation_catalog_for(manifest, e5_data)
    return render_grouped_entries(renderizado) if renderizado else ""


def distill_exec_context(manifest: ManifestData, e5_data: Mapping[str, Any]) -> str:
    """Aplica manifest sobre E5 → corpo orçado com eviction por seção (ADR-341)
    + hints + catálogo de citação — ambos anexados APÓS o cap, com orçamento
    próprio (padrão A26.l1): guidance/evidência nunca competem com dado."""
    bodies = [_render_section_body(section, e5_data) for section in manifest.sections]
    body = _fit_body_to_budget(manifest.sections, bodies, manifest.max_exec_context_bytes)
    hints = _render_hints_block(manifest.sections)
    catalog = _render_catalog_block(manifest, e5_data)
    return "\n\n".join(part for part in (body, hints, catalog) if part)
