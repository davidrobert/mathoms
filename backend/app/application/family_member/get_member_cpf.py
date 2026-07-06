"""Use case: leitura de CPF do membro — mascarado ou completo (ADR-259 §4)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
    VaultProtocol,
)
from backend.app.schemas.dto.family_member import CpfFullResponse, CpfMaskedResponse
from backend.app.services.family_member_pii_service import mask_cpf_last_digits


async def _decrypted_cpf(
    member_id: str,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
    vault: VaultProtocol,
) -> str:
    member = await repo.get_by_id(workspace_id, member_id)
    if not member or not member.cpf_encrypted:
        raise NotFoundError("Membro sem CPF cadastrado", code="cpf_not_found")
    cpf_plain = vault.decrypt(member.cpf_encrypted)
    if not cpf_plain:
        raise NotFoundError("Membro sem CPF cadastrado", code="cpf_not_found")
    return cpf_plain


async def get_member_cpf_masked(
    member_id: str,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
    vault: VaultProtocol,
) -> CpfMaskedResponse:
    """Máscara canônica — plaintext decriptado e descartado no escopo da função."""
    cpf_plain = await _decrypted_cpf(member_id, workspace_id=workspace_id, repo=repo, vault=vault)
    return CpfMaskedResponse(cpf_masked=mask_cpf_last_digits(cpf_plain))


async def get_member_cpf_full(
    member_id: str,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
    vault: VaultProtocol,
) -> CpfFullResponse:
    """CPF completo — router garante owner-only + auditoria antes de chamar."""
    cpf_plain = await _decrypted_cpf(member_id, workspace_id=workspace_id, repo=repo, vault=vault)
    return CpfFullResponse(cpf_full=cpf_plain)
