"""Stage runner E1.6 (`extract_irpf_full`) — ADR-157."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger("mathoms.pipeline.e16")

# Reda CPF em filenames antes de virar log JSON. Usa lookarounds em vez de \b
# para tolerar underscore (filename clássico tipo "decl_99988877766.pdf").
_FILENAME_CPF_MASKED = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_FILENAME_CPF_LOOSE = re.compile(r"(?<!\d)\d{11}(?!\d)")


def _redact_filename_pii(name: str) -> str:
    """Mascara CPF (com ou sem pontuação) em nomes de arquivo antes de logar."""
    name = _FILENAME_CPF_MASKED.sub("<cpf-redacted>", name)
    name = _FILENAME_CPF_LOOSE.sub("<cpf-redacted>", name)
    return name


# Mesma justificativa de E1.5: payload IRPF é grande e completions abaixo de
# 16k truncam structured output.
_E16_MIN_COMPLETION_TOKENS = 16_384
_MAX_DOCS_PER_RUN = 10
_RECONCILE_FAIL_CONFIDENCE_CAP = 0.7

_KNOWN_TOP_LEVEL_FIELDS = frozenset(
    {
        "contribuinte",
        "rendimentos_pj",
        "rendimentos_pf",
        "rendimentos_exterior",
        "rendimentos_isentos",
        "rendimentos_tributacao_exclusiva",
        "pagamentos_efetuados",
        "dividas_onus",
        "imposto_apurado",
        "dependentes",
        "bens_direitos",
        "confidence",
        "notes",
        "prompt_version",
        "needs_review",
        "validation",
    }
)


def _find_irpf_declarations(ctx: WorkspaceContext) -> list[Path]:
    """Filtra apenas declarações IRPF (recibos não entram — só comprovam envio)."""
    income_dir = ctx.data_dir / "income_tax_br"
    if not income_dir.exists():
        return []
    out: list[Path] = []
    for f in sorted(income_dir.rglob("*")):
        if not f.is_file() or f.suffix.lower() != ".pdf":
            continue
        if "irpfdeclaracao" in f.name.lower():
            out.append(f)
    return out


def _artifact_key_for(doc: Path) -> str:
    """Stem para artifact_key — paridade com E1.5a (strip de ``-0_original``)."""
    name = doc.name
    lowered = name.lower()
    stem = doc.stem
    for ext in (".pdf", ".xlsx", ".xls", ".csv", ".json"):
        if lowered.endswith(ext):
            stem = name[: -len(ext)]
            break
    if "-0_original" in stem:
        stem = stem.split("-0_original")[0]
    return stem


def _emit_phase(
    ctx: WorkspaceContext, doc_name: str | None, idx: int, total: int, phase: str, estimated=None
) -> None:
    from pipeline.live_progress import emit_item_progress

    emit_item_progress(
        ctx.pipeline_run_id,
        "extract_irpf_full",
        current_item=doc_name,
        items_done=idx,
        items_total=total,
        phase=phase,
        estimated_duration_ms=estimated,
    )


def _call_llm(service, config, doc_name: str, text: str):
    from pipeline.llm.prompts.e16_irpf_full import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

    user_prompt = USER_PROMPT_TEMPLATE.format(documents_text=f"=== {doc_name} ===\n{text}")
    return service.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=IRPFFullOutput,
        max_tokens=max(config.max_tokens, _E16_MIN_COMPLETION_TOKENS),
        stage="extract_irpf_full",
    )


def _build_payload(output, validation, prompt_version: str) -> dict:
    """Aplica cap de confidence se reconciliação cross-field falhou (ADR-157)."""
    payload = output.model_dump(mode="json")
    reconcile_failed = any("divergente" in w for w in validation.warnings)
    if reconcile_failed and payload.get("confidence", 1.0) > _RECONCILE_FAIL_CONFIDENCE_CAP:
        payload["confidence"] = _RECONCILE_FAIL_CONFIDENCE_CAP
        payload["needs_review"] = True
    payload["prompt_version"] = prompt_version
    payload["validation"] = validation.to_dict()
    return payload


def _scan_unknown_top_level_fields(payload: dict, ws_id: str) -> None:
    """ADR-157 sub-decisão 4: WARNING quando top-level traz campo desconhecido."""
    for k in payload.keys():
        if k not in _KNOWN_TOP_LEVEL_FIELDS:
            logger.warning("e16_unknown_field", extra={"field": k, "workspace_id": ws_id})


def _process_one(
    doc: Path,
    text: str,
    ctx: WorkspaceContext,
    service,
    config,
    prompt_version: str,
    idx: int,
    total: int,
    estimated,
) -> tuple[dict, "object"]:
    from pipeline.llm.validators import validate_e16_output

    _emit_phase(ctx, doc.name, idx, total, "preparing", estimated if idx == 0 else None)
    _emit_phase(ctx, doc.name, idx, total, "awaiting_llm")
    result = _call_llm(service, config, doc.name, text)
    _emit_phase(ctx, doc.name, idx, total, "validating")
    validation = validate_e16_output(result.output)
    payload = _build_payload(result.output, validation, prompt_version)
    return payload, result


def _extract_texts(docs: list[Path]) -> list[tuple[Path, str]]:
    from pipeline.llm.text_extractor import DocumentTextExtractor

    extractor = DocumentTextExtractor(max_chars=80_000)
    out: list[tuple[Path, str]] = []
    for doc in docs[:_MAX_DOCS_PER_RUN]:
        text = extractor.extract(doc)
        if text.strip():
            out.append((doc, text))
    return out


def _log_run(doc_name: str, ws_id: str, payload: dict, result) -> None:
    ano_base = (payload.get("contribuinte") or {}).get("ano_base")
    logger.info(
        "extract_irpf_full",
        extra={
            "workspace_id": ws_id,
            "doc": _redact_filename_pii(doc_name),
            "ano_base": ano_base,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_estimate_usd,
        },
    )


def _new_accumulator() -> dict:
    return {
        "payloads": [],
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "errors": [],
        "warnings": [],
    }


def _persist_and_accumulate(
    payload: dict, result, doc: Path, ctx, ws_id: str, idx: int, total: int, acc: dict
) -> None:
    store = ctx.get_artifact_store()
    _log_run(doc.name, ws_id, payload, result)
    _scan_unknown_top_level_fields(payload, ws_id)
    _emit_phase(ctx, doc.name, idx, total, "persisting")
    store.write("extract_irpf_full", _artifact_key_for(doc), payload)
    acc["payloads"].append(payload)
    acc["tokens_in"] += result.tokens_in
    acc["tokens_out"] += result.tokens_out
    acc["cost_usd"] += result.cost_estimate_usd
    v = payload.get("validation") or {}
    acc["errors"].extend(v.get("errors", []))
    acc["warnings"].extend(v.get("warnings", []))


def _process_loop(docs_with_text, ctx, service, config, prompt_version, ws_id, estimated) -> dict:
    total = len(docs_with_text)
    acc = _new_accumulator()
    for idx, (doc, text) in enumerate(docs_with_text):
        payload, result = _process_one(
            doc, text, ctx, service, config, prompt_version, idx, total, estimated
        )
        _persist_and_accumulate(payload, result, doc, ctx, ws_id, idx, total, acc)
    _emit_phase(ctx, None, total, total, "finalizing")
    return acc


def _build_result_summary(loop_result: dict) -> dict:
    payloads = loop_result["payloads"]
    return {
        "success": True,
        "declarations_extracted": len(payloads),
        "anos_base": [(p.get("contribuinte") or {}).get("ano_base") for p in payloads],
        "tokens": {"in": loop_result["tokens_in"], "out": loop_result["tokens_out"]},
        "cost_usd": loop_result["cost_usd"],
        "validation": {
            "valid": not loop_result["errors"],
            "errors": loop_result["errors"],
            "warnings": loop_result["warnings"],
        },
    }


def _select_runnable_docs(ctx: WorkspaceContext):
    docs = _find_irpf_declarations(ctx)
    if not docs:
        return {"skipped": True, "reason": "No IRPF declarations found"}
    docs_with_text = _extract_texts(docs)
    if not docs_with_text:
        return {"skipped": True, "reason": "No extractable text in IRPF declarations"}
    return docs_with_text


def run(ctx: WorkspaceContext) -> dict:
    """Execute E1.6 IRPF full extraction via LLM, per-declaration (ADR-157)."""
    from pipeline.llm.litellm_client import LLMConfig, LLMService
    from pipeline.llm.prompts.e16_irpf_full import PROMPT_VERSION

    cfg = ctx.load_config("llm_config.json")
    if not cfg or not cfg.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}
    runnable = _select_runnable_docs(ctx)
    if isinstance(runnable, dict):
        return runnable
    llm_config = LLMConfig(**cfg)
    ws_id = getattr(ctx, "workspace_id", "unknown")
    estimated = ctx.stage_duration_estimates.get(
        "extract_irpf_full"
    ) or ctx.stage_duration_estimates.get("E1.6")
    loop_result = _process_loop(
        runnable, ctx, LLMService(llm_config), llm_config, PROMPT_VERSION, ws_id, estimated
    )
    return _build_result_summary(loop_result)
