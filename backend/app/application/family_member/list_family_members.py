"""Use case: listar membros do workspace (com fallback para defaults globais)."""

from __future__ import annotations

from typing import Any

from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
    VaultProtocol,
)
from backend.app.schemas.dto.family_member import (
    FamilyMemberListResponse,
    convert_global_defaults_to_responses,
    member_to_response,
)


async def list_family_members(
    workspace_id: str,
    *,
    repo: FamilyMemberRepositoryProtocol,
    vault: VaultProtocol,
    global_defaults: dict[str, Any] | None = None,
) -> FamilyMemberListResponse:
    """Retorna membros do workspace; se vazio, devolve defaults neutros.

    ``global_defaults`` é o dict carregado de ``config/family_members.json``
    (injetado pelo router — use case não lê filesystem).
    """
    members = await repo.list_by_workspace(workspace_id)
    if members:
        responses = [member_to_response(m, vault=vault) for m in members]
        return FamilyMemberListResponse(members=responses, total=len(responses))

    defaults = global_defaults or {}
    return FamilyMemberListResponse(
        members=convert_global_defaults_to_responses(defaults),
        total=len(defaults.get("membros", {})),
    )
