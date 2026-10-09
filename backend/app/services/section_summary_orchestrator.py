"""Section summary orchestrator (v2.9 · ADR-144)."""
# Wire-up de SectionSummaryGenerator com LLMService (LiteLLM/Instructor)
# + Redis cache. Vive em backend/ porque conhece Anthropic API key (env),
# Redis client e LLMService com seu setup. pipeline/ permanece boundary-clean.
# Sem fallback aqui: seção que falha fica ausente de `section_summaries`, e a
# precedência da ADR-356 (camadas 2 e 3) decide no renderer.

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Mapping, Optional

from backend.app.services.parecer_prose_money import extract_money_tokens, extract_usd_tokens
from pipeline.domain.services.section_summary_generator import (
    LLMRawResponse,
    PromptTemplate,
    SectionSummaryGenerator,
    SectionSummaryGeneratorConfig,
    load_prompt_templates_from_yaml,
    load_prompt_version_from_yaml,
    serialize_section_payload,
)
from pipeline.llm.schemas.section_summaries import SectionSummaryOutput

logger = logging.getLogger("mathoms.llm.section_summaries")

#: Caminho relativo ao repo root.
_PROMPT_YAML = "config/prompts/section_summaries.yaml"

#: Section IDs cobertos por LLM em v2.9 — paridade com YAML.
#: ADR-168 (A8.4 PR4): U1/U2 removidos com Modo USA.
SUPPORTED_SECTION_IDS: tuple[str, ...] = (
    "S1",
    "S2",
    "S3",
    "S4",
    "S7",
    "S8",
    "S9",
    "S10",
    "T2",
    "T3",
    "T5",
)


def _build_summary_llm_service(api_key: str, model_name: str, max_tokens: int, call_hooks):
    from backend.app.core.llm_metrics import get_llm_metrics_emitter
    from pipeline.llm.litellm_client import LLMConfig, LLMService

    return LLMService(
        LLMConfig(
            provider="anthropic",
            api_key=api_key,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=0.0,
            call_hooks=call_hooks,
            metrics_emitter=get_llm_metrics_emitter(),
        )
    )


#: Amostragem das narrativas. A `temperature` já era 0.0 no `LLMConfig`; o gate
#: `dev/check_llm_sampling.py` exige no call-site, que é a superfície que ele
#: inspeciona — valor em config é invisível a ele. Versão do prompt vem do YAML
#: (`load_prompt_version_from_yaml`), então não há módulo em PROMPT_DIRS p/ hospedar.
SUMMARY_TEMPERATURE = 0.0
SUMMARY_SEED = 20260819


class _LiteLLMSectionSummaryClient:
    """Adapter ``SectionSummaryLLMClient`` sobre ``pipeline.llm.LLMService``."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        max_tokens: int = 600,
        call_hooks=None,
        prompt_version: Optional[str] = None,
    ) -> None:
        self._prompt_version = prompt_version
        self._service = _build_summary_llm_service(api_key, model_name, max_tokens, call_hooks)

    def call(self, *, system_prompt: str, user_prompt: str, section_id: str) -> LLMRawResponse:
        result = self._service.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=SectionSummaryOutput,
            stage=f"section-summary[{section_id}]",
            temperature=SUMMARY_TEMPERATURE,
            seed=SUMMARY_SEED,
            prompt_version=self._prompt_version,
            prompt_name="section_summaries",
        )
        return LLMRawResponse(
            output=result.output,
            prompt_tokens=result.tokens_in,
            completion_tokens=result.tokens_out,
        )


# Detector do parecer, não `\breais\b`: "juros reais" e "ganhos reais" são
# vocabulário do relatório. Exige número junto de R$/reais/US$/dólares.
def _cita_valor_monetario(summary_md: str) -> bool:
    """Prosa com valor monetário — o prompt proíbe (ADR-090)."""
    return bool(extract_money_tokens([summary_md]) or extract_usd_tokens([summary_md]))


def _resolve_yaml_path() -> str:
    """Localiza o YAML de prompts independente de cwd."""
    candidates = [Path(_PROMPT_YAML), Path(__file__).resolve().parents[3] / _PROMPT_YAML]
    for path in candidates:
        if path.is_file():
            return str(path)
    return _PROMPT_YAML  # last resort; load_prompt_templates_from_yaml errors clean


def _resolve_llm_enabled() -> bool:
    return os.environ.get("MATHOMS_LLM_SECTION_SUMMARIES", "0") == "1"


def _resolve_model() -> str:
    return os.environ.get("MATHOMS_LLM_SECTION_SUMMARY_MODEL", "claude-haiku-4-5")


def _build_llm_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    return _LiteLLMSectionSummaryClient(
        api_key=api_key,
        model_name=_resolve_model(),
        prompt_version=load_prompt_version_from_yaml(_resolve_yaml_path()),
    )


def _build_cache():
    from backend.app.services.storage.llm_cache import get_default_llm_cache

    return get_default_llm_cache()


def compute_snapshot_hash(snapshot_data: Mapping[str, Any]) -> str:
    """Hash do payload na serialização que vai ao prompt (entra em cache key)."""
    raw = serialize_section_payload(snapshot_data)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_default_generator(
    *,
    templates: Optional[Mapping[str, PromptTemplate]] = None,
    config: Optional[SectionSummaryGeneratorConfig] = None,
) -> SectionSummaryGenerator:
    """Construtor padrão — wire LiteLLM + Redis."""
    yaml_path = _resolve_yaml_path()
    resolved_templates = templates or load_prompt_templates_from_yaml(yaml_path)
    llm_client = _build_llm_client() or _NoLLMRaisingClient()
    return SectionSummaryGenerator(
        llm_client=llm_client,
        cache=_build_cache(),
        cites_money=_cita_valor_monetario,
        templates=resolved_templates,
        config=config
        or SectionSummaryGeneratorConfig(
            model=_resolve_model(),
            prompt_version=load_prompt_version_from_yaml(yaml_path),
        ),
    )


class _NoLLMRaisingClient:
    """Stub que sempre levanta — seção fica ausente, sem chamada de rede."""

    def call(self, *, system_prompt: str, user_prompt: str, section_id: str) -> LLMRawResponse:
        raise RuntimeError("ANTHROPIC_API_KEY missing — section summaries via LLM disabled")


def generate_all_section_summaries(
    *,
    workspace_id: int,
    e5_data: Mapping[str, Any],
    generator: Optional[SectionSummaryGenerator] = None,
) -> dict[str, str]:
    """Itera sobre ``SUPPORTED_SECTION_IDS`` e retorna mapa ``{id: text}``."""
    if not _resolve_llm_enabled() and generator is None:
        logger.info("section_summaries_skipped_llm_disabled")
        return {}
    gen = generator or build_default_generator()
    return _run_for_all_sections(gen, workspace_id, e5_data)


def _run_for_all_sections(
    gen: SectionSummaryGenerator,
    workspace_id: int,
    e5_data: Mapping[str, Any],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for section_id in SUPPORTED_SECTION_IDS:
        section_payload = _slice_section_data(e5_data, section_id)
        result = gen.generate(
            section_id=section_id,
            snapshot_hash=compute_snapshot_hash(section_payload),
            workspace_id=workspace_id,
            snapshot_data=section_payload,
        )
        if result.text:
            out[section_id] = result.text
    return out


def _slice_section_data(e5_data: Mapping[str, Any], section_id: str) -> dict[str, Any]:
    """Filtra E5 snapshot p/ payload mínimo da seção (sem PII redundante)."""
    keys = _SECTION_KEYS.get(section_id, ())
    return {key: e5_data[key] for key in keys if e5_data.get(key) is not None}


# Mapa de section_id → keys do E5 que entram no prompt. É o payload inteiro:
# chave fora daqui não vai ao provider (ADR-144 §Emenda 2026-10-09). Não
# exaustivo — caller (Fase 3) pode estender via parâmetro de override;
# placeholder Fase 2.
_SECTION_KEYS: dict[str, tuple[str, ...]] = {
    "S1": ("patrimonio", "reserva_emergencia", "endividamento"),
    "S2": ("fluxo_caixa", "diagnostico_comportamental"),
    "S3": ("investimentos",),
    "S4": ("patrimonio",),
    "S7": ("cenarios_conjuge", "ratios"),
    "S8": ("previdencia_pgbl", "ratios"),
    "S9": ("alertas", "pontos_urgentes"),
    "S10": ("score", "pontos_fortes", "pontos_urgentes"),
    "T2": ("goals", "investimentos"),
    "T3": ("ratios",),
    "T5": ("cenarios_conjuge",),
}
