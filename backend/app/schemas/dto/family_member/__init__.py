"""DTOs do agregado ``FamilyMember`` (inclui ``BankAccount`` como sub-entidade).

Re-exports convenientes — prefira estes imports ao invés de alcançar módulos
internos, para manter o pacote como fronteira do agregado.
"""

from backend.app.schemas.dto.family_member.command import (
    BankAccountCreateCommand,
    BankAccountUpdateCommand,
    FamilyMemberCreateCommand,
    FamilyMemberUpdateCommand,
)
from backend.app.schemas.dto.family_member.mapper import (
    convert_global_defaults_to_responses,
    member_to_response,
)
from backend.app.schemas.dto.family_member.response import (
    BankAccountResponse,
    FamilyMemberListResponse,
    FamilyMemberResponse,
)

__all__ = [
    "BankAccountCreateCommand",
    "BankAccountResponse",
    "BankAccountUpdateCommand",
    "FamilyMemberCreateCommand",
    "FamilyMemberListResponse",
    "FamilyMemberResponse",
    "FamilyMemberUpdateCommand",
    "convert_global_defaults_to_responses",
    "member_to_response",
]
