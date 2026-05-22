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

# Filename patterns por tipo_comprovante. L1 cobre crlv + apolice (L2);
# V2 estende para imóveis (rgi/iptu) e outros bens.
_TIPO_FILENAME_TOKENS: dict[str, tuple[str, ...]] = {
    "crlv": (
        "crlv",
        "licenciamento",
        "renavam",
        "denatran",
    ),
    "apolice": (
        "apolice",
        "apolice_seguro",
        "seguro_",  # underscore evita match em "segurado"/"segurador" inline
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


# ===========================================================================
# Apólice — cascata Haiku → Sonnet (ADR-239 D6)
# ===========================================================================

# Strings que disparam cascata para Sonnet quando detectadas no texto do PDF
# (caso V1 obrigatório: combinada Porto = Toro + residência num único PDF).
_CASCADE_TRIGGER_STRINGS = (
    "combinada",
    "proteção combinada",
    "residencial+auto",
    "residencial + auto",
    "multi-bem",
)


def _build_apolice_user_prompt(doc_name: str, text: str) -> str:
    from pipeline.llm.prompts import apolice as prompt_mod

    return prompt_mod.USER_PROMPT_TEMPLATE.format(filename=doc_name, document_text=text)


def _call_llm_apolice(service, config, doc_name: str, text: str, content_hash: str, model: str):
    """LLM call para apólice com `model` injetado (haiku ou sonnet) — ADR-144 cache key inclui modelo."""
    from pipeline.llm.prompts import apolice as prompt_mod
    from pipeline.llm.schemas.apolice import ApolicePayload

    cache_key = (
        f"extract_comprovantes_bens:apolice:{model}:{content_hash[:16]}:"
        f"{prompt_mod.PROMPT_VERSION}"
    )
    result = service.call(
        system_prompt=prompt_mod.SYSTEM_PROMPT,
        user_prompt=_build_apolice_user_prompt(doc_name, text),
        output_schema=ApolicePayload,
        max_tokens=max(config.max_tokens, _LLM_MIN_TOKENS),
        stage=cache_key,
        model=model,
    )
    return result, prompt_mod.PROMPT_VERSION


def _cascade_needed(payload: dict, text: str) -> bool:
    """ADR-239 D6: cascata Sonnet quando combinada OU confidence baixo OU strings textuais."""
    bens = payload.get("bens_segurados") or []
    if len(bens) > 1:
        return True
    confidence = payload.get("confidence", 1.0)
    if confidence < _NEEDS_REVIEW_CONFIDENCE_THRESHOLD:
        return True
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in _CASCADE_TRIGGER_STRINGS)


def _build_apolice_payload(
    output, prompt_version: str, doc_text: str, source_artifact_id: str, cascade_triggered: bool
) -> dict:
    """Payload apólice + mask CPFs (pagador + segurado) Python pós-LLM (LGPD ADR-231 D8)."""
    payload = output.model_dump(mode="json")
    payload["prompt_version"] = prompt_version
    payload["source_artifact_id"] = source_artifact_id
    payload["cascade_triggered"] = cascade_triggered
    # LGPD: mascara CPF do texto livre (LLM SEMPRE retorna null nos campos cpf_masked).
    cpf_first = _extract_titular_cpf_masked(doc_text)
    payload["pagador_cpf_masked"] = cpf_first
    payload["segurado_cpf_masked"] = cpf_first
    # Placeholder V1 — sinistro só entra em V2 com ADR-238 integração.
    payload["sinistro_indenizacao_recebida_brl"] = None
    confidence = payload.get("confidence", 1.0)
    if confidence < _NEEDS_REVIEW_CONFIDENCE_THRESHOLD:
        payload["needs_review"] = True
    return payload


def _apolice_haiku_first(doc: Path, text: str, service, config):
    """Primeira call em Haiku (cheap); retorna (result, prompt_version, payload_dict)."""
    content_hash = _content_hash(doc)
    result, prompt_version = _call_llm_apolice(
        service, config, doc.name, text, content_hash, model="haiku"
    )
    return result, prompt_version, content_hash, result.output.model_dump(mode="json")


def _extract_apolice(doc: Path, text: str, service, config) -> tuple[dict, Any, str]:
    """Apólice — Haiku primeiro; cascata Sonnet se gate triggered (ADR-239 D6)."""
    haiku_result, prompt_version, content_hash, haiku_payload = _apolice_haiku_first(
        doc, text, service, config
    )
    source_artifact_id = _stem_for_filename(doc.name)
    if not _cascade_needed(haiku_payload, text):
        payload = _build_apolice_payload(
            haiku_result.output, prompt_version, text, source_artifact_id, cascade_triggered=False
        )
        return payload, haiku_result, prompt_version
    sonnet_result, _ = _call_llm_apolice(
        service, config, doc.name, text, content_hash, model="sonnet"
    )
    payload = _build_apolice_payload(
        sonnet_result.output, prompt_version, text, source_artifact_id, cascade_triggered=True
    )
    return payload, sonnet_result, prompt_version


def _extract_one(
    doc: Path, text: str, service, config, tipo_comprovante: str
) -> tuple[dict, Any, str]:
    """Despacho por tipo_comprovante (ADR-239 D8): L1 cobre crlv; L2 adiciona apolice."""
    if tipo_comprovante == "crlv":
        return _extract_crlv(doc, text, service, config)
    if tipo_comprovante == "apolice":
        return _extract_apolice(doc, text, service, config)
    raise NotImplementedError(
        f"tipo_comprovante={tipo_comprovante!r} ainda não implementado em A18 L1/L2. "
        f"V2 cobre imóveis (rgi/iptu) e outros bens."
    )


def _extract_text(doc: Path) -> str:
    from pipeline.llm.text_extractor import DocumentTextExtractor

    return DocumentTextExtractor(max_chars=40_000).extract(doc)


def _telemetry_extra(doc_name: str, ws_id: str, payload: dict, result, outcome: str, tipo: str):
    """Monta extras do log; isolado para manter _log_run dentro do limite (≤20L)."""
    return {
        "workspace_id": ws_id,
        "doc": _redact_filename_pii(doc_name),
        "tipo_comprovante": tipo,
        "placa_redacted": _redact_placa(payload.get("placa", "")),
        "ano_exercicio": payload.get("exercicio") or payload.get("vigencia_inicio"),
        "confidence": payload.get("confidence"),
        "needs_review": payload.get("needs_review", False),
        "upsert_outcome": outcome,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": result.cost_estimate_usd,
        "cascade_triggered": payload.get("cascade_triggered", False),
        "bens_count": len(payload.get("bens_segurados") or []),
    }


def _log_run(doc_name: str, ws_id: str, payload: dict, result, outcome: str, tipo: str) -> None:
    """Telemetria LGPD-safe (ADR-239 + ADR-231). Sem PII, sem valor monetário."""
    logger.info(
        "mathoms.comprovantes.classified",
        extra=_telemetry_extra(doc_name, ws_id, payload, result, outcome, tipo),
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
    needs_review = payload.get("needs_review", False)
    upsert_outcome = upsert.outcome.value if upsert is not None else "skipped"
    upsert_reason = upsert.reason if upsert is not None else None
    if upsert is not None and upsert.outcome.value == "needs_review":
        needs_review = True
    return {
        "file": _redact_filename_pii(doc.name),
        "artifact_key": key,
        "tipo_comprovante": tipo,
        "placa_redacted": _redact_placa(payload.get("placa", "")),
        "ano_exercicio": ano,
        "confidence": payload.get("confidence"),
        "needs_review": needs_review,
        "upsert_outcome": upsert_outcome,
        "upsert_reason": upsert_reason,
    }


def _reconcile_apolice_against_db(payload: dict, *, workspace_id: str) -> dict:
    """ADR-239 D3 — try/except backend; degrada graceful. Muta payload in-place."""
    runner = _try_import_apolice_runner()
    if runner is None:
        return payload
    reconcile_fn, session_factory = runner
    return _invoke_apolice_reconciliation(reconcile_fn, session_factory, workspace_id, payload)


def _try_import_apolice_runner():
    """Try-import do runner backend; None se indisponível (CLI/tests sem DB)."""
    try:
        from backend.app.core.database import SyncSessionLocal
        from backend.app.services.apolice_reconciliation_runner import reconcile_apolice_with_db
    except Exception as exc:  # noqa: BLE001
        logger.info("apolice reconciliation skipped (backend unavailable: %s)", exc)
        return None
    return reconcile_apolice_with_db, SyncSessionLocal


def _invoke_apolice_reconciliation(reconcile_fn, session_factory, workspace_id, payload):
    """Helper isolado — degradação graceful em runtime."""
    try:
        with session_factory() as db:
            new_payload, _ = reconcile_fn(workspace_id, payload, db=db)
            return new_payload
    except Exception as exc:  # noqa: BLE001
        logger.warning("apolice reconciliation failed: %s", exc)
        return payload


def _apolice_artifact_key(payload: dict) -> str:
    """Key apólice = ``apolice_<numero_sanitized>_<vigencia_ano>`` (ADR-239 D7 temporal)."""
    numero = payload.get("apolice_numero", "")
    sanitized = re.sub(r"[^A-Za-z0-9\-]", "_", numero) or "sem_numero"
    vigencia_inicio = payload.get("vigencia_inicio") or ""
    ano = (
        vigencia_inicio[:4]
        if isinstance(vigencia_inicio, str) and len(vigencia_inicio) >= 4
        else "ano_desconhecido"
    )
    return f"apolice_{sanitized}_{ano}"


def _persist_processed(
    doc: Path, payload: dict, result, ctx: WorkspaceContext, ws_id: str, tipo: str
) -> dict[str, Any]:
    """Persiste artifact + upsert (CRLV) ou apenas artifact (apólice — reconciliação P4)."""
    if tipo == "crlv":
        placa = payload.get("placa", "")
        ano = payload.get("exercicio")
        key = _artifact_key_for(tipo, placa, ano)
        ctx.get_artifact_store().write("extract_comprovantes_bens", key, payload)
        upsert = _upsert_in_db(ws_id, payload)
        _log_run(doc.name, ws_id, payload, result, upsert.outcome.value, tipo)
        return _processed_summary(doc, payload, key, tipo, ano, upsert)
    # Apólice — reconciliação assíncrona contra vehicles + property_identity (ADR-239 D3).
    payload = _reconcile_apolice_against_db(payload, workspace_id=ws_id)
    key = _apolice_artifact_key(payload)
    ctx.get_artifact_store().write("extract_comprovantes_bens", key, payload)
    ano = int(key.rsplit("_", 1)[-1]) if key.rsplit("_", 1)[-1].isdigit() else None
    _log_run(doc.name, ws_id, payload, result, "no_upsert", tipo)
    return _processed_summary(doc, payload, key, tipo, ano, upsert=None)


def _err(doc: Path, exc_or_msg) -> dict[str, str]:
    return {"file": _redact_filename_pii(doc.name), "error": str(exc_or_msg)[:300]}


def _process_doc_safe(
    doc: Path, ctx: WorkspaceContext, service, config
) -> tuple[dict | None, dict | None]:
    """Processa 1 doc capturando erros; retorna (processed_summary, error_dict)."""
    try:
        triple = _process_one(doc, ctx, service, config)
    except NotImplementedError as exc:
        return None, _err(doc, exc)
    except Exception as exc:
        logger.error(
            "extract_comprovantes_bens failed for %s: %s",
            _redact_filename_pii(doc.name),
            exc,
        )
        return None, _err(doc, exc)
    if triple[0] is None:
        return None, _err(doc, triple[1])
    payload, result, tipo = triple
    ws_id = getattr(ctx, "workspace_id", "unknown")
    return _persist_processed(doc, payload, result, ctx, ws_id, tipo), None


def _process_one(
    doc: Path, ctx: WorkspaceContext, service, config
) -> tuple[dict, Any, str] | tuple[None, str, str]:
    """Processa 1 doc; retorna (payload, result, tipo) ou (None, error_message, '')."""
    tipo = _detect_tipo_comprovante(doc.name)
    if tipo is None:
        return None, f"filename não casa tipo_comprovante: {_redact_filename_pii(doc.name)}", ""
    text = _extract_text(doc)
    if not text.strip():
        return None, f"texto vazio extraído de {_redact_filename_pii(doc.name)}", ""
    payload, result, _ = _extract_one(doc, text, service, config, tipo)
    return payload, result, tipo


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
