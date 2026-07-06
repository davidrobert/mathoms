"""Mapper ORM → DTO para o agregado ``FamilyMember``.

Responsabilidades:

1. Mascarar CPF via `mask_cpf_last_digits` (ADR-259 §4) — o CPF pleno nunca
   sai deste mapper; leitura completa é owner-only e auditada, exclusiva
   de `get_member_cpf_full` (`backend/app/api/family_members.py`).
2. Extrair ``birth_name`` de ``extra.nome_nascimento`` (é campo de primeira
   classe no DTO mesmo sendo armazenado dentro de ``extra``).
3. Converter defaults globais (``config/family_members.json``) em DTOs
   **neutros** — não expor identidade real do founder nos fallbacks
   (F6.5E.6 / BUG-004).

O mapper **não** recebe ``AsyncSession``. Recebe a instância ORM já
hidratada e o ``VaultService``. Isso torna o mapper testável sem DB.
"""

from __future__ import annotations

from typing import Protocol, TypedDict

from backend.app.models.family_member import FamilyMember
from backend.app.schemas.dto.family_member.response import (
    BankAccountResponse,
    FamilyMemberResponse,
)
from backend.app.services.family_member_pii_service import mask_cpf_last_digits


class _VaultLike(Protocol):
    """Só a superfície que o mapper precisa — dependency inversion (R8)."""

    def decrypt(self, ciphertext: str) -> str | None:  # pragma: no cover
        ...


class _FamilyMemberDefault(TypedDict, total=False):
    """Shape parcial de ``config/family_members.json::membros[<key>]``.

    Apenas ``papel`` é lido pelo mapper; outras chaves (``variantes_nome``,
    ``regex_nome_fatura``, ``profissao`…) existem no JSON mas passam direto
    — TypedDict com ``total=False`` + ausência da chave é no-op, preserva
    compat.
    """

    papel: str


class _FamilyMembersConfig(TypedDict, total=False):
    """Shape raiz de ``config/family_members.json``."""

    membros: dict[str, _FamilyMemberDefault]


# F6.5E.6 / BUG-004: placeholders que substituem identidade real em fallbacks.
# Originalmente apenas CPF era stripado (BUG-004); F6.5E.6 estendeu para
# nome/sobrenome/data_nascimento.
_NEUTRAL_PLACEHOLDER_NAMES: dict[str, tuple[str, str]] = {
    "titular": ("Titular Exemplo", "Titular"),
    "conjuge": ("Cônjuge Exemplo", "Cônjuge"),
    "filho": ("Filho Exemplo", "Filho"),
    "dependente": ("Dependente Exemplo", "Dependente"),
}


def _birth_name_from_extra(extra: dict[str, object] | None) -> str | None:
    """Extrai ``birth_name`` do dict ``extra`` (aceita variações legadas)."""
    if not extra:
        return None
    for k in ("nome_nascimento", "nome_solteiro", "nome_solteira"):
        raw = extra.get(k)
        if raw is None:
            continue
        s = str(raw).strip()
        if s:
            return s
    return None


def member_to_response(
    member: FamilyMember,
    *,
    vault: _VaultLike,
) -> FamilyMemberResponse:
    """Converte ORM ``FamilyMember`` → DTO de resposta.

    Pré-condição: ``member.accounts`` deve estar eager-loaded. Se não estiver,
    SQLAlchemy lança ``MissingGreenlet`` em contexto async — mapper **não**
    tenta recarregar (não tem session).
    """
    cpf_plain = vault.decrypt(member.cpf_encrypted) if member.cpf_encrypted else None
    accounts = (
        [BankAccountResponse.model_validate(a) for a in member.accounts] if member.accounts else []
    )
    return FamilyMemberResponse(
        id=member.id,
        key=member.key,
        full_name=member.full_name,
        short_name=member.short_name,
        birth_name=_birth_name_from_extra(member.extra),
        cpf_masked=mask_cpf_last_digits(cpf_plain) if cpf_plain else None,
        birth_date=member.birth_date,
        role=member.role,
        order=member.order,
        extra=member.extra,
        accounts=accounts,
    )


def convert_global_defaults_to_responses(
    data: _FamilyMembersConfig,
) -> list[FamilyMemberResponse]:
    """Converte ``config/family_members.json`` global → DTOs **neutros**.

    REGRA F6.5E.6 (privacidade): nunca expor identidade real via fallback.
    Substitui ``full_name`` / ``short_name`` / ``birth_date`` / ``cpf`` por
    placeholders neutros. ``key`` e ``role`` são preservados porque carregam
    a *estrutura* esperada (titular/conjuge/etc.), não a identidade.
    """
    membros = data.get("membros", {})
    responses: list[FamilyMemberResponse] = []
    for order, (key, info) in enumerate(membros.items()):
        role = info.get("papel", "titular")
        full_default, short_default = _NEUTRAL_PLACEHOLDER_NAMES.get(
            role, ("Membro Exemplo", "Membro")
        )
        responses.append(
            FamilyMemberResponse(
                key=key,
                full_name=full_default,
                short_name=short_default,
                cpf_masked=None,
                birth_date=None,
                role=role,
                order=order,
                accounts=[],
            )
        )
    return responses
