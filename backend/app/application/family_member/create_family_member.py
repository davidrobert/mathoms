"""Use case: criar membro da família (aloca key, criptografa CPF)."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from backend.app.events import dispatch_sync
from backend.app.events.domain import FamilyMemberCreatedEvent
from backend.app.schemas.dto.family_member import (
    FamilyMemberCreateCommand,
    FamilyMemberResponse,
    member_to_response,
)

if TYPE_CHECKING:  # pragma: no cover - só para type hints
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_family_member(
    cmd: FamilyMemberCreateCommand,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
    vault: VaultProtocol,
    db: "AsyncSession | None" = None,
    actor_user_id: str | None = None,
) -> FamilyMemberResponse:
    """Cria membro. Se ``cmd.key`` é dado, valida unicidade; senão, aloca slug.

    ``db`` é injetado pelo router para permitir que ``FamilyMemberCreatedEvent``
    persista audit na mesma transação (A6e.events · ADR-115). Testes unitários
    com fakes passam ``db=None`` e o dispatch é puramente no-op — não há
    regressão de comportamento observável nos paths antigos.
    """
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

    if db is not None:
        await dispatch_sync(
            FamilyMemberCreatedEvent(
                aggregate_id=member.id,
                aggregate_type="family_member",
                workspace_id=workspace_id,
                member_id=member.id,
                member_key=member.key,
                member_name=member.full_name,
                actor_user_id=actor_user_id,
            ),
            {"db": db},
        )
        # repo.create() já commitou o membro; side-effects do evento vivem
        # em txn separada que precisa ser fechada aqui (ADR-115 §atomicidade
        # parcial — repo owns-commit é legado). Handler falha → rollback
        # descarta o audit sem afetar o membro.
        await db.commit()

    return member_to_response(member, vault=vault)
