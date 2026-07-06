"""DTOs do agregado ``FamilyMember`` (inclui ``BankAccount`` como sub-entidade).

Re-exports convenientes — prefira estes imports ao invés de alcançar módulos
internos, para manter o pacote como fronteira do agregado.
"""

from backend.app.schemas.dto.family_member.command import (
    BankAccountCreateCommand,
    BankAccountUpdateCommand,
    FamilyMemberCreateCommand,
    FamilyMemberUpdateCommand,
    IrpfDismissCommand,
)
from backend.app.schemas.dto.family_member.mapper import (
    convert_global_defaults_to_responses,
    member_to_response,
)
from backend.app.schemas.dto.family_member.response import (
    BankAccountResponse,
    CpfFullResponse,
    CpfMaskedResponse,
    FamilyMemberListResponse,
    FamilyMemberResponse,
    IrpfSuggestionItem,
    SuggestionsFromIrpfResponse,
)

__all__ = [
    "BankAccountCreateCommand",
    "BankAccountResponse",
    "BankAccountUpdateCommand",
    "CpfFullResponse",
    "CpfMaskedResponse",
    "FamilyMemberCreateCommand",
    "FamilyMemberListResponse",
    "FamilyMemberResponse",
    "FamilyMemberUpdateCommand",
    "IrpfDismissCommand",
    "IrpfSuggestionItem",
    "SuggestionsFromIrpfResponse",
    "convert_global_defaults_to_responses",
    "member_to_response",
]
