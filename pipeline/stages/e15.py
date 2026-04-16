"""Stage wrapper for E1.5 — LLM-powered baseline patrimonial extraction from IRPF."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger(__name__)

# OP-009 / IRPF: baseline JSON is large; sub-16k completions truncate and break structured output.
_E15_MIN_COMPLETION_TOKENS = 16_384


def _find_irpf_docs(ctx: WorkspaceContext) -> list[Path]:
    """Find IRPF declarations and related patrimony documents."""
    search_dirs = [
        ctx.data_dir / "income_tax_br",
        ctx.data_dir / "real_estate",
        ctx.data_dir / "vehicles",
    ]
    extensions = {".pdf", ".xlsx", ".xls", ".csv", ".json"}
    found = []
    for d in search_dirs:
        if d.exists():
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.suffix.lower() in extensions:
                    found.append(f)
    return found


def _output_to_baseline_json(output) -> dict:
    """Convert BaselinePatrimonialOutput to baseline_patrimonial format."""
    items = []
    for item in output.items:
        entry = {
            "codigo": item.code,
            "descricao": item.description,
            "categoria": item.category,
            "valor_brl": item.value_brl,
            "membro": item.member_key,
            "ano": item.year,
        }
        if item.institution:
            entry["instituicao"] = item.institution
        items.append(entry)

    return {
        "itens": items,
        "resumo": {
            "total_ativos": output.total_assets_brl,
            "total_passivos": output.total_liabilities_brl,
            "patrimonio_liquido": output.net_worth_brl,
            "ano_referencia": output.reference_year,
            "membros": output.members_found,
        },
        "_meta": {
            "source": "E1.5-llm",
            "confidence": output.confidence,
            "notes": output.notes,
        },
    }


def run(ctx: WorkspaceContext) -> dict:
    """Execute E1.5 baseline patrimonial extraction via LLM.

    Reads IRPF docs, sends to LLM, saves baseline JSON in E2_extracts/.
    """
    from pipeline.llm.service import LLMService, LLMConfig
    from pipeline.llm.text_extractor import DocumentTextExtractor
    from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
    from pipeline.llm.prompts.e15_baseline import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    docs = _find_irpf_docs(ctx)
    if not docs:
        return {"skipped": True, "reason": "No IRPF/patrimony documents found"}

    extractor = DocumentTextExtractor(max_chars=80_000)
    docs_text_parts = []
    for doc in docs[:10]:
        text = extractor.extract(doc)
        if text.strip():
            docs_text_parts.append(f"=== {doc.name} ===\n{text}")

    if not docs_text_parts:
        return {"skipped": True, "reason": "No extractable text in IRPF documents"}

    from pipeline.live_progress import emit_stage_activity

    emit_stage_activity(
        ctx.pipeline_run_id,
        "E1.5",
        message=f"Lendo declaração IRPF com IA ({len(docs_text_parts)} documento(s))…",
    )

    documents_text = "\n\n".join(docs_text_parts)
    # JSON/IRPF podem conter `{`/`}` — em kwargs do str.format o valor é inserido literalmente.
    user_prompt = USER_PROMPT_TEMPLATE.format(documents_text=documents_text)

    config = LLMConfig(**llm_config_data)
    service = LLMService(config)

    result = service.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=BaselinePatrimonialOutput,
        max_tokens=max(config.max_tokens, _E15_MIN_COMPLETION_TOKENS),
    )

    output: BaselinePatrimonialOutput = result.output

    from pipeline.llm.validators import validate_e15_output
    validation = validate_e15_output(output)
    if not validation.valid:
        logger.warning("E1.5: validation errors: %s", validation.errors)
    if validation.warnings:
        logger.info("E1.5: validation warnings: %s", validation.warnings)

    baseline_json = _output_to_baseline_json(output)

    ctx.e2_dir.mkdir(parents=True, exist_ok=True)
    out_path = ctx.e2_dir / "baseline_patrimonial-1.5_consolidated.json"
    out_path.write_text(json.dumps(baseline_json, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(
        "E1.5: %d items, net_worth=%.2f, confidence=%.2f",
        len(output.items), output.net_worth_brl, output.confidence,
    )

    return {
        "success": True,
        "items_extracted": len(output.items),
        "net_worth_brl": output.net_worth_brl,
        "confidence": output.confidence,
        "output_file": out_path.name,
        "tokens": {"in": result.tokens_in, "out": result.tokens_out},
        "cost_usd": result.cost_estimate_usd,
        "validation": validation.to_dict(),
    }
