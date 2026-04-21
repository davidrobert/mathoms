"""Fake in-memory do ``FamilyMemberRepository`` + ``Vault``.

Implementa a superfície declarada em ``backend/app/application/
family_member/_protocols.py`` suficiente para rodar os use cases sem DB.

Instâncias ``FamilyMember`` / ``BankAccount`` criadas aqui são ORM objects
standalone (sem sessão SQLAlchemy) — uso ok em testes de use case porque
o mapper não acessa ``relationship`` lazy.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Optional

from backend.app.models.family_member import BankAccount, FamilyMember


class FakeFamilyMemberRepository:
    """Repo em memória — isolado por instância."""

    def __init__(self) -> None:
        self._members: dict[str, FamilyMember] = {}
        self._accounts: dict[str, BankAccount] = {}

    async def list_by_workspace(self, workspace_id: str) -> list[FamilyMember]:
        members = [m for m in self._members.values() if m.workspace_id == workspace_id]
        members.sort(key=lambda m: (m.order, m.key))
        for m in members:
            m.accounts = [a for a in self._accounts.values() if a.member_id == m.id]
        return members

    async def get_by_id(
        self, workspace_id: str, member_id: str
    ) -> Optional[FamilyMember]:
        m = self._members.get(member_id)
        if m is None or m.workspace_id != workspace_id:
            return None
        return m

    async def get_by_id_with_accounts(
        self, workspace_id: str, member_id: str
    ) -> Optional[FamilyMember]:
        m = await self.get_by_id(workspace_id, member_id)
        if m is not None:
            m.accounts = [a for a in self._accounts.values() if a.member_id == m.id]
        return m

    async def key_exists(
        self,
        workspace_id: str,
        key: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> bool:
        for m in self._members.values():
            if m.workspace_id != workspace_id or m.key != key:
                continue
            if exclude_id is not None and m.id == exclude_id:
                continue
            return True
        return False

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
        member = FamilyMember(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            key=key,
            full_name=full_name,
            short_name=short_name,
            role=role,
            order=order,
            cpf_encrypted=cpf_encrypted,
            birth_date=birth_date,
            extra=extra,
        )
        member.accounts = []
        self._members[member.id] = member
        return member

    async def update(
        self,
        member: FamilyMember,
        *,
        updates: dict[str, Any],
    ) -> FamilyMember:
        for field, value in updates.items():
            setattr(member, field, value)
        member.accounts = [a for a in self._accounts.values() if a.member_id == member.id]
        return member

    async def delete(self, member: FamilyMember) -> None:
        self._members.pop(member.id, None)
        for acc_id in [a.id for a in self._accounts.values() if a.member_id == member.id]:
            self._accounts.pop(acc_id, None)

    async def list_accounts(self, member_id: str) -> list[BankAccount]:
        return [a for a in self._accounts.values() if a.member_id == member_id]

    async def get_account(
        self, member_id: str, account_id: str
    ) -> Optional[BankAccount]:
        acc = self._accounts.get(account_id)
        if acc is None or acc.member_id != member_id:
            return None
        return acc

    async def add_account(
        self,
        member_id: str,
        *,
        institution_code: str,
        account_type: str,
        agency: Optional[str] = None,
        account_number: Optional[str] = None,
        label: Optional[str] = None,
    ) -> BankAccount:
        account = BankAccount(
            id=str(uuid.uuid4()),
            member_id=member_id,
            institution_code=institution_code,
            account_type=account_type,
            agency=agency,
            account_number=account_number,
            label=label,
        )
        self._accounts[account.id] = account
        return account

    async def update_account(
        self,
        account: BankAccount,
        *,
        institution_code: str,
        account_type: str,
        agency: Optional[str] = None,
        account_number: Optional[str] = None,
        label: Optional[str] = None,
    ) -> BankAccount:
        account.institution_code = institution_code
        account.account_type = account_type
        account.agency = agency
        account.account_number = account_number
        account.label = label
        return account

    async def delete_account(self, account: BankAccount) -> None:
        self._accounts.pop(account.id, None)


class FakeVault:
    """Vault mock — prefixa/remove ``enc:`` para simular encrypt/decrypt reversível."""

    def encrypt(self, plaintext: str) -> str:
        return f"enc:{plaintext}"

    def decrypt(self, ciphertext: str) -> str | None:
        if ciphertext is None:
            return None
        if ciphertext.startswith("enc:"):
            return ciphertext[4:]
        return ciphertext
