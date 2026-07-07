"""DTOs do console interno (/admin/*) — ADR-116."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# Clamp anti-typo de ordem de grandeza no editor de budget (sre-devops,
# A30.l1). Calibrar com unit economics quando houver pricing.
MAX_SETTABLE_BUDGET_USD = Decimal("1000.00")


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


class ScopeContextDTO(BaseModel):
    owner_email: str | None = None
    workspace_names: list[str] = Field(default_factory=list)


class PurgeDocumentsRequest(BaseModel):
    user_id: str | None = None
    workspace_id: str | None = None
    preview: bool = True


class PurgeDocumentItemDTO(BaseModel):
    id: str
    name: str


class PurgeDocumentsResponse(BaseModel):
    preview: bool
    count: int
    ids: list[str]
    items: list[PurgeDocumentItemDTO] = Field(default_factory=list)
    runs_to_remove: int = 0
    runs_removed: int | None = None
    blobs_removed: int | None = None
    scope_context: ScopeContextDTO | None = None


class PurgeReportsRequest(BaseModel):
    user_id: str | None = None
    workspace_id: str | None = None
    preview: bool = True


class PurgeReportsResponse(BaseModel):
    preview: bool
    count: int
    ids: list[str]
    artifacts_to_remove: int = 0
    artifacts_removed: int | None = None
    scope_context: ScopeContextDTO | None = None


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
    owner_email: str | None = None
    workspace_name: str | None = None


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


class WorkspaceLLMSpendDTO(BaseModel):
    """Spend snapshot de um workspace na janela consultada."""

    workspace_id: str
    workspace_name: str | None = None
    monthly_budget_usd: str  # Decimal serializado como string (wire ADR-090)
    period_start: str
    period_end: str
    call_count: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: str  # Decimal serializado como string
    unknown_cost_calls: int
    pct_of_budget: float  # 0.0 a >1.0 (acima do orçamento) — para alarme
    over_budget: bool


class LLMSpendByWorkspaceResponse(BaseModel):
    period_days: int
    period_start: str
    period_end: str
    items: list[WorkspaceLLMSpendDTO]


class WorkspaceLLMBudgetUpdate(BaseModel):
    """Edição do cap mensal (A30.l1). `NULL` só via `remove_cap` explícito."""

    cap_usd: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    remove_cap: bool = False

    @model_validator(mode="after")
    def _cap_xor_remove(self) -> "WorkspaceLLMBudgetUpdate":
        if self.remove_cap:
            if self.cap_usd is not None:
                raise ValueError(
                    f"remove_cap=true não aceita cap_usd (recebido cap_usd={self.cap_usd})"
                )
            return self
        if self.cap_usd is None:
            raise ValueError("cap_usd ausente — para remover o cap envie remove_cap=true explícito")
        if self.cap_usd > MAX_SETTABLE_BUDGET_USD:
            raise ValueError(
                f"cap_usd={self.cap_usd} acima do teto de sanidade "
                f"US$ {MAX_SETTABLE_BUDGET_USD} (anti-typo; ajuste a constante se intencional)"
            )
        self.cap_usd = self.cap_usd.quantize(Decimal("0.01"))
        return self


class WorkspaceLLMBudgetResponse(BaseModel):
    workspace_id: str
    previous_budget_usd: str | None  # Decimal serializado como string (wire ADR-090)
    monthly_budget_usd: str | None  # None = sem cap
    remove_cap: bool


class WorkspaceLLMBudgetMonthDTO(BaseModel):
    """Snapshot mês-calendário UTC — mesma janela do hard-stop (ADR-173)."""

    workspace_id: str
    workspace_name: str | None = None
    cap_usd: str | None  # None = sem cap
    spent_month_usd: str
    pct_of_cap: float | None  # None quando sem cap
    status: Literal["ok", "warn", "hard_stop", "uncapped"]
    call_count: int
    unknown_cost_calls: int


class LLMBudgetMonthResponse(BaseModel):
    month: str  # "YYYY-MM"
    period_start: str
    period_end: str
    warn_ratio: float
    hard_stop_ratio: float
    items: list[WorkspaceLLMBudgetMonthDTO]


class PlannerFieldRequestTopItem(BaseModel):
    """Telemetria de campo faltante — agregação por path (ADR-206 §D3)."""

    field_path: str
    frequency: int
    workspaces_count: int
    last_requested_at: str  # ISO 8601


class PlannerFieldRequestTopResponse(BaseModel):
    """Top-N paths pedidos pelo LLM via ``campos_faltantes_pediria_se_iterasse[]``."""

    days: int
    limit: int
    items: list[PlannerFieldRequestTopItem]
