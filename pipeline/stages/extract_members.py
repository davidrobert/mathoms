"""Stage wrapper for E1 — LLM-powered member extraction from personal documents."""

from __future__ import annotations

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


def _member_info(m) -> dict:
    info = {"nome_completo": m.full_name, "nome_curto": m.short_name, "papel": m.role}
    # ADR-259 §2 (A20.l15): o artifact NUNCA carrega CPF cru — só o sinal.
    # O valor é extraído do documento original e cifrado pelo backend
    # (family_member_pii_service) no pós-run.
    if getattr(m, "cpf_present", False):
        info["cpf_present"] = True
    if m.birth_date:
        info["data_nascimento"] = m.birth_date
    return info


def _conta_entry(m, acc) -> dict:
    # A24.l2 (ADR-280): extração emite só raw; normalização canônica roda nos
    # consumidores (config_parsers._make_account / investments_consolidator).
    return {
        "member_key": m.key,
        "institution_code": acc.institution_code,
        "account_type": getattr(acc, "account_type", "") or "",
        "account_number_raw": getattr(acc, "account_number", None),
        "agency": getattr(acc, "agency", None),
        "is_joint": False,
        "co_titulares": [],
    }


def _output_to_family_members_json(output) -> dict:
    """Convert MembersExtractOutput to family_members.json format (ADR-226 PR3: contas[])."""
    membros, banco_membro, contas = {}, {}, []
    for m in output.members:
        membros[m.key] = _member_info(m)
        for acc in m.accounts:
            banco_membro[acc.institution_code] = m.key
            contas.append(_conta_entry(m, acc))
    result: dict = {"membros": membros}
    if banco_membro:
        result["banco_membro"] = banco_membro
    if contas:
        result["contas"] = contas
    if output.titular_key:
        result["titular"] = output.titular_key
    return result


def run(ctx: WorkspaceContext) -> dict:
    """Execute E1 member extraction via LLM.

    Reads personal documents, sends to LLM, saves members JSON.
    Requires llm_config.json in ctx.config_dir.
    """
    from pipeline.llm.litellm_client import LLMConfig, LLMService
    from pipeline.llm.prompts.e1_members import PROMPT_VERSION, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from pipeline.llm.schemas.e1_members import MembersExtractOutput
    from pipeline.llm.text_extractor import DocumentTextExtractor

    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    docs = _find_personal_docs(ctx)
    if not docs:
        return {"skipped": True, "reason": "No personal documents found"}

    # ADR-169: em modo incremental, ``extract_members`` produz UM agregado
    # (members-1b_unified.json) por run. Sem layer per-doc no store, merge
    # seguro entre run anterior e novos docs exigiria LLM extra de
    # consolidação — fora de escopo desta lane. Skip total quando nenhum
    # doc novo é "personal"; preserva o agregado existente. Quando há ao
    # menos um novo, roda full sobre todos os docs (paridade com modo
    # full — texto concatenado de até 10 docs).
    if ctx.incremental:
        from pipeline.incremental import has_incremental_overlap

        if not has_incremental_overlap(ctx, docs):
            return {"skipped": True, "reason": "incremental: no new personal documents"}

    extractor = DocumentTextExtractor(max_chars=80_000)
    docs_text_parts = []
    for doc in docs[:10]:
        text = extractor.extract(doc)
        if text.strip():
            docs_text_parts.append(f"=== {doc.name} ===\n{text}")

    if not docs_text_parts:
        return {"skipped": True, "reason": "No extractable text in documents"}

    from pipeline.live_progress import emit_item_progress

    item_label = f"{len(docs_text_parts)} documento(s) pessoais"
    emit_item_progress(
        ctx.pipeline_run_id,
        "E1",
        current_item=item_label,
        items_done=0,
        items_total=1,
        phase="preparing",
    )

    documents_text = "\n\n".join(docs_text_parts)
    # JSON/PDF podem conter `{`/`}` — em kwargs do str.format o valor é inserido literalmente.
    user_prompt = USER_PROMPT_TEMPLATE.format(documents_text=documents_text)

    config = LLMConfig(**llm_config_data, call_hooks=ctx.llm_call_hooks)
    service = LLMService(config)

    emit_item_progress(
        ctx.pipeline_run_id,
        "E1",
        current_item=item_label,
        items_done=0,
        items_total=1,
        phase="awaiting_llm",
    )
    result = service.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=MembersExtractOutput,
        max_tokens=max(config.max_tokens, _E1_MIN_COMPLETION_TOKENS),
        stage="E1",
        prompt_version=PROMPT_VERSION,
    )

    output: MembersExtractOutput = result.output

    from pipeline.llm.validators import validate_e1_output

    emit_item_progress(
        ctx.pipeline_run_id,
        "E1",
        current_item=item_label,
        items_done=0,
        items_total=1,
        phase="validating",
    )
    validation = validate_e1_output(output)
    if not validation.valid:
        logger.warning("E1: validation errors: %s", validation.errors)
    if validation.warnings:
        logger.info("E1: validation warnings: %s", validation.warnings)

    family_json = _output_to_family_members_json(output)
    # Propaga prompt_version no payload para auditabilidade (ADR-233 · W2-T05).
    family_json["prompt_version"] = PROMPT_VERSION

    store = ctx.get_artifact_store()
    emit_item_progress(
        ctx.pipeline_run_id,
        "E1",
        current_item=item_label,
        items_done=0,
        items_total=1,
        phase="persisting",
    )
    store.write("E1", "members", family_json)
    emit_item_progress(
        ctx.pipeline_run_id,
        "E1",
        current_item=None,
        items_done=1,
        items_total=1,
        phase="finalizing",
    )

    logger.info("E1: extracted %d members, confidence=%.2f", len(output.members), output.confidence)

    return {
        "success": True,
        "members_extracted": len(output.members),
        "confidence": output.confidence,
        "output_file": "members-1b_unified.json",
        "tokens": {"in": result.tokens_in, "out": result.tokens_out},
        "cost_usd": result.cost_estimate_usd,
        "validation": validation.to_dict(),
    }
