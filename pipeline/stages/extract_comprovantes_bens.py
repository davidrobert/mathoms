"""Stage runner extract_comprovantes_bens — comprovantes de bem polimórficos (ADR-239 D8)."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger("mathoms.pipeline.comprovantes_bens")

_LLM_MIN_TOKENS = 4_096
_MAX_DOCS_PER_RUN = 20
_NEEDS_REVIEW_CONFIDENCE_THRESHOLD = 0.7

# CPF detection (LGPD ADR-231): Python mask pós-LLM, nunca confiar no LLM.
_CPF_RAW_RE = re.compile(r"(?<!\d)(\d{3})(\d{3})(\d{3})(\d{2})(?!\d)")
_CPF_FORMATTED_RE = re.compile(r"(?<!\d)(\d{3})\.(\d{3})\.(\d{3})-(\d{2})(?!\d)")

# Filename patterns por tipo_comprovante. L1 cobre crlv apenas;
# V2 estende para imóveis (rgi/iptu) e outros bens.
_TIPO_FILENAME_TOKENS: dict[str, tuple[str, ...]] = {
    "crlv": (
        "crlv",
        "licenciamento",
        "renavam",
        "denatran",
    ),
}


def _redact_placa(placa: str) -> str:
    if not placa or len(placa) < 4:
        return "***"
    return f"{placa[:3]}***{placa[-1]}"


def _mask_cpf(cpf: str) -> str:
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11:
        return ""
    return f"***.{digits[3:6]}.{digits[6:9]}-**"


def _extract_titular_cpf_masked(text: str) -> str | None:
    """Extrai 1º CPF do texto e mascara em Python (LGPD ADR-231; nunca confiar no LLM)."""
    m = _CPF_FORMATTED_RE.search(text) or _CPF_RAW_RE.search(text)
    if m is None:
        return None
    return _mask_cpf("".join(m.groups()))


def _content_hash(doc: Path) -> str:
    """SHA-256 do PDF para cache key idempotente (ADR-144 padrão A17 L1 P2)."""
    h = hashlib.sha256()
    with doc.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_tipo_comprovante(filename: str) -> str | None:
    lowered = filename.lower()
    for tipo, tokens in _TIPO_FILENAME_TOKENS.items():
        if any(token in lowered for token in tokens):
            return tipo
    return None


def _find_comprovantes(ctx: WorkspaceContext) -> list[Path]:
    """Localiza PDFs em ``data/comprovantes/`` cujo filename indica comprovante de bem."""
    base = ctx.data_dir / "comprovantes"
    if not base.exists():
        return []
    out: list[Path] = []
    for f in sorted(base.rglob("*")):
        if not f.is_file() or f.suffix.lower() != ".pdf":
            continue
        if _detect_tipo_comprovante(f.name):
            out.append(f)
    return out


def _artifact_key_for(tipo: str, placa: str, ano_exercicio: int | None) -> str:
    """Compõe ``<tipo>_<placa_normalizada>_<exercicio>`` (ADR-239 D8)."""
    ano_part = str(ano_exercicio) if ano_exercicio is not None else "ano_desconhecido"
    return f"{tipo}_{placa}_{ano_part}"


def _stem_for_filename(name: str) -> str:
    for ext in (".pdf", ".PDF"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    if "-0_original" in name:
        name = name.split("-0_original")[0]
    return name


def _build_user_prompt(doc_name: str, text: str) -> str:
    from pipeline.llm.prompts import crlv as prompt_mod

    return prompt_mod.USER_PROMPT_TEMPLATE.format(filename=doc_name, document_text=text)


def _call_llm_crlv(service, config, doc_name: str, text: str, content_hash: str):
    from pipeline.llm.prompts import crlv as prompt_mod
    from pipeline.llm.schemas.crlv import CRLVPayload

    cache_key = f"extract_comprovantes_bens:{content_hash[:16]}:{prompt_mod.PROMPT_VERSION}"
    result = service.call(
        system_prompt=prompt_mod.SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(doc_name, text),
        output_schema=CRLVPayload,
        max_tokens=max(config.max_tokens, _LLM_MIN_TOKENS),
        stage=cache_key,
    )
    return result, prompt_mod.PROMPT_VERSION


def _build_payload(output, prompt_version: str, doc_text: str, source_artifact_id: str) -> dict:
    """Materializa payload + força prompt_version + mask CPF Python + source_artifact_id."""
    payload = output.model_dump(mode="json")
    payload["prompt_version"] = prompt_version
    payload["source_artifact_id"] = source_artifact_id
    # LGPD: NUNCA confiar no LLM para mascarar CPF.
    payload["proprietario_cpf_masked"] = _extract_titular_cpf_masked(doc_text)
    confidence = payload.get("confidence", 1.0)
    if confidence < _NEEDS_REVIEW_CONFIDENCE_THRESHOLD:
        payload["needs_review"] = True
    return payload


def _extract_crlv(doc: Path, text: str, service, config) -> tuple[dict, Any, str]:
    """Caminho CRLV — content_hash + LLM Haiku + payload com lineage."""
    content_hash = _content_hash(doc)
    result, prompt_version = _call_llm_crlv(service, config, doc.name, text, content_hash)
    source_artifact_id = _stem_for_filename(doc.name)
    payload = _build_payload(result.output, prompt_version, text, source_artifact_id)
    return payload, result, prompt_version


def _extract_one(
    doc: Path, text: str, service, config, tipo_comprovante: str
) -> tuple[dict, Any, str]:
    """Despacho por tipo_comprovante; L1 só implementa crlv."""
    if tipo_comprovante == "crlv":
        return _extract_crlv(doc, text, service, config)
    raise NotImplementedError(
        f"tipo_comprovante={tipo_comprovante!r} ainda não implementado em A18 L1. "
        f"V2 cobre imóveis (rgi/iptu) e outros bens."
    )


def _extract_text(doc: Path) -> str:
    from pipeline.llm.text_extractor import DocumentTextExtractor

    return DocumentTextExtractor(max_chars=40_000).extract(doc)


def _log_run(doc_name: str, ws_id: str, payload: dict, result, outcome: str) -> None:
    """Telemetria LGPD-safe (ADR-239 + ADR-231). Sem PII, sem valor monetário."""
    logger.info(
        "mathoms.comprovantes.classified",
        extra={
            "workspace_id": ws_id,
            "doc": _redact_filename_pii(doc_name),
            "tipo_comprovante": "crlv",
            "placa_redacted": _redact_placa(payload.get("placa", "")),
            "ano_exercicio": payload.get("exercicio"),
            "confidence": payload.get("confidence"),
            "needs_review": payload.get("needs_review", False),
            "upsert_outcome": outcome,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_estimate_usd,
        },
    )


def _redact_filename_pii(name: str) -> str:
    name = _CPF_FORMATTED_RE.sub("<cpf-redacted>", name)
    name = _CPF_RAW_RE.sub("<cpf-redacted>", name)
    return name


def _upsert_in_db(ws_id: str, payload: dict):
    """Upsert em vehicles via service (boundary backend; pipeline puro só dispara)."""
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.vehicle_upsert import upsert_vehicle_from_payload

    with SyncSessionLocal() as db:
        upsert = upsert_vehicle_from_payload(ws_id, payload, db=db)
        db.commit()
    return upsert


def _processed_summary(
    doc: Path, payload: dict, key: str, tipo: str, ano, upsert
) -> dict[str, Any]:
    return {
        "file": _redact_filename_pii(doc.name),
        "artifact_key": key,
        "tipo_comprovante": tipo,
        "placa_redacted": _redact_placa(payload.get("placa", "")),
        "ano_exercicio": ano,
        "confidence": payload.get("confidence"),
        "needs_review": payload.get("needs_review", False)
        or upsert.outcome.value == "needs_review",
        "upsert_outcome": upsert.outcome.value,
        "upsert_reason": upsert.reason,
    }


def _persist_processed(
    doc: Path, payload: dict, result, ctx: WorkspaceContext, ws_id: str
) -> dict[str, Any]:
    """Persiste artifact + upsert em vehicles + emite log estruturado."""
    placa = payload.get("placa", "")
    tipo = "crlv"
    ano = payload.get("exercicio")
    key = _artifact_key_for(tipo, placa, ano)
    ctx.get_artifact_store().write("extract_comprovantes_bens", key, payload)
    upsert = _upsert_in_db(ws_id, payload)
    _log_run(doc.name, ws_id, payload, result, upsert.outcome.value)
    return _processed_summary(doc, payload, key, tipo, ano, upsert)


def _err(doc: Path, exc_or_msg) -> dict[str, str]:
    return {"file": _redact_filename_pii(doc.name), "error": str(exc_or_msg)[:300]}


def _process_doc_safe(
    doc: Path, ctx: WorkspaceContext, service, config
) -> tuple[dict | None, dict | None]:
    """Processa 1 doc capturando erros; retorna (processed_summary, error_dict)."""
    try:
        payload, result = _process_one(doc, ctx, service, config)
    except NotImplementedError as exc:
        return None, _err(doc, exc)
    except Exception as exc:
        logger.error(
            "extract_comprovantes_bens failed for %s: %s",
            _redact_filename_pii(doc.name),
            exc,
        )
        return None, _err(doc, exc)
    if payload is None:
        return None, _err(doc, result)
    ws_id = getattr(ctx, "workspace_id", "unknown")
    return _persist_processed(doc, payload, result, ctx, ws_id), None


def _process_one(
    doc: Path, ctx: WorkspaceContext, service, config
) -> tuple[dict, Any] | tuple[None, str]:
    """Processa 1 doc; retorna (payload, result) ou (None, error_message)."""
    tipo = _detect_tipo_comprovante(doc.name)
    if tipo is None:
        return None, f"filename não casa tipo_comprovante: {_redact_filename_pii(doc.name)}"
    text = _extract_text(doc)
    if not text.strip():
        return None, f"texto vazio extraído de {_redact_filename_pii(doc.name)}"
    payload, result, _ = _extract_one(doc, text, service, config, tipo)
    return payload, result


def _bootstrap_or_skip(ctx: WorkspaceContext):
    """Resolve config LLM + docs ou retorna dict ``{"skipped": True, "reason": ...}``."""
    from pipeline.llm.litellm_client import LLMConfig, LLMService

    cfg = ctx.load_config("llm_config.json")
    if not cfg or not cfg.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}
    docs = _find_comprovantes(ctx)
    if not docs:
        return {"skipped": True, "reason": "No comprovantes de bem found"}
    llm_config = LLMConfig(**cfg)
    return docs[:_MAX_DOCS_PER_RUN], LLMService(llm_config), llm_config


def _summarize(processed: list[dict], errors: list[dict]) -> dict[str, Any]:
    return {
        "success": len(errors) == 0,
        "processed": processed,
        "errors": errors,
        "total_processed": len(processed),
        "total_errors": len(errors),
    }


def run(ctx: WorkspaceContext) -> dict[str, Any]:
    """Executa extração de comprovantes de bem — L1 cobre CRLV (ADR-239)."""
    bootstrap = _bootstrap_or_skip(ctx)
    if isinstance(bootstrap, dict):
        return bootstrap
    docs, service, llm_config = bootstrap
    processed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for doc in docs:
        summary, err = _process_doc_safe(doc, ctx, service, llm_config)
        if err is not None:
            errors.append(err)
        if summary is not None:
            processed.append(summary)
    return _summarize(processed, errors)
