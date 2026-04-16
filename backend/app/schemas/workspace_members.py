"""Pydantic schemas para gestão de membros e convites (F9)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Roles aceitas na API pública. `owner` só aparece em respostas, nunca
# em request — criar owner é responsabilidade do fluxo de criação de
# workspace, não de convite.
InvitableRole = Literal["member", "viewer"]
AnyRole = Literal["owner", "member", "viewer"]


# ─── Members ──────────────────────────────────────────────────────────


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    full_name: str
    role: AnyRole
    joined_at: datetime
    invited_by: Optional[str] = None


class MemberListResponse(BaseModel):
    members: list[MemberResponse]
    total: int


class MemberRoleUpdateRequest(BaseModel):
    role: InvitableRole = Field(..., description="Novo role do membro.")


# ─── Invitations ──────────────────────────────────────────────────────


class InvitationCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Email do convidado.")
    role: InvitableRole = Field(
        "viewer",
        description="Role oferecido. Default é `viewer` — upgrade explícito.",
    )


class InvitationResponse(BaseModel):
    """Representa um convite existente. **Não** inclui o token cru;
    esse só aparece em `InvitationCreateResponse`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    email: str
    role: AnyRole
    status: Literal["pending", "accepted", "revoked", "expired"]
    invited_by: Optional[str] = None
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime


class InvitationCreateResponse(BaseModel):
    """Resposta da criação. **Inclui `token` cru uma única vez** —
    guarde o link com cuidado, não é recuperável depois."""

    invitation: InvitationResponse
    token: str = Field(
        ...,
        description=(
            "Token cru. Inclua em `/invite/{token}` e envie ao convidado. "
            "Este é o único momento em que é exposto — não persistido em "
            "outros lugares."
        ),
    )
    invite_path: str = Field(
        ...,
        description="Caminho relativo da URL de aceite: `/invite/{token}`.",
    )


class InvitationListResponse(BaseModel):
    invitations: list[InvitationResponse]
    total: int


class InvitationPreviewResponse(BaseModel):
    """Metadados mínimos do convite, seguros para mostrar numa página
    pública antes do aceite (o usuário pode nem estar logado ainda)."""

    workspace_name: str
    workspace_family_surname: Optional[str] = None
    role: AnyRole
    invited_by_name: Optional[str] = None
    invited_by_email: Optional[str] = None
    email: str
    expires_at: datetime
    status: Literal["pending", "accepted", "revoked", "expired"]


class InvitationAcceptResponse(BaseModel):
    workspace_id: str
    role: AnyRole
    joined_at: datetime


__all__ = [
    "InvitableRole",
    "AnyRole",
    "MemberResponse",
    "MemberListResponse",
    "MemberRoleUpdateRequest",
    "InvitationCreateRequest",
    "InvitationResponse",
    "InvitationCreateResponse",
    "InvitationListResponse",
    "InvitationPreviewResponse",
    "InvitationAcceptResponse",
]
