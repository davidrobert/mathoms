"""Config API — CRUD for the 5 editable configs, import/export, fallback to disk defaults.

**A6e (ADR-101)** — endpoints dos agregados ``FamilyMember`` (A6e.1+.2),
``Category`` (A6e.3) e dos 3 blobs de config ``Pipeline``/``Institution``/
``ReportLayout`` (A6e.4) delegam persistência aos respectivos repositórios
(``FamilyMemberRepository`` / ``CategoryRepository`` /
``ConfigBlobRepository``) e retornam DTOs de
``schemas/dto/{family_member,category,config_blob}/``.

**A6e.3 slice 1** — CRUD de ``FamilyMember`` + ``BankAccount`` migrou para
``backend/app/api/family_members.py`` (router fino delegando a use cases
em ``backend/app/application/family_member/``). Helpers ``_import_family_members``
/ ``_export_family_members`` usam o repo — sem ``select(FamilyMember)`` aqui.
"""

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
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.category import Category, CategoryKeyword
from backend.app.models.config_blob import InstitutionConfig, PipelineConfig, ReportLayout
from backend.app.models.workspace import Workspace
from backend.app.repositories.category_repository import CategoryRepository
from backend.app.repositories.config_blob_repository import ConfigBlobRepository
from backend.app.repositories.family_member_repository import FamilyMemberRepository
from backend.app.schemas.config import (
    ConfigExportResponse,
    ConfigImportRequest,
    ConfigImportResponse,
    WorkspaceSettingsSchema,
    WorkspaceSettingsUpdateRequest,
)
from backend.app.schemas.dto.config_blob import (
    InstitutionConfigResponse,
    InstitutionConfigUpdateCommand,
    PipelineConfigResponse,
    PipelineConfigUpdateCommand,
    ReportLayoutResponse,
    ReportLayoutUpdateCommand,
    deep_merge,
    institution_blob_to_response,
    pipeline_blob_to_response,
    report_layout_to_response,
)
from backend.app.schemas.dto.category import (
    CategoryCreateCommand,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateCommand,
    category_to_response,
)
from backend.app.schemas.dto.category import (
    convert_global_defaults_to_responses as convert_category_defaults_to_responses,
)
from backend.app.schemas.dto.category import (
    count_defaults as count_category_defaults,
)
from backend.app.services.vault import get_vault

router = APIRouter(
    prefix="/workspaces/{workspace_id}/config",
    tags=["config"],
)

_vault = get_vault()


def _get_category_repo(
    db: AsyncSession = Depends(get_db),
) -> CategoryRepository:
    """DI helper — injeta o ``CategoryRepository`` no endpoint (A6e.3)."""
    return CategoryRepository(db)


def _get_config_blob_repo(
    db: AsyncSession = Depends(get_db),
) -> ConfigBlobRepository:
    """DI helper — injeta o ``ConfigBlobRepository`` no endpoint (A6e.4).

    Um repo paramétrico atende os 3 blobs (pipeline/institutions/
    report-layout); o endpoint passa a classe do modelo nos métodos.
    """
    return ConfigBlobRepository(db)


def _get_family_repo(db: AsyncSession = Depends(get_db)) -> FamilyMemberRepository:
    """DI helper — usado apenas por import/export (CRUD migrou para family_members.py)."""
    return FamilyMemberRepository(db)


# =============================================================================
# Helpers
# =============================================================================


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


# =============================================================================
# Workspace settings (family_surname — exibido no relatório E6)
# =============================================================================


@router.get("/workspace", response_model=WorkspaceSettingsSchema)
async def get_workspace_settings(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return WorkspaceSettingsSchema(name=workspace.name, family_surname=workspace.family_surname)


@router.patch(
    "/workspace",
    response_model=WorkspaceSettingsSchema,
    dependencies=[Depends(require_write_role)],
)
async def update_workspace_settings(
    body: WorkspaceSettingsUpdateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    # Tratamento explícito: empty string → None (limpa o campo)
    if body.family_surname is not None:
        workspace.family_surname = body.family_surname.strip() or None
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceSettingsSchema(name=workspace.name, family_surname=workspace.family_surname)


# =============================================================================
# Categories — CRUD with nested keywords (3B.3)
# =============================================================================


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_category_repo),
):
    cats = await repo.list_by_workspace(workspace.id)
    if cats:
        responses = [category_to_response(c) for c in cats]
        return CategoryListResponse(categories=responses, total=len(responses))

    defaults = _load_global_json("categorization.json")
    return CategoryListResponse(
        categories=convert_category_defaults_to_responses(defaults),
        total=count_category_defaults(defaults),
    )


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    body: CategoryCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_category_repo),
):
    if await repo.code_exists(workspace.id, body.code):
        raise HTTPException(
            status_code=409,
            detail=f"Categoria com code '{body.code}' já existe",
        )
    cat = await repo.create(
        workspace.id,
        code=body.code,
        name=body.name,
        category_type=body.category_type,
        monthly_cap=body.monthly_cap,
        order=body.order,
        keywords=body.keywords,
    )
    return category_to_response(cat)


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    body: CategoryUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_category_repo),
):
    cat = await repo.get_by_id_with_keywords(workspace.id, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    update_data = body.model_dump(exclude_unset=True)
    keywords_update = update_data.pop("keywords", None)

    new_code = update_data.get("code")
    if new_code is not None and new_code != cat.code:
        if await repo.code_exists(
            workspace.id, new_code, exclude_id=cat.id
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Categoria com code '{new_code}' já existe",
            )

    cat = await repo.update(cat, updates=update_data, keywords=keywords_update)
    return category_to_response(cat)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_category_repo),
):
    cat = await repo.get_by_id(workspace.id, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    await repo.delete(cat)


# =============================================================================
# Pipeline Config — GET/PUT (3B.4) · A6e.4
# =============================================================================


@router.get("/pipeline", response_model=PipelineConfigResponse)
async def get_pipeline_config(
    workspace: Workspace = Depends(get_current_workspace),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
):
    cfg_json = await repo.get_config_json(workspace.id, PipelineConfig)
    if cfg_json is None:
        cfg_json = _load_global_json("pipeline.json")
    return pipeline_blob_to_response(cfg_json)


@router.put("/pipeline", response_model=PipelineConfigResponse)
async def update_pipeline_config(
    body: PipelineConfigUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
):
    existing = await repo.get_config_json(workspace.id, PipelineConfig)
    base = existing if existing is not None else _load_global_json("pipeline.json")
    merged = deep_merge(base, body.model_dump(exclude_unset=True))
    await repo.upsert(workspace.id, PipelineConfig, merged)
    await db.commit()
    return pipeline_blob_to_response(merged)


# =============================================================================
# Institution Config — GET/PUT (3B.5) · A6e.4
# =============================================================================


@router.get("/institutions", response_model=InstitutionConfigResponse)
async def get_institution_config(
    workspace: Workspace = Depends(get_current_workspace),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
):
    cfg_json = await repo.get_config_json(workspace.id, InstitutionConfig)
    if cfg_json is None:
        cfg_json = _load_global_json("institutions.json")
    return institution_blob_to_response(cfg_json)


@router.put("/institutions", response_model=InstitutionConfigResponse)
async def update_institution_config(
    body: InstitutionConfigUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
):
    cfg = await repo.upsert(workspace.id, InstitutionConfig, body.config_json)
    await db.commit()
    return institution_blob_to_response(cfg.config_json)


# =============================================================================
# Report Layout — GET/PUT (3B.6) · A6e.4
# =============================================================================


@router.get("/report-layout", response_model=ReportLayoutResponse)
async def get_report_layout(
    workspace: Workspace = Depends(get_current_workspace),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
):
    cfg_json = await repo.get_config_json(workspace.id, ReportLayout)
    if cfg_json is None:
        cfg_json = _load_global_yaml("report_layout.yaml")
    return report_layout_to_response(cfg_json)


@router.put("/report-layout", response_model=ReportLayoutResponse)
async def update_report_layout(
    body: ReportLayoutUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
):
    cfg = await repo.upsert(workspace.id, ReportLayout, body.config_json)
    await db.commit()
    return report_layout_to_response(cfg.config_json)


# =============================================================================
# Import / Export (3B.8, 3B.9)
# =============================================================================


@router.post(
    "/import",
    response_model=ConfigImportResponse,
    status_code=status.HTTP_200_OK,
)
async def import_config(
    body: ConfigImportRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    blob_repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
    family_repo: FamilyMemberRepository = Depends(_get_family_repo),
) -> ConfigImportResponse:
    imported: list[str] = []

    if body.family_members:
        await _import_family_members(workspace.id, body.family_members, db, family_repo)
        imported.append("family_members")

    if body.categorization:
        await _import_categorization(workspace.id, body.categorization, db)
        imported.append("categorization")

    if body.pipeline:
        await blob_repo.upsert(workspace.id, PipelineConfig, body.pipeline)
        imported.append("pipeline")

    if body.institutions:
        await blob_repo.upsert(workspace.id, InstitutionConfig, body.institutions)
        imported.append("institutions")

    if body.report_layout:
        await blob_repo.upsert(workspace.id, ReportLayout, body.report_layout)
        imported.append("report_layout")

    await db.commit()
    return ConfigImportResponse(imported=imported, total=len(imported))


@router.get("/export", response_model=ConfigExportResponse)
async def export_config(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    blob_repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
    family_repo: FamilyMemberRepository = Depends(_get_family_repo),
):

    members_data = await _export_family_members(workspace.id, db, family_repo)
    categorization_data = await _export_categorization(workspace.id, db)
    pipeline_data = await _export_blob_or_default(
        blob_repo, workspace.id, PipelineConfig, "pipeline.json", yaml_source=False
    )
    institutions_data = await _export_blob_or_default(
        blob_repo, workspace.id, InstitutionConfig, "institutions.json", yaml_source=False
    )
    layout_data = await _export_blob_or_default(
        blob_repo, workspace.id, ReportLayout, "report_layout.yaml", yaml_source=True
    )

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


async def _import_family_members(
    ws_id: str,
    data: dict[str, Any],
    db: AsyncSession,
    repo: FamilyMemberRepository,
) -> None:
    await repo.delete_all_in_workspace(ws_id)

    family_surname = (
        data.get("familia", {}).get("sobrenome")
        if isinstance(data.get("familia"), dict)
        else None
    )
    if family_surname is not None:
        ws_result = await db.execute(select(Workspace).where(Workspace.id == ws_id))
        ws = ws_result.scalar_one_or_none()
        if ws is not None:
            ws.family_surname = family_surname or None

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
        member = await repo.create(
            ws_id,
            key=key,
            full_name=info.get("nome_completo", key),
            short_name=info.get("nome_curto", key),
            cpf_encrypted=cpf_enc,
            birth_date=info.get("data_nascimento"),
            role=info.get("papel", "titular"),
            order=order,
            extra=extra or None,
        )
        for bank_code in account_map.get(key, []):
            await repo.add_account(
                member.id,
                institution_code=bank_code,
                account_type="extratoconta",
            )


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


async def _export_blob_or_default(
    repo: ConfigBlobRepository,
    ws_id: str,
    model_class: type,
    default_filename: str,
    *,
    yaml_source: bool,
) -> dict[str, Any]:
    """Retorna o blob do DB ou o default do disco.

    ``yaml_source=True`` lê ``config/report_layout.yaml``; ``False`` lê um
    JSON do mesmo diretório. Export precisa do shape dict — os DTOs
    ``pipeline_blob_to_response`` etc. não cabem aqui (``ConfigExportResponse``
    espera ``dict[str, Any]``).
    """
    cfg_json = await repo.get_config_json(ws_id, model_class)
    if cfg_json is not None:
        return cfg_json
    return (
        _load_global_yaml(default_filename)
        if yaml_source
        else _load_global_json(default_filename)
    )


# =============================================================================
# Private helpers — export (DB → pipeline-compatible JSON format)
# =============================================================================


async def _export_family_members(
    ws_id: str,
    db: AsyncSession,
    repo: FamilyMemberRepository,
) -> dict[str, Any]:
    members = await repo.list_by_workspace(ws_id)

    ws_result = await db.execute(select(Workspace).where(Workspace.id == ws_id))
    workspace = ws_result.scalar_one_or_none()
    family_surname = workspace.family_surname if workspace else None

    if not members:
        # F6.5E.6: NÃO retornar global cru (vaza identidade do founder).
        # Em vez disso, retornar a estrutura mínima esperada — vazia se o
        # workspace ainda não tem nada. Surname só vai se o user setou.
        result_dict: dict[str, Any] = {"membros": {}}
        if family_surname:
            result_dict["familia"] = {"sobrenome": family_surname}
        return result_dict

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


# =============================================================================
# Conversion helpers — global config JSON → Pydantic DTOs (for fallback)
# =============================================================================

# ``family_members`` fallback: ``convert_global_defaults_to_responses`` vive
# em ``schemas/dto/family_member/mapper`` (A6e.1+.2).
# ``categorization`` fallback: ``convert_global_defaults_to_responses`` +
# ``count_defaults`` vivem em ``schemas/dto/category/mapper`` (A6e.3).
# ``pipeline``/``institutions``/``report_layout`` fallback: respectivos
# ``*_blob_to_response`` + ``deep_merge`` vivem em
# ``schemas/dto/config_blob/mapper`` (A6e.4).
