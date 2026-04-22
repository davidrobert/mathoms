"""Protocols consumidos pelos use cases de ``FamilyMember``.

Documentam a superfície mínima que cada dependência precisa expor — o
repo SQLAlchemy concreto e o ``FakeFamilyMemberRepository`` dos testes
implementam estes Protocols por duck typing.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional, Protocol

from backend.app.models.family_member import BankAccount, FamilyMember


class FamilyMemberRepositoryProtocol(Protocol):
    """Repositório do agregado (inclui BankAccount como sub-entidade)."""

    async def list_by_workspace(self, workspace_id: str) -> list[FamilyMember]: ...

    async def get_by_id(self, workspace_id: str, member_id: str) -> Optional[FamilyMember]: ...

    async def get_by_id_with_accounts(
        self, workspace_id: str, member_id: str
    ) -> Optional[FamilyMember]: ...

    async def key_exists(
        self,
        workspace_id: str,
        key: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> bool: ...

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
    ) -> FamilyMember: ...

    async def update(
        self,
        member: FamilyMember,
        *,
        updates: dict[str, Any],
    ) -> FamilyMember: ...

    async def delete(self, member: FamilyMember) -> None: ...

    async def list_accounts(self, member_id: str) -> list[BankAccount]: ...

    async def get_account(self, member_id: str, account_id: str) -> Optional[BankAccount]: ...

    async def add_account(
        self,
        member_id: str,
        *,
        institution_code: str,
        account_type: str,
        agency: Optional[str] = None,
        account_number: Optional[str] = None,
        label: Optional[str] = None,
    ) -> BankAccount: ...

    async def update_account(
        self,
        account: BankAccount,
        *,
        institution_code: str,
        account_type: str,
        agency: Optional[str] = None,
        account_number: Optional[str] = None,
        label: Optional[str] = None,
    ) -> BankAccount: ...

    async def delete_account(self, account: BankAccount) -> None: ...


class VaultProtocol(Protocol):
    """Vault de campos sensíveis (CPF)."""

    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, ciphertext: str) -> str | None: ...
