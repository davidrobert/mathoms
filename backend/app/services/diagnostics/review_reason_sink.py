"""Sink de `review_reasons` (ADR-399) — sessão própria, fail-open, sem `Session`
na API pública. O run `140ac8d7` morreu em 12/18 porque esta escrita dividia
transação com `run.status = needs_review` (CTO-6 · §r7)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.core.logging import get_logger
from backend.app.models.document import Document
from backend.app.models.review_reason import ReviewReason
from backend.app.services.diagnostics.review_reason_boundary import (
    ReviewReasonRow,
    sanitize_review_reasons,
)
from pipeline.domain.review_reason import ReviewReasonCode

logger = get_logger("pipeline.diagnostics")

# Cap de rows por (run, code) — proteção contra row explosion (ADR-272 Fase 2).
# Consolidamos para 1 row por (run, code) somando occurrence_count cross-doc; o cap
# é defensivo (há só ~20 ReviewReasonCode, então <=20 rows por run na prática).
_REVIEW_REASON_ROW_CAP = 50

_KNOWN_CODES = frozenset(c.value for c in ReviewReasonCode)


def _existing_review_reason(db, *, run_id: str, workspace_id: str, code: str):
    """Row já materializada para (run, code) — autoflush torna add anterior visível na mesma transação."""
    return db.execute(
        select(ReviewReason).where(
            ReviewReason.workspace_id == workspace_id,
            ReviewReason.pipeline_run_id == run_id,
            ReviewReason.code == code,
        )
    ).scalar_one_or_none()


def _resolvable_document_ids(db, workspace_id: str, reasons: list[dict]) -> set[str]:
    """Subconjunto dos `document_id` reivindicados que existe em `documents`."""
    claimed = {r.get("document_id") for r in reasons if r.get("document_id")}
    if not claimed:
        return set()
    rows = db.query(Document.id).filter(
        Document.workspace_id == workspace_id, Document.id.in_(claimed)
    )
    return {row[0] for row in rows}


# A FK de `document_id` é enforçada (ADR-371): um id que não resolve abortaria o
# run inteiro no INSERT — o caminho de REPORTE matando a execução que ele existe
# para documentar. Degrada a row, nunca a execução.
def _with_safe_document_id(payload: dict, stage_name: str, known_docs: set[str]) -> dict:
    """Payload com `document_id` que não resolve trocado por None."""
    claimed = payload.get("document_id")
    if not claimed or claimed in known_docs:
        return payload
    logger.warning(
        "review_reason.document_id descartado — não resolve em documents",
        extra={
            "event": "mathoms.pipeline.review_reason_document_id_dropped",
            "stage": stage_name,
            "code": payload.get("code"),
        },
    )
    return {**payload, "document_id": None}


def _new_review_reason_row(
    payload: dict, *, run_id: str, workspace_id: str, stage_name: str, inc: int
):
    """Constrói row ReviewReason a partir do dict projetado pelo stage."""
    return ReviewReason(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        stage=stage_name,
        code=payload["code"],
        artifact_key=payload.get("artifact_key", "") or "",
        document_id=payload.get("document_id"),
        offending_value=payload.get("offending_value", "") or "",
        expected=payload.get("expected", "") or "",
        message=payload.get("message", "") or "",
        occurrence_count=inc,
    )


def _apply_one_reason(
    db, payload: dict, *, run_id: str, workspace_id: str, stage_name: str, can_insert: bool
) -> bool:
    """Bump (run, code) existente ou insere nova row se can_insert. Retorna True se inseriu."""
    code = payload.get("code")
    if not code:
        return False
    inc = int(payload.get("occurrence_count", 1) or 1)
    existing = _existing_review_reason(db, run_id=run_id, workspace_id=workspace_id, code=code)
    if existing is not None:
        existing.occurrence_count += inc
        return False
    if not can_insert:
        return False
    db.add(
        _new_review_reason_row(
            payload, run_id=run_id, workspace_id=workspace_id, stage_name=stage_name, inc=inc
        )
    )
    return True


# UMA sessão para o loop inteiro, de propósito: o bump depende do autoflush
# tornar o `db.add` anterior visível na mesma transação. Sessão por-row
# inseriria duplicata em vez de somar — e é o bump por (run, code) que torna o
# redelivery do Celery (`acks_late`) idempotente.
def _materialize_review_reasons(
    db, *, run_id: str, workspace_id: str, stage_name: str, reasons: list[dict]
) -> int:
    """1 row por (run, code), somando occurrence_count (ADR-272 Fase 2). Retorna nº inseridas."""
    inserted = 0
    known_docs = _resolvable_document_ids(db, workspace_id, reasons)
    for payload in reasons:
        if _apply_one_reason(
            db,
            _with_safe_document_id(payload, stage_name, known_docs),
            run_id=run_id,
            workspace_id=workspace_id,
            stage_name=stage_name,
            can_insert=inserted < _REVIEW_REASON_ROW_CAP,
        ):
            inserted += 1
    return inserted


def _drop_unknown_codes(rows: list[dict], stage_name: str) -> list[dict]:
    """Code fora de `ReviewReasonCode` não entra: `(run, code)` é a chave de
    consolidação, e code fabricado a envenena. O sinal vai para o log — é onde
    o operador lê, já que a tabela não tem consumidor de UI hoje. Doutrina
    herdada de `_warn_unmapped` (`pipeline/domain/review_reason_projection.py`)."""
    known = [r for r in rows if r.get("code") in _KNOWN_CODES]
    for row in rows:
        if row.get("code") not in _KNOWN_CODES:
            logger.error(
                "review_reason descartado — code fora do vocabulário fechado",
                extra={
                    "event": "mathoms.pipeline.review_reason_unknown_code",
                    "stage": stage_name,
                    "code": str(row.get("code"))[:80],
                },
            )
    return known


# SEM traceback: `StatementError` do driver carrega os bound parameters, e
# `artifact_key` é stem de filename — `redact_pii` (CPF + BRL) e o `_redact` por
# chave do formatter não alcançam nome próprio ali. ERROR e não CRITICAL: é
# ticket, não page. O worker Celery não popula os contextvars de correlação
# (`backend/app/middleware/correlation.py`), então todo campo vai no `extra`.
def _log_sink_failure(exc: Exception, *, run_id, workspace_id, stage_name, rows) -> None:
    """Falha do sink vira evento estruturado — é a métrica, não há contador."""
    logger.error(
        "review_reasons não materializadas — run segue pausado, diagnóstico perdido",
        exc_info=False,
        extra={
            "event": "mathoms.pipeline.review_reason_sink_failed",
            "run_id": run_id,
            "workspace_id": workspace_id,
            "stage": stage_name,
            "exc_type": type(exc).__name__,
            "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
            "codes": sorted({str(r.get("code")) for r in rows}),
            "rows_attempted": len(rows),
            "rows_written": 0,
        },
    )


def _log_sink_ok(*, run_id: str, stage_name: str, written: int, attempted: int) -> None:
    logger.info(
        "review_reasons materializadas",
        extra={
            "event": "mathoms.pipeline.review_reason_sink_ok",
            "run_id": run_id,
            "stage": stage_name,
            "rows_written": written,
            "rows_attempted": attempted,
        },
    )


# Não aceita `Session` de propósito (ADR-399): quem chama não consegue
# compartilhar a transação da transição de estado nem por engano.
# `sanitize_review_reasons` é idempotente e silenciosa sobre entrada já
# normalizada — chamá-la aqui mantém o sink seguro standalone sem duplicar o
# warning que o call-site do orquestrador já emitiu.
def record_review_reasons(*, run_id: str, workspace_id: str, stage_name: str, reasons: Any) -> int:
    """Materializa a razão de `needs_review` em sessão própria. Nunca levanta."""
    rows = _drop_unknown_codes(sanitize_review_reasons(reasons, stage_name=stage_name), stage_name)
    if not rows:
        return 0
    try:
        with SyncSessionLocal() as db:
            inserted = _materialize_review_reasons(
                db, run_id=run_id, workspace_id=workspace_id, stage_name=stage_name, reasons=rows
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001 — fail-open é a decisão da ADR-399
        _log_sink_failure(
            exc, run_id=run_id, workspace_id=workspace_id, stage_name=stage_name, rows=rows
        )
        return 0
    _log_sink_ok(run_id=run_id, stage_name=stage_name, written=inserted, attempted=len(rows))
    return inserted


__all__ = ["ReviewReasonRow", "record_review_reasons"]
