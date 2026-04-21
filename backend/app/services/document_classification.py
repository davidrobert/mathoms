"""Classificação unificada de documentos (P2).

Única implementação usada por upload web, ``POST /documents/reclassify``,
``scripts/e0_route.route_file`` (quando o backend está importável) e scripts
de manutenção. Ver ADR-081 em ``docs/DECISIONS.md``.

Saída: ``doc_type`` (:class:`DocumentType`), códigos E0 em ``e0_doc_type``,
metadados em ``classification_meta`` (inclui ``confidence`` e ``needs_review``).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from backend.app.models.document import DocumentType

# Alinhado ao fluxo descrito em ADR-079 / document_processor legado.
_CONTENT_CONFIDENCE_THRESHOLD = 0.8
_REVIEW_CONFIDENCE_THRESHOLD = 0.7

# P1.4 — classificação de erros do LLM (transiente vs permanente).
_TRANSIENT_ERROR_NAMES = frozenset({
    "APIConnectionError", "APITimeoutError", "ConnectionError",
    "ReadTimeout", "ConnectTimeout", "Timeout", "RateLimitError",
    "APIStatusError",
    "InternalServerError", "ServiceUnavailableError",
})
_PERMANENT_ERROR_NAMES = frozenset({
    "AuthenticationError", "PermissionDeniedError", "PermissionError",
    "BadRequestError", "NotFoundError", "UnprocessableEntityError",
    "InvalidRequestError", "APIKeyError",
})


def _classify_llm_error(exc: BaseException) -> str:
    """Return 'transient' | 'permanent' | 'unknown'."""
    name = type(exc).__name__
    if name in _TRANSIENT_ERROR_NAMES:
        return "transient"
    if name in _PERMANENT_ERROR_NAMES:
        return "permanent"

    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    try:
        status_code = int(status_code)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        status_code = None

    if status_code is not None:
        if status_code in (408, 429) or 500 <= status_code < 600:
            return "transient"
        if 400 <= status_code < 500:
            return "permanent"

    return "unknown"


def map_e0_doc_type_to_document_type(e0_doc_type: str) -> DocumentType:
    """Map E0-route doc_type string to :class:`DocumentType`.

    E0-route (``scripts/e0_route.py``) gera códigos como ``faturaunique``,
    ``extratocontabrl``, etc. Mantido alinhado a ``_build_doc_type_patterns``.
    """
    if not e0_doc_type:
        return DocumentType.other

    code = e0_doc_type.lower()

    if code.startswith("irpf") or code.startswith("informerendimento"):
        return DocumentType.irpf

    if (
        code.startswith("cdb")
        or code.startswith("investimentos")
        or code.startswith("carteirarenda")
        or code == "extratoinvest"
    ):
        return DocumentType.investment_report

    if code.startswith("fatura"):
        if code.startswith("faturaaluguel"):
            return DocumentType.other
        return DocumentType.credit_card_bill

    if code.startswith("extratoconta") or code.startswith("extratopoupanca"):
        return DocumentType.bank_statement

    return DocumentType.other


class ClassificationResult(BaseModel):
    """Resultado canônico do classificador (contrato P2)."""

    doc_type: DocumentType
    bank_code: str | None = None
    period: str | None = None
    dest_group: str | None = None
    e0_doc_type: str | None = None
    routed_path: str | None = None
    classification_meta: dict = Field(default_factory=dict)
    confidence: float = 0.0
    needs_review: bool = False

    def as_dict(self) -> dict:
        """Mesmo formato histórico usado por upload / API (enum Python em ``doc_type``)."""
        return self.model_dump(mode="python")


def classification_can_route_to_data(classification: dict) -> bool:
    """Mesmo critério que inbox → ``data/`` no upload e ``POST /reclassify``."""
    if classification.get("needs_review", False):
        return False
    return bool(
        classification.get("dest_group")
        and classification.get("e0_doc_type")
    )


def classify_document(file_path: Path, base_dir: Path, *, use_llm: bool = True) -> dict:
    """Classifica por conteúdo (regex → LLM opcional). **Não** usa nome do arquivo.

    Retorna dict com chaves legadas: ``doc_type``, ``bank_code``, ``period``,
    ``dest_group``, ``e0_doc_type``, ``routed_path``, ``classification_meta``,
    ``confidence``, ``needs_review``.
    """
    from scripts.e0_route import (
        _init_config as route_init_config,
        _extract_file_preview,
        classify_by_llm,
    )
    from backend.app.services.content_classifier import classify_file

    route_init_config(base_dir)

    content_result = classify_file(file_path, _extract_file_preview)
    meta: dict = {
        "source": content_result.source,
        "content": content_result.to_dict(),
    }

    best_type = content_result.doc_type
    best_institution = content_result.institution
    best_period = content_result.period
    best_dest_group = content_result.dest_group
    confidence = content_result.confidence

    if use_llm and confidence < _CONTENT_CONFIDENCE_THRESHOLD:
        llm_result = None
        try:
            llm_result = classify_by_llm(file_path)
        except Exception as exc:  # noqa: BLE001 — não derrubar upload
            kind = _classify_llm_error(exc)
            meta["llm_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            meta["llm_error_kind"] = kind

        if llm_result:
            meta["llm"] = llm_result
            llm_confidence = float(llm_result.get("confidence", 0.0) or 0.0)
            if llm_confidence > confidence:
                best_type = llm_result.get("doc_type") or best_type
                best_institution = llm_result.get("institution") or best_institution
                best_period = llm_result.get("period") or best_period
                best_dest_group = llm_result.get("dest_group") or best_dest_group
                confidence = llm_confidence
                meta["source"] = "llm_fallback"

    needs_review = confidence < _REVIEW_CONFIDENCE_THRESHOLD
    meta["confidence"] = confidence
    meta["needs_review"] = needs_review

    if not best_type:
        return ClassificationResult(
            doc_type=DocumentType.other,
            bank_code=best_institution,
            period=best_period,
            dest_group=None,
            e0_doc_type=None,
            routed_path=None,
            classification_meta=meta,
            confidence=confidence,
            needs_review=True,
        ).as_dict()

    return ClassificationResult(
        doc_type=map_e0_doc_type_to_document_type(best_type),
        bank_code=best_institution,
        period=best_period,
        dest_group=best_dest_group,
        e0_doc_type=best_type,
        routed_path=None,
        classification_meta=meta,
        confidence=confidence,
        needs_review=needs_review,
    ).as_dict()
