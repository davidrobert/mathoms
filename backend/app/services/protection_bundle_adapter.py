"""Adapter ``ProtectionBundle`` (ADR-192 §D3) — boundary DB↔TypedDict↔Pydantic; delega populator a ``protection_bundle_populator`` (SRP)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from backend.app.models.family_member import FamilyMember
from backend.app.models.protection import Protection
from backend.app.models.workspace import Workspace
from backend.app.services.protection_bundle_populator import populate_protection_bundle
from pipeline.domain.protection_bundle import ProtectionBundle, ProtectionItem

_PROTECTION_BUNDLE_VERSION: int = 2  # bump T03 — populator real


def _protection_to_bundle_item(protection: Protection) -> ProtectionItem:
    return {
        "id": protection.id,
        "category": protection.category,
        "holder_family_member_id": protection.holder_family_member_id,
        "insurer": protection.insurer,
        "coverage_brl_cents": protection.coverage_brl_cents,
        "premium_monthly_brl_cents": protection.premium_monthly_brl_cents,
        "coverage_type": protection.coverage_type,
        "starts_at": protection.starts_at.isoformat() if protection.starts_at else "",
        "ends_at": protection.ends_at.isoformat() if protection.ends_at else None,
        "status": protection.status,
    }


def _protections_active_stmt(workspace_id: str):
    """Statement compartilhado entre vias sync/async."""
    return (
        select(Protection)
        .where(
            Protection.workspace_id == workspace_id,
            Protection.status == "Ativa",
        )
        .order_by(
            Protection.category.asc(),
            Protection.ends_at.is_(None).asc(),
            Protection.ends_at.asc(),
        )
    )


def _family_members_stmt(workspace_id: str):
    return select(FamilyMember).where(FamilyMember.workspace_id == workspace_id)


def _workspace_stmt(workspace_id: str):
    return select(Workspace).where(Workspace.id == workspace_id)


def _project_protection_bundle_sync(workspace_id: str, *, db: SyncSession) -> ProtectionBundle:
    """Sync — usado por workers/pipeline."""
    protections = list(db.execute(_protections_active_stmt(workspace_id)).scalars().all())
    items = [_protection_to_bundle_item(p) for p in protections]
    members = list(db.execute(_family_members_stmt(workspace_id)).scalars().all())
    workspace = db.execute(_workspace_stmt(workspace_id)).scalar_one_or_none()
    return populate_protection_bundle(
        items=items,
        members=members,
        workspace=workspace,
        today=date.today(),
        adapter_version=_PROTECTION_BUNDLE_VERSION,
    )


async def _project_protection_bundle_async(
    workspace_id: str, *, db: AsyncSession
) -> ProtectionBundle:
    """Async — usado por endpoints HTTP."""
    result = await db.execute(_protections_active_stmt(workspace_id))
    items = [_protection_to_bundle_item(p) for p in result.scalars().all()]
    members_result = await db.execute(_family_members_stmt(workspace_id))
    members = list(members_result.scalars().all())
    ws_result = await db.execute(_workspace_stmt(workspace_id))
    workspace = ws_result.scalar_one_or_none()
    return populate_protection_bundle(
        items=items,
        members=members,
        workspace=workspace,
        today=date.today(),
        adapter_version=_PROTECTION_BUNDLE_VERSION,
    )


def build_protection_bundle_sync(workspace_id: str, *, db: SyncSession) -> ProtectionBundle:
    """Reconstrói o ``ProtectionBundle`` (sync, ADR-192)."""
    return _project_protection_bundle_sync(workspace_id, db=db)


async def build_protection_bundle(workspace_id: str, *, db: AsyncSession):
    """Async para endpoint HTTP — retorna Pydantic ``ProtectionBundleResponse``."""
    bundle = await _project_protection_bundle_async(workspace_id, db=db)
    return _bundle_to_response(bundle)


def _cents_to_decimal(value):
    if value is None:
        return None
    return (Decimal(value) / Decimal(100)).quantize(Decimal("0.01"))


def _policies_to_response(bundle: ProtectionBundle):
    from backend.app.schemas.dto.protection.bundle import ProtectionItemResponse

    return [
        ProtectionItemResponse(
            id=item["id"],
            category=item["category"],
            holder_family_member_id=item.get("holder_family_member_id"),
            insurer=item.get("insurer"),
            coverage_brl=_cents_to_decimal(item["coverage_brl_cents"]) or Decimal("0.00"),
            premium_monthly_brl=_cents_to_decimal(item.get("premium_monthly_brl_cents")),
            coverage_type=item.get("coverage_type"),
            starts_at=item["starts_at"],
            ends_at=item.get("ends_at"),
            status=item["status"],
        )
        for item in bundle.get("policies", [])
    ]


def _gap_analysis_to_response(bundle: ProtectionBundle):
    from backend.app.schemas.dto.protection.bundle import ProtectionGapItemResponse

    raw = bundle.get("gap_analysis", {}) or {}
    return {
        key: ProtectionGapItemResponse(
            ideal_brl=_cents_to_decimal(value.get("ideal_brl_cents")),
            actual_brl=_cents_to_decimal(value.get("actual_brl_cents")) or Decimal("0.00"),
            gap_brl=_cents_to_decimal(value.get("gap_brl_cents")),
            methodology=value.get("methodology"),
        )
        for key, value in raw.items()
    }


def _recommendations_to_response(bundle: ProtectionBundle):
    from backend.app.schemas.dto.protection.bundle import ProtectionRecommendationResponse

    return [
        ProtectionRecommendationResponse(
            category=rec["category"],
            rationale=rec["rationale"],
            priority=rec.get("priority", "média"),
        )
        for rec in bundle.get("recommendations", [])
    ]


def _auto_inferred_to_response(bundle: ProtectionBundle):
    from backend.app.schemas.dto.protection.bundle import RiskInferredResponse

    return [
        RiskInferredResponse(
            category=item["category"],
            name=item["name"],
            rationale=item["rationale"],
            estimated_impact_brl=_cents_to_decimal(item.get("estimated_impact_brl_cents")),
            source_calculator=item["source_calculator"],
        )
        for item in bundle.get("auto_inferred_risks", [])
    ]


def _bundle_to_response(bundle: ProtectionBundle):
    """TypedDict → Pydantic DTO."""
    from backend.app.schemas.dto.protection.bundle import (
        ProtectionBundleResponse,
        ProtectionThresholdsResponse,
    )

    thresholds_raw = bundle.get("methodology_thresholds", {}) or {}
    return ProtectionBundleResponse(
        policies=_policies_to_response(bundle),
        gap_analysis=_gap_analysis_to_response(bundle),
        recommendations=_recommendations_to_response(bundle),
        auto_inferred_risks=_auto_inferred_to_response(bundle),
        methodology_thresholds=ProtectionThresholdsResponse(**thresholds_raw),
        has_us_exposure=bundle.get("has_us_exposure", False),
        adapter_version=bundle.get("_adapter_version", _PROTECTION_BUNDLE_VERSION),
    )


__all__ = [
    "build_protection_bundle",
    "build_protection_bundle_sync",
]
