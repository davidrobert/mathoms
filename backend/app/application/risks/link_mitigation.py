"""Use case: associa uma Decision como mitigação do Risk e remove o link.

Validação:
    - Risk deve existir no workspace.
    - Decision com ``decision_id`` deve existir no mesmo workspace
      (cross-tenant é bloqueado pela validação explícita).
    - Idempotente: link já presente não é duplicado.

Não emite evento (ADR-178 §"Trade-offs": v1 sem event-sourcing). Cliente
auditará via ``updated_at`` se precisar.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.application.risks._protocols import RiskRepositoryProtocol
from backend.app.schemas.dto.risk import (
    RiskMitigationLinkCommand,
    RiskResponse,
    risk_to_response,
)


async def link_mitigation(
    cmd: RiskMitigationLinkCommand,
    *,
    workspace_id: str,
    risk_id: str,
    risk_repo: RiskRepositoryProtocol,
    decision_repo: DecisionRepositoryProtocol,
) -> RiskResponse:
    """Adiciona ``cmd.decision_id`` em ``mitigations_decision_ids`` (idempotente)."""
    risk = await risk_repo.get_by_id(workspace_id, risk_id)
    if risk is None:
        raise NotFoundError(f"Risk id={risk_id} não encontrado", code="risk_not_found")

    decision = await decision_repo.get_by_id(workspace_id, cmd.decision_id)
    if decision is None:
        raise ValidationError(
            f"Decision id={cmd.decision_id} não encontrada no workspace",
            code="invalid_decision",
        )

    current = list(risk.mitigations_decision_ids or [])
    if cmd.decision_id not in current:
        current.append(cmd.decision_id)
        risk.mitigations_decision_ids = current
        risk.updated_at = datetime.now(timezone.utc)
        await risk_repo.add(risk)
    return risk_to_response(risk)


async def unlink_mitigation(
    *,
    workspace_id: str,
    risk_id: str,
    decision_id: str,
    risk_repo: RiskRepositoryProtocol,
) -> RiskResponse:
    """Remove ``decision_id`` de ``mitigations_decision_ids`` (idempotente)."""
    risk = await risk_repo.get_by_id(workspace_id, risk_id)
    if risk is None:
        raise NotFoundError(f"Risk id={risk_id} não encontrado", code="risk_not_found")

    current = list(risk.mitigations_decision_ids or [])
    if decision_id in current:
        current.remove(decision_id)
        risk.mitigations_decision_ids = current
        risk.updated_at = datetime.now(timezone.utc)
        await risk_repo.add(risk)
    return risk_to_response(risk)
