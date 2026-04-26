"""ConfigMaterializer — copies global config to tenant dir, overrides with DB edits.

Called before each pipeline run. Scripts read from disk via _init_config() — zero changes needed.

Flow:
  1. Copy config/ global → storage/{workspace_id}/config/ (full tree)
  2. For each config edited in DB → serialize to pipeline-compatible JSON → overwrite in tenant config/
  3. For YAML configs (report_layout) → write as YAML to preserve compatibility
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.models.category import Category, CategoryKeyword
from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
    TransferConfig,
)
from backend.app.models.family_member import BankAccount, FamilyMember
from backend.app.models.llm_config import LLMConfig
from backend.app.models.workspace import Workspace
from backend.app.services.vault import get_vault

_vault = get_vault()


def materialize_config(workspace_id: str, tenant_root: Path, db: Session) -> Path:
    """Materialize configs from DB to disk for the pipeline to read.

    Returns the tenant config dir path.
    """
    tenant_config = tenant_root / "config"
    global_config = _global_config_dir()

    _copy_global(global_config, tenant_config)
    _override_family_members(workspace_id, tenant_config, db)
    _override_categorization(workspace_id, tenant_config, db)
    _override_pipeline(workspace_id, tenant_config, db)
    _override_institutions(workspace_id, tenant_config, db)
    _override_report_layout(workspace_id, tenant_config, db)
    _override_llm_config(workspace_id, tenant_config, db)
    _override_transfer_config(workspace_id, tenant_config, db)

    return tenant_config


def _global_config_dir() -> Path:
    return settings.PIPELINE_ROOT / "config"


def _copy_global(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


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
# Override helpers — write serialized data to tenant config dir
# =============================================================================


def _override_family_members(workspace_id: str, config_dir: Path, db: Session) -> None:
    data = serialize_family_members(workspace_id, db)
    if data is not None:
        _write_json(config_dir / "family_members.json", data)


def _resolve_transfer_block(workspace_id: str, db: Session) -> dict[str, Any] | None:
    """DB → global fallback. ``None`` se não há bloco em nenhum lugar."""
    data = serialize_transfer_config(workspace_id, db)
    if data is not None:
        return data
    global_family_path = _global_config_dir() / "family_members.json"
    if not global_family_path.is_file():
        return None
    global_doc = json.loads(global_family_path.read_text(encoding="utf-8"))
    return global_doc.get("transferencias_internas")


def _override_transfer_config(workspace_id: str, config_dir: Path, db: Session) -> None:
    """Overlay ``transferencias_internas`` em ``family_members.json`` (ADR-133)."""
    data = _resolve_transfer_block(workspace_id, db)
    if data is None:
        return
    family_path = config_dir / "family_members.json"
    family_doc: dict[str, Any] = {}
    if family_path.is_file():
        family_doc = json.loads(family_path.read_text(encoding="utf-8"))
    family_doc["transferencias_internas"] = data
    _write_json(family_path, family_doc)


def _override_categorization(workspace_id: str, config_dir: Path, db: Session) -> None:
    data = serialize_categorization(workspace_id, db)
    if data is not None:
        _write_json(config_dir / "categorization.json", data)


def _override_pipeline(workspace_id: str, config_dir: Path, db: Session) -> None:
    data = serialize_pipeline_config(workspace_id, db)
    if data is not None:
        _write_json(config_dir / "pipeline.json", data)


def _override_institutions(workspace_id: str, config_dir: Path, db: Session) -> None:
    data = serialize_institution_config(workspace_id, db)
    if data is not None:
        _write_json(config_dir / "institutions.json", data)


def _override_report_layout(workspace_id: str, config_dir: Path, db: Session) -> None:
    data = serialize_report_layout(workspace_id, db)
    if data is not None:
        _write_yaml(config_dir / "report_layout.yaml", data)


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
    """
    tenant_root = Path(tenant_root).resolve()
    marker = tenant_root / "config" / "institutions.json"
    if marker.is_file():
        return tenant_root / "config"

    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as db:
        return materialize_config(workspace_id, tenant_root, db)
