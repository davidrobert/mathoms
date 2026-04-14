"""Stage wrapper for E2-llm — LLM-powered extraction for docs without deterministic parser."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger(__name__)


def _find_unprocessed_docs(ctx: WorkspaceContext) -> list[Path]:
    """Find documents in data/ that don't have corresponding E2 extract JSONs.

    These are docs that the deterministic E2 parsers couldn't handle —
    e.g. investment reports, informes de rendimentos, unusual bank formats.
    """
    e2_existing = set()
    if ctx.e2_dir.exists():
        for f in ctx.e2_dir.glob("*-2_extract.json"):
            stem = f.stem.replace("-2_extract", "")
            e2_existing.add(stem)

    extensions = {".pdf", ".xlsx", ".xls", ".csv"}
    candidates = []

    search_dir = ctx.data_dir / "financial_statements"
    if search_dir.exists():
        for f in sorted(search_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in extensions:
                stem = f.stem.split("-0_original")[0]
                if stem not in e2_existing:
                    candidates.append(f)

    for subdir_name in ("income_tax_br", "real_estate", "vehicles"):
        subdir = ctx.data_dir / subdir_name
        if subdir.exists():
            for f in sorted(subdir.rglob("*")):
                if f.is_file() and f.suffix.lower() in extensions:
                    candidates.append(f)

    return candidates


def _output_to_e2_json(output) -> dict:
    """Convert LLMExtractOutput to E2-compatible JSON format."""
    transactions = []
    for t in output.transactions:
        entry = {
            "data": t.date,
            "descricao": t.description,
            "valor": t.amount,
        }
        if t.category_hint:
            entry["categoria_sugerida"] = t.category_hint
        if t.balance_after is not None:
            entry["saldo_apos"] = t.balance_after
        transactions.append(entry)

    investments = []
    for inv in output.investments:
        entry = {
            "tipo": inv.type,
            "instituicao": inv.institution,
            "descricao": inv.description,
            "valor_brl": inv.value_brl,
        }
        if inv.applied_date:
            entry["data_aplicacao"] = inv.applied_date
        if inv.maturity_date:
            entry["data_vencimento"] = inv.maturity_date
        if inv.rate:
            entry["taxa"] = inv.rate
        if inv.member_key:
            entry["membro"] = inv.member_key
        investments.append(entry)

    result = {
        "arquivo_origem": output.source_file,
        "instituicao": output.institution,
        "tipo_documento": output.document_type,
        "moeda": output.currency,
        "extraido_por": "llm",
        "_meta": {
            "confidence": output.confidence,
            "notes": output.notes,
        },
    }
    if output.period:
        result["periodo"] = output.period
    if output.member_key:
        result["membro"] = output.member_key
    if transactions:
        result["transacoes"] = transactions
    if investments:
        result["investimentos"] = investments

    return result


def run(ctx: WorkspaceContext) -> dict:
    """Execute E2-llm extraction for documents without deterministic parsers.

    For each unprocessed document, sends to LLM and saves E2-compatible JSON.
    """
    from pipeline.llm.service import LLMService, LLMConfig
    from pipeline.llm.text_extractor import DocumentTextExtractor
    from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
    from pipeline.llm.prompts.e2_llm import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    docs = _find_unprocessed_docs(ctx)
    if not docs:
        return {"skipped": True, "reason": "No unprocessed documents for LLM extraction"}

    config = LLMConfig(**llm_config_data)
    service = LLMService(config)
    extractor = DocumentTextExtractor(max_chars=60_000)

    ctx.e2_dir.mkdir(parents=True, exist_ok=True)

    processed = []
    errors = []

    for doc in docs:
        text = extractor.extract(doc)
        if not text.strip():
            logger.warning("E2-llm: empty text for %s, skipping", doc.name)
            continue

        user_prompt = USER_PROMPT_TEMPLATE.format(
            filename=doc.name,
            doc_type="unknown",
            institution="unknown",
            document_text=text,
        )

        try:
            result = service.call(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=LLMExtractOutput,
            )
            output: LLMExtractOutput = result.output

            from pipeline.llm.validators import validate_e2_llm_output
            validation = validate_e2_llm_output(output)
            if not validation.valid:
                logger.warning("E2-llm: validation errors for %s: %s", doc.name, validation.errors)

            e2_json = _output_to_e2_json(output)

            safe_stem = doc.stem.replace(" ", "_")[:80]
            out_path = ctx.e2_dir / f"{safe_stem}-2_extract.json"
            out_path.write_text(json.dumps(e2_json, ensure_ascii=False, indent=2), encoding="utf-8")

            processed.append({
                "file": doc.name,
                "output": out_path.name,
                "transactions": len(output.transactions),
                "investments": len(output.investments),
                "confidence": output.confidence,
            })

            logger.info(
                "E2-llm: %s → %d txns, %d investments, confidence=%.2f",
                doc.name, len(output.transactions), len(output.investments), output.confidence,
            )

        except Exception as exc:
            logger.error("E2-llm: failed for %s: %s", doc.name, exc)
            errors.append({"file": doc.name, "error": str(exc)[:300]})

    summary = service.summary.to_dict()

    return {
        "success": len(errors) == 0,
        "processed": processed,
        "errors": errors,
        "total_processed": len(processed),
        "total_errors": len(errors),
        "llm_usage": summary,
    }
