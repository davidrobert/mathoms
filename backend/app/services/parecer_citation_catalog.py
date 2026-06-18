"""Catálogo de citação E5→E6 — folhas monetárias citáveis (ADR-279 §E · A26.l1)."""

# O LLM citava evidencia_path adivinhando JSONPath. Aqui as folhas monetárias
# não-nulas do E5 são resolvidas pelo MESMO get_e5_jsonpath do verificador
# (parecer_evidencia) — todo path listado passa o verify por construção
# (mata whitelist_miss + resolve_null) e o valor exibido faz round-trip em cents
# (mata value_mismatch quando o LLM copia o token).

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from pipeline.llm.tools.planner_drill_down import PlannerDrillDown
from pipeline.llm.value_formatter import format_value

# Folhas cujo nome indica valor monetário (R$). O verificador só checa tokens R$;
# contagens/percentuais/anos não são citáveis e só inflam o budget.
_MONEY_KEY_TOKENS = (
    "valor",
    "total",
    "saldo",
    "bruto",
    "liquido",
    "liquida",
    "despesa",
    "despesas",
    "receita",
    "renda",
    "reserva",
    "divida",
    "dividas",
    "patrimonio",
    "contribuicao",
    "aporte",
    "custo",
    "gasto",
    "limite",
    "capital",
    "premio",
    "folga",
    "caixa",
    "nivel_",
    "abate",
    "meta",
)
# Sufixos/infixos que vetam mesmo com noun monetário — ``meta_pct`` (percentual),
# ``n_imoveis_total`` (contagem) e correlatos não são R$. (``_meses`` fica fora:
# ``nivel_6_meses`` é nível de reserva em R$.)
_NON_MONEY_MARKERS = ("pct", "percent", "count", "qtd", "n_imoveis")

# Raízes top-level cujo conteúdo é score/ratio/comportamento — nunca R$ citável.
_NON_MONEY_ROOTS = frozenset({"score", "ratios", "equilibrio_cerbasi"})

# Densidade de citação esperada (narrative_hints), não valor R$ — prompt-engineer
# 2026-06-16. Raiz fora desta lista cai no fim, truncada primeiro sob max_bytes.
_PRIORITY_ROOTS = (
    "reserva_emergencia",
    "endividamento",
    "passive_income",
    "if_monte_carlo",
    "patrimonio",
    "fluxo_caixa",
    "investimentos",
    "previdencia_pgbl",
    "irpf_kpis",
)

_CATALOG_HEADER = "### Evidência citável (evidencia_paths_disponiveis)"
_CATALOG_INSTRUCTION = (
    "_Cite valores R$ EXCLUSIVAMENTE destes paths, copiando o valor exato. "
    "Campo ausente daqui → não cite o valor (use "
    "campos_faltantes_pediria_se_iterasse[]). A lista é seu vocabulário de "
    "evidência: cite o que ESTÁ nela quando relevante._"
)


@dataclass(frozen=True)
class CatalogEntry:
    """Uma folha citável: path + valor formatado (R$) + raiz (seção dona)."""

    path: str
    display_value: str
    root: str


def _is_money_key(key: str) -> bool:
    low = key.lower()
    if any(marker in low for marker in _NON_MONEY_MARKERS):
        return False
    return any(token in low for token in _MONEY_KEY_TOKENS)


def _is_money_leaf(key: str, value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and _is_money_key(key)


# Top-K itens por lista (A26.l7). Listas de alto valor (top_ativos) já vêm
# ordenadas por valor desc; o cap evita estourar max_entries com lista longa.
_MAX_LIST_ITEMS = 5


def _leaf_paths_for(key: str, value: Any, prefix: str) -> Iterator[str]:
    """Paths citáveis de um par chave/valor (recursa em dicts E listas — A26.l7)."""
    if not key.isidentifier() or (prefix == "$" and key in _NON_MONEY_ROOTS):
        return
    path = f"{prefix}.{key}"
    if isinstance(value, Mapping):
        yield from _iter_money_leaf_paths(value, path)
        return
    if isinstance(value, list):
        yield from _iter_list_money_leaf_paths(value, path, key)
        return
    if _is_money_leaf(key, value):
        yield path


def _item_money_value(item: Any):
    """Valor representativo do item de lista, para ranquear top-K (maior folha R$)."""
    if isinstance(item, Mapping):
        return max((v for k, v in item.items() if _is_money_leaf(k, v)), default=0)
    return item if isinstance(item, (int, float)) and not isinstance(item, bool) else 0


def _top_money_indices(items: list, k: int) -> list[int]:
    """Índices ORIGINAIS dos k itens de maior valor (re-indexar quebraria o path)."""
    ranked = sorted(range(len(items)), key=lambda i: _item_money_value(items[i]), reverse=True)
    return sorted(ranked[:k])


def _iter_list_money_leaf_paths(items: list, prefix: str, key: str) -> Iterator[str]:
    """Folhas R$ de itens de lista — top-K por valor, índice original, ``[idx].subkey`` escalar (nunca ``[*]``: resolveria à lista inteira e o ``any()`` do verificador maximizaria falso-verde, ADR-292)."""
    for i in _top_money_indices(items, _MAX_LIST_ITEMS):
        item = items[i]
        if isinstance(item, Mapping):
            yield from _iter_money_leaf_paths(item, f"{prefix}[{i}]")
            continue
        if _is_money_leaf(key, item):
            yield f"{prefix}[{i}]"


def _iter_money_leaf_paths(data: Any, prefix: str = "$") -> Iterator[str]:
    """Paths $.a.b.c de folhas monetárias (int/float), recursando dicts e listas (A26.l7)."""
    if not isinstance(data, Mapping):
        return
    for key, value in data.items():
        yield from _leaf_paths_for(key, value, prefix)


def _priority_key(entry: CatalogEntry) -> tuple[int, str]:
    try:
        rank = _PRIORITY_ROOTS.index(entry.root)
    except ValueError:
        rank = len(_PRIORITY_ROOTS)
    return (rank, entry.path)


def _entry_for(drill: PlannerDrillDown, path: str) -> CatalogEntry | None:
    """CatalogEntry se o path resolve no verificador; None caso contrário."""
    result = drill.get_e5_jsonpath(path)
    if not result.found:
        return None
    value = format_value(result.value, "brl")
    return CatalogEntry(path=path, display_value=value, root=path[2:].split(".", 1)[0])


def build_citation_catalog(
    e5_data: Mapping[str, Any], *, section_whitelist: frozenset[str], max_entries: int = 30
) -> list[CatalogEntry]:
    """Folhas monetárias resolvíveis pelo verificador, priorizadas e capadas."""
    drill = PlannerDrillDown(e5_data=e5_data, section_whitelist=section_whitelist, format_hints={})
    entries = [e for p in _iter_money_leaf_paths(e5_data) if (e := _entry_for(drill, p))]
    entries.sort(key=_priority_key)
    return entries[:max_entries]


def _render_grouped(entries: list[CatalogEntry]) -> str:
    head = f"{_CATALOG_HEADER}\n{_CATALOG_INSTRUCTION}"
    lines: list[str] = []
    current_root: str | None = None
    for entry in entries:
        if entry.root != current_root:
            current_root = entry.root
            lines.append(f"**{entry.root}**")
        lines.append(f"- `{entry.path}` → {entry.display_value}")
    return head + "\n" + "\n".join(lines)


def render_citation_catalog(entries: list[CatalogEntry], *, max_bytes: int) -> str:
    """Bloco markdown agrupado por raiz; trunca por entry (prioridade) sem órfãos."""
    if not entries:
        return ""
    selected: list[CatalogEntry] = []
    for entry in entries:
        projection = _render_grouped(selected + [entry])
        if selected and len(projection.encode("utf-8")) > max_bytes:
            break
        selected.append(entry)
    return _render_grouped(selected)


__all__ = ["CatalogEntry", "build_citation_catalog", "render_citation_catalog"]
