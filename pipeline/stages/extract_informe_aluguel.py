"""Stage runner extract_informe_aluguel — Onda 0.5b (ADR-216). Workspace-scoped, descritivo (ADR-093 F9.2+)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext
    from pipeline.llm.litellm_client import LLMConfig, LLMService

logger = logging.getLogger("mathoms.pipeline.informe_aluguel")

_INFORME_MIN_COMPLETION_TOKENS = 16_384
_MAX_DOCS_PER_RUN = 20

_FILENAME_CPF_MASKED = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_FILENAME_CPF_LOOSE = re.compile(r"(?<!\d)\d{11}(?!\d)")
_FILENAME_CNPJ_MASKED = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")


def _redact_filename_pii(name: str) -> str:
    """Mascara CPF/CNPJ em filenames antes de logar (PII)."""
    name = _FILENAME_CPF_MASKED.sub("<cpf-redacted>", name)
    name = _FILENAME_CPF_LOOSE.sub("<cpf-redacted>", name)
    name = _FILENAME_CNPJ_MASKED.sub("<cnpj-redacted>", name)
    return name


def _artifact_key_for(doc: Path) -> str:
    """Stem para artifact_key — strip de ``-0_original`` (paridade com E1.6)."""
    name = doc.name
    stem = doc.stem
    lowered = name.lower()
    for ext in (".pdf", ".xlsx", ".xls", ".csv", ".json"):
        if lowered.endswith(ext):
            stem = name[: -len(ext)]
            break
    if "-0_original" in stem:
        stem = stem.split("-0_original")[0]
    return stem


def _find_informes(ctx: WorkspaceContext) -> list[Path]:
    """Localiza informes em ``data/income_tax_br/`` por filename ``informerendimentosaluguel``."""
    income_dir = ctx.data_dir / "income_tax_br"
    if not income_dir.exists():
        return []
    out: list[Path] = []
    for f in sorted(income_dir.rglob("*")):
        if not f.is_file() or f.suffix.lower() != ".pdf":
            continue
        if "informerendimentosaluguel" in f.name.lower():
            out.append(f)
    return out


def extract_one_informe(
    doc_path: Path,
    config: LLMConfig,
    *,
    max_input_chars: int = 80_000,
    institution_hint: str | None = None,
    ano_referencia_hint: int | None = None,
):
    """Extrai um informe via LLM e retorna (payload_dict, llm_run_summary) sem persistir."""
    from pipeline.llm.litellm_client import LLMService
    from pipeline.llm.prompts.informe_aluguel import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from pipeline.llm.schemas.informe_aluguel import PROMPT_VERSION, InformeAluguelExtract
    from pipeline.llm.text_extractor import DocumentTextExtractor

    service = LLMService(config)
    extractor = DocumentTextExtractor(max_chars=max_input_chars)
    text = extractor.extract(doc_path)
    if not text.strip():
        raise ValueError(f"informe_aluguel: texto vazio para {doc_path.name}")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        filename=doc_path.name,
        institution=institution_hint or "unknown",
        ano_referencia=ano_referencia_hint or "(inferir do documento)",
        document_text=text,
    )

    result = service.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=InformeAluguelExtract,
        max_tokens=max(config.max_tokens, _INFORME_MIN_COMPLETION_TOKENS),
        stage=f"extract_informe_aluguel:{doc_path.name}",
    )

    output: InformeAluguelExtract = result.output
    payload = output.model_dump(mode="json")
    payload["prompt_version"] = PROMPT_VERSION
    return payload, result


def _log_informe_telemetry(entry: dict[str, Any], result) -> None:
    logger.info(
        "extract_informe_aluguel",
        extra={
            "doc": entry["file"],
            "imoveis": entry["imoveis"],
            "imobiliaria_cnpj_present": entry["imobiliaria_cnpj_present"],
            "locador_cpf_present": entry["locador_cpf_present"],
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_estimate_usd,
        },
    )


def _extract_and_persist(doc: Path, config: LLMConfig, store) -> dict[str, Any]:
    """Extrai 1 informe, persiste e loga telemetria — retorna entry de `processed`."""
    payload, result = extract_one_informe(doc, config)
    key = _artifact_key_for(doc)
    # Schema validation roda no hook pós-write de DBArtifactStore
    # (ADR-212 PR3 — SCHEMA_BY_STAGE['extract_informe_aluguel']).
    store.write("extract_informe_aluguel", key, payload)
    entry = {
        "file": _redact_filename_pii(doc.name),
        "artifact_key": key,
        "imoveis": len(payload.get("imoveis", [])),
        "confidence": payload.get("confidence"),
        # Flags de presença detectam drift de layout/extração de texto sem
        # logar o identificador em si (ADR-288 — PII fica fora dos logs).
        "imobiliaria_cnpj_present": payload.get("imobiliaria_cnpj") is not None,
        "locador_cpf_present": payload.get("locador_cpf") is not None,
    }
    _log_informe_telemetry(entry, result)
    return entry


def run(ctx: WorkspaceContext) -> dict[str, Any]:
    """Stage runner — persiste informes encontrados em ``data/income_tax_br/`` (não registrado em STAGE_REGISTRY)."""
    from pipeline.llm.litellm_client import LLMConfig

    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    docs = _find_informes(ctx)
    if not docs:
        return {"skipped": True, "reason": "No informe_aluguel documents found"}

    docs = docs[:_MAX_DOCS_PER_RUN]
    config = LLMConfig(
        provider=str(llm_config_data.get("provider") or "anthropic"),
        api_key=str(llm_config_data.get("api_key") or ""),
        model_name=str(llm_config_data.get("model_name") or "claude-sonnet-4-20250514"),
        max_tokens=int(llm_config_data.get("max_tokens") or 4096),
        temperature=float(
            llm_config_data["temperature"]
            if llm_config_data.get("temperature") is not None
            else 0.1
        ),
    )

    store = ctx.get_artifact_store()
    processed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for doc in docs:
        try:
            processed.append(_extract_and_persist(doc, config, store))
        except Exception as exc:
            logger.error(
                "extract_informe_aluguel failed for %s: %s", _redact_filename_pii(doc.name), exc
            )
            errors.append({"file": _redact_filename_pii(doc.name), "error": str(exc)[:300]})

    return {
        "success": len(errors) == 0,
        "processed": processed,
        "errors": errors,
        "total_processed": len(processed),
        "total_errors": len(errors),
    }
