"""Backend test factories — F6.5 (sub-fase 6.5F.2).

Cada factory:
1. Aceita `db: AsyncSession` como primeiro arg (obrigatório).
2. Aceita overrides via kwargs.
3. Faz `db.add(...)` + `await db.flush()` para ter ID atribuído antes de
   relacionar com outros models — NÃO faz commit; o test decide quando
   commitar (ou nem comitar, em caso de transação rolled back).
4. Retorna o model populado.

Ver `__init__.py` para convenções e exemplos de uso.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import (
    BankAccount,
    Category,
    CategoryKeyword,
    Document,
    FamilyMember,
    Goal,
    LLMConfig,
    Notification,
    PasswordVault,
    PipelineRun,
    PipelineStageLog,
    Report,
    Task,
    TaskSuggestion,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
)

# ─── Counters ─────────────────────────────────────────────────────────

_counters = {
    "user": 0,
    "workspace": 0,
    "member": 0,
    "account": 0,
    "category": 0,
    "document": 0,
    "report": 0,
    "run": 0,
    "stage": 0,
    "vault": 0,
    "notification": 0,
    "ws_member": 0,
    "ws_invitation": 0,
    "goal": 0,
    "task": 0,
    "task_suggestion": 0,
}


def reset_counters() -> None:
    for k in _counters:
        _counters[k] = 0


def _next(k: str) -> int:
    _counters[k] += 1
    return _counters[k]


# ─── User ─────────────────────────────────────────────────────────────


async def make_user(
    db: AsyncSession,
    *,
    email: Optional[str] = None,
    password: str = "TestPass123!",
    full_name: Optional[str] = None,
    is_active: bool = True,
) -> User:
    n = _next("user")
    user = User(
        email=email or f"user{n}@test.com",
        hashed_password=hash_password(password),
        full_name=full_name or f"Test User {n}",
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    return user


# ─── Workspace ────────────────────────────────────────────────────────


async def make_workspace(
    db: AsyncSession,
    *,
    owner: Optional[User] = None,
    name: Optional[str] = None,
    family_surname: Optional[str] = None,
    skip_membership: bool = False,
) -> Workspace:
    """Cria workspace + auto-cria WorkspaceMember(role='owner') para o
    owner. ADR-072: nenhum acesso sem membership.

    Use `skip_membership=True` apenas em testes que validam ausência
    de membership (ex: cross-tenant isolation negativa)."""
    n = _next("workspace")
    if owner is None:
        owner = await make_user(db)
    ws = Workspace(
        name=name or f"Workspace {n}",
        family_surname=family_surname,
        owner_id=owner.id,
    )
    db.add(ws)
    await db.flush()

    if not skip_membership:
        await make_workspace_member(db, workspace=ws, user=owner, role="owner")
    return ws


# ─── WorkspaceMember (ADR-072) ────────────────────────────────────────


async def make_workspace_member(
    db: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    role: str = "member",
    invited_by: Optional[User] = None,
) -> WorkspaceMember:
    _next("ws_member")
    wm = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
        invited_by=invited_by.id if invited_by else None,
    )
    db.add(wm)
    await db.flush()
    return wm


# ─── WorkspaceInvitation (F9) ─────────────────────────────────────────


async def make_invitation(
    db: AsyncSession,
    *,
    workspace: Workspace,
    email: Optional[str] = None,
    role: str = "viewer",
    invited_by: Optional[User] = None,
    expires_in_hours: int = 72,
    already_accepted: bool = False,
    already_revoked: bool = False,
    already_expired: bool = False,
) -> WorkspaceInvitation:
    """Cria um convite. Por padrão, em estado `pending`.

    Use os flags `already_*` para simular estados terminais em tests. Eles
    são mutuamente exclusivos na prática — o teste decide qual ativa.
    """
    from datetime import timedelta

    from backend.app.services.invitation_service import _generate_token

    n = _next("ws_invitation")
    _, token_hash = _generate_token()
    now = datetime.now(timezone.utc)

    expires_at = (
        now - timedelta(hours=1) if already_expired else now + timedelta(hours=expires_in_hours)
    )

    inv = WorkspaceInvitation(
        workspace_id=workspace.id,
        email=email or f"invitee{n}@test.com",
        role=role,
        token_hash=token_hash,
        invited_by=invited_by.id if invited_by else None,
        expires_at=expires_at,
        accepted_at=now if already_accepted else None,
        revoked_at=now if already_revoked else None,
    )
    db.add(inv)
    await db.flush()
    return inv


# ─── Goal (ADR-073) ───────────────────────────────────────────────────


async def make_if_goal(
    db: AsyncSession,
    *,
    workspace: Workspace,
    renda_passiva_mensal_brl: Decimal = Decimal("20000"),
    trs_pct: float = 5.0,
    retorno_real_anual_pct: float = 6.0,
    horizonte_anos: int = 15,
    created_by: Optional[User] = None,
    effective_from: Optional[date] = None,
    is_template: bool = False,
) -> Goal:
    """Factory dogfood: usa compute_if_derived do service para manter
    paridade com produção."""
    from backend.app.schemas.goal import IFGoalInputs
    from backend.app.services.goal_service import compute_if_derived

    _next("goal")
    inputs = IFGoalInputs(
        renda_passiva_mensal_brl=renda_passiva_mensal_brl,
        trs_pct=trs_pct,
        retorno_real_anual_pct=retorno_real_anual_pct,
        horizonte_anos=horizonte_anos,
    )
    derived = compute_if_derived(inputs)
    goal = Goal(
        workspace_id=workspace.id,
        type="INDEPENDENCIA_FINANCEIRA",
        params_json={"inputs": inputs.model_dump(mode="json"), "meta_version": 1},
        derived_json=derived.model_dump(mode="json", exclude_none=True),
        effective_from=effective_from or date.today(),
        effective_to=None,
        created_by=created_by.id if created_by else None,
        is_template=is_template,
    )
    db.add(goal)
    await db.flush()
    return goal


# ─── Task / TaskSuggestion (ADR-074) ──────────────────────────────────


async def make_task(
    db: AsyncSession,
    *,
    workspace: Workspace,
    number: Optional[int] = None,
    title: Optional[str] = None,
    category: str = "Invest",
    priority: str = "R",
    status: str = "pending",
    deadline_kind: str = "UNSCHEDULED",
    deadline_date=None,
    deadline_label: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    ref: Optional[str] = None,
    created_by: Optional[User] = None,
    created_from: str = "manual",
) -> Task:
    n = _next("task")
    task = Task(
        workspace_id=workspace.id,
        number=number or n,
        title=title or f"Test task {n}",
        category=category,
        priority=priority,
        status=status,
        deadline_kind=deadline_kind,
        deadline_date=deadline_date,
        deadline_label=deadline_label,
        parent_task_id=parent_task_id,
        ref=ref,
        created_by=created_by.id if created_by else None,
        created_from=created_from,
    )
    db.add(task)
    await db.flush()
    return task


async def make_task_suggestion(
    db: AsyncSession,
    *,
    workspace: Workspace,
    proposed_payload: Optional[dict] = None,
    source: str = "e5n_llm",
    source_run_id: Optional[str] = None,
    status: str = "pending",
) -> TaskSuggestion:
    n = _next("task_suggestion")
    default_payload = {
        "title": f"Sugestão {n}",
        "category": "Orcamento",
        "priority": "R",
        "deadline_kind": "UNSCHEDULED",
    }
    sugg = TaskSuggestion(
        workspace_id=workspace.id,
        proposed_payload=proposed_payload or default_payload,
        source=source,
        source_run_id=source_run_id,
        status=status,
    )
    db.add(sugg)
    await db.flush()
    return sugg


# ─── FamilyMember + BankAccount ───────────────────────────────────────


async def make_member(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    key: Optional[str] = None,
    full_name: Optional[str] = None,
    short_name: Optional[str] = None,
    cpf_encrypted: Optional[str] = None,
    birth_date: Optional[date] = None,
    role: str = "titular",  # schema valida ^(titular|conjuge|filho|dependente)$
    order: int = 0,
    extra: Optional[dict] = None,
) -> FamilyMember:
    n = _next("member")
    if workspace is None:
        workspace = await make_workspace(db)
    m = FamilyMember(
        workspace_id=workspace.id,
        key=key or f"member_{n}",
        full_name=full_name or f"Member {n}",
        short_name=short_name or f"M{n}",
        cpf_encrypted=cpf_encrypted,  # tests cuidam de cifrar se precisar
        birth_date=birth_date or date(1990, 1, 1),
        role=role,
        order=order or n,
        extra=extra,
    )
    db.add(m)
    await db.flush()
    return m


async def make_bank_account(
    db: AsyncSession,
    *,
    member: FamilyMember,
    institution_code: str = "c6bank",
    account_type: str = "corrente",
    agency: str = "0001",
    account_number: Optional[str] = None,
    label: Optional[str] = None,
) -> BankAccount:
    n = _next("account")
    acc = BankAccount(
        member_id=member.id,
        institution_code=institution_code,
        account_type=account_type,
        agency=agency,
        account_number=account_number or f"12345-{n}",
        label=label,
    )
    db.add(acc)
    await db.flush()
    return acc


# ─── Category ─────────────────────────────────────────────────────────


async def make_category(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    code: Optional[str] = None,
    name: Optional[str] = None,
    category_type: str = "expense",
    monthly_cap: Optional[float] = None,
    order: int = 0,
    keywords: Optional[list[str]] = None,
) -> Category:
    n = _next("category")
    if workspace is None:
        workspace = await make_workspace(db)
    cat = Category(
        workspace_id=workspace.id,
        code=code or f"cat_{n}",
        name=name or f"Categoria {n}",
        category_type=category_type,
        monthly_cap=monthly_cap,
        order=order or n,
    )
    db.add(cat)
    await db.flush()
    for kw in keywords or []:
        db.add(CategoryKeyword(category_id=cat.id, keyword=kw))
    if keywords:
        await db.flush()
    return cat


# ─── Document ─────────────────────────────────────────────────────────


async def make_document(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    original_name: Optional[str] = None,
    stored_path: Optional[str] = None,
    doc_type: str = "bank_statement",
    bank_code: str = "c6bank",
    period: str = "2026-04",
    status: str = "ready",
    file_size_bytes: int = 100_000,
    content_hash: Optional[str] = None,
    content_type: str = "application/pdf",
) -> Document:
    n = _next("document")
    if workspace is None:
        workspace = await make_workspace(db)
    doc = Document(
        workspace_id=workspace.id,
        original_name=original_name or f"extrato_{n}.pdf",
        stored_path=stored_path or f"{workspace.id}/uploads/doc-{n}.pdf",
        doc_type=doc_type,
        bank_code=bank_code,
        period=period,
        status=status,
        file_size_bytes=file_size_bytes,
        content_hash=content_hash or f"hash{n:06d}",
        content_type=content_type,
    )
    db.add(doc)
    await db.flush()
    return doc


# ─── Vault ────────────────────────────────────────────────────────────


async def make_vault_password(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    label: Optional[str] = None,
    encrypted_password: str = "encrypted-test-value",
) -> PasswordVault:
    n = _next("vault")
    if workspace is None:
        workspace = await make_workspace(db)
    vp = PasswordVault(
        workspace_id=workspace.id,
        label=label or f"Senha {n}",
        encrypted_password=encrypted_password,
    )
    db.add(vp)
    await db.flush()
    return vp


# ─── PipelineRun + StageLog ───────────────────────────────────────────


async def make_run(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    status: str = "completed",
    current_stage: Optional[str] = None,
    failed_at_stage: Optional[str] = None,
    paused_at_stage: Optional[str] = None,
    tier_at_run: str = "free",
    total_documents: int = 1,
    celery_task_id: Optional[str] = None,
    config_snapshot: Optional[dict] = None,
) -> PipelineRun:
    n = _next("run")
    if workspace is None:
        workspace = await make_workspace(db)
    now = datetime.now(timezone.utc)
    run = PipelineRun(
        workspace_id=workspace.id,
        status=status,
        current_stage=current_stage,
        failed_at_stage=failed_at_stage,
        paused_at_stage=paused_at_stage,
        tier_at_run=tier_at_run,
        total_documents=total_documents,
        celery_task_id=celery_task_id or f"celery-{n}",
        config_snapshot=config_snapshot,
        started_at=now,
        completed_at=now if status == "completed" else None,
    )
    db.add(run)
    await db.flush()
    return run


async def make_stage_log(
    db: AsyncSession,
    *,
    run: PipelineRun,
    stage: str = "E0",
    status: str = "completed",
    output_summary: Optional[dict] = None,
    errors: Optional[str] = None,
    duration_ms: int = 1000,
) -> PipelineStageLog:
    _next("stage")
    now = datetime.now(timezone.utc)
    log = PipelineStageLog(
        pipeline_run_id=run.id,
        stage=stage,
        status=status,
        output_summary=output_summary or {"processed": 1},
        errors=errors,
        duration_ms=duration_ms,
        started_at=now,
        completed_at=now if status == "completed" else None,
    )
    db.add(log)
    await db.flush()
    return log


# ─── Report ───────────────────────────────────────────────────────────


async def make_report(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    pipeline_run: Optional[PipelineRun] = None,
    title: Optional[str] = None,
    period: str = "2026-04",
    analysis_artifact_id: Optional[int] = None,
    score: Optional[float] = 78.0,
    patrimonio_liquido: Optional[float] = 250_000.0,
) -> Report:
    n = _next("report")
    if workspace is None:
        workspace = await make_workspace(db)
    r = Report(
        workspace_id=workspace.id,
        pipeline_run_id=pipeline_run.id if pipeline_run else None,
        title=title or f"Relatório {n}",
        period=period,
        analysis_artifact_id=analysis_artifact_id,
        score=score,
        patrimonio_liquido=patrimonio_liquido,
    )
    db.add(r)
    await db.flush()
    return r


# ─── Notification ─────────────────────────────────────────────────────


async def make_notification(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    severity: str = "info",
    title: Optional[str] = None,
    message: str = "Mensagem de teste",
    source: str = "pipeline",
    is_read: bool = False,
) -> Notification:
    n = _next("notification")
    if workspace is None:
        workspace = await make_workspace(db)
    notif = Notification(
        workspace_id=workspace.id,
        severity=severity,
        title=title or f"Notificação {n}",
        message=message,
        source=source,
        is_read=is_read,
    )
    db.add(notif)
    await db.flush()
    return notif


# ─── LLM Config ───────────────────────────────────────────────────────


async def make_llm_config(
    db: AsyncSession,
    *,
    workspace: Optional[Workspace] = None,
    provider: str = "anthropic",
    model_name: str = "claude-opus-4-6",
    api_key_encrypted: str = "encrypted-test-key",
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> LLMConfig:
    if workspace is None:
        workspace = await make_workspace(db)
    cfg = LLMConfig(
        workspace_id=workspace.id,
        provider=provider,
        model_name=model_name,
        api_key_encrypted=api_key_encrypted,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    db.add(cfg)
    await db.flush()
    return cfg
