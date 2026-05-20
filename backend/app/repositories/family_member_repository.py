"""FamilyMemberRepository — CRUD async para o agregado ``FamilyMember``.

Encapsula todas as queries sobre ``family_members`` + ``bank_accounts`` para
que routers e use cases não construam SQL ad-hoc (R13). Toda query inclui
``workspace_id`` no predicado — multi-tenancy é invariante do agregado.

``BankAccount`` é **parte deste agregado** (não tem ciclo de vida fora de um
``FamilyMember``; cascade delete no schema). Não existe
``BankAccountRepository`` separado — os métodos aqui cobrem o caso.

Uso:

    repo = FamilyMemberRepository(session)
    members = await repo.list_by_workspace(ws_id)
    member = await repo.get_by_id_with_accounts(ws_id, member_id)
    member = await repo.create(ws_id, full_name="...", key="...", ...)
    account = await repo.add_account(ws_id, member_id, institution_code="...", ...)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.family_member import (
    BankAccount,
    FamilyMember,
    WorkspaceIrpfSuggestionDismissal,
)


class FamilyMemberRepository:
    """Single Responsibility: persistência do agregado ``FamilyMember``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # FamilyMember — queries
    # -------------------------------------------------------------------

    async def list_by_workspace(self, workspace_id: str) -> list[FamilyMember]:
        """Retorna membros do workspace (com ``accounts`` eager-loaded), ordenados."""
        result = await self._session.execute(
            select(FamilyMember)
            .where(FamilyMember.workspace_id == workspace_id)
            .options(selectinload(FamilyMember.accounts))
            .order_by(FamilyMember.order, FamilyMember.key)
        )
        return list(result.scalars().all())

    async def get_by_id(self, workspace_id: str, member_id: str) -> Optional[FamilyMember]:
        """Retorna membro por id dentro do workspace (sem accounts)."""
        result = await self._session.execute(
            select(FamilyMember).where(
                FamilyMember.id == member_id,
                FamilyMember.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_accounts(
        self, workspace_id: str, member_id: str
    ) -> Optional[FamilyMember]:
        """Retorna membro com ``accounts`` eager-loaded.

        ``execution_options(populate_existing=True)`` evita que instâncias já
        no identity map da sessão sirvam ``accounts`` stale (caso típico:
        caller acabou de criar o membro, adicionou contas, e quer reler o
        agregado com estado atual).
        """
        result = await self._session.execute(
            select(FamilyMember)
            .where(
                FamilyMember.id == member_id,
                FamilyMember.workspace_id == workspace_id,
            )
            .options(selectinload(FamilyMember.accounts))
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, workspace_id: str, key: str) -> Optional[FamilyMember]:
        """Retorna membro por ``key`` (único dentro do workspace)."""
        result = await self._session.execute(
            select(FamilyMember).where(
                FamilyMember.workspace_id == workspace_id,
                FamilyMember.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def key_exists(
        self,
        workspace_id: str,
        key: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> bool:
        """``True`` se já existe membro com ``key`` no workspace.

        ``exclude_id`` permite validar unicidade em updates (ignora o próprio
        membro que está sendo atualizado).
        """
        stmt = select(FamilyMember.id).where(
            FamilyMember.workspace_id == workspace_id,
            FamilyMember.key == key,
        )
        if exclude_id is not None:
            stmt = stmt.where(FamilyMember.id != exclude_id)
        result = await self._session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    # -------------------------------------------------------------------
    # FamilyMember — commands
    # -------------------------------------------------------------------

    async def create(
        self,
        workspace_id: str,
        *,
        key: str,
        full_name: str,
        short_name: str,
        role: str,
        order: int = 0,
        cpf_encrypted: Optional[str] = None,
        birth_date: Optional[date] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> FamilyMember:
        """Cria membro e retorna a instância já com ``accounts=[]`` carregado."""
        member = FamilyMember(
            workspace_id=workspace_id,
            key=key,
            full_name=full_name,
            short_name=short_name,
            cpf_encrypted=cpf_encrypted,
            birth_date=birth_date,
            role=role,
            order=order,
            extra=extra,
        )
        self._session.add(member)
        await self._session.commit()
        # Refresh com accounts eager para manter invariante (agregado completo).
        result = await self._session.execute(
            select(FamilyMember)
            .where(FamilyMember.id == member.id)
            .options(selectinload(FamilyMember.accounts))
        )
        return result.scalar_one()

    async def update(
        self,
        member: FamilyMember,
        *,
        updates: dict[str, Any],
    ) -> FamilyMember:
        """Aplica ``updates`` em ``member`` e devolve agregado com accounts.

        O caller resolve campos derivados (``cpf_encrypted``, ``extra.nome_nascimento``)
        antes de chamar — o repo não conhece criptografia nem birth_name unpack.
        """
        for field, value in updates.items():
            setattr(member, field, value)
        await self._session.commit()
        result = await self._session.execute(
            select(FamilyMember)
            .where(FamilyMember.id == member.id)
            .options(selectinload(FamilyMember.accounts))
        )
        return result.scalar_one()

    async def delete(self, member: FamilyMember) -> None:
        """Remove o membro e suas contas bancárias.

        Apaga contas explicitamente antes do membro — não depende de
        ``ondelete='CASCADE'`` (inativo em SQLite de testes) nem de
        ``cascade='all, delete-orphan'`` (exige accounts eager). Idempotente
        em termos de comportamento: resultado final é membro + contas fora
        do DB.
        """
        from sqlalchemy import delete as sql_delete

        await self._session.execute(
            sql_delete(BankAccount).where(BankAccount.member_id == member.id)
        )
        await self._session.delete(member)
        await self._session.commit()

    async def delete_all_in_workspace(self, workspace_id: str) -> int:
        """Remove todos os membros de um workspace. Usado em import/replace."""
        members = await self.list_by_workspace(workspace_id)
        count = 0
        for m in members:
            await self._session.delete(m)
            count += 1
        await self._session.flush()
        return count

    # -------------------------------------------------------------------
    # BankAccount — sub-entidade do agregado
    # -------------------------------------------------------------------

    async def list_accounts(self, member_id: str) -> list[BankAccount]:
        """Retorna contas de um membro (sem ordenação garantida além do FK default)."""
        result = await self._session.execute(
            select(BankAccount).where(BankAccount.member_id == member_id)
        )
        return list(result.scalars().all())

    async def get_account(self, member_id: str, account_id: str) -> Optional[BankAccount]:
        """Conta por id (validando pertence ao ``member_id``)."""
        result = await self._session.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.member_id == member_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_account(self, member_id: str, **fields: Any) -> BankAccount:
        """Cria conta bancária — Protocol tipa kwargs (ADR-226)."""
        account = BankAccount(member_id=member_id, **fields)
        self._session.add(account)
        await self._session.commit()
        await self._session.refresh(account)
        return account

    async def update_account(self, account: BankAccount, **fields: Any) -> BankAccount:
        """Sobrescreve campos da conta (PUT); workspace_id imutável (ADR-226)."""
        for k, v in fields.items():
            setattr(account, k, v)
        await self._session.commit()
        await self._session.refresh(account)
        return account

    async def delete_account(self, account: BankAccount) -> None:
        await self._session.delete(account)
        await self._session.commit()

    # -------------------------------------------------------------------
    # ADR-229: IRPF suggestion dismissals
    # -------------------------------------------------------------------

    async def list_irpf_dismissals(
        self, workspace_id: str
    ) -> list[WorkspaceIrpfSuggestionDismissal]:
        """Descartes persistentes do workspace (todos os anos)."""
        result = await self._session.execute(
            select(WorkspaceIrpfSuggestionDismissal).where(
                WorkspaceIrpfSuggestionDismissal.workspace_id == workspace_id,
            )
        )
        return list(result.scalars().all())

    async def _find_dismissal(
        self,
        *,
        workspace_id: str,
        irpf_year: int,
        institution_code: str,
        account_number_norm: Optional[str] = None,
    ) -> Optional[WorkspaceIrpfSuggestionDismissal]:
        stmt = select(WorkspaceIrpfSuggestionDismissal).where(
            WorkspaceIrpfSuggestionDismissal.workspace_id == workspace_id,
            WorkspaceIrpfSuggestionDismissal.irpf_year == irpf_year,
            WorkspaceIrpfSuggestionDismissal.institution_code == institution_code,
            WorkspaceIrpfSuggestionDismissal.account_number_norm == account_number_norm,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_irpf_dismissal(self, **kwargs: Any) -> WorkspaceIrpfSuggestionDismissal:
        """Idempotente por UNIQUE — retorna existente em colisão."""
        existing = await self._find_dismissal(
            workspace_id=kwargs["workspace_id"],
            irpf_year=kwargs["irpf_year"],
            institution_code=kwargs["institution_code"],
            account_number_norm=kwargs.get("account_number_norm"),
        )
        if existing is not None:
            return existing
        dismissal = WorkspaceIrpfSuggestionDismissal(**kwargs)
        self._session.add(dismissal)
        await self._session.commit()
        await self._session.refresh(dismissal)
        return dismissal
