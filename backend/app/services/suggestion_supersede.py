"""Ciclo de vida de Suggestion origin='llm' do parecer — expiração por parecer-fonte (ADR-378) sobre a base ADR-290 (thesis_key, janela de dismiss, guard run-level); consumido por planner_review_persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import ParecerOutcome
from backend.app.models.suggestion import Suggestion
from backend.app.services.parecer_finalization import (
    compute_suggestion_thesis_key,
    severity_from_prioridade,
)
from backend.app.services.security.crypto import read_artifact_content
from pipeline.domain.services.suggestion_generator import DISMISS_RESPECT_WINDOW_DAYS

logger = logging.getLogger("mathoms.pipeline.suggestion_supersede")

_SUGGESTION_KIND = "parecer_planejador"

_HORIZON_BY_BUCKET = {
    "sugestoes_execucao": "execucao",
    "sugestoes_taticas": "tatica",
    "sugestoes_estrategicas": "estrategica",
}

_ZERO_STATS = {
    "suggestions_created": 0,
    "suggestions_superseded": 0,
    "skipped_dismiss": 0,
    "skipped_dup": 0,
    "reemitted": 0,
    "near_dup_candidates": 0,
    "thesis_collision_intra_run": 0,
    "pending_after": 0,
}


# Run retido ou sem sugestões NÃO expira nada (ADR-378 §D1 guard): parecer que
# não entregou não pode apagar o inbox do cliente (revisão senior-cto B-1).
def persist_suggestions_for_run(
    db: Session,
    *,
    workspace_id: str,
    run_id: str,
    parecer_artifact: PipelineArtifact,
    outcome: ParecerOutcome,
) -> dict[str, int]:
    """Expira as pendentes de pareceres anteriores + insere o conjunto do run atual; retorna contadores KR4."""
    sugs = _current_run_sugs(parecer_artifact)
    if outcome is ParecerOutcome.retido or not sugs:
        _log_skip_undelivered(workspace_id, run_id, outcome, len(sugs))
        return dict(_ZERO_STATS)
    return _expire_and_reissue(db, workspace_id, run_id, sugs)


# Flush entre expirar e inserir é obrigatório: sem ele, o INSERT de uma
# dedup_key reafirmada pode ser emitido antes do UPDATE de status no
# unit-of-work e violar o índice único parcial `uq_sugagg_ws_dedup_ativa`
# (revisão senior-cto B-2, ADR-378).
def _expire_and_reissue(
    db: Session, workspace_id: str, run_id: str, sugs: list[tuple[str, dict]]
) -> dict[str, int]:
    """Fase destrutiva + fase de insert do run entregue (ADR-378 §D1/§D2)."""
    now = datetime.now(timezone.utc)
    pendings = _expirable_pendings(db, workspace_id=workspace_id, run_id=run_id)
    near_dups = _count_near_dup_candidates(pendings)
    expired_keys = _expire_previous(pendings, run_id=run_id, now=now)
    db.flush()
    insert_counts = _insert_new_suggestions(db, workspace_id, run_id, sugs, now, expired_keys)
    db.flush()
    return _assemble_stats(db, workspace_id, sugs, len(expired_keys), near_dups, insert_counts)


def _log_skip_undelivered(
    workspace_id: str, run_id: str, outcome: ParecerOutcome, sugs_count: int
) -> None:
    logger.info(
        "supersede_skipped_undelivered",
        extra={
            "workspace_id": workspace_id,
            "run_id": run_id,
            "outcome": outcome.value,
            "sugs_in_artifact": sugs_count,
        },
    )


def _assemble_stats(
    db: Session,
    workspace_id: str,
    sugs: list[tuple[str, dict]],
    expired: int,
    near_dups: int,
    insert_counts: dict[str, int],
) -> dict[str, int]:
    """Contadores KR4 (ADR-378 §D5) — `pending_after` é o único que enxerga "inbox esvaziou"."""
    return {
        **insert_counts,
        "suggestions_superseded": expired,
        "near_dup_candidates": near_dups,
        "thesis_collision_intra_run": _count_thesis_collisions(workspace_id, sugs),
        "pending_after": _count_pending(db, workspace_id=workspace_id),
    }


def _iter_sugestoes(content_json: dict):
    """Yields tuples (horizon, sug_dict) — horizon canônico preservado do bucket (ADR-378 §D4)."""
    for bucket, horizon in _HORIZON_BY_BUCKET.items():
        for sug in content_json.get(bucket, []) or []:
            yield horizon, sug


def _current_run_sugs(parecer_artifact: PipelineArtifact) -> list[tuple[str, dict]]:
    """Sugestões do artifact do run atual como (horizon, dict cru)."""
    content = read_artifact_content(parecer_artifact.content_json) or {}
    return list(_iter_sugestoes(content))


def _not_from_run(col, run_id: str):
    """`col != run` que NÃO descarta NULL (NULL = pré-migration/run expurgado, conta como run anterior)."""
    return or_(col.is_(None), col != run_id)


def _expirable_pendings(db: Session, *, workspace_id: str, run_id: str) -> list[Suggestion]:
    """Pendentes do parecer de runs anteriores (ADR-378 §D1) — sem filtro de thesis_key: a fotografia que as originou não é mais a vigente, inclusive para rows com thesis_key NULL (zumbis pós-backfill F4)."""
    query = select(Suggestion).where(
        Suggestion.workspace_id == workspace_id,
        Suggestion.status == "Pendente",
        Suggestion.origin == "llm",
        Suggestion.kind == _SUGGESTION_KIND,
        Suggestion.accepted_decision_id.is_(None),
        _not_from_run(Suggestion.pipeline_run_id, run_id),
        _not_from_run(Suggestion.superseded_by_run_id, run_id),
    )
    return list(db.execute(query).scalars().all())


def _count_near_dup_candidates(pendings: list[Suggestion]) -> int:
    """Pendentes pré-expiração que dividem thesis_key com dedup_key distinto (KR4)."""
    by_thesis: dict[str, set[str]] = {}
    for p in pendings:
        if p.thesis_key is None:
            continue
        by_thesis.setdefault(p.thesis_key, set()).add(p.dedup_key)
    return sum(len(keys) - 1 for keys in by_thesis.values() if len(keys) > 1)


def _expire_previous(pendings: list[Suggestion], *, run_id: str, now: datetime) -> set[str]:
    """Marca Superseded TODAS as pendentes de pareceres anteriores — "último parecer vence" literal (ADR-378 §D1). Tese reafirmada é reinserida pelo run atual com rationale/valor vigentes (dedup_key não cobre rationale). Retorna as dedup_keys expiradas (alimenta o contador `reemitted`)."""
    for p in pendings:
        p.status = "Superseded"
        p.superseded_at = now
        p.superseded_by_run_id = run_id
    return {p.dedup_key for p in pendings}


def _count_thesis_collisions(workspace_id: str, sugs: list[tuple[str, dict]]) -> int:
    """Teses distintas (dedup_key ≠) sob o mesmo thesis_key DENTRO do run atual (ADR-378 §D5) — chave grossa demais é drift detectável, não surpresa. Gatilho medido em 2026-08-11: 2 colisões num run real → F6 (action_slug) nomeada no plano."""
    by_thesis: dict[str, set[str]] = {}
    for _horizon, sug in sugs:
        thesis = _thesis_key_for(workspace_id, sug)
        if thesis is None:
            continue
        by_thesis.setdefault(thesis, set()).add(sug["suggestion_dedup_key"])
    return sum(len(keys) - 1 for keys in by_thesis.values() if len(keys) > 1)


def _count_pending(db: Session, *, workspace_id: str) -> int:
    """count(Pendente) do parecer pós-persist — o modo de falha novo do desenho é "inbox esvaziou"; só este contador o enxerga (revisão senior-cto M-1)."""
    return int(
        db.execute(
            select(func.count())
            .select_from(Suggestion)
            .where(
                Suggestion.workspace_id == workspace_id,
                Suggestion.kind == _SUGGESTION_KIND,
                Suggestion.status == "Pendente",
            )
        ).scalar_one()
    )


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


def _accepted_dedup_keys(db: Session, *, workspace_id: str) -> set[str]:
    """dedup_keys já promovidas a Decision (Aceita/Modificada) — reemissão idêntica não vira Pendente nova enquanto a Decision existir. Alinha o caminho llm à política de dedup ADR-153 §2 (`_should_skip` do caminho determinístico usa o mesmo conjunto ativo); Superseded deixa de bloquear reafirmação (ADR-378 §D2)."""
    rows = db.execute(
        select(Suggestion.dedup_key).where(
            Suggestion.workspace_id == workspace_id,
            Suggestion.kind == _SUGGESTION_KIND,
            Suggestion.status.in_(("Aceita", "Modificada")),
        )
    ).all()
    return {row[0] for row in rows}


def _skip_reason(
    sug: dict, workspace_id: str, blocked_keys: set[str], dismissed_theses: set[str]
) -> Optional[str]:
    """'dup' (já aceita ou repetida no batch), 'dismiss' (tese descartada <90d, B4) ou None."""
    if sug["suggestion_dedup_key"] in blocked_keys:
        return "dup"
    thesis = _thesis_key_for(workspace_id, sug)
    if thesis is not None and thesis in dismissed_theses:
        return "dismiss"
    return None


def _log_dismiss_suppression(workspace_id: str, run_id: str, sug: dict) -> None:
    """Supressão por janela de dismiss é auditável item a item — com thesis_key de cardinalidade baixa, descartar T1 pode silenciar T2/T3 legítimas (revisão senior-cto sobre B4); o log é o rastro."""
    logger.info(
        "suggestion_suppressed_by_dismiss_window",
        extra={
            "workspace_id": workspace_id,
            "run_id": run_id,
            "thesis_key": _thesis_key_for(workspace_id, sug),
            "dedup_key": sug["suggestion_dedup_key"],
            "section_id": sug.get("section_id"),
        },
    )


def _insert_new_suggestions(
    db: Session,
    workspace_id: str,
    run_id: str,
    sugs: list[tuple[str, dict]],
    now: datetime,
    expired_keys: set[str],
) -> dict[str, int]:
    """Insere o conjunto do run atual; retorna contadores de insert (KR4)."""
    blocked_keys = _accepted_dedup_keys(db, workspace_id=workspace_id)
    dismissed = _recently_dismissed_theses(db, workspace_id=workspace_id, now=now)
    report_id = _find_report_id(db, workspace_id=workspace_id, run_id=run_id)
    counts = {"suggestions_created": 0, "skipped_dismiss": 0, "skipped_dup": 0, "reemitted": 0}
    for horizon, sug in sugs:
        reason = _skip_reason(sug, workspace_id, blocked_keys, dismissed)
        if reason is not None:
            _count_skip(counts, reason, workspace_id, run_id, sug)
            continue
        _add_fresh_row(
            db,
            counts,
            blocked_keys,
            expired_keys,
            _build_suggestion(workspace_id, run_id, sug, horizon, report_id),
        )
    return counts


def _add_fresh_row(
    db: Session, counts: dict, blocked_keys: set[str], expired_keys: set[str], row: Suggestion
) -> None:
    db.add(row)
    blocked_keys.add(row.dedup_key)
    counts["suggestions_created"] += 1
    counts["reemitted"] += int(row.dedup_key in expired_keys)


def _count_skip(
    counts: dict[str, int], reason: str, workspace_id: str, run_id: str, sug: dict
) -> None:
    if reason == "dismiss":
        counts["skipped_dismiss"] += 1
        _log_dismiss_suppression(workspace_id, run_id, sug)
    else:
        counts["skipped_dup"] += 1


def _thesis_key_for(workspace_id: str, sug: dict) -> Optional[str]:
    """thesis_key da sugestão do artifact (ADR-290 B1); campo-fonte ausente → None."""
    return compute_suggestion_thesis_key(
        workspace_id=workspace_id,
        tema_canonico=sug.get("tema_canonico"),
        section_id=sug.get("section_id"),
        ancora=sug.get("ancora_metodologica"),
    )


def _build_suggestion(
    workspace_id: str, run_id: str, sug: dict, horizon: str, report_id: Optional[str] = None
) -> Suggestion:
    """Constrói Suggestion(origin='llm') do run vigente (ADR-378 §D1/§D4)."""
    return Suggestion(
        workspace_id=workspace_id,
        report_id=report_id,
        pipeline_run_id=run_id,
        horizon=horizon,
        status="Pendente",
        **_suggestion_content_fields(workspace_id, sug),
    )


def _suggestion_content_fields(workspace_id: str, sug: dict) -> dict:
    """Campos derivados do item do artifact — title vem do `acao`, rationale do `impacto` (conteúdo imutável pós-insert, ADR-153)."""
    return {
        "section_id": sug["section_id"],
        "kind": _SUGGESTION_KIND,
        "category": None,
        "origin": "llm",
        "severity": severity_from_prioridade(sug["prioridade"]),
        "title": sug["acao"][:500],
        "rationale": sug["impacto_qualitativo"],
        "amount_brl_cents": _extract_amount_cents(sug),
        "dedup_key": sug["suggestion_dedup_key"],
        "thesis_key": _thesis_key_for(workspace_id, sug),
    }


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
