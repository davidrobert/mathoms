"""Config API — CRUD for the 5 editable configs, import/export, fallback to disk defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.category import Category, CategoryKeyword
from backend.app.models.config_blob import InstitutionConfig, PipelineConfig, ReportLayout
from backend.app.models.family_member import BankAccount, FamilyMember
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.config import (
    BankAccountCreateRequest,
    BankAccountSchema,
    CategoryCreateRequest,
    CategoryListResponse,
    CategorySchema,
    CategoryUpdateRequest,
    ConfigExportResponse,
    ConfigImportRequest,
    FamilyMemberCreateRequest,
    FamilyMemberListResponse,
    FamilyMemberSchema,
    FamilyMemberUpdateRequest,
    InstitutionConfigSchema,
    InstitutionConfigUpdateRequest,
    PipelineConfigSchema,
    PipelineConfigUpdateRequest,
    ReportLayoutSchema,
    ReportLayoutUpdateRequest,
    WorkspaceSettingsSchema,
    WorkspaceSettingsUpdateRequest,
)
from backend.app.services.vault import VaultService

router = APIRouter(prefix="/config", tags=["config"])

_vault = VaultService()


# =============================================================================
# Helpers
# =============================================================================


async def _get_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


def _global_config_dir() -> Path:
    return settings.PIPELINE_ROOT / "config"


def _load_global_json(name: str) -> dict[str, Any]:
    path = _global_config_dir() / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_global_yaml(name: str) -> dict[str, Any]:
    path = _global_config_dir() / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _member_to_schema(m: FamilyMember) -> FamilyMemberSchema:
    cpf_plain = None
    if m.cpf_encrypted:
        cpf_plain = _vault.decrypt(m.cpf_encrypted)
    accounts = [BankAccountSchema.model_validate(a) for a in m.accounts] if m.accounts else []
    return FamilyMemberSchema(
        id=m.id, key=m.key, full_name=m.full_name, short_name=m.short_name,
        cpf=cpf_plain, birth_date=m.birth_date, role=m.role, order=m.order,
        extra=m.extra, accounts=accounts,
    )


def _category_to_schema(c: Category) -> CategorySchema:
    keywords = [kw.keyword for kw in c.keywords] if c.keywords else []
    return CategorySchema(
        id=c.id, code=c.code, name=c.name, category_type=c.category_type,
        monthly_cap=c.monthly_cap, order=c.order, keywords=keywords,
    )


# =============================================================================
# Workspace settings (family_surname — exibido no relatório E6)
# =============================================================================


@router.get("/workspace", response_model=WorkspaceSettingsSchema)
async def get_workspace_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    return WorkspaceSettingsSchema(name=ws.name, family_surname=ws.family_surname)


@router.patch("/workspace", response_model=WorkspaceSettingsSchema)
async def update_workspace_settings(
    body: WorkspaceSettingsUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    # Tratamento explícito: empty string → None (limpa o campo)
    if body.family_surname is not None:
        ws.family_surname = body.family_surname.strip() or None
    await db.commit()
    await db.refresh(ws)
    return WorkspaceSettingsSchema(name=ws.name, family_surname=ws.family_surname)


# =============================================================================
# Family Members — CRUD (3B.1)
# =============================================================================


@router.get("/members", response_model=FamilyMemberListResponse)
async def list_members(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(FamilyMember)
        .where(FamilyMember.workspace_id == ws.id)
        .options(selectinload(FamilyMember.accounts))
        .order_by(FamilyMember.order, FamilyMember.key)
    )
    members = result.scalars().all()
    if members:
        schemas = [_member_to_schema(m) for m in members]
        return FamilyMemberListResponse(members=schemas, total=len(schemas))

    defaults = _load_global_json("family_members.json")
    return FamilyMemberListResponse(
        members=_convert_members_json_to_schemas(defaults),
        total=len(defaults.get("membros", {})),
    )


@router.post("/members", response_model=FamilyMemberSchema, status_code=status.HTTP_201_CREATED)
async def create_member(
    body: FamilyMemberCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    existing = await db.execute(
        select(FamilyMember).where(FamilyMember.workspace_id == ws.id, FamilyMember.key == body.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Membro com key '{body.key}' já existe neste workspace")

    cpf_enc = _vault.encrypt(body.cpf) if body.cpf else None
    member = FamilyMember(
        workspace_id=ws.id, key=body.key, full_name=body.full_name,
        short_name=body.short_name, cpf_encrypted=cpf_enc,
        birth_date=body.birth_date, role=body.role, order=body.order,
        extra=body.extra,
    )
    db.add(member)
    await db.commit()

    result = await db.execute(
        select(FamilyMember).where(FamilyMember.id == member.id).options(selectinload(FamilyMember.accounts))
    )
    return _member_to_schema(result.scalar_one())


@router.put("/members/{member_id}", response_model=FamilyMemberSchema)
async def update_member(
    member_id: str,
    body: FamilyMemberUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(FamilyMember)
        .where(FamilyMember.id == member_id, FamilyMember.workspace_id == ws.id)
        .options(selectinload(FamilyMember.accounts))
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado")

    update_data = body.model_dump(exclude_unset=True)
    if "cpf" in update_data:
        cpf_val = update_data.pop("cpf")
        member.cpf_encrypted = _vault.encrypt(cpf_val) if cpf_val else None
    for field, value in update_data.items():
        setattr(member, field, value)

    await db.commit()
    await db.refresh(member)
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.id == member.id).options(selectinload(FamilyMember.accounts))
    )
    return _member_to_schema(result.scalar_one())


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.id == member_id, FamilyMember.workspace_id == ws.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    await db.delete(member)
    await db.commit()


# =============================================================================
# Bank Accounts — CRUD nested under members (3B.2)
# =============================================================================


@router.get("/members/{member_id}/accounts", response_model=list[BankAccountSchema])
async def list_accounts(
    member_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    member = await _verify_member(member_id, ws.id, db)
    result = await db.execute(select(BankAccount).where(BankAccount.member_id == member.id))
    return [BankAccountSchema.model_validate(a) for a in result.scalars().all()]


@router.post("/members/{member_id}/accounts", response_model=BankAccountSchema, status_code=status.HTTP_201_CREATED)
async def create_account(
    member_id: str,
    body: BankAccountCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    member = await _verify_member(member_id, ws.id, db)
    account = BankAccount(
        member_id=member.id, institution_code=body.institution_code,
        account_type=body.account_type, agency=body.agency,
        account_number=body.account_number, label=body.label,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return BankAccountSchema.model_validate(account)


@router.put("/members/{member_id}/accounts/{account_id}", response_model=BankAccountSchema)
async def update_account(
    member_id: str,
    account_id: str,
    body: BankAccountCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    await _verify_member(member_id, ws.id, db)
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id, BankAccount.member_id == member_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada")
    account.institution_code = body.institution_code
    account.account_type = body.account_type
    account.agency = body.agency
    account.account_number = body.account_number
    await db.commit()
    await db.refresh(account)
    return BankAccountSchema.model_validate(account)


@router.delete("/members/{member_id}/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    member_id: str,
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    await _verify_member(member_id, ws.id, db)
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id, BankAccount.member_id == member_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada")
    await db.delete(account)
    await db.commit()


async def _verify_member(member_id: str, ws_id: str, db: AsyncSession) -> FamilyMember:
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.id == member_id, FamilyMember.workspace_id == ws_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return member


# =============================================================================
# Categories — CRUD with nested keywords (3B.3)
# =============================================================================


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(Category)
        .where(Category.workspace_id == ws.id)
        .options(selectinload(Category.keywords))
        .order_by(Category.order, Category.code)
    )
    cats = result.scalars().all()
    if cats:
        schemas = [_category_to_schema(c) for c in cats]
        return CategoryListResponse(categories=schemas, total=len(schemas))

    defaults = _load_global_json("categorization.json")
    return CategoryListResponse(
        categories=_convert_categorization_json_to_schemas(defaults),
        total=len(defaults.get("expense_keywords", {})) + len(defaults.get("income_keywords", {})),
    )


@router.post("/categories", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    existing = await db.execute(
        select(Category).where(Category.workspace_id == ws.id, Category.code == body.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Categoria com code '{body.code}' já existe")

    cat = Category(
        workspace_id=ws.id, code=body.code, name=body.name,
        category_type=body.category_type, monthly_cap=body.monthly_cap, order=body.order,
    )
    db.add(cat)
    await db.flush()

    for kw_text in body.keywords:
        db.add(CategoryKeyword(category_id=cat.id, keyword=kw_text))
    await db.commit()

    result = await db.execute(
        select(Category).where(Category.id == cat.id).options(selectinload(Category.keywords))
    )
    return _category_to_schema(result.scalar_one())


@router.put("/categories/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: str,
    body: CategoryUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.workspace_id == ws.id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    update_data = body.model_dump(exclude_unset=True)
    keywords_update = update_data.pop("keywords", None)

    for field, value in update_data.items():
        setattr(cat, field, value)

    if keywords_update is not None:
        old_kws = (await db.execute(
            select(CategoryKeyword).where(CategoryKeyword.category_id == cat.id)
        )).scalars().all()
        for kw in old_kws:
            await db.delete(kw)
        await db.flush()
        for kw_text in keywords_update:
            db.add(CategoryKeyword(category_id=cat.id, keyword=kw_text))

    await db.commit()
    result = await db.execute(
        select(Category).where(Category.id == cat.id).options(selectinload(Category.keywords))
    )
    return _category_to_schema(result.scalar_one())


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.workspace_id == ws.id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    await db.delete(cat)
    await db.commit()


# =============================================================================
# Pipeline Config — GET/PUT (3B.4)
# =============================================================================


@router.get("/pipeline", response_model=PipelineConfigSchema)
async def get_pipeline_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(select(PipelineConfig).where(PipelineConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()
    if cfg:
        return PipelineConfigSchema(**cfg.config_json)
    return PipelineConfigSchema(**_load_global_json("pipeline.json"))


@router.put("/pipeline", response_model=PipelineConfigSchema)
async def update_pipeline_config(
    body: PipelineConfigUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(select(PipelineConfig).where(PipelineConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()

    new_data = body.model_dump(exclude_unset=True)
    merged = _deep_merge(cfg.config_json if cfg else _load_global_json("pipeline.json"), new_data)

    if cfg:
        cfg.config_json = merged
    else:
        cfg = PipelineConfig(workspace_id=ws.id, config_json=merged)
        db.add(cfg)
    await db.commit()
    return PipelineConfigSchema(**merged)


# =============================================================================
# Institution Config — GET/PUT (3B.5)
# =============================================================================


@router.get("/institutions", response_model=InstitutionConfigSchema)
async def get_institution_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(select(InstitutionConfig).where(InstitutionConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()
    if cfg:
        return InstitutionConfigSchema(config_json=cfg.config_json)
    return InstitutionConfigSchema(config_json=_load_global_json("institutions.json"))


@router.put("/institutions", response_model=InstitutionConfigSchema)
async def update_institution_config(
    body: InstitutionConfigUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(select(InstitutionConfig).where(InstitutionConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.config_json = body.config_json
    else:
        cfg = InstitutionConfig(workspace_id=ws.id, config_json=body.config_json)
        db.add(cfg)
    await db.commit()
    return InstitutionConfigSchema(config_json=cfg.config_json)


# =============================================================================
# Report Layout — GET/PUT (3B.6)
# =============================================================================


@router.get("/report-layout", response_model=ReportLayoutSchema)
async def get_report_layout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(select(ReportLayout).where(ReportLayout.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()
    if cfg:
        return ReportLayoutSchema(config_json=cfg.config_json)
    return ReportLayoutSchema(config_json=_load_global_yaml("report_layout.yaml"))


@router.put("/report-layout", response_model=ReportLayoutSchema)
async def update_report_layout(
    body: ReportLayoutUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(select(ReportLayout).where(ReportLayout.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.config_json = body.config_json
    else:
        cfg = ReportLayout(workspace_id=ws.id, config_json=body.config_json)
        db.add(cfg)
    await db.commit()
    return ReportLayoutSchema(config_json=cfg.config_json)


# =============================================================================
# Import / Export (3B.8, 3B.9)
# =============================================================================


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_config(
    body: ConfigImportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    imported = []

    if body.family_members:
        await _import_family_members(ws.id, body.family_members, db)
        imported.append("family_members")

    if body.categorization:
        await _import_categorization(ws.id, body.categorization, db)
        imported.append("categorization")

    if body.pipeline:
        await _import_blob(ws.id, PipelineConfig, body.pipeline, db)
        imported.append("pipeline")

    if body.institutions:
        await _import_blob(ws.id, InstitutionConfig, body.institutions, db)
        imported.append("institutions")

    if body.report_layout:
        await _import_blob(ws.id, ReportLayout, body.report_layout, db)
        imported.append("report_layout")

    await db.commit()
    return {"imported": imported, "total": len(imported)}


@router.get("/export", response_model=ConfigExportResponse)
async def export_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)

    members_data = await _export_family_members(ws.id, db)
    categorization_data = await _export_categorization(ws.id, db)
    pipeline_data = await _export_pipeline(ws.id, db)
    institutions_data = await _export_institutions(ws.id, db)
    layout_data = await _export_report_layout(ws.id, db)

    return ConfigExportResponse(
        family_members=members_data,
        categorization=categorization_data,
        pipeline=pipeline_data,
        institutions=institutions_data,
        report_layout=layout_data,
    )


# =============================================================================
# Private helpers — import
# =============================================================================


async def _import_family_members(ws_id: str, data: dict[str, Any], db: AsyncSession) -> None:
    await db.execute(select(FamilyMember).where(FamilyMember.workspace_id == ws_id))
    existing = (await db.execute(select(FamilyMember).where(FamilyMember.workspace_id == ws_id))).scalars().all()
    for m in existing:
        await db.delete(m)
    await db.flush()

    family_surname = data.get("familia", {}).get("sobrenome") if isinstance(data.get("familia"), dict) else None
    if family_surname is not None:
        ws_result = await db.execute(select(Workspace).where(Workspace.id == ws_id))
        ws = ws_result.scalar_one_or_none()
        if ws is not None:
            ws.family_surname = family_surname or None  # empty string → None

    membros = data.get("membros", {})
    banco_membro = data.get("banco_membro", {})

    account_map: dict[str, list[str]] = {}
    for bank_code, member_key in banco_membro.items():
        account_map.setdefault(member_key, []).append(bank_code)

    for order, (key, info) in enumerate(membros.items()):
        cpf_enc = _vault.encrypt(info.get("cpf")) if info.get("cpf") else None
        extra = {k: v for k, v in info.items() if k not in (
            "nome_completo", "nome_curto", "cpf", "data_nascimento", "papel"
        )}
        member = FamilyMember(
            workspace_id=ws_id, key=key,
            full_name=info.get("nome_completo", key),
            short_name=info.get("nome_curto", key),
            cpf_encrypted=cpf_enc,
            birth_date=info.get("data_nascimento"),
            role=info.get("papel", "titular"),
            order=order, extra=extra or None,
        )
        db.add(member)
        await db.flush()

        for bank_code in account_map.get(key, []):
            db.add(BankAccount(member_id=member.id, institution_code=bank_code, account_type="extratoconta"))


async def _import_categorization(ws_id: str, data: dict[str, Any], db: AsyncSession) -> None:
    existing = (await db.execute(select(Category).where(Category.workspace_id == ws_id))).scalars().all()
    for c in existing:
        await db.delete(c)
    await db.flush()

    order = 0
    for cat_type, key in [("expense", "expense_keywords"), ("income", "income_keywords")]:
        keywords_map = data.get(key, {})
        for code, keywords in keywords_map.items():
            cat = Category(
                workspace_id=ws_id, code=code, name=code.replace("_", " ").title(),
                category_type=cat_type, order=order,
            )
            db.add(cat)
            await db.flush()
            for kw_text in keywords:
                db.add(CategoryKeyword(category_id=cat.id, keyword=kw_text))
            order += 1


async def _import_blob(ws_id: str, model_class: type, data: dict[str, Any], db: AsyncSession) -> None:
    result = await db.execute(select(model_class).where(model_class.workspace_id == ws_id))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.config_json = data
    else:
        cfg = model_class(workspace_id=ws_id, config_json=data)
        db.add(cfg)


# =============================================================================
# Private helpers — export (DB → pipeline-compatible JSON format)
# =============================================================================


async def _export_family_members(ws_id: str, db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        select(FamilyMember)
        .where(FamilyMember.workspace_id == ws_id)
        .options(selectinload(FamilyMember.accounts))
        .order_by(FamilyMember.order)
    )
    members = result.scalars().all()

    ws_result = await db.execute(select(Workspace).where(Workspace.id == ws_id))
    workspace = ws_result.scalar_one_or_none()
    family_surname = workspace.family_surname if workspace else None

    if not members:
        return _load_global_json("family_members.json")

    membros: dict[str, Any] = {}
    banco_membro: dict[str, str] = {}
    titular = None

    for m in members:
        cpf_plain = _vault.decrypt(m.cpf_encrypted) if m.cpf_encrypted else None
        info: dict[str, Any] = {
            "nome_completo": m.full_name,
            "nome_curto": m.short_name,
        }
        if cpf_plain:
            info["cpf"] = cpf_plain
        if m.birth_date:
            info["data_nascimento"] = m.birth_date.isoformat()
        info["papel"] = m.role
        if m.extra:
            info.update(m.extra)
        membros[m.key] = info

        if m.role == "titular":
            titular = m.key
        for acc in m.accounts:
            banco_membro[acc.institution_code] = m.key

    result_dict: dict[str, Any] = {"membros": membros}
    if family_surname:
        result_dict["familia"] = {"sobrenome": family_surname}
    if banco_membro:
        result_dict["banco_membro"] = banco_membro
    if titular:
        result_dict["titular"] = titular
    return result_dict


async def _export_categorization(ws_id: str, db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        select(Category)
        .where(Category.workspace_id == ws_id)
        .options(selectinload(Category.keywords))
        .order_by(Category.order)
    )
    cats = result.scalars().all()
    if not cats:
        return _load_global_json("categorization.json")

    expense_keywords: dict[str, list[str]] = {}
    income_keywords: dict[str, list[str]] = {}

    for cat in cats:
        kws = [kw.keyword for kw in cat.keywords]
        if cat.category_type == "expense":
            expense_keywords[cat.code] = kws
        else:
            income_keywords[cat.code] = kws

    return {"expense_keywords": expense_keywords, "income_keywords": income_keywords}


async def _export_pipeline(ws_id: str, db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(PipelineConfig).where(PipelineConfig.workspace_id == ws_id))
    cfg = result.scalar_one_or_none()
    return cfg.config_json if cfg else _load_global_json("pipeline.json")


async def _export_institutions(ws_id: str, db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(InstitutionConfig).where(InstitutionConfig.workspace_id == ws_id))
    cfg = result.scalar_one_or_none()
    return cfg.config_json if cfg else _load_global_json("institutions.json")


async def _export_report_layout(ws_id: str, db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(ReportLayout).where(ReportLayout.workspace_id == ws_id))
    cfg = result.scalar_one_or_none()
    return cfg.config_json if cfg else _load_global_yaml("report_layout.yaml")


# =============================================================================
# Conversion helpers — global config JSON → Pydantic schemas (for fallback)
# =============================================================================


def _convert_members_json_to_schemas(data: dict[str, Any]) -> list[FamilyMemberSchema]:
    membros = data.get("membros", {})
    schemas = []
    for order, (key, info) in enumerate(membros.items()):
        schemas.append(FamilyMemberSchema(
            key=key,
            full_name=info.get("nome_completo", key),
            short_name=info.get("nome_curto", key),
            cpf=None,  # BUG-004: never expose real CPFs from global fallback file
            birth_date=info.get("data_nascimento"),
            role=info.get("papel", "titular"),
            order=order,
            accounts=[],
        ))
    return schemas


def _convert_categorization_json_to_schemas(data: dict[str, Any]) -> list[CategorySchema]:
    schemas = []
    order = 0
    for cat_type, key in [("expense", "expense_keywords"), ("income", "income_keywords")]:
        for code, keywords in data.get(key, {}).items():
            schemas.append(CategorySchema(
                code=code, name=code.replace("_", " ").title(),
                category_type=cat_type, order=order, keywords=keywords,
            ))
            order += 1
    return schemas


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (override wins at leaf level)."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
