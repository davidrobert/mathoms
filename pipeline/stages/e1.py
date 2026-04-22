"""Stage wrapper for E1 — LLM-powered member extraction from personal documents."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger(__name__)

# Família típica tem 3–5 membros com contas em múltiplos bancos. O schema
# MembersExtractOutput sai facilmente de 4096 tokens — dimensionado igual a E1.5/E2-llm.
_E1_MIN_COMPLETION_TOKENS = 16_384


def _find_personal_docs(ctx: WorkspaceContext) -> list[Path]:
    """Find documents that may contain personal data (IRPF, IDs, etc.)."""
    search_dirs = [
        ctx.data_dir / "income_tax_br",
        ctx.data_dir,
        ctx.inbox_dir,
    ]
    extensions = {".pdf", ".xlsx", ".xls", ".csv", ".json", ".txt"}
    found = []
    for d in search_dirs:
        if d.exists():
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.suffix.lower() in extensions:
                    found.append(f)
    return found


def _output_to_family_members_json(output) -> dict:
    """Convert MembersExtractOutput to family_members.json format."""
    membros = {}
    banco_membro = {}
    titular = output.titular_key

    for m in output.members:
        info = {
            "nome_completo": m.full_name,
            "nome_curto": m.short_name,
            "papel": m.role,
        }
        if m.cpf:
            info["cpf"] = m.cpf
        if m.birth_date:
            info["data_nascimento"] = m.birth_date
        membros[m.key] = info

        for acc in m.accounts:
            banco_membro[acc.institution_code] = m.key

    result = {"membros": membros}
    if banco_membro:
        result["banco_membro"] = banco_membro
    if titular:
        result["titular"] = titular
    return result


def run(ctx: WorkspaceContext) -> dict:
    """Execute E1 member extraction via LLM.

    Reads personal documents, sends to LLM, saves members JSON.
    Requires llm_config.json in ctx.config_dir.
    """
    from pipeline.llm.litellm_client import LLMConfig, LLMService
    from pipeline.llm.prompts.e1_members import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from pipeline.llm.schemas.e1_members import MembersExtractOutput
    from pipeline.llm.text_extractor import DocumentTextExtractor

    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    docs = _find_personal_docs(ctx)
    if not docs:
        return {"skipped": True, "reason": "No personal documents found"}

    extractor = DocumentTextExtractor(max_chars=80_000)
    docs_text_parts = []
    for doc in docs[:10]:
        text = extractor.extract(doc)
        if text.strip():
            docs_text_parts.append(f"=== {doc.name} ===\n{text}")

    if not docs_text_parts:
        return {"skipped": True, "reason": "No extractable text in documents"}

    from pipeline.live_progress import emit_stage_activity

    emit_stage_activity(
        ctx.pipeline_run_id,
        "E1",
        message=f"Lendo dados pessoais com IA ({len(docs_text_parts)} documento(s))…",
    )

    documents_text = "\n\n".join(docs_text_parts)
    # JSON/PDF podem conter `{`/`}` — em kwargs do str.format o valor é inserido literalmente.
    user_prompt = USER_PROMPT_TEMPLATE.format(documents_text=documents_text)

    config = LLMConfig(**llm_config_data)
    service = LLMService(config)

    result = service.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=MembersExtractOutput,
        max_tokens=max(config.max_tokens, _E1_MIN_COMPLETION_TOKENS),
        stage="E1",
    )

    output: MembersExtractOutput = result.output

    from pipeline.llm.validators import validate_e1_output

    validation = validate_e1_output(output)
    if not validation.valid:
        logger.warning("E1: validation errors: %s", validation.errors)
    if validation.warnings:
        logger.info("E1: validation warnings: %s", validation.warnings)

    family_json = _output_to_family_members_json(output)

    members_dir = ctx.members_dir
    members_dir.mkdir(parents=True, exist_ok=True)
    out_path = members_dir / "members-1b_unified.json"
    out_path.write_text(json.dumps(family_json, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("E1: extracted %d members, confidence=%.2f", len(output.members), output.confidence)

    return {
        "success": True,
        "members_extracted": len(output.members),
        "confidence": output.confidence,
        "output_file": out_path.name,
        "tokens": {"in": result.tokens_in, "out": result.tokens_out},
        "cost_usd": result.cost_estimate_usd,
        "validation": validation.to_dict(),
    }
