"""Use case: aceita Suggestion → cria Decision + transição de status (ADR-153).

Operação atômica em uma transaction:
    1. Carrega suggestion (validação tenancy + status pendente)
    2. (ADR-163) Lê `context_snapshot` do relatório-fonte da Suggestion
       para congelar KPIs no momento da aceitação.
    3. Cria Decision via use case ``create_decision`` (ADR-136 — emite
       DecisionEvent ``Created`` com payload incluindo
       ``derived_from_suggestion_id`` para rastreabilidade) já com
       ``context_snapshot`` populado.
    4. Atualiza suggestion: status='Aceita', accepted_decision_id=<novo>,
       accepted_at=now
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.decisions import create_decision
from backend.app.application.decisions._protocols import (
    DecisionRepositoryProtocol,
)
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.models.decision import DecisionEvent
from backend.app.models.suggestion import Suggestion
from backend.app.schemas.dto.decision import DecisionCreateCommand
from backend.app.schemas.dto.decision.mapper import cents_to_brl
from backend.app.schemas.dto.suggestion import (
    AcceptSuggestionCommand,
    SuggestionResponse,
    suggestion_to_response,
)
from backend.app.services.security.crypto import read_artifact_content


async def accept_suggestion(
    cmd: AcceptSuggestionCommand,
    *,
    workspace_id: str,
    suggestion_id: str,
    suggestion_repo: SuggestionRepositoryProtocol,
    decision_repo: DecisionRepositoryProtocol,
    actor: str,
    db: AsyncSession | None = None,
) -> SuggestionResponse:
    suggestion = await _load_pending(workspace_id, suggestion_id, suggestion_repo)
    snapshot = await _build_context_snapshot(suggestion, db=db)
    decision = await _create_decision_from(
        suggestion,
        cmd=cmd,
        amount_brl=cents_to_brl(suggestion.amount_brl_cents),
        decision_repo=decision_repo,
        actor=actor,
        workspace_id=workspace_id,
        modified_title=None,
        modified_rationale=None,
        context_snapshot=snapshot,
    )
    _apply_acceptance(suggestion, decision_id=decision.id, target_status="Aceita")
    await suggestion_repo.add(suggestion)
    response = suggestion_to_response(suggestion)
    response.accepted_decision_code = decision.code  # ADR-214 — toast UX
    return response


async def _load_pending(
    workspace_id: str,
    suggestion_id: str,
    repo: SuggestionRepositoryProtocol,
) -> Suggestion:
    suggestion = await repo.get_by_id(workspace_id, suggestion_id)
    if suggestion is None:
        raise NotFoundError(
            f"Suggestion id={suggestion_id} não encontrada no workspace",
            code="suggestion_not_found",
        )
    if suggestion.status != "Pendente":
        raise ConflictError(
            f"Suggestion id={suggestion_id} já está em status={suggestion.status!r}; "
            f"transição só é permitida de Pendente",
            code="suggestion_not_pending",
        )
    return suggestion


async def _create_decision_from(
    suggestion: Suggestion,
    *,
    cmd: AcceptSuggestionCommand,
    amount_brl: Decimal | None,
    decision_repo: DecisionRepositoryProtocol,
    actor: str,
    workspace_id: str,
    modified_title: str | None,
    modified_rationale: str | None,
    context_snapshot: dict[str, Any] | None = None,
):
    """Cria Decision via use case canônico (ADR-136). Emite event extra
    com ``derived_from_suggestion_id`` para rastreabilidade. ADR-163 —
    propaga `context_snapshot` para Decision."""
    title = modified_title if modified_title is not None else suggestion.title
    rationale = modified_rationale if modified_rationale is not None else suggestion.rationale
    # ADR-214 — code é server-generated dentro de create_decision (omit aqui).
    decision_response = await create_decision(
        DecisionCreateCommand(
            title=title,
            rationale=rationale,
            amount_brl=amount_brl,
            status="Pendente",
            context_snapshot=context_snapshot,
        ),
        workspace_id=workspace_id,
        repo=decision_repo,
        actor=actor,
    )
    # Evento extra registra a origem na Suggestion (rastreabilidade ADR-153).
    derivation_event = DecisionEvent(
        decision_id=decision_response.id,
        event_type="Updated",
        actor=actor,
        payload={
            "derivation": {
                "suggestion_id": suggestion.id,
                "kind": suggestion.kind,
                "section_id": suggestion.section_id,
                "report_id": suggestion.report_id,
                "modified": modified_title is not None or modified_rationale is not None,
                "note": cmd.note,
            }
        },
    )
    await decision_repo.add_event(derivation_event)
    return decision_response


def _apply_acceptance(
    suggestion: Suggestion,
    *,
    decision_id: str,
    target_status: str,
) -> None:
    suggestion.status = target_status
    suggestion.accepted_decision_id = decision_id
    suggestion.accepted_at = datetime.now(timezone.utc)


_SNAPSHOT_KPI_PATHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("patrimonio_brl", ("patrimonio", "liquido")),
    ("if_progress_pct", ("goals", "progresso_if_pct")),
    ("trs_pct_when_decided", ("goals", "taxa_retirada_efetiva_pct")),
)


async def _build_context_snapshot(
    suggestion: Suggestion, *, db: AsyncSession | None
) -> Optional[dict[str, Any]]:
    """ADR-163 — congela KPIs do relatório-fonte da Suggestion.

    Lê do `report.analysis_artifact.content_json` apontado por
    ``suggestion.report_id``. Retorna None silenciosamente se report
    ausente, snapshot inválido ou DB indisponível — Decision continua
    sendo criada (campo fica NULL).
    """
    if db is None or suggestion.report_id is None:
        return None
    from backend.app.application.report._common import fetch_report  # noqa: PLC0415

    try:
        report = await fetch_report(suggestion.workspace_id, suggestion.report_id, db=db)
    except Exception:  # noqa: BLE001
        return None
    artifact = getattr(report, "analysis_artifact", None)
    snap_dict = read_artifact_content(getattr(artifact, "content_json", None))
    if not isinstance(snap_dict, dict):
        return None
    out: dict[str, Any] = {
        "report_id": suggestion.report_id,
        "report_period": snap_dict.get("periodo_dados"),
    }
    for key, path in _SNAPSHOT_KPI_PATHS:
        out[key] = _read_path(snap_dict, path)
    # Limpa chaves None só por estética — JSONB lida bem com null mas
    # frontend prefere ausência explícita.
    return {k: v for k, v in out.items() if v is not None}


def _read_path(d: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d
