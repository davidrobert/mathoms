"""Projeta a fonte documental de seguro no bundle de proteção (ADR-395 §D2/§D6).

O bundle é calculado sobre o cadastro (`Protection`, ADR-192). O documento
(`protecao_patrimonial`, ADR-240) entra aqui como **hint**: nomeia o que foi
identificado e diz em que categoria o inventário do cadastro está provadamente
incompleto. Nada daqui vira valor — as duas fontes não compartilham chave de
identidade (ADR-240 §D12) e somá-las arriscaria dupla-contagem.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from pipeline.domain.protection_bundle import DocumentaryCoverage

# Só `vida` tem par no vocabulário do bundle. `saude` é categoria documental sem
# calculator; `acidentes` foi recusado como equivalente de invalidez em
# ADR-240 §D11. Mapear por semelhança silenciaria gap com cobertura fabricada.
_BUNDLE_CATEGORY_BY_DOCUMENTARY: dict[str, str] = {"vida": "vida"}


def documentary_coverage_from_payload(
    payload: Optional[Mapping[str, Any]] = None,
) -> Optional[DocumentaryCoverage]:
    """`None` quando o run não observou documento de seguro algum."""
    block = payload or {}
    active = _active_policies(block)
    unconfirmed = _unconfirmed_bundle_categories(block)
    if not active and not unconfirmed:
        return None
    return DocumentaryCoverage(
        active_policies_count=len(active),
        insurers=_insurers(active),
        earliest_coverage_end=_earliest_coverage_end(active),
        unconfirmed_categories=unconfirmed,
    )


def _active_policies(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = payload.get("apolices_vigentes") or []
    return [item for item in raw if isinstance(item, Mapping)]


def _unconfirmed_bundle_categories(payload: Mapping[str, Any]) -> list[str]:
    escopo = payload.get("escopo_cobertura") or {}
    documental = escopo.get("categorias_somente_no_documento") or []
    mapped = {
        _BUNDLE_CATEGORY_BY_DOCUMENTARY[str(name)]
        for name in documental
        if str(name) in _BUNDLE_CATEGORY_BY_DOCUMENTARY
    }
    return sorted(mapped)


def _insurers(active: list[Mapping[str, Any]]) -> list[str]:
    names = {_insurer_display(item) for item in active}
    return sorted(name for name in names if name)


def _insurer_display(item: Mapping[str, Any]) -> str:
    return str(item.get("seguradora_nome") or item.get("seguradora") or "").strip()


def _earliest_coverage_end(active: list[Mapping[str, Any]]) -> Optional[str]:
    ends = sorted(str(item.get("vigencia_fim") or "").strip() for item in active)
    observed = [end for end in ends if end]
    return observed[0] if observed else None


__all__ = ["documentary_coverage_from_payload"]
