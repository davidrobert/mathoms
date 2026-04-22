"""P2.5 — observabilidade da classificação (sem PII: sem nome de arquivo).

Logs em JSON numa linha com prefixo fixo para grep/agregação de mismatch
antes/depois de mudanças no classificador.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger("fin.classification_telemetry")


def _doc_type_str(doc_type: object | None) -> str | None:
    if doc_type is None:
        return None
    if hasattr(doc_type, "value"):
        return str(doc_type.value)
    return str(doc_type)


def emit_classification_outcome(
    *,
    context: str,
    classification: dict | None,
    workspace_id: str | None = None,
    prior_doc_type: object | None = None,
    outcome: str = "classified",
) -> None:
    """Emite um evento estruturado; mensagem contém JSON após o prefixo."""
    payload: dict = {
        "event": "classification_outcome",
        "context": context,
        "outcome": outcome,
    }
    if workspace_id:
        payload["workspace_id"] = workspace_id
    if classification is not None:
        conf = float(classification.get("confidence") or 0.0)
        dt = _doc_type_str(classification.get("doc_type"))
        payload["doc_type"] = dt
        payload["bank_present"] = bool(classification.get("bank_code"))
        payload["confidence_bucket"] = "low" if conf < 0.5 else ("medium" if conf < 0.7 else "high")
        payload["needs_review"] = bool(classification.get("needs_review"))
        meta = classification.get("classification_meta")
        if isinstance(meta, dict):
            payload["source"] = meta.get("source", "unknown")
        prior_s = _doc_type_str(prior_doc_type)
        payload["type_changed_vs_prior"] = bool(prior_s and dt and prior_s != dt)
    line = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    logger.info("classification_outcome %s", line)
