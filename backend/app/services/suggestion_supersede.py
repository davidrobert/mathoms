"""Ciclo de vida de Suggestion origin='llm' do parecer — supersede-per-run + thesis_key + dedup + janela de dismiss (ADR-290 B1–B6); consumido por planner_review_persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.suggestion import Suggestion
from backend.app.services.crypto import read_artifact_content
from backend.app.services.parecer_finalization import (
    compute_suggestion_thesis_key,
    severity_from_prioridade,
)
from pipeline.domain.services.suggestion_generator import DISMISS_RESPECT_WINDOW_DAYS

_SUGGESTION_KIND = "parecer_planejador"


def persist_suggestions_for_run(
    db: Session, *, workspace_id: str, run_id: str, parecer_artifact: PipelineArtifact
) -> dict[str, int]:
    """Supersede de pendentes obsoletas + insert com dedup; retorna contadores KR4."""
    now = datetime.now(timezone.utc)
    sugs = _current_run_sugs(parecer_artifact)
    superseded, near_dups = _run_supersede(db, workspace_id, run_id, sugs=sugs, now=now)
    created, skipped_dismiss = _insert_new_suggestions(
        db, workspace_id=workspace_id, parecer_artifact=parecer_artifact, sugs=sugs, now=now
    )
    return {
        "suggestions_created": created,
        "suggestions_superseded": superseded,
        "skipped_dismiss": skipped_dismiss,
        "near_dup_candidates": near_dups,
    }


def _run_supersede(
    db: Session, workspace_id: str, run_id: str, *, sugs: list[dict], now: datetime
) -> tuple[int, int]:
    """Retorna (superseded, near_dup_candidates) para o run atual (B3/B6)."""
    pendings = _superseable_pendings(db, workspace_id=workspace_id, run_id=run_id)
    near_dups = _count_near_dup_candidates(pendings)
    current_keys = {s["suggestion_dedup_key"] for s in sugs}
    superseded = _supersede_obsolete(
        pendings, current_dedup_keys=current_keys, run_id=run_id, now=now
    )
    return superseded, near_dups


def _iter_sugestoes(content_json: dict):
    """Yields tuples (horizon, sug_dict) achatando os 3 buckets."""
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        for sug in content_json.get(horizon, []) or []:
            yield horizon, sug


def _current_run_sugs(parecer_artifact: PipelineArtifact) -> list[dict]:
    """Sugestões do artifact do run atual (dicts crus dos 3 buckets)."""
    content = read_artifact_content(parecer_artifact.content_json) or {}
    return [sug for _horizon, sug in _iter_sugestoes(content)]


def _superseable_pendings(db: Session, *, workspace_id: str, run_id: str) -> list[Suggestion]:
    """Pendentes do parecer candidatas a supersede (ADR-290 B3/B5/B6)."""
    return list(
        db.execute(
            select(Suggestion).where(
                Suggestion.workspace_id == workspace_id,
                Suggestion.status == "Pendente",
                Suggestion.origin == "llm",
                Suggestion.kind == _SUGGESTION_KIND,
                Suggestion.accepted_decision_id.is_(None),
                Suggestion.thesis_key.is_not(None),
                or_(
                    Suggestion.superseded_by_run_id.is_(None),
                    Suggestion.superseded_by_run_id != run_id,
                ),
            )
        )
        .scalars()
        .all()
    )


def _count_near_dup_candidates(pendings: list[Suggestion]) -> int:
    """Pendentes pré-supersede que dividem thesis_key com dedup_key distinto (KR4)."""
    by_thesis: dict[str, set[str]] = {}
    for p in pendings:
        by_thesis.setdefault(p.thesis_key, set()).add(p.dedup_key)
    return sum(len(keys) - 1 for keys in by_thesis.values() if len(keys) > 1)


def _supersede_obsolete(
    pendings: list[Suggestion], *, current_dedup_keys: set[str], run_id: str, now: datetime
) -> int:
    """Marca Superseded pendentes cujo conteúdo (dedup_key) não reaparece no run atual — cobre tese obsoleta (B3) e tese re-redigida (antiga sai, nova entra no insert)."""
    count = 0
    for p in pendings:
        if p.dedup_key in current_dedup_keys:
            continue
        p.status = "Superseded"
        p.superseded_at = now
        p.superseded_by_run_id = run_id
        count += 1
    return count


def _recently_dismissed_theses(db: Session, *, workspace_id: str, now: datetime) -> set[str]:
    """thesis_keys Descartadas dentro da janela de respeito (ADR-290 B4)."""
    cutoff = now - timedelta(days=DISMISS_RESPECT_WINDOW_DAYS)
    rows = db.execute(
        select(Suggestion.thesis_key).where(
            Suggestion.workspace_id == workspace_id,
            Suggestion.status == "Descartada",
            Suggestion.kind == _SUGGESTION_KIND,
            Suggestion.thesis_key.is_not(None),
            Suggestion.dismissed_at.is_not(None),
            Suggestion.dismissed_at >= cutoff,
        )
    ).all()
    return {row[0] for row in rows}


def _existing_dedup_keys(db: Session, *, workspace_id: str) -> set[str]:
    """Suggestions ativas (qualquer status) para o workspace — idempotência ADR-153."""
    rows = db.execute(
        select(Suggestion.dedup_key).where(Suggestion.workspace_id == workspace_id)
    ).all()
    return {row[0] for row in rows}


def _skip_reason(
    sug: dict, workspace_id: str, existing_keys: set[str], dismissed_theses: set[str]
) -> Optional[str]:
    """'dup' (dedup_key já existe), 'dismiss' (tese descartada <90d, B4) ou None."""
    if sug["suggestion_dedup_key"] in existing_keys:
        return "dup"
    thesis = _thesis_key_for(workspace_id, sug)
    if thesis is not None and thesis in dismissed_theses:
        return "dismiss"
    return None


def _insert_new_suggestions(
    db: Session,
    *,
    workspace_id: str,
    parecer_artifact: PipelineArtifact,
    sugs: list[dict],
    now: datetime,
) -> tuple[int, int]:
    """Insere sugestões inéditas; retorna (created, skipped_dismiss)."""
    existing_keys = _existing_dedup_keys(db, workspace_id=workspace_id)
    dismissed = _recently_dismissed_theses(db, workspace_id=workspace_id, now=now)
    report_id = _find_report_id(
        db, workspace_id=workspace_id, run_id=parecer_artifact.pipeline_run_id
    )
    created, skipped_dismiss = 0, 0
    for sug in sugs:
        reason = _skip_reason(sug, workspace_id, existing_keys, dismissed)
        if reason == "dismiss":
            skipped_dismiss += 1
        if reason is None:
            db.add(_build_suggestion(workspace_id=workspace_id, report_id=report_id, sug=sug))
            existing_keys.add(sug["suggestion_dedup_key"])
            created += 1
    return created, skipped_dismiss


def _thesis_key_for(workspace_id: str, sug: dict) -> Optional[str]:
    """thesis_key da sugestão do artifact (ADR-290 B1); campo-fonte ausente → None."""
    return compute_suggestion_thesis_key(
        workspace_id=workspace_id,
        tema_canonico=sug.get("tema_canonico"),
        section_id=sug.get("section_id"),
        ancora=sug.get("ancora_metodologica"),
    )


def _build_suggestion(*, workspace_id: str, report_id: Optional[str], sug: dict) -> Suggestion:
    """Constrói Suggestion(origin='llm') — title vem do `acao`, rationale do `impacto`."""
    return Suggestion(
        workspace_id=workspace_id,
        report_id=report_id,
        section_id=sug["section_id"],
        kind=_SUGGESTION_KIND,
        category=None,
        origin="llm",
        severity=severity_from_prioridade(sug["prioridade"]),
        title=sug["acao"][:500],
        rationale=sug["impacto_qualitativo"],
        amount_brl_cents=_extract_amount_cents(sug),
        dedup_key=sug["suggestion_dedup_key"],
        thesis_key=_thesis_key_for(workspace_id, sug),
        status="Pendente",
    )


def _extract_amount_cents(sug: dict) -> Optional[int]:
    """Converte ``impacto_estimado.valor_estimado_brl`` (BRL) → cents (ADR-090). Opcional — só presente quando confianca='alta' (ADR-202 §D6)."""
    impacto = sug.get("impacto_estimado")
    if not impacto:
        return None
    valor_brl = impacto.get("valor_estimado_brl")
    if valor_brl is None:
        return None
    return int(round(float(valor_brl) * 100))


def _find_report_id(db: Session, *, workspace_id: str, run_id: str) -> Optional[str]:
    """Resolve `report_id` para FK opcional em Suggestion. None = ainda sem Report."""
    from backend.app.models.report import Report

    row = (
        db.execute(
            select(Report.id).where(
                Report.workspace_id == workspace_id,
                Report.pipeline_run_id == run_id,
            )
        )
        .scalars()
        .first()
    )
    return row


__all__ = ["persist_suggestions_for_run"]
