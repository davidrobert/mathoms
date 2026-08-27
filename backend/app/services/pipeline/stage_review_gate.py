"""Predicado de CONTROLE da pausa: nenhuma entrada retoma e nenhum desfecho ENTREGA
sobre `StageReview` que ninguém decidiu.

ADR-404 D2 vale para a OPERAÇÃO de retomada, não para uma camada (§Emenda 2026-08-27):
o predicado vivia só no use case HTTP, o service era caminho vivo, e dois runs de dogfood
completaram sobre review pendente (RV8-08) — um deles o baseline de comparação do outro.
"""

from __future__ import annotations

from sqlalchemy import select

from backend.app.core.logging import get_logger
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.stage_review import StageReview, StageReviewStatus

logger = get_logger("mathoms.pipeline.review_gate")

# Restritivo de propósito: destrava só sobre decisão REGISTRADA. Escrito como
# `== pending`, membro novo do enum destravaria calado — o modo de falha que a
# ADR-417 D3 recusou ao não criar `dismissed`.
REVIEW_DECIDIDA = (StageReviewStatus.approved, StageReviewStatus.edited)

# Desfechos que ENTREGAM — os que criam a row em `reports` (`_POST_PROCESS_STATUSES`).
# LISTADOS, nunca derivados de "terminal menos X": `(cancelled, pending)` é resíduo
# SANCIONADO (ADR-417 D3) e `(failed, pending)` diz a verdade — ninguém decidiu e o
# run morreu. Escrito como "terminal + pending", este predicado morderia a D3.
DELIVERING_STATUSES = (PipelineRunStatus.completed, PipelineRunStatus.partial_failure)


def pending_reviews(db, run_id: str) -> list[tuple[str, str]]:
    """`(stage, review_id)` das conferências sem decisão registrada neste run."""
    rows = db.execute(
        select(StageReview.stage, StageReview.id).where(
            StageReview.pipeline_run_id == run_id,
            StageReview.status.notin_(REVIEW_DECIDIDA),
        )
    ).all()
    return [(stage, review_id) for stage, review_id in rows]


def pending_review_message(run_id: str, pendentes: list[tuple[str, str]]) -> str:
    """Nomeia QUAIS, não só quantas: id ausente manda o operador para o `sqlite3`."""
    alvos = ", ".join(f"{stage} (review {review_id[:8]})" for stage, review_id in pendentes[:5])
    resto = f" (+{len(pendentes) - 5})" if len(pendentes) > 5 else ""
    return (
        f"{len(pendentes)} conferência(s) sem decisão: {alvos}{resto}. "
        f"Aprove ou edite cada uma (POST .../runs/{run_id}/reviews/<review_id>) e retome — "
        f"a retomada roda tudo a jusante do stage pausado e re-custa LLM. "
        f"Ou descarte: POST .../runs/{run_id}/cancel (irreversível). O run permanece em "
        f"needs_review; não escreva em pipeline_runs nem em stage_reviews pelo DB."
    )


def repark_stage_if_undecided(db, run: PipelineRun, status: PipelineRunStatus) -> str | None:
    """Stage em que re-estacionar a pausa; ``None`` = o desfecho pode ser gravado."""
    if status not in DELIVERING_STATUSES:
        return None
    pendentes = pending_reviews(db, run.id)
    if not pendentes:
        return None
    logger.error(
        "entrega_bloqueada_por_review_sem_decisao",
        extra={
            "run_id": run.id,
            "intencao": status.value,
            "stages": [stage for stage, _ in pendentes],
        },
    )
    # `paused_at_stage` falsy leva a `_stages_after_paused(None) -> []` -> run
    # reportando sucesso sem executar nada (A40.l27).
    return run.paused_at_stage or pendentes[0][0]
