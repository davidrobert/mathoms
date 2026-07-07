"""Stage runner extract_informes_anuais — informes anuais polimórficos (ADR-238)."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext
    from pipeline.llm.litellm_client import LLMConfig

logger = logging.getLogger("mathoms.pipeline.informes_anuais")

_INFORME_MIN_COMPLETION_TOKENS = 8_192
_MAX_DOCS_PER_RUN = 20
_NEEDS_REVIEW_CONFIDENCE_THRESHOLD = 0.7

_FILENAME_CPF_MASKED = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_FILENAME_CPF_LOOSE = re.compile(r"(?<!\d)\d{11}(?!\d)")
_FILENAME_CNPJ_MASKED = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")

# CPF do titular: extração via Python pós-LLM (gate financial-planner Q8).
# LLM nunca emite CPF — risco LGPD de o LLM errar a máscara e vazar PII.
_CPF_RAW_RE = re.compile(r"(?<!\d)(\d{3})(\d{3})(\d{3})(\d{2})(?!\d)")
_CPF_FORMATTED_RE = re.compile(r"(?<!\d)(\d{3})\.(\d{3})\.(\d{3})-(\d{2})(?!\d)")

# Filename patterns por tipo_informe. L1 cobre previdencia_privada apenas;
# L2-L4 estendem este mapping para financeiro_pj/pf, proventos, aluguel.
# Tokens são lowercase e comparados após .lower() do filename.
_TIPO_FILENAME_TOKENS: dict[str, tuple[str, ...]] = {
    "previdencia_privada": (
        "informepgbl",
        "informevgbl",
        "informe_previdencia",
        "informeprevidencia",
        "brasilprev",
        "bradesco_vida",
        "bradescovida",
        "caixa_vida",
        "caixavida",
        "icatu",
        "mongeral",
    ),
    "financeiro_pj": (
        "informe_pj",
        "informepj",
        "comprovante_pj",
        "comprovantepj",
        "comprovante_rendimentos_pj",
        "stone_pj",
        "stonepj",
        "cielo_pj",
        "cielopj",
        "rede_pj",
        "redepj",
        "getnet_pj",
        "getnetpj",
        "pagseguro_pj",
        "pagseguropj",
        "c6_pj",
        "c6pj",
    ),
    "financeiro_pf": (
        "informe_pf",
        "informepf",
        "informerendimentos",
        "informe_rendimentos",
        "informerendimentosfinanceiros",
        "informe_rendimentos_financeiros",
        "wise",
        "avenue",
        "nomad",
        "stake",
    ),
    "proventos_acoes": (
        "informe_proventos",
        "informeproventos",
        "xp_proventos",
        "xpproventos",
        "proventos_acoes",
        "proventos_xp",
        "itausa_acoes",
        "itausaacoes",
        "bradespar_acoes",
        "relatorio_proventos",
    ),
}


def _redact_filename_pii(name: str) -> str:
    """Mascara CPF/CNPJ em filenames antes de logar (PII)."""
    name = _FILENAME_CPF_MASKED.sub("<cpf-redacted>", name)
    name = _FILENAME_CPF_LOOSE.sub("<cpf-redacted>", name)
    name = _FILENAME_CNPJ_MASKED.sub("<cnpj-redacted>", name)
    return name


def _mask_cpf(cpf: str) -> str:
    """``12345678900`` → ``***.456.789-**`` (mask parcial preservando centrais — LGPD ADR-231)."""
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11:
        return ""
    return f"***.{digits[3:6]}.{digits[6:9]}-**"


def _extract_titular_cpf_masked(text: str) -> str | None:
    """Extrai 1º CPF do texto do informe e mascara em Python (gate financial-planner Q8)."""
    m = _CPF_FORMATTED_RE.search(text) or _CPF_RAW_RE.search(text)
    if m is None:
        return None
    return _mask_cpf("".join(m.groups()))


def _content_hash(doc: Path) -> str:
    """SHA-256 do PDF para cache key idempotente (gate data-engineer Q4)."""
    h = hashlib.sha256()
    with doc.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# Informe de aluguel tem stage dedicado (extract_informe_aluguel · ADR-216) com
# schema próprio. Seu filename `informerendimentosaluguel` contém o substring
# `informerendimentos` (token financeiro_pf) — sem este guard, este stage o
# reclassifica como financeiro_pf, o LLM não popula nenhum dos 4 quadros RFB e
# `_ao_menos_um_quadro_nao_vazio` hard-falha após 4 retries (incidente dogfood).
_ALUGUEL_EXCLUSIVE_TOKEN = "informerendimentosaluguel"


def _detect_tipo_informe(filename: str) -> str | None:
    """Detecta tipo_informe pelo filename (lowercase) — None se nenhum tipo casar."""
    lowered = filename.lower()
    if _ALUGUEL_EXCLUSIVE_TOKEN in lowered:
        return None
    for tipo, tokens in _TIPO_FILENAME_TOKENS.items():
        if any(token in lowered for token in tokens):
            return tipo
    return None


_INSTITUTION_HINTS: tuple[str, ...] = (
    "brasilprev",
    "bradesco",
    "caixa",
    "icatu",
    "mongeral",
    "xp",
    "stone",
    "cielo",
    "rede",
    "getnet",
    "pagseguro",
    "c6bank",
    "c6_pj",
    "itau",
    "itausa",
    "bradespar",
    "santander",
    "nubank",
    "picpay",
    "rico",
    "btgpactual",
    "inter",
    "wise",
    "avenue",
    "nomad",
    "stake",
    "interinvestusa",
    "xpinvestimentos",
    "clear",
    "modal",
)


def _detect_institution_hint(filename: str) -> str:
    """Heurística simples para institution_code; sem match → unknown."""
    lowered = filename.lower()
    return next((code for code in _INSTITUTION_HINTS if code in lowered), "unknown")


def _find_informes(ctx: WorkspaceContext) -> list[Path]:
    """Localiza PDFs em ``data/income_tax_br/`` com filename de informe anual coberto pela lane."""
    income_dir = ctx.data_dir / "income_tax_br"
    if not income_dir.exists():
        return []
    out: list[Path] = []
    for f in sorted(income_dir.rglob("*")):
        if not f.is_file() or f.suffix.lower() != ".pdf":
            continue
        if _detect_tipo_informe(f.name):
            out.append(f)
    return out


def _artifact_key_for(tipo_informe: str, institution: str, ano_base: int | None) -> str:
    """Compõe artifact_key ``<tipo_curto>_<inst>_<ano>`` (ADR-238 D3)."""
    short = tipo_informe.replace("_privada", "").replace("_acoes", "")
    ano_part = str(ano_base) if ano_base is not None else "ano_desconhecido"
    return f"{short}_{institution}_{ano_part}"


def _stem_for_filename(name: str) -> str:
    """Stem do filename para tracing — strip de ``-0_original`` e extensão."""
    for ext in (".pdf", ".PDF"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    if "-0_original" in name:
        name = name.split("-0_original")[0]
    return name


def _load_prompt_module(tipo_informe: str):
    """Importa o módulo de prompt correspondente ao `tipo_informe` (ADR-238 D2)."""
    from pipeline.llm.prompts import informe_pf, informe_pj, informe_previdencia, informe_proventos

    return {
        "previdencia_privada": informe_previdencia,
        "financeiro_pj": informe_pj,
        "financeiro_pf": informe_pf,
        "proventos_acoes": informe_proventos,
    }[tipo_informe]


def _build_user_prompt_for(
    tipo_informe: str, doc_name: str, text: str, ano_hint: int | None
) -> str:
    """User prompt formatado com filename/institution/ano + texto do documento."""
    prompt_mod = _load_prompt_module(tipo_informe)
    return prompt_mod.USER_PROMPT_TEMPLATE.format(
        filename=doc_name,
        institution=_detect_institution_hint(doc_name),
        ano_referencia=ano_hint if ano_hint is not None else "(inferir do documento)",
        document_text=text,
    )


def _build_user_prompt(doc_name: str, text: str, ano_hint: int | None) -> str:
    """Compat alias para previdência (preservado para callers externos pré-L2)."""
    return _build_user_prompt_for("previdencia_privada", doc_name, text, ano_hint)


def _call_llm_for(tipo_informe, service, config, doc_name, text, ano_hint, content_hash):
    """Cache key idempotente: content_hash + PROMPT_VERSION (gate data-engineer Q4)."""
    from pipeline.llm.metrics import prompt_name_of
    from pipeline.llm.schemas.informe_base import InformeRendimentosBase

    prompt_mod = _load_prompt_module(tipo_informe)
    result = service.call(
        system_prompt=prompt_mod.SYSTEM_PROMPT,
        user_prompt=_build_user_prompt_for(tipo_informe, doc_name, text, ano_hint),
        output_schema=InformeRendimentosBase,
        max_tokens=max(config.max_tokens, _INFORME_MIN_COMPLETION_TOKENS),
        stage=f"extract_informes_anuais:{content_hash[:16]}:{prompt_mod.PROMPT_VERSION}",
        prompt_version=prompt_mod.PROMPT_VERSION,
        prompt_name=prompt_name_of(prompt_mod),
    )
    return result, prompt_mod.PROMPT_VERSION


def _persist_processed(
    doc: Path, payload: dict, result, ctx: WorkspaceContext, ws_id: str
) -> dict[str, Any]:
    """Persiste o artifact + emite log estruturado; retorna summary do processado."""
    store = ctx.get_artifact_store()
    tipo = payload.get("tipo_informe", "previdencia_privada")
    institution = _detect_institution_hint(doc.name)
    ano_base = payload.get("ano_base")
    key = _artifact_key_for(tipo, institution, ano_base)
    # Schema validation roda no hook pós-write de DBArtifactStore (ADR-212 PR3).
    store.write("extract_informes_anuais", key, payload)
    _log_run(doc.name, ws_id, payload, result, tipo)
    return {
        "file": _redact_filename_pii(doc.name),
        "artifact_key": key,
        "tipo_informe": tipo,
        "ano_base": ano_base,
        "confidence": payload.get("confidence"),
        "needs_review": payload.get("needs_review", False),
    }


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
            "extract_informes_anuais failed for %s: %s", _redact_filename_pii(doc.name), exc
        )
        return None, _err(doc, exc)
    if payload is None:
        return None, _err(doc, result)
    ws_id = getattr(ctx, "workspace_id", "unknown")
    return _persist_processed(doc, payload, result, ctx, ws_id), None


_NOTA_REGRESSIVO_SEM_ADESAO = (
    "Regime regressivo sem data_adesao no informe — alíquota PEPS indeterminada; "
    "saldo registrado (ADR-238 V1)."
)


def _flag_regressivo_sem_adesao(payload: dict) -> None:
    """Regressivo sem data_adesao → needs_review + nota (ADR-238: não perder saldo)."""
    prev = payload.get("previdencia")
    if not isinstance(prev, dict):
        return
    if prev.get("regime_tributacao") != "regressivo" or prev.get("data_adesao") is not None:
        return
    payload["needs_review"] = True
    nota = prev.get("notas")
    prev["notas"] = (
        f"{nota} {_NOTA_REGRESSIVO_SEM_ADESAO}".strip() if nota else _NOTA_REGRESSIVO_SEM_ADESAO
    )


def _build_payload(output, prompt_version: str, doc_text: str, source_artifact_id: str) -> dict:
    """Materializa payload + força prompt_version + mask CPF Python + source_artifact_id."""
    payload = output.model_dump(mode="json")
    payload["prompt_version"] = prompt_version
    payload["source_artifact_id"] = source_artifact_id
    # LGPD ADR-231 + financial-planner Q8: NUNCA confiar no LLM para mascarar CPF.
    # Force null + extrai via regex Python no texto do documento.
    payload["titular_cpf_masked"] = _extract_titular_cpf_masked(doc_text)
    confidence = payload.get("confidence", 1.0)
    if confidence < _NEEDS_REVIEW_CONFIDENCE_THRESHOLD:
        payload["needs_review"] = True
    _flag_regressivo_sem_adesao(payload)
    return payload


_SUPPORTED_TIPOS_INFORME: tuple[str, ...] = (
    "previdencia_privada",
    "financeiro_pj",
    "financeiro_pf",
    "proventos_acoes",
)


def _extract_one(doc: Path, text: str, service, config, tipo_informe: str) -> tuple[dict, Any, str]:
    """Despacho por tipo_informe; A17 L1-L4 cobrem todos os 4 tipos canônicos."""
    if tipo_informe not in _SUPPORTED_TIPOS_INFORME:
        raise NotImplementedError(
            f"tipo_informe={tipo_informe!r} não suportado. Tipos canônicos A17: "
            f"{', '.join(_SUPPORTED_TIPOS_INFORME)}."
        )
    content_hash = _content_hash(doc)
    result, prompt_version = _call_llm_for(
        tipo_informe, service, config, doc.name, text, ano_hint=None, content_hash=content_hash
    )
    # source_artifact_id = stem do `-0_original` (P3 promove para FK UUID).
    source_artifact_id = _stem_for_filename(doc.name)
    payload = _build_payload(result.output, prompt_version, text, source_artifact_id)
    return payload, result, prompt_version


def _extract_text(doc: Path) -> str:
    from pipeline.llm.text_extractor import DocumentTextExtractor

    extractor = DocumentTextExtractor(max_chars=80_000)
    return extractor.extract(doc)


def _log_run(doc_name: str, ws_id: str, payload: dict, result, tipo_informe: str) -> None:
    """Telemetria LGPD-safe (ADR-238 P6 + ADR-231): sem PII, sem valores monetários."""
    logger.info(
        "mathoms.informes.classified",
        extra={
            "workspace_id": ws_id,
            "doc": _redact_filename_pii(doc_name),
            "tipo_informe": tipo_informe,
            "instituicao": _detect_institution_hint(doc_name),
            "ano_base": payload.get("ano_base"),
            "confidence": payload.get("confidence"),
            "needs_review": payload.get("needs_review", False),
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_estimate_usd,
        },
    )


def _process_one(
    doc: Path, ctx: WorkspaceContext, service, config
) -> tuple[dict, Any] | tuple[None, str]:
    """Processa 1 doc; retorna (payload, result) ou (None, error_message)."""
    tipo = _detect_tipo_informe(doc.name)
    if tipo is None:
        return (
            None,
            f"filename não casa nenhum tipo_informe conhecido: {_redact_filename_pii(doc.name)}",
        )

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
    docs = _find_informes(ctx)
    if not docs:
        return {"skipped": True, "reason": "No informes anuais found"}
    llm_config = LLMConfig(
        **cfg, call_hooks=ctx.llm_call_hooks, metrics_emitter=ctx.llm_metrics_emitter
    )
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
    """Executa extração de informes anuais — L1 cobre previdência (ADR-238)."""
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
