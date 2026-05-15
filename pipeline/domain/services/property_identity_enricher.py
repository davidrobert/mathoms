"""Anexa `property_id` UUID estável a imóveis do baseline consolidado (ADR-215 P2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipeline.domain.services.endereco_canonicalizer import canonicalize
from pipeline.domain.types.property_identity import PropertyLookupKey

if TYPE_CHECKING:
    from pipeline.ports import PropertyIdentityResolver


def enrich_imoveis_with_property_ids(
    consolidated: dict,
    resolver: "PropertyIdentityResolver",
    workspace_id: str,
) -> dict:
    """Anexa `property_id`, `endereco_canonical`, `low_confidence` (ADR-215 P2)."""
    # Mutates `consolidated["imoveis_consolidados"]` in-place. Entries sem
    # codigo_rfb (legado) recebem low_confidence=True sem property_id.
    imoveis = consolidated.get("imoveis_consolidados", [])
    if not imoveis:
        return consolidated

    for entry in imoveis:
        titular_key = (entry.get("proprietario") or "").strip().lower()
        codigo_rfb = (entry.get("codigo_rfb") or "").strip()
        descricao = entry.get("descricao") or ""
        first_seen_year = int(entry.get("ano_referencia") or 0)

        if not titular_key or not codigo_rfb:
            entry["property_id"] = None
            entry["endereco_canonical"] = None
            entry["low_confidence"] = True
            continue

        endereco_canonical = canonicalize(descricao)
        lookup = PropertyLookupKey(
            titular_key=titular_key,
            codigo_rfb=codigo_rfb,
            endereco_canonical=endereco_canonical,
        )
        record = resolver.match_or_create(
            workspace_id=workspace_id,
            lookup=lookup,
            first_seen_year=first_seen_year,
            descricao_sample=descricao,
        )
        entry["property_id"] = record.property_id
        entry["endereco_canonical"] = record.endereco_canonical
        entry["low_confidence"] = record.low_confidence

    return consolidated


__all__ = ["enrich_imoveis_with_property_ids"]
