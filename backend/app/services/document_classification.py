"""Classificação unificada de documentos (P2).

Única implementação usada por upload web, ``POST /documents/reclassify``,
``scripts/e0_route.route_file`` (quando o backend está importável) e scripts
de manutenção. Ver ADR-081 em ``docs/DECISIONS.md``.

Saída: ``doc_type`` (:class:`DocumentType`), códigos E0 em ``e0_doc_type``,
metadados em ``classification_meta`` (inclui ``confidence`` e ``needs_review``).
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

from backend.app.models.document import DocumentType

# Alinhado ao fluxo descrito em ADR-079 / document_processor legado.
_CONTENT_CONFIDENCE_THRESHOLD = 0.8
_REVIEW_CONFIDENCE_THRESHOLD = 0.7

# P1.4 — classificação de erros do LLM (transiente vs permanente).
_TRANSIENT_ERROR_NAMES = frozenset(
    {
        "APIConnectionError",
        "APITimeoutError",
        "ConnectionError",
        "ReadTimeout",
        "ConnectTimeout",
        "Timeout",
        "RateLimitError",
        "APIStatusError",
        "InternalServerError",
        "ServiceUnavailableError",
    }
)
_PERMANENT_ERROR_NAMES = frozenset(
    {
        "AuthenticationError",
        "PermissionDeniedError",
        "PermissionError",
        "BadRequestError",
        "NotFoundError",
        "UnprocessableEntityError",
        "InvalidRequestError",
        "APIKeyError",
    }
)


def _llm_prerequisites_skip_reason() -> str | None:
    """Pré-cheque silencioso: ``sdk_not_installed`` | ``missing_api_key`` | ``None``."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return "sdk_not_installed"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "missing_api_key"
    return None


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


_INFORME_TIPADO_PREFIXES = ("informe_previdencia", "informe_financeiro", "informe_proventos")
_INVESTMENT_PREFIXES = ("cdb", "investimentos", "carteirarenda")
# ADR-239 A18 L1 — CRLV-e em L1; A18 V2 estende para RGI/IPTU (imóveis) etc.
_COMPROVANTE_BEM_PREFIXES = ("crlv_eletronico", "crlv")


def _map_informe(code: str) -> DocumentType | None:
    """ADR-238 A17 L1 P3: informe anual tipado vai para enum próprio (não .irpf)."""
    if any(code.startswith(p) for p in _INFORME_TIPADO_PREFIXES):
        return DocumentType.informe_rendimentos_anuais
    if code.startswith("informerendimentosaluguel"):
        # ADR-216 aluguel — vive em .other até cutover separado.
        return DocumentType.other
    if code.startswith("informerendimento"):
        # Genérico legado (sem tipo específico) mantém compat com .irpf.
        return DocumentType.irpf
    return None


def _map_comprovante_bem(code: str) -> DocumentType | None:
    """ADR-239 A18 L1 P3: CRLV-e e demais comprovantes de bem vão para enum próprio."""
    if any(code.startswith(p) for p in _COMPROVANTE_BEM_PREFIXES):
        return DocumentType.comprovante_bem
    return None


def _map_fatura(code: str) -> DocumentType:
    return DocumentType.other if code.startswith("faturaaluguel") else DocumentType.credit_card_bill


def map_e0_doc_type_to_document_type(e0_doc_type: str) -> DocumentType:
    """Map E0-route doc_type string to :class:`DocumentType`."""
    if not e0_doc_type:
        return DocumentType.other
    code = e0_doc_type.lower()
    informe = _map_informe(code)
    if informe is not None:
        return informe
    comprovante = _map_comprovante_bem(code)
    if comprovante is not None:
        return comprovante
    if code.startswith("irpf"):
        return DocumentType.irpf
    if any(code.startswith(p) for p in _INVESTMENT_PREFIXES) or code == "extratoinvest":
        return DocumentType.investment_report
    if code.startswith("fatura"):
        return _map_fatura(code)
    if code.startswith("extratoconta") or code.startswith("extratopoupanca"):
        return DocumentType.bank_statement
    return DocumentType.other


# Reverse mapping: cada DocumentType → (e0_doc_type canônico, dest_group).
# Usado quando o usuário corrige doc_type via PATCH e o arquivo precisa ser
# renomeado para o filename canônico que o pipeline reconhece.
_DOCUMENT_TYPE_TO_E0_DEST: dict[DocumentType, tuple[str, str]] = {
    DocumentType.bank_statement: ("extratoconta", "financial_statements"),
    DocumentType.credit_card_bill: ("fatura", "financial_statements"),
    DocumentType.investment_report: ("investimentosposicao", "financial_statements"),
    DocumentType.irpf: ("irpfdeclaracao", "income_tax_br"),
    # ADR-238 (A17 L1) — informe anual avulso. Override do tipo via PATCH
    # cai no canonical de previdência (P1 cobre apenas esse tipo); L2-L4
    # adicionam canonicals próprios (financeiro_pj/pf/proventos).
    DocumentType.informe_rendimentos_anuais: ("informe_previdencia_privada", "income_tax_br"),
    # ADR-239 (A18 L1) — comprovante de bem. Override cai em CRLV (V1 cobre só
    # veículos); A18 V2 adiciona canonicals para imóveis (rgi/iptu) e outros.
    DocumentType.comprovante_bem: ("crlv_eletronico", "comprovantes"),
}


def document_type_to_e0_dest(doc_type: DocumentType) -> tuple[str, str] | None:
    """Reverse de :func:`map_e0_doc_type_to_document_type` para rename pós-override (None para tipos sem padrão canônico: ``other``, ``e1_*_json``)."""
    return _DOCUMENT_TYPE_TO_E0_DEST.get(doc_type)


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
    return bool(classification.get("dest_group") and classification.get("e0_doc_type"))


def classify_document(file_path: Path, base_dir: Path, *, use_llm: bool = True) -> dict:
    """Classifica por conteúdo (regex → LLM opcional). **Não** usa nome do arquivo.

    Retorna dict com chaves legadas: ``doc_type``, ``bank_code``, ``period``,
    ``dest_group``, ``e0_doc_type``, ``routed_path``, ``classification_meta``,
    ``confidence``, ``needs_review``.
    """
    from backend.app.services.content_classifier import classify_file
    from scripts.e0_route import (
        _extract_file_preview,
        classify_by_llm,
    )
    from scripts.e0_route import (
        _init_config as route_init_config,
    )

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
        skip_reason = _llm_prerequisites_skip_reason()
        if skip_reason is not None:
            meta["llm_skipped_reason"] = skip_reason
        else:
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
            elif "llm_error" not in meta:
                # classify_by_llm devolveu None sem exceção: confidence < threshold,
                # JSON inválido, retries esgotados, ou import/key falhou dentro do
                # script. Marca explicitamente p/ diferenciar de "LLM nem foi chamado".
                meta["llm_skipped_reason"] = "no_result"

    needs_review = confidence < _REVIEW_CONFIDENCE_THRESHOLD
    if content_result.force_review:
        needs_review = True
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
