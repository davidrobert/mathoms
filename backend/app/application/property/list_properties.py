"""Use case: lista imóveis classificáveis do workspace + fuzzy match sugestão (ADR-215 P4)."""

from __future__ import annotations

from typing import Optional

from backend.app.repositories.property_repository import PropertyRepository
from backend.app.schemas.dto.property import (
    PropertyListResponse,
    PropertyResponse,
)
from backend.app.services.property_fuzzy_match import (
    THRESHOLD_PRE_SELECT,
    match_score,
)


async def list_properties(
    workspace_id: str,
    *,
    repo: PropertyRepository,
    contribuinte_endereco: Optional[str] = None,
) -> PropertyListResponse:
    """Lista imóveis com classification atual + sugestão fuzzy para residência."""
    workspace = await repo.get_workspace(workspace_id)
    if workspace is None:
        raise LookupError(f"workspace {workspace_id} não encontrado")

    identities = await repo.list_identities(workspace_id)
    overrides = await repo.list_overrides(workspace_id)

    scored: list[tuple[int, PropertyResponse]] = []
    for ident in identities:
        score = 0
        if contribuinte_endereco and ident.descricao_sample:
            score = match_score(contribuinte_endereco, ident.descricao_sample)

        override = overrides.get(ident.id)
        scored.append(
            (
                score,
                PropertyResponse(
                    property_id=ident.id,
                    titular_key=ident.titular_key,
                    codigo_rfb=ident.codigo_rfb,
                    descricao_sample=ident.descricao_sample,
                    endereco_canonical=ident.endereco_canonical,
                    first_seen_year=ident.first_seen_year,
                    low_confidence=ident.low_confidence,
                    classification=override.classification if override else None,
                    override_source=override.override_source if override else None,
                    classification_set_at=override.updated_at if override else None,
                    suggested_score=score if score >= THRESHOLD_PRE_SELECT else None,
                    suggested_residencia_principal=False,
                ),
            )
        )

    # Marca como pré-selecionado APENAS o topo do ranking (score >= THRESHOLD)
    # — UI mostra exatamente uma sugestão de "residência principal" por vez.
    if scored:
        scored.sort(key=lambda x: -x[0])
        top_score, top_resp = scored[0]
        if top_score >= THRESHOLD_PRE_SELECT and top_resp.classification is None:
            top_resp.suggested_residencia_principal = True

    return PropertyListResponse(
        workspace_id=workspace_id,
        residencia_status=workspace.residencia_status,
        properties=[r for _, r in scored],
    )
