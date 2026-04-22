"""Use case: atualizar membro (partial update + reencriptação CPF)."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.family_member._helpers import extra_with_birth_name
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
    VaultProtocol,
)
from backend.app.schemas.dto.family_member import (
    FamilyMemberResponse,
    FamilyMemberUpdateCommand,
    member_to_response,
)


async def update_family_member(
    member_id: str,
    cmd: FamilyMemberUpdateCommand,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
    vault: VaultProtocol,
) -> FamilyMemberResponse:
    """Aplica partial update. Derivações (vault, birth_name, key collision) ficam aqui."""
    member = await repo.get_by_id_with_accounts(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")

    updates = cmd.model_dump(exclude_unset=True)

    if "cpf" in updates:
        cpf_val = updates.pop("cpf")
        updates["cpf_encrypted"] = vault.encrypt(cpf_val) if cpf_val else None
    if "birth_name" in updates:
        birth_val = updates.pop("birth_name")
        updates["extra"] = extra_with_birth_name(member.extra, birth_val)
    if updates.get("key") is None:
        updates.pop("key", None)

    new_key = updates.get("key")
    if new_key is not None and new_key != member.key:
        if await repo.key_exists(workspace_id, new_key, exclude_id=member_id):
            raise ConflictError(
                f"Já existe um membro com o identificador interno '{new_key}' " "neste workspace",
                code="duplicate_key",
            )

    updated = await repo.update(member, updates=updates)
    return member_to_response(updated, vault=vault)
