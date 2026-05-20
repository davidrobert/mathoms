"""Stage wrapper for E2-llm — LLM-powered extraction for docs without deterministic parser."""

from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger(__name__)

# Evita escada 4k→8k→16k em extratos longos; alinhado ao mínimo de E1.5 para JSON grande.
_E2_LLM_MIN_COMPLETION_TOKENS = 16_384


class _E2LLMProgress:
    """Counter compartilhado para emissões LiveStep concorrentes (ADR-119).

    `_process_one_e2_llm_document` roda em ThreadPoolExecutor — `items_done`
    precisa ser snapshot atômico do progresso global no momento de cada fase.
    Increment fica no thread principal após `as_completed`, fora do crítico.
    """

    def __init__(self, total: int, run_id: str | None) -> None:
        self._lock = threading.Lock()
        self._done = 0
        self.total = total
        self.run_id = run_id

    def emit(self, current_item: str | None, phase: str) -> None:
        from pipeline.live_progress import emit_item_progress

        with self._lock:
            done = self._done
        emit_item_progress(
            self.run_id,
            "E2-llm",
            current_item=current_item,
            items_done=done,
            items_total=self.total,
            phase=phase,
        )

    def increment(self) -> None:
        with self._lock:
            self._done += 1


def _e2_extract_stem(path: Path) -> str:
    """Stem used for `*-2_extract.json` matching (same as deterministic E2 outputs)."""
    return path.stem.split("-0_original")[0]


def _find_unprocessed_docs(ctx: WorkspaceContext, store=None) -> list[Path]:
    """Find documents in data/ that don't have corresponding E2 extract JSONs.

    These are docs that the deterministic E2 parsers couldn't handle —
    e.g. investment reports, informes de rendimentos, unusual bank formats.

    A6a: usa ``store.list_keys`` em vez de glob direto para ser compatível com
    DB-backed store (A6b+). Fallback para glob se store não fornecido.
    """
    e2_existing: set[str] = set()
    if store is not None:
        for stage_key in ("E2", "E2-extratos", "E2-faturas", "E2-llm"):
            e2_existing.update(store.list_keys(stage_key))
    elif ctx.e2_dir.exists():
        for f in ctx.e2_dir.glob("*-2_extract.json"):
            stem = f.stem.replace("-2_extract", "")
            e2_existing.add(stem)

    extensions = {".pdf", ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png"}
    candidates = []

    search_dir = ctx.data_dir / "financial_statements"
    if search_dir.exists():
        for f in sorted(search_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in extensions:
                if _e2_extract_stem(f) not in e2_existing:
                    candidates.append(f)

    # `income_tax_br` é processado exclusivamente por E1.5 (baseline patrimonial).
    # O schema do E2-llm (transactions + investments) não tem campos para rendimentos,
    # imposto, dependentes ou despesas dedutíveis — rodar IRPF aqui produz JSON vazio
    # e gasta LLM. Mantemos `real_estate` e `vehicles` porque podem conter docs
    # sem parser determinístico que viram informações úteis (saldo, posição).
    for subdir_name in ("real_estate", "vehicles"):
        subdir = ctx.data_dir / subdir_name
        if subdir.exists():
            for f in sorted(subdir.rglob("*")):
                if f.is_file() and f.suffix.lower() in extensions:
                    if _e2_extract_stem(f) not in e2_existing:
                        candidates.append(f)

    return candidates


def _e2_llm_queue_stats(data_dir: Path, docs: list[Path]) -> dict[str, int]:
    """Group queued paths by first segment under ``data_dir`` (e.g. financial_statements)."""
    counts: dict[str, int] = {}
    try:
        base = data_dir.resolve()
    except OSError:
        return {"(unresolved_data_dir)": len(docs)}
    for p in docs:
        try:
            rel = p.resolve().relative_to(base)
        except ValueError:
            key = "(outside_data_dir)"
        else:
            key = rel.parts[0] if rel.parts else "(empty_rel)"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _llm_config_from_runtime(data: dict) -> Any:
    """Build ``LLMConfig`` from serialized llm_config.json (ignore unknown keys)."""
    from pipeline.llm.litellm_client import LLMConfig

    return LLMConfig(
        provider=str(data.get("provider") or "anthropic"),
        api_key=str(data.get("api_key") or ""),
        model_name=str(data.get("model_name") or "claude-sonnet-4-20250514"),
        max_tokens=int(data.get("max_tokens") or 4096),
        temperature=float(data["temperature"] if data.get("temperature") is not None else 0.1),
    )


def _e2_llm_perf_settings(ctx: "WorkspaceContext") -> dict[str, Any]:
    """Concurrency and PDF/text limits — from ``pipeline.json`` ``e2_llm`` + env override.

    ``MATHOMS_E2_LLM_CONCURRENCY`` (1–8) overrides ``pipeline.json`` when set.
    Smaller inputs reduce latency; defaults are tuned for informes/IRPF-style PDFs.
    """
    out: dict[str, Any] = {
        "concurrency": 4,
        "max_input_chars": 40_000,
        "max_pdf_pages": 35,
    }
    pipe = ctx.load_config("pipeline.json") or {}
    e2 = pipe.get("e2_llm")
    if isinstance(e2, dict):
        if "concurrency" in e2:
            try:
                out["concurrency"] = max(1, min(8, int(e2["concurrency"])))
            except (TypeError, ValueError):
                pass
        if "max_input_chars" in e2:
            try:
                v = int(e2["max_input_chars"])
                if 4_000 <= v <= 120_000:
                    out["max_input_chars"] = v
            except (TypeError, ValueError):
                pass
        if "max_pdf_pages" in e2:
            try:
                v = int(e2["max_pdf_pages"])
                if 5 <= v <= 100:
                    out["max_pdf_pages"] = v
            except (TypeError, ValueError):
                pass

    env = os.environ.get("MATHOMS_E2_LLM_CONCURRENCY", "").strip()
    if env:
        try:
            out["concurrency"] = max(1, min(8, int(env)))
        except ValueError:
            pass

    return out


def _process_one_e2_llm_document(
    doc: Path,
    store: Any,
    llm_config_data: dict[str, Any],
    max_chars: int,
    max_pages: int,
    progress: _E2LLMProgress,
) -> tuple[dict[str, Any] | None, dict[str, str] | None, Any]:
    """Extract + one LLM call for a single file. Returns (processed, error, run_summary).

    A6a: escreve via ``store.write("E2-llm", safe_stem, e2_json)`` em vez de
    disco direto — compatível com DiskArtifactStore e DBArtifactStore (A6b+).
    """
    from pipeline.llm.litellm_client import LLMRunSummary, LLMService
    from pipeline.llm.prompts.e2_llm import PROMPT_VERSION, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
    from pipeline.llm.text_extractor import DocumentTextExtractor
    from pipeline.llm.validators import validate_e2_llm_output

    empty_summary = LLMRunSummary()
    cfg = _llm_config_from_runtime(llm_config_data)
    service = LLMService(cfg)
    extractor = DocumentTextExtractor(max_chars=max_chars, max_pages=max_pages)

    # Imagens são enviadas como conteúdo multimodal; demais formatos via extração de texto.
    image_bytes: bytes | None = None
    image_media_type: str = "image/jpeg"
    if extractor.is_image(doc):
        image_bytes, image_media_type = extractor.extract_image_bytes(doc)
        if not image_bytes:
            logger.warning("E2-llm: imagem vazia para %s, pulando", doc.name)
            return None, None, empty_summary
        text = ""
    else:
        text = extractor.extract(doc)
        if not text.strip():
            logger.warning("E2-llm: texto vazio para %s, pulando", doc.name)
            return None, None, empty_summary

    progress.emit(doc.name, "preparing")

    try:
        # Valores em str.format(**kwargs) são inseridos literalmente; chaves no texto do PDF/JSON não conflitam.
        # Para imagens, document_text fica vazio — o conteúdo visual é enviado como image content block.
        user_prompt = USER_PROMPT_TEMPLATE.format(
            filename=doc.name,
            doc_type="unknown",
            institution="unknown",
            document_text=text or "[imagem — conteúdo enviado como anexo visual]",
        )

        min_out = max(cfg.max_tokens, _E2_LLM_MIN_COMPLETION_TOKENS)
        progress.emit(doc.name, "awaiting_llm")
        result = service.call(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=LLMExtractOutput,
            max_retries=2,
            max_tokens=min_out,
            stage=f"E2-llm:{doc.name}",
            image_bytes=image_bytes,
            image_media_type=image_media_type,
        )
        output: LLMExtractOutput = result.output

        progress.emit(doc.name, "validating")
        validation = validate_e2_llm_output(output)
        if not validation.valid:
            logger.warning("E2-llm: validation errors for %s: %s", doc.name, validation.errors)

        e2_json = _output_to_e2_json(output)
        # Propaga prompt_version no payload para auditabilidade (ADR-233 · W2-T05).
        e2_json["prompt_version"] = PROMPT_VERSION

        safe_stem = _e2_extract_stem(doc).replace(" ", "_")[:80]
        progress.emit(doc.name, "persisting")
        # Validação JSON-schema é executada pelo hook pós-write em
        # DBArtifactStore.write (ADR-212 PR3 — SCHEMA_BY_STAGE inclui
        # "E2-llm" → "e2_extract.schema.json").
        store.write("E2-llm", safe_stem, e2_json)

        out_filename = f"{safe_stem}-2_extract.json"
        processed = {
            "file": doc.name,
            "output": out_filename,
            "transactions": len(output.transactions),
            "investments": len(output.investments),
            "confidence": output.confidence,
        }

        logger.info(
            "E2-llm: %s → %d txns, %d investments, confidence=%.2f",
            doc.name,
            len(output.transactions),
            len(output.investments),
            output.confidence,
        )

        return processed, None, service.summary

    except Exception as exc:
        logger.error("E2-llm: failed for %s: %s", doc.name, exc)
        return None, {"file": doc.name, "error": str(exc)[:300]}, service.summary


def _merge_llm_run_summaries(parts: list[Any]) -> dict[str, Any]:
    from pipeline.llm.litellm_client import LLMRunSummary

    merged = LLMRunSummary()
    for p in parts:
        merged.calls.extend(p.calls)
    return merged.to_dict()


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
        p = output.period.strip()
        # E3 espera periodo como {inicio, fim}; schema LLM usa YYYYMM string.
        if len(p) == 6 and p.isdigit():
            from calendar import monthrange

            y, m = int(p[:4]), int(p[4:6])
            if 1 <= m <= 12:
                last = monthrange(y, m)[1]
                result["periodo"] = {
                    "inicio": f"{y}-{m:02d}-01",
                    "fim": f"{y}-{m:02d}-{last:02d}",
                }
            else:
                result["periodo"] = p
        else:
            result["periodo"] = p
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
    Documents are processed concurrently (see ``pipeline.json`` ``e2_llm``) to
    reduce wall time when multiple files need LLM extraction.
    """
    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    store = ctx.get_artifact_store()
    docs = _find_unprocessed_docs(ctx, store)
    if not docs:
        return {"skipped": True, "reason": "No unprocessed documents for LLM extraction"}

    # ADR-080 + W2-T05: em modo incremental, restringe ao allowlist
    # (`ctx.incremental_doc_paths`). Modo full mantém docs intacto.
    # Padrão alinhado com extract_baseline.py:163 — sem cache hash em DB.
    # Invalidação por bump de PROMPT_VERSION exige re-delete manual de
    # artifacts antigos (runbook), não auto-skip aqui.
    if ctx.incremental:
        from pipeline.incremental import filter_to_incremental

        docs = filter_to_incremental(ctx, docs)
        if not docs:
            return {"skipped": True, "reason": "incremental: no new documents for LLM extraction"}

    perf = _e2_llm_perf_settings(ctx)
    workers = min(int(perf["concurrency"]), len(docs), 8)
    workers = max(1, workers)

    queue_stats = _e2_llm_queue_stats(ctx.data_dir, docs)
    logger.info(
        "E2-llm: %d document(s) queued for LLM extraction — under data/: %s — "
        "workers=%d max_input_chars=%d max_pdf_pages=%d",
        len(docs),
        queue_stats,
        workers,
        perf["max_input_chars"],
        perf["max_pdf_pages"],
    )
    if logger.isEnabledFor(logging.DEBUG):
        names = [p.name for p in docs]
        if len(names) > 50:
            logger.debug(
                "E2-llm: queued file names (first 50 of %d): %s",
                len(names),
                names[:50],
            )
        else:
            logger.debug("E2-llm: queued file names: %s", names)

    processed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    summary_parts: list[Any] = []

    max_chars = int(perf["max_input_chars"])
    max_pages = int(perf["max_pdf_pages"])

    progress = _E2LLMProgress(total=len(docs), run_id=ctx.pipeline_run_id)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _process_one_e2_llm_document,
                doc,
                store,
                llm_config_data,
                max_chars,
                max_pages,
                progress,
            )
            for doc in docs
        ]
        for fut in as_completed(futures):
            proc, err, summ = fut.result()
            progress.increment()
            summary_parts.append(summ)
            if proc is not None:
                processed.append(proc)
            if err is not None:
                errors.append(err)

    from pipeline.live_progress import emit_item_progress

    emit_item_progress(
        ctx.pipeline_run_id,
        "E2-llm",
        current_item=None,
        items_done=len(docs),
        items_total=len(docs),
        phase="finalizing",
    )

    summary = _merge_llm_run_summaries(summary_parts)

    out: dict[str, Any] = {
        "success": len(errors) == 0,
        "processed": processed,
        "errors": errors,
        "total_processed": len(processed),
        "total_errors": len(errors),
        "llm_usage": summary,
        "queued": {
            "total": len(docs),
            "by_data_subdir": queue_stats,
        },
        "e2_llm_settings": {
            "workers": workers,
            "max_input_chars": max_chars,
            "max_pdf_pages": max_pages,
        },
    }
    return out
