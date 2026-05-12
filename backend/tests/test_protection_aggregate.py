"""Testes do aggregate `Protection` (ADR-192 · Sprint A11.W5) — valores fictícios."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    PreconditionFailedError,
    ValidationError,
)
from backend.app.application.protections import (
    cancel_protection,
    create_protection,
    get_protection,
    link_to_risk,
    list_protections,
    unlink_from_risk,
    update_protection,
)
from backend.app.application.risks import create_risk
from backend.app.models.protection import VALID_PROTECTION_CATEGORIES
from backend.app.repositories.protection_repository import ProtectionRepository
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.schemas.dto.protection import (
    ProtectionCancelCommand,
    ProtectionCreateCommand,
    ProtectionLinkToRiskCommand,
    ProtectionUpdateCommand,
)
from backend.app.schemas.dto.risk import RiskCreateCommand
from backend.app.services.protection_pii import mask_coverage_bucket
from backend.tests.factories.builders import make_workspace

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def setup(db: AsyncSession):
    ws = await make_workspace(db, name="WS Protection Test")
    await db.commit()
    return ws, ProtectionRepository(db), RiskRepository(db)


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession):
    ws_a = await make_workspace(db, name="WS Protection A")
    ws_b = await make_workspace(db, name="WS Protection B")
    await db.commit()
    return ws_a, ws_b, ProtectionRepository(db)


def _new_create_cmd(**overrides) -> ProtectionCreateCommand:
    base = {
        "category": "vida",
        "coverage_brl": Decimal("1000000.00"),
        "starts_at": date(2026, 1, 1),
    }
    base.update(overrides)
    return ProtectionCreateCommand(**base)


async def _seed_protection_and_risk(
    ws, prot_repo, risk_repo, db, *, code: str, impact: str = "alto"
):
    protection = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=prot_repo)
    risk = await create_risk(
        RiskCreateCommand(
            code=code,
            name="Risco fictício",
            rationale="Risco fictício para teste de link.",
            impact_level=impact,
        ),
        workspace_id=ws.id,
        repo=risk_repo,
    )
    await db.commit()
    return protection, risk


# ---------------------------------------------------------------------------
# create + get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_protection_persists_defaults(db, setup):
    ws, repo, _ = setup
    resp = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    assert resp.category == "vida"
    assert resp.status == "Ativa"
    assert resp.coverage_brl == Decimal("1000000.00")
    assert resp.premium_monthly_brl is None
    assert resp.ends_at is None
    assert resp.policy_ref_masked is None


@pytest.mark.asyncio
async def test_create_protection_with_full_payload(db, setup):
    ws, repo, _ = setup
    resp = await create_protection(
        _new_create_cmd(
            category="patrimonial",
            insurer="Seguradora Fictícia S/A",
            policy_ref="POL-FAKE-998877",
            premium_monthly_brl=Decimal("250.00"),
            coverage_type="whole",
            ends_at=date(2030, 12, 31),
            notes="apólice fictícia",
        ),
        workspace_id=ws.id,
        repo=repo,
    )
    await db.commit()

    assert resp.category == "patrimonial"
    assert resp.insurer == "Seguradora Fictícia S/A"
    assert resp.coverage_type == "whole"
    assert resp.ends_at == date(2030, 12, 31)
    assert resp.policy_ref_masked == "****8877"


@pytest.mark.asyncio
async def test_create_protection_invalid_category(db, setup):
    ws, repo, _ = setup
    with pytest.raises(Exception):
        ProtectionCreateCommand(
            category="invalid_xyz",
            coverage_brl=Decimal("1000.00"),
            starts_at=date(2026, 1, 1),
        )
    # Garantir que o frozenset não ficou vazio.
    assert len(VALID_PROTECTION_CATEGORIES) == 6


@pytest.mark.asyncio
async def test_create_protection_ends_before_starts_raises(db, setup):
    ws, repo, _ = setup
    cmd = _new_create_cmd(
        starts_at=date(2026, 6, 1),
        ends_at=date(2026, 1, 1),
    )
    with pytest.raises(ValidationError):
        await create_protection(cmd, workspace_id=ws.id, repo=repo)


@pytest.mark.asyncio
async def test_create_protection_invalid_insurer_raises(db, setup):
    ws, repo, _ = setup
    with pytest.raises(Exception):
        ProtectionCreateCommand(
            category="vida",
            coverage_brl=Decimal("1000.00"),
            starts_at=date(2026, 1, 1),
            insurer="http://evil.example.com/exec",
        )


@pytest.mark.asyncio
async def test_get_protection_returns_persisted(db, setup):
    ws, repo, _ = setup
    created = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    fetched = await get_protection(ws.id, created.id, repo=repo)
    assert fetched.id == created.id
    assert fetched.category == "vida"


@pytest.mark.asyncio
async def test_get_protection_404_for_nonexistent(db, setup):
    ws, repo, _ = setup
    with pytest.raises(NotFoundError):
        await get_protection(ws.id, "missing-id", repo=repo)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_protections_empty(db, setup):
    ws, repo, _ = setup
    response = await list_protections(ws.id, repo=repo)
    assert response.total == 0
    assert response.protections == []


@pytest.mark.asyncio
async def test_list_protections_orders_by_category(db, setup):
    ws, repo, _ = setup
    await create_protection(_new_create_cmd(category="vida"), workspace_id=ws.id, repo=repo)
    await create_protection(_new_create_cmd(category="invalidez"), workspace_id=ws.id, repo=repo)
    await create_protection(_new_create_cmd(category="patrimonial"), workspace_id=ws.id, repo=repo)
    await db.commit()

    response = await list_protections(ws.id, repo=repo)
    categories = [p.category for p in response.protections]
    assert categories == sorted(categories)  # alfabético


# ---------------------------------------------------------------------------
# update + cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_protection_changes_coverage(db, setup):
    ws, repo, _ = setup
    created = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    response = await update_protection(
        ProtectionUpdateCommand(coverage_brl=Decimal("2500000.00")),
        workspace_id=ws.id,
        protection_id=created.id,
        repo=repo,
    )
    await db.commit()
    assert response.coverage_brl == Decimal("2500000.00")


@pytest.mark.asyncio
async def test_update_protection_404(db, setup):
    ws, repo, _ = setup
    with pytest.raises(NotFoundError):
        await update_protection(
            ProtectionUpdateCommand(coverage_brl=Decimal("100.00")),
            workspace_id=ws.id,
            protection_id="missing",
            repo=repo,
        )


@pytest.mark.asyncio
async def test_update_protection_invalid_period_raises(db, setup):
    ws, repo, _ = setup
    created = await create_protection(
        _new_create_cmd(starts_at=date(2026, 1, 1), ends_at=date(2027, 1, 1)),
        workspace_id=ws.id,
        repo=repo,
    )
    await db.commit()
    with pytest.raises(ValidationError):
        await update_protection(
            ProtectionUpdateCommand(ends_at=date(2025, 1, 1)),
            workspace_id=ws.id,
            protection_id=created.id,
            repo=repo,
        )


@pytest.mark.asyncio
async def test_cancel_protection_sets_status(db, setup):
    ws, repo, _ = setup
    created = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    response = await cancel_protection(
        ProtectionCancelCommand(reason="cliente migrou de seguradora"),
        workspace_id=ws.id,
        protection_id=created.id,
        repo=repo,
    )
    await db.commit()
    assert response.status == "Cancelada"
    assert "Cancelamento: cliente migrou de seguradora" in (response.notes or "")


@pytest.mark.asyncio
async def test_cancel_already_cancelled_raises(db, setup):
    ws, repo, _ = setup
    created = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()
    await cancel_protection(
        ProtectionCancelCommand(),
        workspace_id=ws.id,
        protection_id=created.id,
        repo=repo,
    )
    await db.commit()

    with pytest.raises(PreconditionFailedError):
        await cancel_protection(
            ProtectionCancelCommand(),
            workspace_id=ws.id,
            protection_id=created.id,
            repo=repo,
        )


# ---------------------------------------------------------------------------
# link_to_risk / unlink_from_risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_to_risk_adds_protection_id(db, setup):
    ws, prot_repo, risk_repo = setup
    protection, risk = await _seed_protection_and_risk(
        ws, prot_repo, risk_repo, db, code="morte_provedor", impact="crítico"
    )
    await link_to_risk(
        ProtectionLinkToRiskCommand(risk_id=risk.id),
        workspace_id=ws.id,
        protection_id=protection.id,
        repo=prot_repo,
        risk_repo=risk_repo,
    )
    await db.commit()
    risk_row = await risk_repo.get_by_id(ws.id, risk.id)
    assert risk_row.mitigation_protection_ids == [protection.id]


@pytest.mark.asyncio
async def test_link_to_risk_duplicate_raises_conflict(db, setup):
    ws, prot_repo, risk_repo = setup
    protection, risk = await _seed_protection_and_risk(
        ws, prot_repo, risk_repo, db, code="duplicate_link"
    )
    cmd = ProtectionLinkToRiskCommand(risk_id=risk.id)
    await link_to_risk(
        cmd, workspace_id=ws.id, protection_id=protection.id, repo=prot_repo, risk_repo=risk_repo
    )
    await db.commit()
    with pytest.raises(ConflictError):
        await link_to_risk(
            cmd,
            workspace_id=ws.id,
            protection_id=protection.id,
            repo=prot_repo,
            risk_repo=risk_repo,
        )


@pytest.mark.asyncio
async def test_unlink_from_risk_removes_id(db, setup):
    ws, prot_repo, risk_repo = setup
    protection, risk = await _seed_protection_and_risk(
        ws, prot_repo, risk_repo, db, code="unlink_test", impact="médio"
    )

    await link_to_risk(
        ProtectionLinkToRiskCommand(risk_id=risk.id),
        workspace_id=ws.id,
        protection_id=protection.id,
        repo=prot_repo,
        risk_repo=risk_repo,
    )
    await db.commit()
    await unlink_from_risk(
        workspace_id=ws.id,
        protection_id=protection.id,
        risk_id=risk.id,
        repo=prot_repo,
        risk_repo=risk_repo,
    )
    await db.commit()

    risk_row = await risk_repo.get_by_id(ws.id, risk.id)
    assert not risk_row.mitigation_protection_ids


@pytest.mark.asyncio
async def test_unlink_from_risk_404_when_not_linked(db, setup):
    ws, prot_repo, risk_repo = setup
    protection = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=prot_repo)
    risk = await create_risk(
        RiskCreateCommand(
            code="never_linked",
            name="Risco fictício",
            rationale="Teste do unlink em ausência de link.",
            impact_level="baixo",
        ),
        workspace_id=ws.id,
        repo=risk_repo,
    )
    await db.commit()
    with pytest.raises(NotFoundError):
        await unlink_from_risk(
            workspace_id=ws.id,
            protection_id=protection.id,
            risk_id=risk.id,
            repo=prot_repo,
            risk_repo=risk_repo,
        )


# ---------------------------------------------------------------------------
# Tenancy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_protection_isolated_per_workspace(db, two_workspaces):
    ws_a, ws_b, repo = two_workspaces
    await create_protection(_new_create_cmd(), workspace_id=ws_a.id, repo=repo)
    await db.commit()

    response = await list_protections(ws_b.id, repo=repo)
    assert response.total == 0


@pytest.mark.asyncio
async def test_protection_cross_tenant_404(db, two_workspaces):
    ws_a, ws_b, repo = two_workspaces
    created = await create_protection(_new_create_cmd(), workspace_id=ws_a.id, repo=repo)
    await db.commit()

    with pytest.raises(NotFoundError):
        await get_protection(ws_b.id, created.id, repo=repo)


# ---------------------------------------------------------------------------
# Bundle skeleton (T02) + PII helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bundle_skeleton_returns_empty_lists_when_no_policies(db, setup):
    from backend.app.services.protection_bundle_adapter import (
        _project_protection_bundle_async,
    )

    ws, _, _ = setup
    bundle = await _project_protection_bundle_async(ws.id, db=db)
    assert bundle["policies"] == []
    assert bundle["gap_analysis"] == {}
    assert bundle["recommendations"] == []
    assert bundle["auto_inferred_risks"] == []
    assert bundle["has_us_exposure"] is False
    # T03 (ADR-192 §D3) bumpou adapter_version → 2 ao popular calculators.
    # methodology_thresholds passa a vir preenchido com defaults.
    assert bundle["_adapter_version"] == 2
    assert bundle["methodology_thresholds"]["fbar_threshold_usd"] == 10_000


@pytest.mark.asyncio
async def test_bundle_only_lists_active_policies(db, setup):
    from backend.app.services.protection_bundle_adapter import (
        _project_protection_bundle_async,
    )

    ws, repo, _ = setup
    active = await create_protection(_new_create_cmd(), workspace_id=ws.id, repo=repo)
    cancelled = await create_protection(
        _new_create_cmd(category="invalidez"), workspace_id=ws.id, repo=repo
    )
    await db.commit()
    await cancel_protection(
        ProtectionCancelCommand(),
        workspace_id=ws.id,
        protection_id=cancelled.id,
        repo=repo,
    )
    await db.commit()

    bundle = await _project_protection_bundle_async(ws.id, db=db)
    assert len(bundle["policies"]) == 1
    assert bundle["policies"][0]["id"] == active.id
    assert bundle["policies"][0]["status"] == "Ativa"


def test_coverage_bucket_mapping():
    assert mask_coverage_bucket(None) == 0
    assert mask_coverage_bucket(0) == 0
    assert mask_coverage_bucket(50_000_00) == 0  # < R$ 100k
    assert mask_coverage_bucket(500_000_00) == 1  # R$ 100k-1M
    assert mask_coverage_bucket(2_000_000_00) == 2  # R$ 1-5M
    assert mask_coverage_bucket(7_000_000_00) == 3  # R$ 5-10M
    assert mask_coverage_bucket(20_000_000_00) == 4  # R$ 10-50M
    assert mask_coverage_bucket(100_000_000_00) == 5  # R$ 50M+


def test_policy_ref_masked_format():
    from backend.app.schemas.dto.protection.mapper import _mask_policy_ref

    assert _mask_policy_ref(None) is None
    assert _mask_policy_ref("AB") == "****"
    assert _mask_policy_ref("POLICY-12345678") == "****5678"


def test_logging_redacts_policy_ref():
    from backend.app.core.logging import _redact

    redacted = _redact({"policy_ref": "POLICY-12345678", "category": "vida"})
    assert redacted["policy_ref"] == "***"
    assert redacted["category"] == "vida"


def test_logging_redacts_coverage_brl():
    from backend.app.core.logging import _redact

    redacted = _redact({"coverage_brl": "1000000.00", "coverage_bucket": 2})
    assert redacted["coverage_brl"] == "***"
    assert redacted["coverage_bucket"] == 2


# ---------------------------------------------------------------------------
# Bundle populator (T03) — calculators acopla pelo adapter
# ---------------------------------------------------------------------------


async def _add_titular_with_us_status(db, ws, us_tax_status: str):
    from backend.app.models.family_member import FamilyMember

    db.add(
        FamilyMember(
            workspace_id=ws.id,
            key="titular",
            full_name="Titular Teste",
            short_name="T.",
            role="titular",
            us_tax_status=us_tax_status,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_bundle_t03_us_exposure_from_family_member_us_tax_status(db, setup):
    """ADR-192 §D4: ``has_us_exposure`` deriva de ``family_members.us_tax_status``."""
    from backend.app.services.protection_bundle_adapter import _project_protection_bundle_async

    ws, _, _ = setup
    await _add_titular_with_us_status(db, ws, "citizen")
    bundle = await _project_protection_bundle_async(ws.id, db=db)
    assert bundle["has_us_exposure"] is True
    fbar = [r for r in bundle["auto_inferred_risks"] if r.get("name") == "compliance_us_fbar"]
    assert len(fbar) == 1
    assert fbar[0]["source_calculator"] == "compliance_risk_us_person"


@pytest.mark.asyncio
async def test_bundle_t03_whitelist_invariant_apenas_4_calculators(db, setup):
    """ADR-192 §D3: somente calculators whitelisted podem emitir RiskInferred."""
    from backend.app.services.protection_bundle_adapter import _project_protection_bundle_async
    from pipeline.domain.services.protection.risk_inferred import SOURCE_CALCULATORS_WHITELIST

    ws, _, _ = setup
    await _add_titular_with_us_status(db, ws, "resident")
    bundle = await _project_protection_bundle_async(ws.id, db=db)
    for risk in bundle["auto_inferred_risks"]:
        assert risk["source_calculator"] in SOURCE_CALCULATORS_WHITELIST


@pytest.mark.asyncio
async def test_bundle_t03_thresholds_populados(db, setup):
    """T03: bundle expõe thresholds default de ``fiscal_parameters``."""
    from backend.app.services.protection_bundle_adapter import (
        _project_protection_bundle_async,
    )

    ws, _, _ = setup
    bundle = await _project_protection_bundle_async(ws.id, db=db)
    thresholds = bundle["methodology_thresholds"]
    assert thresholds["fbar_threshold_usd"] == 10_000
    assert thresholds["estate_tax_threshold_usd"] == 60_000
    assert thresholds["life_insurance_multiple_renda_anual"] == 10.0
