"""Anexa `property_id` UUID estável a imóveis do baseline consolidado (ADR-215 P2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.baseline_item_classifier import ClassificationAuthority
from pipeline.domain.services.endereco_canonicalizer import canonicalize
from pipeline.domain.services.titular_key_normalizer import normalize_titular_key
from pipeline.domain.types.property_identity import PropertyLookupKey

if TYPE_CHECKING:
    from pipeline.domain.types.config import FamilyMembersConfig
    from pipeline.ports import PropertyIdentityResolver


def enrich_imoveis_with_property_ids(
    consolidated: dict,
    resolver: "PropertyIdentityResolver",
    workspace_id: str,
    family_members: Optional["FamilyMembersConfig"] = None,
) -> dict:
    """Anexa `property_id`, `endereco_canonical`, `low_confidence` (ADR-215 P2)."""
    # ADR-215 fix-B3: family_members opcional permite normalizar
    # titular_key cross-IRPF (LLM extrai mariana_ribeiro_andrade vs
    # mariana_andrade_silva para a mesma pessoa). Quando ausente,
    # comportamento legado preservado.
    imoveis = consolidated.get("imoveis_consolidados", [])
    if not imoveis:
        return consolidated

    for entry in imoveis:
        if not _eixo_atestado_por_fato(entry):
            _mark_eixo_por_hint(entry)
            continue

        raw_titular = (entry.get("proprietario") or "").strip().lower()
        titular_key = normalize_titular_key(raw_titular, family_members)
        codigo_rfb = (entry.get("codigo_rfb") or "").strip()
        descricao = entry.get("descricao") or ""
        first_seen_year = int(entry.get("ano_referencia") or 0)

        if not titular_key or not codigo_rfb:
            _mark_uncanonical(entry, None)
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
        _apply_record(entry, record, endereco_canonical)

    return consolidated


# [[ADR-398]]: mintar é ato durável com CTA de rótulo — só o degrau de FATO da
# [[ADR-394]] D1 o autoriza. O eixo ATIVO só sai de `secao` ou de `hint`
# (`sinal` nunca promove a ativo, e o catálogo refina subtipo, nunca eixo), então
# a ausência de fato aqui significa exatamente "quem decidiu foi o rótulo do LLM".
_AUTORIDADE_DE_FATO = frozenset(
    {ClassificationAuthority.SECAO.value, ClassificationAuthority.CATALOGO.value}
)


# `secao` é OPCIONAL no contrato do E1.5a e 766 artefatos históricos não a
# carregam. Exigir o fato onde ele nunca existiu não fecharia o eixo: apagaria a
# identidade de todo imóvel do corpus antigo. A precondição vale onde a
# declaração provou saber emitir `secao` ([[ADR-398]] D2).
def _eixo_atestado_por_fato(entry: dict) -> bool:
    """Fato decidiu o eixo — ou a declaração de origem nunca ofereceu o fato."""
    if str(entry.get("eixo_autoridade") or "") in _AUTORIDADE_DE_FATO:
        return True
    return not entry.get("secao_disponivel")


def _mark_eixo_por_hint(entry: dict) -> None:
    """Sem fato de eixo não há identidade — nem `endereco_canonical`, que é chave de dedup."""
    entry["property_id"] = None
    entry["endereco_canonical"] = None
    entry["low_confidence"] = True
    entry["needs_review"] = True
    reasons = entry.setdefault("review_reasons", [])
    reasons.append(
        ReviewReason(
            code=ReviewReasonCode.domain_property_identity_eixo_por_hint,
            stage="consolidate_baseline",
            artifact_key="baseline_patrimonial",
            document_id=None,
            offending_value=f"eixo_autoridade={entry.get('eixo_autoridade') or 'ausente'}",
            expected="eixo ativo atestado por secao ou catalogo",
            message="identity not minted: axis decided by hint, not by fact",
        ).to_dict()
    )


def _apply_record(entry: dict, record, endereco_canonical: str | None) -> None:
    if record is None:
        _mark_uncanonical(entry, endereco_canonical)
        return
    entry["property_id"] = record.property_id
    entry["endereco_canonical"] = record.endereco_canonical
    entry["low_confidence"] = record.low_confidence
    # `low_confidence` sem razão é sinal que nenhum consumidor enxerga — e aqui ele
    # significa "identidade não canonicalizada", que é a chave de dedup cross-IRPF
    # ([[ADR-246]]): item que não canonicaliza ganha `property_id` novo a cada ano.
    # Paridade com `_mark_uncanonical`, que já emite o mesmo code.
    if record.low_confidence:
        _append_uncanonical_reason(entry, record.endereco_canonical)


def _mark_uncanonical(entry: dict, endereco_canonical: str | None) -> None:
    entry["property_id"] = None
    entry["endereco_canonical"] = endereco_canonical
    entry["low_confidence"] = True
    _append_uncanonical_reason(entry, endereco_canonical)


def _ja_tem_razao(reasons: list) -> bool:
    code = ReviewReasonCode.domain_property_identity_uncanonical.value
    return any(r.get("code") == code for r in reasons if isinstance(r, dict))


def _append_uncanonical_reason(entry: dict, endereco_canonical: str | None) -> None:
    """Marca revisão + razão. Único produtor da razão, para os 3 sítios não divergirem."""
    entry["needs_review"] = True
    reasons = entry.setdefault("review_reasons", [])
    if _ja_tem_razao(reasons):
        return
    reasons.append(
        ReviewReason(
            code=ReviewReasonCode.domain_property_identity_uncanonical,
            stage="consolidate_baseline",
            artifact_key="baseline_patrimonial",
            document_id=None,
            offending_value="endereco_canonical=None",
            expected="canonical or unique (titular, codigo_rfb)",
            message="identity not minted without endereco_canonical",
        ).to_dict()
    )


__all__ = ["enrich_imoveis_with_property_ids"]
