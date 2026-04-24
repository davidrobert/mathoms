"""DTOs do console interno (/admin/*) — ADR-116."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class AdminLoginResponse(BaseModel):
    username: str
    role: str
    expires_in_minutes: int


class AdminLogoutResponse(BaseModel):
    ok: bool = True


class AdminPrincipalResponse(BaseModel):
    username: str
    role: str


class AdminUserSummary(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_developer: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    users: list[AdminUserSummary]
    total: int


class AnonymizeUserRequest(BaseModel):
    confirm: Literal["delete"] = Field(
        description="UI exige typing 'delete' — bloqueia request acidental."
    )


class AnonymizeUserResponse(BaseModel):
    user_id: str
    anonymized_email: str


class HardDeleteUserRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    confirm: Literal["hard_delete"] = Field(
        description="UI exige typing 'hard_delete' — segundo nível de confirmação."
    )


class HardDeleteUserResponse(BaseModel):
    user_id: str


class ResetPasswordRequest(BaseModel):
    new_password: str | None = Field(default=None, min_length=8, max_length=200)


class ResetPasswordResponse(BaseModel):
    user_id: str
    temp_password: str


class SetDeveloperFlagRequest(BaseModel):
    enabled: bool


class SetDeveloperFlagResponse(BaseModel):
    user_id: str
    is_developer: bool
    changed: bool


class UpdateUserEmailRequest(BaseModel):
    new_email: EmailStr


class UpdateUserEmailResponse(BaseModel):
    user_id: str
    email: str
    changed: bool


class UpdateUserProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class UpdateUserProfileResponse(BaseModel):
    user_id: str
    changed: bool
    fields: list[str] = Field(default_factory=list)


class PurgeDocumentsRequest(BaseModel):
    user_id: str | None = None
    workspace_id: str | None = None
    preview: bool = True


class PurgeDocumentsResponse(BaseModel):
    preview: bool
    count: int
    ids: list[str]
    blobs_removed: int | None = None


class DeleteDocumentResponse(BaseModel):
    document_id: str
    blob_removed: bool


class MetricsResponse(BaseModel):
    users_total: int
    users_active: int
    workspaces_total: int
    documents_total: int
    documents_needs_review: int
    storage_bytes_total: int
    pipeline_runs_total: int
    pipeline_runs_last_period: int
    documents_uploaded_last_period: int
    new_users_last_period: int
    period_days: int
    generated_at: str


class UserWorkspaceDTO(BaseModel):
    id: str
    name: str
    role: str
    created_at: datetime


class AdminUserWorkspacesResponse(BaseModel):
    workspaces: list[UserWorkspaceDTO]


class ReportSummaryDTO(BaseModel):
    id: str
    workspace_id: str
    title: str
    period: str | None
    created_at: datetime
    size_bytes: int | None


class AdminReportListResponse(BaseModel):
    reports: list[ReportSummaryDTO]
    total: int = 0


class AuditEntryDTO(BaseModel):
    action: str
    actor: str
    target_type: str | None = None
    target_id: str | None = None
    result: str
    details: dict
    timestamp: str


class AuditListResponse(BaseModel):
    entries: list[AuditEntryDTO]


class AdminErrorResponse(BaseModel):
    detail: str
