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
from pipeline.llm.value_formatter import FormatHint, format_value

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

# Raízes top-level fora do catálogo monetário. ``previdencia_pgbl`` é um
# contrato legado: o Card B em ``irpf_kpis`` é o dono único do teto/capacidade.
_NON_CITABLE_ROOTS = frozenset({"score", "ratios", "equilibrio_cerbasi", "previdencia_pgbl"})

# Séries do cone Monte Carlo — NÃO citáveis por decisão (A40.l25), não por
# acidente de predicado. São estimativas com dispersão amostral de ~1,2% a
# n=50k; citá-las daria ao parecer uma frase como "R$ 11.037.269,90" sobre um
# número que muda de run para run dentro dessa faixa — precisão inventada sobre
# projeção. Hoje `_is_money_leaf` já não casa lista de pares, então a exclusão
# é redundante NA PRÁTICA; existe para que tornar a folha citável seja uma
# escolha explícita e não um efeito colateral de mexer no predicado.
_NAO_CITAVEL_ESTIMATIVA = frozenset({"caminho_p10", "caminho_p50", "caminho_p90"})

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
    "irpf_kpis",
)

_CATALOG_HEADER = "### Evidência citável (evidencia_paths_disponiveis)"
_CATALOG_INSTRUCTION = (
    "_Para fundamentar um valor, NÃO escreva o R$ na prosa: emita uma âncora "
    "ancoras:[{path, rotulo}] copiando UMA linha abaixo — path = o path da linha, "
    "rotulo = o rotulo_id entre colchetes (identificador, não o texto do chip). "
    "O sistema renderiza o número a partir do path. Conceito ausente daqui → "
    "não ancore (use campos_faltantes_pediria_se_iterasse[])._"
)


@dataclass(frozen=True)
class CatalogEntry:
    """Uma folha citável: path + valor formatado (R$) + raiz + rotulo_id opcional."""

    path: str
    display_value: str
    root: str
    rotulo_id: str | None = None


def _is_money_key(key: str) -> bool:
    low = key.lower()
    if any(marker in low for marker in _NON_MONEY_MARKERS):
        return False
    return any(token in low for token in _MONEY_KEY_TOKENS)


# --- Tipo de folha por nome de campo (A28.l10) ---------------------------------
# A folha conhece seu campo: o dispatch de formatação do finalize (ADR-296) vem
# DAQUI — nunca de heurística sobre o valor. Ordem importa: "prob_reserva_ideal"
# contém o token monetário "reserva" e só é percentual porque "prob" vence
# primeiro. O exemplo canônico era `prob_if_ate_idade_meta` ("meta" é token
# monetário), removida na ADR-369 D2 junto com `idade_meta_usada`: as chaves
# sucessoras (`prob_if_ate_prazo_declarado`, `prazo_declarado_anos`) não contêm
# token monetário e, por isso, deixam de ser folhas citáveis — o catálogo é
# `monetary_only`, e a citabilidade das anteriores era acidente, não feature.
_PCT_KEY_MARKERS = ("pct", "percent", "percentual")
_COUNT_KEY_MARKERS = ("count", "qtd", "quantidade")


def _ancora_leaf_key(path: str) -> str:
    """Último segmento do JSONPath, sem índice de lista: ``$.a.b[2]`` → ``b``."""
    return path.rsplit(".", 1)[-1].split("[", 1)[0]


def ancora_format_hint(path: str) -> FormatHint:
    """Format hint da folha citada, derivado do nome do campo no path (A28.l10) —
    fecha o dogfood 72883bde: ``prob_if_ate_idade_meta=0.31`` → "31%" (não
    "R$ 0,31"); ``idade_meta_usada=53`` → "53 anos" (não "R$ 53,00")."""
    key = _ancora_leaf_key(path).lower()
    if "prob" in key:
        return "prob_pct"
    if "idade" in key:
        return "anos"
    if "concentracao" in key:  # SSOT risco ADR-340, sem _pct (R3.3)
        return "percent2"
    if any(m in key for m in _PCT_KEY_MARKERS):
        return "pct"
    if "meses" in key and "nivel" not in key:
        return "meses"  # nivel_N_meses é nível de reserva em R$ (cai no _is_money_key)
    if key.startswith("n_") or any(m in key for m in _COUNT_KEY_MARKERS):
        return "int"
    if _is_money_key(key):
        return "brl"
    return "string"


def _is_money_leaf(key: str, value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and _is_money_key(key)


# Top-K itens por lista (A26.l7). Listas de alto valor (top_ativos) já vêm
# ordenadas por valor desc; o cap evita estourar max_entries com lista longa.
_MAX_LIST_ITEMS = 5


def _leaf_paths_for(key: str, value: Any, prefix: str) -> Iterator[str]:
    """Paths citáveis de um par chave/valor (recursa em dicts E listas — A26.l7)."""
    if not key.isidentifier() or (prefix == "$" and key in _NON_CITABLE_ROOTS):
        return
    if key in _NAO_CITAVEL_ESTIMATIVA:
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


def _entry_for(
    drill: PlannerDrillDown, path: str, labels: Mapping[str, Any]
) -> CatalogEntry | None:
    """CatalogEntry se o path resolve no verificador; None caso contrário."""
    result = drill.get_e5_jsonpath(path)
    if not result.found:
        return None
    mapped = labels.get(path)
    rotulo_id = mapped.rotulo_id if mapped is not None else None
    return CatalogEntry(
        path=path,
        display_value=format_value(result.value, "brl"),
        root=path[2:].split(".", 1)[0],
        rotulo_id=rotulo_id,
    )


def build_citation_catalog(
    e5_data: Mapping[str, Any],
    *,
    section_whitelist: frozenset[str],
    max_entries: int = 30,
    labels: Mapping[str, Any] | None = None,
) -> list[CatalogEntry]:
    """Folhas monetárias resolvíveis pelo verificador, priorizadas e capadas."""
    from backend.app.services.parecer_manifest import load_manifest

    resolved = labels if labels is not None else load_manifest().citation_labels
    drill = PlannerDrillDown(e5_data=e5_data, section_whitelist=section_whitelist, format_hints={})
    entries = [e for p in _iter_money_leaf_paths(e5_data) if (e := _entry_for(drill, p, resolved))]
    entries.sort(key=_priority_key)
    return entries[:max_entries]


def _render_line(entry: CatalogEntry) -> str:
    if entry.rotulo_id:
        return f"- `{entry.path}` [{entry.rotulo_id}] → {entry.display_value}"
    return f"- `{entry.path}` → {entry.display_value}"


def _render_grouped(entries: list[CatalogEntry]) -> str:
    head = f"{_CATALOG_HEADER}\n{_CATALOG_INSTRUCTION}"
    lines: list[str] = []
    current_root: str | None = None
    for entry in entries:
        if entry.root != current_root:
            current_root = entry.root
            lines.append(f"**{entry.root}**")
        lines.append(_render_line(entry))
    return head + "\n" + "\n".join(lines)


# Extraído de ``render_citation_catalog`` (sem mudança de comportamento) porque
# ancorabilidade é propriedade do catálogo **renderizado**, não do construído: medido em
# 2026-08-07 no corpus sintético, `build_citation_catalog` devolve 29 entries e este corte
# deixa 20 — a diferença entre 94% e 78% de cobertura. Um instrumento que consultasse o
# construído ficaria verde-falso (A40.l30 item 2).
def select_catalog_entries(entries: list[CatalogEntry], *, max_bytes: int) -> list[CatalogEntry]:
    """Entries que CABEM no bloco — as que o modelo de fato recebe."""
    selected: list[CatalogEntry] = []
    for entry in entries:
        projection = _render_grouped(selected + [entry])
        if selected and len(projection.encode("utf-8")) > max_bytes:
            break
        selected.append(entry)
    return selected


def render_citation_catalog(entries: list[CatalogEntry], *, max_bytes: int) -> str:
    """Bloco markdown agrupado por raiz; trunca por entry (prioridade) sem órfãos."""
    if not entries:
        return ""
    return _render_grouped(select_catalog_entries(entries, max_bytes=max_bytes))


__all__ = [
    "CatalogEntry",
    "ancora_format_hint",
    "build_citation_catalog",
    "render_citation_catalog",
    "select_catalog_entries",
]
