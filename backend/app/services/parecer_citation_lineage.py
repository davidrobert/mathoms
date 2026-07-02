"""Chave natural estável de folhas de LISTA citadas no parecer (A27.l1 · ADR-293 slice 1).

O path de citação (ADR-292 / A26.l7) endereça itens de lista por índice posicional
(``$.investimentos.top_ativos[3].valor``). ``top_ativos`` é ordenado por valor desc, então
``[3]`` aponta para outro ativo após rebaseline — **instável cross-run**. Para materializar
a citação como edge de lineage persistente ([[ADR-293]]), a ``src`` precisa de chave
NATURAL derivada do conteúdo do item, não do índice: ``top_ativos`` →
``(membro, instituicao, nome)`` + ``posicao`` como tie-break; ``alocacao_por_classe`` →
``classe``. Confinada à serialização do edge (``src_field`` string) — **não** toca o schema
E5 (zero migration). Path escalar (sem ``[i]``) já é estável por path → retorna ``None``."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from pipeline.domain.services.lineage_edge_deriver import LineageEdge

_SEGMENT_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?")

# Campos que formam a chave natural por tipo de lista (ADR-293 §2). Ordem = ordem no key.
_TOP_ATIVO_KEY = ("membro", "instituicao", "nome")


def _walk_to_last_list_item(e5_data: Mapping[str, Any], path: str) -> dict | None:
    """Navega o path e retorna o item-dict do segmento mais profundo com ``[idx]``, ou None."""
    body = path[2:] if path.startswith("$.") else path.lstrip("$")
    node: Any = e5_data
    last_item: dict | None = None
    for seg in body.split("."):
        m = _SEGMENT_RE.fullmatch(seg)
        if m is None or not isinstance(node, Mapping) or m.group(1) not in node:
            return None
        node = node[m.group(1)]
        if m.group(2) is None:
            continue
        idx = int(m.group(2))
        if not isinstance(node, list) or idx >= len(node):
            return None
        node = node[idx]
        if isinstance(node, Mapping):
            last_item = node
    return last_item


def _natural_key_of(item: Mapping[str, Any]) -> str | None:
    """String de chave natural do item de lista (ADR-293 §2); None se não reconhecido."""
    if "classe" in item:
        return f"classe={item['classe']}"
    if all(k in item for k in _TOP_ATIVO_KEY):
        parts = [f"{k}={item[k]}" for k in _TOP_ATIVO_KEY]
        if "posicao" in item:  # tie-break determinístico (ADR-293 §2)
            parts.append(f"posicao={item['posicao']}")
        return "|".join(parts)
    return None


def resolve_citation_natural_key(e5_data: Mapping[str, Any], path: str) -> str | None:
    """Chave natural estável da folha de LISTA citada (ADR-293 A27.l1); ``None`` se o path é
    escalar (estável por path) ou não resolve a item conhecido. Content-based: o mesmo item
    produz a mesma chave em qualquer posição — torna o edge reproduzível cross-run (KR3)."""
    item = _walk_to_last_list_item(e5_data, path)
    return _natural_key_of(item) if item is not None else None


def _citation_edge(src_field: str, dst_field: str) -> "LineageEdge":
    from backend.app.services.lineage_edge_writer import PARECER_CITATION_DST_STAGE
    from pipeline.domain.services.lineage_edge_deriver import LineageEdge

    return LineageEdge(
        src_stage="E5",
        src_key="analise_financeira",
        src_field=src_field,
        dst_stage=PARECER_CITATION_DST_STAGE,
        dst_key="parecer_planejador",
        dst_field=dst_field,
        edge_type="parecer_citation",
        rule_ref="",
        source_document_id=None,
        data_source_id=None,
        winner=True,
    )


def build_parecer_citation_edges(
    e5_data: Mapping[str, Any], evidencia_entries: list[Mapping[str, Any]]
) -> list["LineageEdge"]:
    """Edges ``parecer_citation`` das âncoras VERIFICADAS (ADR-293 slice 2): ``src_field`` =
    chave natural em folha de lista (estável cross-run) ou o próprio path escalar; âncora
    falhada/sem path nunca vira edge — o grafo só carrega citação verificada."""
    edges: list["LineageEdge"] = []
    seen: set[tuple[str, str]] = set()
    for entry in evidencia_entries:
        path = entry.get("path")
        if entry.get("outcome") != "verified" or not path:
            continue
        dst_field = f"{entry.get('item_type')}[{entry.get('item_index')}]"
        src_field = resolve_citation_natural_key(e5_data, path) or path
        if (src_field, dst_field) in seen:
            continue
        seen.add((src_field, dst_field))
        edges.append(_citation_edge(src_field, dst_field))
    return edges


__all__ = ["build_parecer_citation_edges", "resolve_citation_natural_key"]
