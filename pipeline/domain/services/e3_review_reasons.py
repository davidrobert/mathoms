"""Projeção de warnings E3 → ReviewReason (ADR-272/ADR-308 · A29.l2)."""

from __future__ import annotations

from typing import Any, Iterable

from pipeline.artifact_store import ArtifactStore
from pipeline.domain.review_reason import ReviewReason

E3_REVIEW_STAGE = "reconcile_transactions"


def project_e3_reasons(
    warnings: Iterable[Any], artifact_key: str, document_id: str | None = None
) -> list[ReviewReason]:
    """Projeta warnings → ReviewReason (ADR-272); sem mapeamento → descartado."""
    reasons: list[ReviewReason] = []
    for w in warnings:
        reason = w.to_review_reason(
            stage=E3_REVIEW_STAGE, artifact_key=artifact_key, document_id=document_id
        )
        if reason is not None:
            reasons.append(reason)
    return reasons


def store_document_id(store: ArtifactStore, stage: str, key: str) -> str | None:
    """FK do documento quando o store expõe (ADR-308 §5); DBArtifactStore não
    popula document_id em E2 — backend resolve por prefixo de content_hash."""
    lookup = getattr(store, "document_id_for", None)
    if lookup is None:
        return None
    try:
        return lookup(stage, key)
    except Exception:
        return None
