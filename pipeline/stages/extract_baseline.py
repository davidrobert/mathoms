"""Stage wrapper for E1.5 — LLM-powered baseline patrimonial extraction from IRPF."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger(__name__)

_CENTS = Decimal("0.01")


def _money_str(v) -> str:
    """Serializa monetário no artifact como string decimal em centavos (ADR-090/A20.l11)."""
    if not isinstance(v, Decimal):
        v = Decimal(str(v or 0))
    return str(v.quantize(_CENTS))


def _money_dec(v) -> Decimal:
    """Parse defensivo de valor vindo de artifact (str novo, number legado)."""
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v if v is not None else 0))
    except InvalidOperation:
        logger.warning("E1.5: valor monetário não-parseável %r — tratado como 0", v)
        return Decimal("0")


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
            "valor_brl": _money_str(item.value_brl),
            "membro": item.member_key,
            "ano": item.year,
        }
        if item.institution:
            entry["instituicao"] = item.institution
        # ADR-267: propaga CPF do contribuinte quando LLM extraiu — habilita
        # identidade canônica via `MemberNameResolver.resolve_by_cpf` no E1.5c.
        if item.cpf:
            entry["cpf"] = item.cpf
        items.append(entry)

    return {
        "payload_version": 2,
        "itens": items,
        "resumo": {
            "total_ativos": _money_str(output.total_assets_brl),
            "total_passivos": _money_str(output.total_liabilities_brl),
            "patrimonio_liquido": _money_str(output.net_worth_brl),
            "ano_referencia": output.reference_year,
            "membros": output.members_found,
        },
        "_meta": {
            "source": "E1.5-llm",
            "confidence": output.confidence,
            "notes": output.notes,
        },
    }


_MAX_DOCS_PER_RUN = 10


def _artifact_key_for(doc: Path) -> str:
    """Stem usado como artifact_key — casamento em disco via filename.

    Paridade com `scripts.extract_bank_documents._artifact_key_for_file`: strip de
    ``-0_original`` para que o artefato final seja ``{stem}-1.5a_extract.json``
    (e não ``{stem}-0_original-1.5a_extract.json``). `document_pipeline_sync`
    e `document_extract_json_service` localizam o arquivo por esse nome.
    """
    name = doc.name
    lowered = name.lower()
    stem = name
    for ext in (".pdf", ".xlsx", ".xls", ".csv", ".json"):
        if lowered.endswith(ext):
            stem = name[: -len(ext)]
            break
    else:
        stem = doc.stem
    if "-0_original" in stem:
        stem = stem.split("-0_original")[0]
    return stem


def _aggregate_baselines(per_file: list[dict]) -> dict:
    """Combina N baselines per-arquivo num único baseline consolidado."""
    all_items: list[dict] = []
    assets = Decimal("0")
    liabilities = Decimal("0")
    members: list[str] = []
    notes_parts: list[str] = []
    confidences: list[float] = []
    years: list[int] = []

    for baseline in per_file:
        all_items.extend(baseline.get("itens") or [])
        resumo = baseline.get("resumo") or {}
        assets += _money_dec(resumo.get("total_ativos"))
        liabilities += _money_dec(resumo.get("total_passivos"))
        ano = resumo.get("ano_referencia")
        if isinstance(ano, int):
            years.append(ano)
        for m in resumo.get("membros") or []:
            if m not in members:
                members.append(m)
        meta = baseline.get("_meta") or {}
        conf = meta.get("confidence")
        if isinstance(conf, (int, float)):
            confidences.append(float(conf))
        note = meta.get("notes")
        if note:
            notes_parts.append(str(note))

    return {
        "payload_version": 2,
        "itens": all_items,
        "resumo": {
            "total_ativos": _money_str(assets),
            "total_passivos": _money_str(liabilities),
            "patrimonio_liquido": _money_str(assets - liabilities),
            "ano_referencia": max(years) if years else 0,
            "membros": members,
        },
        "_meta": {
            "source": "E1.5-llm",
            "confidence": min(confidences) if confidences else 0.0,
            "notes": "\n".join(notes_parts) if notes_parts else None,
        },
    }


def run(ctx: WorkspaceContext) -> dict:
    """Execute E1.5 baseline patrimonial extraction via LLM, per-arquivo.

    Uma chamada LLM por IRPF → artefato E1.5a (`{stem}-1.5a_extract.json`)
    vinculável ao documento. Depois agrega tudo num único
    `baseline_patrimonial-1.5_baseline.json` (E1.5) lido por E1.5c.
    """
    from pipeline.llm.litellm_client import LLMConfig, LLMService
    from pipeline.llm.prompts.e15_baseline import (
        PROMPT_VERSION,
        SYSTEM_PROMPT,
        USER_PROMPT_TEMPLATE,
    )
    from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
    from pipeline.llm.text_extractor import DocumentTextExtractor

    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    docs = _find_irpf_docs(ctx)
    if not docs:
        return {"skipped": True, "reason": "No IRPF/patrimony documents found"}

    # ADR-169: em modo incremental, processa apenas docs novos. Cada IRPF
    # tem seu artefato E1.5a próprio; o agregado E1.5 é recombinado a partir
    # do store (novos + existentes) abaixo, preservando paridade.
    if ctx.incremental:
        from pipeline.incremental import filter_to_incremental

        filtered = filter_to_incremental(ctx, docs)
        if not filtered:
            return {"skipped": True, "reason": "incremental: no new IRPF/patrimony documents"}
        docs = filtered

    extractor = DocumentTextExtractor(max_chars=80_000)
    selected = docs[:_MAX_DOCS_PER_RUN]

    docs_with_text: list[tuple[Path, str]] = []
    for doc in selected:
        text = extractor.extract(doc)
        if text.strip():
            docs_with_text.append((doc, text))

    if not docs_with_text:
        return {"skipped": True, "reason": "No extractable text in IRPF documents"}

    from pipeline.live_progress import emit_item_progress

    config = LLMConfig(**llm_config_data, call_hooks=ctx.llm_call_hooks)
    service = LLMService(config)
    store = ctx.get_artifact_store()

    from pipeline.domain.review_reason_projection import project_review_reasons
    from pipeline.llm.validators import validate_e15_output

    per_file_baselines: list[dict] = []
    total_tokens_in = 0
    total_tokens_out = 0
    total_cost_usd = 0.0
    errors: list[str] = []
    warnings: list[str] = []
    issues: list[dict] = []  # ADR-165: ValidationIssue dicts agregadas cross-doc
    review_reasons: list[dict] = []  # ADR-272 Fase 2: projeção consultável por-doc
    total = len(docs_with_text)

    estimated = ctx.stage_duration_estimates.get("extract_baseline")
    for idx, (doc, text) in enumerate(docs_with_text):
        emit_item_progress(
            ctx.pipeline_run_id,
            "extract_baseline",
            current_item=doc.name,
            items_done=idx,
            items_total=total,
            phase="preparing",
            # ADR-119: estimativa só no primeiro evento da stage.
            estimated_duration_ms=estimated if idx == 0 else None,
        )
        documents_text = f"=== {doc.name} ===\n{text}"
        # JSON/IRPF podem conter `{`/`}` — em kwargs do str.format o valor é inserido literalmente.
        user_prompt = USER_PROMPT_TEMPLATE.format(documents_text=documents_text)

        emit_item_progress(
            ctx.pipeline_run_id,
            "extract_baseline",
            current_item=doc.name,
            items_done=idx,
            items_total=total,
            phase="awaiting_llm",
        )
        result = service.call(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=BaselinePatrimonialOutput,
            max_tokens=max(config.max_tokens, _E15_MIN_COMPLETION_TOKENS),
            stage="extract_baseline",
            prompt_version=PROMPT_VERSION,
        )

        emit_item_progress(
            ctx.pipeline_run_id,
            "extract_baseline",
            current_item=doc.name,
            items_done=idx,
            items_total=total,
            phase="validating",
        )
        output: BaselinePatrimonialOutput = result.output
        validation = validate_e15_output(output)
        if not validation.valid:
            errors.extend(validation.errors)
        if validation.warnings:
            warnings.extend(validation.warnings)
        if validation.issues:
            issues.extend(i.to_dict() for i in validation.issues)
            reasons = project_review_reasons(
                list(validation.issues),
                stage="extract_baseline",
                artifact_key=_artifact_key_for(doc),
                document_id=None,
            )
            review_reasons.extend(rr.to_dict() for rr in reasons)

        emit_item_progress(
            ctx.pipeline_run_id,
            "extract_baseline",
            current_item=doc.name,
            items_done=idx,
            items_total=total,
            phase="persisting",
        )
        baseline_json = _output_to_baseline_json(output)
        # Propaga prompt_version no payload para auditabilidade (ADR-233 · W2-T05).
        baseline_json["prompt_version"] = PROMPT_VERSION
        per_file_baselines.append(baseline_json)
        store.write("E1.5a", _artifact_key_for(doc), baseline_json)

        total_tokens_in += result.tokens_in
        total_tokens_out += result.tokens_out
        total_cost_usd += result.cost_estimate_usd

    emit_item_progress(
        ctx.pipeline_run_id,
        "extract_baseline",
        current_item=None,
        items_done=total,
        items_total=total,
        phase="finalizing",
    )

    # ADR-169: em modo incremental, agrega lendo todos E1.5a do store
    # (existentes não-tocados + novos escritos acima). Em modo full, agrega
    # apenas os processados na run — preserva paridade com comportamento
    # legado e evita reincluir E1.5a órfão de doc removido pelo usuário.
    if ctx.incremental:
        baselines_for_aggregate = [
            b for b in (store.read("E1.5a", k) for k in store.list_keys("E1.5a")) if b is not None
        ]
    else:
        baselines_for_aggregate = per_file_baselines
    combined = _aggregate_baselines(baselines_for_aggregate)
    # Propaga prompt_version no payload agregado (ADR-233 · W2-T05).
    combined["prompt_version"] = PROMPT_VERSION

    # A6a (ADR-105): escreve via ArtifactStore em vez de disco direto.
    # consolidate_baseline lê este artefato e produz o -1.5_consolidated.
    # W6-T03/F9.2: write descritivo; reads legados resolvem via stage_aliases.
    store.write("extract_baseline", "baseline_patrimonial", combined)

    # Sem net_worth no log — valor real é dado sensível (CLAUDE.md §Logging).
    logger.info(
        "E1.5: %d files, %d items",
        len(per_file_baselines),
        len(combined["itens"]),
    )

    return {
        "success": True,
        "items_extracted": len(combined["itens"]),
        "net_worth_brl": combined["resumo"]["patrimonio_liquido"],
        "confidence": combined["_meta"]["confidence"],
        "output_file": "baseline_patrimonial-1.5_baseline.json",
        "tokens": {"in": total_tokens_in, "out": total_tokens_out},
        "cost_usd": total_cost_usd,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "issues": issues,
            "review_reasons": review_reasons,
        },
        "files_processed": len(per_file_baselines),
    }
