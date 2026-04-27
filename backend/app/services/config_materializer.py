"""ConfigMaterializer (post-A7.5) — copia tree global + overrides DB para non-A7.1 configs.

A7.1 (ADR-134) movou ``categorization`` / ``family_members`` / ``institutions`` /
``report_layout`` / ``transfer_config`` para ``WorkspaceContext.config_overrides``
populado por ``DBConfigStore``. ``prepare_pipeline_config_dir`` é o único caminho
suportado: copia ``config/`` global + materializa apenas ``pipeline.json`` e
``llm_config.json`` (configs ainda lidos de disco pelos scripts CLI legacy).

A função ``materialize_config`` (legacy) foi removida em Sprint A7.5.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.models.category import Category
from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
    TransferConfig,
)
from backend.app.models.family_member import FamilyMember
from backend.app.models.llm_config import LLMConfig
from backend.app.models.workspace import Workspace
from backend.app.services.vault import get_vault

_vault = get_vault()


def prepare_pipeline_config_dir(workspace_id: str, tenant_root: Path, db: Session) -> Path:
    """Copia o tree global + materializa apenas configs fora do escopo A7.1 (ADR-134)."""
    tenant_config = tenant_root / "config"
    _copy_global(_global_config_dir(), tenant_config)
    _override_pipeline(workspace_id, tenant_config, db)
    _override_llm_config(workspace_id, tenant_config, db)
    return tenant_config


def _global_config_dir() -> Path:
    return settings.PIPELINE_ROOT / "config"


def _copy_global(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# =============================================================================
# Serializers — DB models → pipeline-compatible dicts
# =============================================================================


def serialize_family_members(workspace_id: str, db: Session) -> dict[str, Any] | None:
    """Serialize FamilyMember + BankAccount rows into family_members.json format.

    Includes `familia.sobrenome` (from Workspace.family_surname) — consumed by E6
    as `{{COVER_FAMILIA}}` and in the report filename pattern. If the workspace has
    no family_surname set, the field is omitted (preserving the value already in
    the global config copied to tenant — typically empty for fresh workspaces).
    """
    members = (
        db.query(FamilyMember)
        .filter(FamilyMember.workspace_id == workspace_id)
        .options(selectinload(FamilyMember.accounts))
        .order_by(FamilyMember.order)
        .all()
    )

    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    family_surname = workspace.family_surname if workspace else None

    if not members and not family_surname:
        return None

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


def serialize_categorization(workspace_id: str, db: Session) -> dict[str, Any] | None:
    """Serialize Category + CategoryKeyword rows into categorization.json format."""
    cats = (
        db.query(Category)
        .filter(Category.workspace_id == workspace_id)
        .options(selectinload(Category.keywords))
        .order_by(Category.order)
        .all()
    )
    if not cats:
        return None

    expense_keywords: dict[str, list[str]] = {}
    income_keywords: dict[str, list[str]] = {}

    for cat in cats:
        kws = [kw.keyword for kw in cat.keywords]
        if cat.category_type == "expense":
            expense_keywords[cat.code] = kws
        else:
            income_keywords[cat.code] = kws

    return {"expense_keywords": expense_keywords, "income_keywords": income_keywords}


def serialize_pipeline_config(workspace_id: str, db: Session) -> dict[str, Any] | None:
    cfg = db.query(PipelineConfig).filter(PipelineConfig.workspace_id == workspace_id).first()
    return cfg.config_json if cfg else None


def serialize_transfer_config(workspace_id: str, db: Session) -> dict[str, Any] | None:
    """Bloco ``transferencias_internas`` (ADR-133) — None se não há row no DB."""
    cfg = db.query(TransferConfig).filter(TransferConfig.workspace_id == workspace_id).first()
    return cfg.config_json if cfg else None


def serialize_institution_config(workspace_id: str, db: Session) -> dict[str, Any] | None:
    cfg = db.query(InstitutionConfig).filter(InstitutionConfig.workspace_id == workspace_id).first()
    return cfg.config_json if cfg else None


def serialize_report_layout(workspace_id: str, db: Session) -> dict[str, Any] | None:
    cfg = db.query(ReportLayout).filter(ReportLayout.workspace_id == workspace_id).first()
    return cfg.config_json if cfg else None


# =============================================================================
# Override helpers — write serialized data to tenant config dir (only non-A7.1)
# =============================================================================


def _override_pipeline(workspace_id: str, config_dir: Path, db: Session) -> None:
    data = serialize_pipeline_config(workspace_id, db)
    if data is not None:
        _write_json(config_dir / "pipeline.json", data)


# =============================================================================
# Phase 4 — LLM Config serializer + override
# =============================================================================


def serialize_llm_config(workspace_id: str, db: Session) -> dict[str, Any] | None:
    """Serialize LLMConfig into a dict the pipeline LLM service can consume."""
    cfg = db.query(LLMConfig).filter(LLMConfig.workspace_id == workspace_id).first()
    if not cfg:
        return None

    api_key_plain = _vault.decrypt(cfg.api_key_encrypted)
    return {
        "provider": cfg.provider,
        "api_key": api_key_plain or "",
        "model_name": cfg.model_name,
        "max_tokens": cfg.max_tokens,
        "temperature": cfg.temperature,
    }


def _override_llm_config(workspace_id: str, config_dir: Path, db: Session) -> None:
    data = serialize_llm_config(workspace_id, db)
    if data is not None:
        _write_json(config_dir / "llm_config.json", data)


def ensure_tenant_pipeline_config(workspace_id: str, tenant_root: Path) -> Path:
    """Materialize ``tenant_root/config/`` when missing (e.g. before first pipeline run).

    Ensures upload and ``POST /documents/reclassify`` can use
    :func:`document_processor.resolve_classification_base` with tenant-specific
    ``family_members`` / ``institutions`` without requiring a prior pipeline execution.

    A7.1 (ADR-134): usa ``prepare_pipeline_config_dir`` (sem materializar configs A7.1
    em disco — esses fluem via ``WorkspaceContext.config_overrides`` no worker).
    Pos-A7.5: ``institutions.json`` global foi removido — marker passou a usar
    ``pipeline.json`` (preservado em ``config/``).
    """
    tenant_root = Path(tenant_root).resolve()
    marker = tenant_root / "config" / "pipeline.json"
    if marker.is_file():
        return tenant_root / "config"

    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as db:
        return prepare_pipeline_config_dir(workspace_id, tenant_root, db)
