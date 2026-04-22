"""Config API — thin router (A6e.4 slice · ADR-101 R15/R16).

Handlers delegam a use cases em ``backend/app/application/config_blob/``
quando possível (3 blobs: pipeline/institutions/report-layout).

Composites (``/import``, ``/export``, ``/workspace`` settings) permanecem
no router porque cruzam agregados (FamilyMember + Category + 3 ConfigBlobs)
— por ADR-112 §rollback, multi-aggregate composites só viram use case
quando ganham caso de uso genuíno reusado por outro endpoint.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.config_blob import (
    get_institution_config as _uc_get_institution_config,
    get_pipeline_config as _uc_get_pipeline_config,
    get_report_layout as _uc_get_report_layout,
    update_institution_config as _uc_update_institution_config,
    update_pipeline_config as _uc_update_pipeline_config,
    update_report_layout as _uc_update_report_layout,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
)
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
)
from backend.app.services.config_defaults import (
    ConfigDefaultsLoader,
    load_global_json,
    load_global_yaml,
)
from backend.app.services.vault import get_vault

router = APIRouter(prefix="/workspaces/{workspace_id}/config", tags=["config"])

_vault = get_vault()
_defaults = ConfigDefaultsLoader()


def _get_config_blob_repo(
    db: AsyncSession = Depends(get_db),
) -> ConfigBlobRepository:
    return ConfigBlobRepository(db)


def _get_family_repo(db: AsyncSession = Depends(get_db)) -> FamilyMemberRepository:
    return FamilyMemberRepository(db)


def _get_category_repo(db: AsyncSession = Depends(get_db)) -> CategoryRepository:
    return CategoryRepository(db)


# =============================================================================
# Workspace settings
# =============================================================================


@router.get("/workspace", response_model=WorkspaceSettingsSchema)
async def get_workspace_settings(
    workspace: Workspace = Depends(get_current_workspace),
) -> WorkspaceSettingsSchema:
    return WorkspaceSettingsSchema(
        name=workspace.name, family_surname=workspace.family_surname
    )


@router.patch(
    "/workspace",
    response_model=WorkspaceSettingsSchema,
    dependencies=[Depends(require_write_role)],
)
async def update_workspace_settings(
    body: WorkspaceSettingsUpdateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceSettingsSchema:
    if body.family_surname is not None:
        workspace.family_surname = body.family_surname.strip() or None
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceSettingsSchema(
        name=workspace.name, family_surname=workspace.family_surname
    )


# =============================================================================
# Pipeline Config
# =============================================================================


@router.get("/pipeline", response_model=PipelineConfigResponse)
async def get_pipeline_config(
    workspace: Workspace = Depends(get_current_workspace),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
) -> PipelineConfigResponse:
    return await _uc_get_pipeline_config(
        workspace.id, repo=repo, defaults=_defaults
    )


@router.put("/pipeline", response_model=PipelineConfigResponse)
async def update_pipeline_config(
    body: PipelineConfigUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
) -> PipelineConfigResponse:
    response = await _uc_update_pipeline_config(
        body, workspace_id=workspace.id, repo=repo, defaults=_defaults
    )
    await db.commit()
    return response


# =============================================================================
# Institution Config
# =============================================================================


@router.get("/institutions", response_model=InstitutionConfigResponse)
async def get_institution_config(
    workspace: Workspace = Depends(get_current_workspace),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
) -> InstitutionConfigResponse:
    return await _uc_get_institution_config(
        workspace.id, repo=repo, defaults=_defaults
    )


@router.put("/institutions", response_model=InstitutionConfigResponse)
async def update_institution_config(
    body: InstitutionConfigUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
) -> InstitutionConfigResponse:
    response = await _uc_update_institution_config(
        body, workspace_id=workspace.id, repo=repo
    )
    await db.commit()
    return response


# =============================================================================
# Report Layout
# =============================================================================


@router.get("/report-layout", response_model=ReportLayoutResponse)
async def get_report_layout(
    workspace: Workspace = Depends(get_current_workspace),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
) -> ReportLayoutResponse:
    return await _uc_get_report_layout(
        workspace.id, repo=repo, defaults=_defaults
    )


@router.put("/report-layout", response_model=ReportLayoutResponse)
async def update_report_layout(
    body: ReportLayoutUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
) -> ReportLayoutResponse:
    response = await _uc_update_report_layout(
        body, workspace_id=workspace.id, repo=repo
    )
    await db.commit()
    return response


# =============================================================================
# Import / Export — composites (multi-aggregate; mantidos no router)
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
    category_repo: CategoryRepository = Depends(_get_category_repo),
) -> ConfigImportResponse:
    imported: list[str] = []
    if body.family_members:
        await _import_family_members(workspace, body.family_members, family_repo)
        imported.append("family_members")
    if body.categorization:
        await _import_categorization(workspace.id, body.categorization, category_repo)
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
    blob_repo: ConfigBlobRepository = Depends(_get_config_blob_repo),
    family_repo: FamilyMemberRepository = Depends(_get_family_repo),
    category_repo: CategoryRepository = Depends(_get_category_repo),
) -> ConfigExportResponse:
    return ConfigExportResponse(
        family_members=await _export_family_members(workspace, family_repo),
        categorization=await _export_categorization(workspace.id, category_repo),
        pipeline=await _export_blob_or_default(
            blob_repo, workspace.id, PipelineConfig, "pipeline.json", yaml_source=False
        ),
        institutions=await _export_blob_or_default(
            blob_repo, workspace.id, InstitutionConfig, "institutions.json", yaml_source=False
        ),
        report_layout=await _export_blob_or_default(
            blob_repo, workspace.id, ReportLayout, "report_layout.yaml", yaml_source=True
        ),
    )


# =============================================================================
# Private helpers — import/export composites
# =============================================================================


async def _import_family_members(
    workspace: Workspace,
    data: dict[str, Any],
    repo: FamilyMemberRepository,
) -> None:
    await repo.delete_all_in_workspace(workspace.id)

    family_surname = (
        data.get("familia", {}).get("sobrenome")
        if isinstance(data.get("familia"), dict)
        else None
    )
    if family_surname is not None:
        workspace.family_surname = family_surname or None

    membros = data.get("membros", {})
    banco_membro = data.get("banco_membro", {})

    account_map: dict[str, list[str]] = {}
    for bank_code, member_key in banco_membro.items():
        account_map.setdefault(member_key, []).append(bank_code)

    for order, (key, info) in enumerate(membros.items()):
        cpf_enc = _vault.encrypt(info.get("cpf")) if info.get("cpf") else None
        extra = {
            k: v
            for k, v in info.items()
            if k not in ("nome_completo", "nome_curto", "cpf", "data_nascimento", "papel")
        }
        member = await repo.create(
            workspace.id,
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


async def _import_categorization(
    ws_id: str,
    data: dict[str, Any],
    repo: CategoryRepository,
) -> None:
    await repo.delete_all_in_workspace(ws_id)
    order = 0
    for cat_type, key in [("expense", "expense_keywords"), ("income", "income_keywords")]:
        keywords_map = data.get(key, {})
        for code, keywords in keywords_map.items():
            await repo.create(
                ws_id,
                code=code,
                name=code.replace("_", " ").title(),
                category_type=cat_type,
                order=order,
                keywords=list(keywords),
            )
            order += 1


async def _export_blob_or_default(
    repo: ConfigBlobRepository,
    ws_id: str,
    model_class: type,
    default_filename: str,
    *,
    yaml_source: bool,
) -> dict[str, Any]:
    """Retorna o blob do DB ou o default do disco (dict, não DTO)."""
    cfg_json = await repo.get_config_json(ws_id, model_class)
    if cfg_json is not None:
        return cfg_json
    return (
        load_global_yaml(default_filename)
        if yaml_source
        else load_global_json(default_filename)
    )


async def _export_family_members(
    workspace: Workspace,
    repo: FamilyMemberRepository,
) -> dict[str, Any]:
    members = await repo.list_by_workspace(workspace.id)
    family_surname = workspace.family_surname

    if not members:
        # F6.5E.6: NÃO retornar global cru (vaza identidade do founder).
        result: dict[str, Any] = {"membros": {}}
        if family_surname:
            result["familia"] = {"sobrenome": family_surname}
        return result

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

    result: dict[str, Any] = {"membros": membros}
    if family_surname:
        result["familia"] = {"sobrenome": family_surname}
    if banco_membro:
        result["banco_membro"] = banco_membro
    if titular:
        result["titular"] = titular
    return result


async def _export_categorization(
    ws_id: str,
    repo: CategoryRepository,
) -> dict[str, Any]:
    cats = await repo.list_by_workspace(ws_id)
    if not cats:
        return load_global_json("categorization.json")

    expense_keywords: dict[str, list[str]] = {}
    income_keywords: dict[str, list[str]] = {}
    for cat in cats:
        kws = [kw.keyword for kw in cat.keywords]
        if cat.category_type == "expense":
            expense_keywords[cat.code] = kws
        else:
            income_keywords[cat.code] = kws
    return {"expense_keywords": expense_keywords, "income_keywords": income_keywords}
