"""Section summary orchestrator (v2.9 · ADR-144)."""
# Wire-up de SectionSummaryGenerator com LLMService (LiteLLM/Instructor)
# + Redis cache + fallback determinístico. Vive em backend/ porque conhece
# Anthropic API key (env), Redis client e LLMService com seu setup.
# pipeline/ permanece boundary-clean.

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping, Optional

from pipeline.domain.services.section_summary_generator import (
    LLMRawResponse,
    PromptTemplate,
    SectionSummaryGenerator,
    SectionSummaryGeneratorConfig,
    load_prompt_templates_from_yaml,
    load_prompt_version_from_yaml,
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
            prompt_version=self._prompt_version,
            prompt_name="section_summaries",
        )
        return LLMRawResponse(
            output=result.output,
            prompt_tokens=result.tokens_in,
            completion_tokens=result.tokens_out,
        )


def _default_fallback(section_id: str, snapshot_data: Mapping[str, Any]) -> Optional[str]:
    """Fallback determinístico — usa narrativas[summaries] do snapshot se houver."""
    text = _read_legacy_summary(snapshot_data, section_id)
    if text:
        return text
    return _GENERIC_FALLBACK.get(section_id)


# ADR-356 §D2: a chave de `narrativas.summaries` NÃO é `section_id.lower()`.
# `summaries.s2` é o parágrafo de SCORE e a S2 do layout é Fluxo de Caixa —
# derivar por lowercase publicava o score no topo do fluxo de caixa. O mapa
# canônico é `summary_source`, declarado no layout (mesma fonte que o renderer
# React lê). Seção sem destino declarado cai no fallback genérico.
def _summary_source_key(section_id: str) -> Optional[str]:
    from backend.app.generated.report_layout import LAYOUT

    estrategico = LAYOUT.estrategico
    for entry in [*estrategico.sections, *estrategico.appendices]:
        if entry.id == section_id:
            return entry.summary_source if entry.enabled else None
    return None


def _read_legacy_summary(snapshot_data: Mapping[str, Any], section_id: str) -> Optional[str]:
    if not isinstance(snapshot_data, Mapping):
        return None
    narrativas = snapshot_data.get("_narrativas")
    if not isinstance(narrativas, Mapping):
        return None
    summaries = narrativas.get("summaries")
    key = _summary_source_key(section_id)
    if not isinstance(summaries, Mapping) or key is None:
        return None
    text = summaries.get(key)
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


_GENERIC_FALLBACK: dict[str, str] = {
    "S1": "Patrimônio consolidado e estrutura de ativos/passivos.",
    "S2": "Fluxo de caixa e diagnóstico comportamental do período.",
    "S3": "Carteira de investimentos: alocação atual, alvo e principais ativos.",
    "S4": "Imóveis e renda passiva — rentabilidade comparada a benchmarks.",
    "S7": "Independência financeira — projeção de longo prazo.",
    "S8": "Estrutura tributária e previdenciária — eficiência fiscal.",
    "S9": "Mapa de riscos e cobertura atual de seguros críticos.",
    "S10": "Síntese dos pontos fortes e urgências do ciclo.",
    "T2": "Cobertura da meta de aportes do ciclo.",
    "T3": "Tributação tática do ciclo.",
    "T5": "Cenários e simulações considerados.",
}


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
    """Hash determinístico do payload da seção (entra em cache key)."""
    raw = json.dumps(snapshot_data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_default_generator(
    *,
    templates: Optional[Mapping[str, PromptTemplate]] = None,
    config: Optional[SectionSummaryGeneratorConfig] = None,
) -> SectionSummaryGenerator:
    """Construtor padrão — wire LiteLLM + Redis + fallback determinístico."""
    yaml_path = _resolve_yaml_path()
    resolved_templates = templates or load_prompt_templates_from_yaml(yaml_path)
    llm_client = _build_llm_client() or _NoLLMRaisingClient()
    return SectionSummaryGenerator(
        llm_client=llm_client,
        cache=_build_cache(),
        fallback=_default_fallback,
        templates=resolved_templates,
        config=config
        or SectionSummaryGeneratorConfig(
            model=_resolve_model(),
            prompt_version=load_prompt_version_from_yaml(yaml_path),
        ),
    )


class _NoLLMRaisingClient:
    """Stub que sempre levanta — força fallback sem chamada de rede."""

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
    narrativas = e5_data.get("narrativas") if isinstance(e5_data, Mapping) else None
    return _run_for_all_sections(gen, workspace_id, e5_data, narrativas)


def _run_for_all_sections(
    gen: SectionSummaryGenerator,
    workspace_id: int,
    e5_data: Mapping[str, Any],
    narrativas: Any,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for section_id in SUPPORTED_SECTION_IDS:
        section_payload = _slice_section_data(e5_data, section_id, narrativas)
        result = gen.generate(
            section_id=section_id,
            snapshot_hash=compute_snapshot_hash(section_payload),
            workspace_id=workspace_id,
            snapshot_data=section_payload,
        )
        if result.text:
            out[section_id] = result.text
    return out


def _slice_section_data(
    e5_data: Mapping[str, Any],
    section_id: str,
    narrativas: Any,
) -> dict[str, Any]:
    """Filtra E5 snapshot p/ payload mínimo da seção (sem PII redundante)."""
    keys = _SECTION_KEYS.get(section_id, ())
    payload: dict[str, Any] = {}
    for key in keys:
        value = e5_data.get(key)
        if value is not None:
            payload[key] = value
    # Anexa narrativas só para fallback determinístico — generator não loga.
    if isinstance(narrativas, Mapping):
        payload["_narrativas"] = {"summaries": narrativas.get("summaries", {})}
    return payload


# Mapa de section_id → keys do E5 que entram no prompt. Não exaustivo —
# caller (Fase 3) pode estender via parâmetro de override; placeholder
# Fase 2.
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
