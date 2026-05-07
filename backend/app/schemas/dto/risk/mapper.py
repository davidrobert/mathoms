"""Mappers DB ↔ DTO do aggregate ``Risk`` (ADR-178).

Money: cents (BIGINT) ↔ Decimal BRL no wire. Centralizar aqui evita que
cada endpoint duplique a conversão.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from backend.app.models.risk import Risk
from backend.app.schemas.dto.risk.response import RiskResponse


def cents_to_brl(cents: Optional[int]) -> Optional[Decimal]:
    """``None`` cents → ``None`` BRL. Senão, ``Decimal(cents) / 100``."""
    if cents is None:
        return None
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def brl_to_cents(brl: Optional[Decimal]) -> Optional[int]:
    """``None`` brl → ``None`` cents. Senão, ``int(round(brl * 100))``."""
    if brl is None:
        return None
    return int((Decimal(brl) * Decimal(100)).quantize(Decimal("1")))


def risk_to_response(risk: Risk) -> RiskResponse:
    """Risk row → DTO. Converte cents → Decimal BRL no wire."""
    return RiskResponse(
        id=risk.id,
        workspace_id=risk.workspace_id,
        code=risk.code,
        name=risk.name,
        rationale=risk.rationale,
        probability=risk.probability,
        impact_level=risk.impact_level,
        impact_brl=cents_to_brl(risk.impact_brl_cents),
        status=risk.status,
        mitigations_decision_ids=list(risk.mitigations_decision_ids or []),
        created_at=risk.created_at,
        updated_at=risk.updated_at,
    )
