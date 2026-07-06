"""Use cases do agregado ``FamilyMember`` (ADR-101 R15).

Cada endpoint REST de ``/workspaces/{id}/config/members[/accounts]``
delega a uma função ``execute(...)`` neste pacote. Use cases recebem
command DTOs + repo + vault e retornam response DTOs ou ``None`` (delete).

Erros de domínio (:mod:`backend.app.application.base.errors`) são
traduzidos para HTTP no router.
"""

from backend.app.application.family_member.create_bank_account import (
    create_bank_account,
)
from backend.app.application.family_member.create_family_member import (
    create_family_member,
)
from backend.app.application.family_member.delete_bank_account import (
    delete_bank_account,
)
from backend.app.application.family_member.delete_family_member import (
    delete_family_member,
)
from backend.app.application.family_member.dismiss_irpf_suggestion import (
    dismiss_irpf_suggestion,
)
from backend.app.application.family_member.get_irpf_suggestions import (
    InstitutionLabelResolverProtocol,
    IrpfArtifactPayload,
    IrpfArtifactSourceProtocol,
    get_irpf_suggestions,
)
from backend.app.application.family_member.get_member_cpf import (
    get_member_cpf_full,
    get_member_cpf_masked,
)
from backend.app.application.family_member.list_bank_accounts import (
    list_bank_accounts,
)
from backend.app.application.family_member.list_family_members import (
    list_family_members,
)
from backend.app.application.family_member.update_bank_account import (
    update_bank_account,
)
from backend.app.application.family_member.update_family_member import (
    update_family_member,
)

__all__ = [
    "create_bank_account",
    "create_family_member",
    "delete_bank_account",
    "delete_family_member",
    "dismiss_irpf_suggestion",
    "get_irpf_suggestions",
    "get_member_cpf_full",
    "get_member_cpf_masked",
    "IrpfArtifactPayload",
    "IrpfArtifactSourceProtocol",
    "InstitutionLabelResolverProtocol",
    "list_bank_accounts",
    "list_family_members",
    "update_bank_account",
    "update_family_member",
]
