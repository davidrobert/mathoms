"""Projeta produtores (ValidationIssue, warnings de domínio) → ReviewReason agregado (ADR-272 Fase 2)."""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import replace

from pipeline.domain.review_reason import ReviewReason, ToReviewReason

logger = logging.getLogger("mathoms.pipeline.review_reason")


def _merge(by_code: OrderedDict[str, ReviewReason], reason: ReviewReason) -> None:
    """Agrega por code somando occurrence_count (parcial por-documento; cap cross-doc é do adapter)."""
    existing = by_code.get(reason.code.value)
    if existing is None:
        by_code[reason.code.value] = reason
        return
    by_code[reason.code.value] = replace(
        existing, occurrence_count=existing.occurrence_count + reason.occurrence_count
    )


def _warn_unmapped(producer: ToReviewReason) -> None:
    """Produtor sem mapeamento nunca é silenciado — emite WARNING (drift detection)."""
    logger.warning(
        "review_reason sem mapeamento, descartado: producer=%s code=%s",
        type(producer).__name__,
        getattr(producer, "code", "?"),
    )


def project_review_reasons(
    producers: list[ToReviewReason],
    *,
    stage: str,
    artifact_key: str,
    document_id: str | None,
) -> list[ReviewReason]:
    """Projeta produtores → ReviewReason agregado por code; produtor sem mapeamento → WARNING + descarte."""
    by_code: OrderedDict[str, ReviewReason] = OrderedDict()
    for producer in producers:
        reason = producer.to_review_reason(
            stage=stage, artifact_key=artifact_key, document_id=document_id
        )
        if reason is None:
            _warn_unmapped(producer)
            continue
        _merge(by_code, reason)
    return list(by_code.values())


__all__ = ["project_review_reasons"]
