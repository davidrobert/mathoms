"""Use case: criar membro da família (aloca key, criptografa CPF)."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError
from backend.app.application.family_member._helpers import (
    allocate_unique_member_key,
    extra_with_birth_name,
    slug_member_key_from_full_name,
)
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
    VaultProtocol,
)
from backend.app.schemas.dto.family_member import (
    FamilyMemberCreateCommand,
    FamilyMemberResponse,
    member_to_response,
)


async def create_family_member(
    cmd: FamilyMemberCreateCommand,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
    vault: VaultProtocol,
) -> FamilyMemberResponse:
    """Cria membro. Se ``cmd.key`` é dado, valida unicidade; senão, aloca slug."""
    if cmd.key:
        if await repo.key_exists(workspace_id, cmd.key):
            raise ConflictError(
                f"Já existe um membro com o identificador interno '{cmd.key}' "
                "neste workspace",
                code="duplicate_key",
            )
        key = cmd.key
    else:
        slug = slug_member_key_from_full_name(cmd.full_name)
        key = await allocate_unique_member_key(repo, workspace_id, slug)

    extra = extra_with_birth_name(cmd.extra, cmd.birth_name)
    cpf_enc = vault.encrypt(cmd.cpf) if cmd.cpf else None

    member = await repo.create(
        workspace_id,
        key=key,
        full_name=cmd.full_name,
        short_name=cmd.short_name,
        role=cmd.role,
        order=cmd.order,
        cpf_encrypted=cpf_enc,
        birth_date=cmd.birth_date,
        extra=extra,
    )
    return member_to_response(member, vault=vault)
