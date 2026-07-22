"""Camada LLM do stage ``extract_comprovantes_bens`` — calls CRLV/apólice + payloads LGPD.

Extraído do stage runner (A33.l8): o runner ultrapassou 500 linhas quando
A33.l7 (métricas OTLP) e A33.l8 (catálogo de seguradoras) cresceram o mesmo
arquivo. Aqui vive o que fala com o LLM (prompts, calls, payload building,
mask de CPF pós-LLM — ADR-239 D6/D8, ADR-231); orquestração/persistência
continuam no stage.
"""

from __future__ import annotations

import logging
import re
from typing import Mapping

from pipeline.domain.services.seguradora_resolver import resolve_seguradora

logger = logging.getLogger("mathoms.pipeline.comprovantes_bens")

_LLM_MIN_TOKENS = 4_096
_NEEDS_REVIEW_CONFIDENCE_THRESHOLD = 0.7

# CPF detection (LGPD ADR-231): Python mask pós-LLM, nunca confiar no LLM.
_CPF_RAW_RE = re.compile(r"(?<!\d)(\d{3})(\d{3})(\d{3})(\d{2})(?!\d)")
_CPF_FORMATTED_RE = re.compile(r"(?<!\d)(\d{3})\.(\d{3})\.(\d{3})-(\d{2})(?!\d)")


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


def _build_user_prompt(doc_name: str, text: str) -> str:
    from pipeline.llm.prompts import crlv as prompt_mod

    return prompt_mod.USER_PROMPT_TEMPLATE.format(filename=doc_name, document_text=text)


def _call_llm_crlv(service, config, doc_name: str, text: str):
    from pipeline.llm.metrics import prompt_name_of
    from pipeline.llm.prompts import crlv as prompt_mod
    from pipeline.llm.schemas.crlv import CRLVPayload

    # ADR-307: cache real no choke-point (key = content-hash do prompt) exige
    # temp=0; ``stage`` volta a ser descritivo (ADR-093 — antes carregava uma
    # pseudo-key que poluía a cardinalidade do LLMCallLog).
    result = service.call(
        system_prompt=prompt_mod.SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(doc_name, text),
        output_schema=CRLVPayload,
        max_tokens=max(config.max_tokens, _LLM_MIN_TOKENS),
        temperature=0.0,
        stage="extract_comprovantes_bens",
        prompt_version=prompt_mod.PROMPT_VERSION,
        prompt_name=prompt_name_of(prompt_mod),
        use_cache=True,
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


# Apólice — cascata Haiku → Sonnet (ADR-239 D6). Strings detectadas no texto do
# PDF disparam Sonnet (caso V1 obrigatório: combinada Porto = Toro + residência).
_CASCADE_TRIGGER_STRINGS = (
    "combinada",
    "proteção combinada",
    "residencial+auto",
    "residencial + auto",
    "multi-bem",
)


def _build_apolice_user_prompt(doc_name: str, text: str, seguradoras_catalog: str) -> str:
    from pipeline.llm.prompts import apolice as prompt_mod

    return prompt_mod.USER_PROMPT_TEMPLATE.format(
        filename=doc_name, document_text=text, seguradoras_catalog=seguradoras_catalog
    )


def _call_llm_apolice(service, config, doc_name, text, seguradoras_catalog):
    """LLM call apólice — ``service`` pré-bound ao modelo (Haiku/Sonnet); o modelo entra na cache key do choke-point (ADR-307)."""
    from pipeline.llm.metrics import prompt_name_of
    from pipeline.llm.prompts import apolice as prompt_mod
    from pipeline.llm.schemas.apolice import ApolicePayload

    result = service.call(
        system_prompt=prompt_mod.SYSTEM_PROMPT,
        user_prompt=_build_apolice_user_prompt(doc_name, text, seguradoras_catalog),
        output_schema=ApolicePayload,
        max_tokens=max(config.max_tokens, _LLM_MIN_TOKENS),
        temperature=0.0,
        stage="extract_comprovantes_bens",
        prompt_version=prompt_mod.PROMPT_VERSION,
        prompt_name=prompt_name_of(prompt_mod),
        use_cache=True,
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
    output,
    prompt_version: str,
    doc_text: str,
    source_artifact_id: str,
    cascade_triggered: bool,
    seguradoras_catalog: Mapping[str, str] | None = None,
) -> dict:
    """Payload apólice + mask CPFs (pagador + segurado) Python pós-LLM (LGPD ADR-231 D8)."""
    payload = output.model_dump(mode="json")
    payload["prompt_version"] = prompt_version
    payload["source_artifact_id"] = source_artifact_id
    payload["cascade_triggered"] = cascade_triggered
    _apply_apolice_cpf_masks(payload, doc_text)
    payload["sinistro_indenizacao_recebida_brl"] = None  # placeholder V1 (ADR-238 integra em V2)
    _canonicalize_output_seguradora(payload, seguradoras_catalog or {})
    confidence = payload.get("confidence", 1.0)
    if confidence < _NEEDS_REVIEW_CONFIDENCE_THRESHOLD:
        payload["needs_review"] = True
    return payload


def _apply_apolice_cpf_masks(payload: dict, doc_text: str) -> None:
    """LGPD ADR-231 D8: mascara CPF do texto em Python (LLM SEMPRE retorna null)."""
    cpf_first = _extract_titular_cpf_masked(doc_text)
    payload["pagador_cpf_masked"] = cpf_first
    payload["segurado_cpf_masked"] = cpf_first


def _canonicalize_output_seguradora(payload: dict, seguradoras_catalog: Mapping[str, str]) -> None:
    """Validação de output contra os codes ``category=insurance`` (A37.l11):
    canonicaliza variante do nome; code fora do catálogo persiste normalizado
    com flag SOFT de telemetria; ``needs_review`` só em ambiguidade real."""
    res = resolve_seguradora(str(payload.get("seguradora") or ""), seguradoras_catalog)
    if not res.code:
        return
    payload["seguradora"] = res.code
    if res.ambiguous:
        payload["needs_review"] = True
    if not res.in_catalog:
        logger.info(
            "mathoms.comprovantes.seguradora_fora_catalogo",
            extra={"seguradora_code": res.code, "ambiguous": res.ambiguous},
        )
