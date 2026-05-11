"""Mappers DB ↔ DTO do aggregate `Protection` (ADR-192)."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from backend.app.models.protection import Protection
from backend.app.schemas.dto.protection.bundle import ProtectionItemResponse
from backend.app.schemas.dto.protection.response import ProtectionResponse
from backend.app.services.protection_pii import decrypt_policy_ref


def cents_to_brl(cents: Optional[int] = None) -> Optional[Decimal]:
    if cents is None:
        return None
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def brl_to_cents(brl: Optional[Decimal] = None) -> Optional[int]:
    if brl is None:
        return None
    return int((Decimal(brl) * Decimal(100)).quantize(Decimal("1")))


def _mask_policy_ref(policy_ref: Optional[str] = None) -> Optional[str]:
    """Decifra Fernet + mascara para `****<últimos 4>`; falha → ciphertext bruto."""
    if policy_ref is None:
        return None
    plaintext = decrypt_policy_ref(policy_ref) or policy_ref
    if len(plaintext) <= 4:
        return "****"
    return f"****{plaintext[-4:]}"


def protection_to_response(protection: Protection) -> ProtectionResponse:
    """Protection row → DTO. Converte cents → Decimal BRL no wire."""
    coverage = cents_to_brl(protection.coverage_brl_cents)
    if coverage is None:  # pragma: no cover — coverage_brl_cents é NOT NULL
        coverage = Decimal("0.00")
    return ProtectionResponse(
        id=protection.id,
        workspace_id=protection.workspace_id,
        category=protection.category,
        holder_family_member_id=protection.holder_family_member_id,
        insurer=protection.insurer,
        policy_ref_masked=_mask_policy_ref(protection.policy_ref),
        coverage_brl=coverage,
        premium_monthly_brl=cents_to_brl(protection.premium_monthly_brl_cents),
        coverage_type=protection.coverage_type,
        starts_at=protection.starts_at,
        ends_at=protection.ends_at,
        status=protection.status,
        notes=protection.notes,
        created_at=protection.created_at,
        updated_at=protection.updated_at,
    )


def protection_to_bundle_item(protection: Protection) -> ProtectionItemResponse:
    """Protection row → bundle item (sem PII de policy_ref)."""
    coverage = cents_to_brl(protection.coverage_brl_cents)
    if coverage is None:  # pragma: no cover
        coverage = Decimal("0.00")
    return ProtectionItemResponse(
        id=protection.id,
        category=protection.category,
        holder_family_member_id=protection.holder_family_member_id,
        insurer=protection.insurer,
        coverage_brl=coverage,
        premium_monthly_brl=cents_to_brl(protection.premium_monthly_brl_cents),
        coverage_type=protection.coverage_type,
        starts_at=protection.starts_at,
        ends_at=protection.ends_at,
        status=protection.status,
    )
