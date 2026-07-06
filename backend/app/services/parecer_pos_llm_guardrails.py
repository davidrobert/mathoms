"""Guardrails determinísticos pós-LLM do parecer (A28.l11 · ADR-292/294/295)."""

# Duas garantias aplicadas em ``_generate_with_llm`` ANTES de ``finalize_output``:
# (1) premissas do Monte Carlo em fallback (``premissas_economicas.status="parcial"``)
#     rebaixam ``confianca alta→media`` de itens ancorados em ``$.if_monte_carlo.*``
#     — rebaixar é a direção segura (ADR-294 "dropar > promover"); nunca bloqueia.
# (2) filtro 3-vias de ``campos_faltantes_pediria_se_iterasse``: path que resolve
#     não-nulo no E5 é espúrio (remove); path nulo com alias conhecido não-nulo é
#     path errado (remove + reanota — alimenta expansão do manifest); path
#     genuinamente ausente é sinal verdadeiro (mantém).
# Coerce/mutação pós-validação, nunca raise, nunca needs_review, zero custo LLM,
# zero reask. NÃO é red line/hard-block (co-design prompt-engineer 2026-07-03).

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from backend.app.services.parecer_distiller import walk_path
from pipeline.llm.schemas.parecer_planejador import (
    CampoFaltante,
    ParecerPlanejadorOutput,
    Risco,
    Sugestao,
)

logger = logging.getLogger("mathoms.llm.parecer_planejador")

_IF_MONTE_CARLO_PREFIX = "$.if_monte_carlo"
_SUGESTAO_HORIZONS = ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")

# Path que o LLM pede errado → path canônico onde o dado vive no E5 (via 2 do
# filtro 3-vias). Dogfood 72883bde: pediu $.composicao_familiar.dependentes com
# o dado presente em $.irpf_kpis.dependentes.
FIELD_PATH_ALIASES: dict[str, str] = {
    "$.composicao_familiar.dependentes": "$.irpf_kpis.dependentes",
}

REASON_SPURIOUS = "field_request_spurious"
REASON_WRONG_PATH = "field_request_wrong_path"


# ----------------------------------------------------------------------
# (1) Confiança sob premissa fallback — camada pós-LLM (garantia)
# ----------------------------------------------------------------------


def _premissas_parciais(e5_data: Mapping[str, Any]) -> bool:
    premissas = e5_data.get("premissas_economicas")
    return isinstance(premissas, Mapping) and premissas.get("status") == "parcial"


def _anchored_on_monte_carlo(item: Risco | Sugestao) -> bool:
    return any(
        a.path is not None and a.path.startswith(_IF_MONTE_CARLO_PREFIX) for a in item.ancoras
    )


def _downgrade_risco(risco: Risco) -> Risco:
    return risco.model_copy(update={"confianca": "media"})


def _downgrade_sugestao(sug: Sugestao) -> Sugestao:
    # Espelha _ck_impacto_only_if_alta (ADR-294): model_copy não re-valida, então
    # o drop de impacto_estimado quando confianca != alta é explícito aqui.
    return sug.model_copy(update={"confianca": "media", "impacto_estimado": None})


def _downgrade_bucket(items: list, downgrade_fn) -> tuple[list, int]:
    out, count = [], 0
    for item in items:
        if item.confianca == "alta" and _anchored_on_monte_carlo(item):
            out.append(downgrade_fn(item))
            count += 1
        else:
            out.append(item)
    return out, count


def _downgraded_buckets(output: ParecerPlanejadorOutput) -> tuple[dict[str, list], int]:
    update: dict[str, list] = {}
    total = 0
    update["riscos"], n = _downgrade_bucket(output.riscos, _downgrade_risco)
    total += n
    for horizon in _SUGESTAO_HORIZONS:
        update[horizon], n = _downgrade_bucket(getattr(output, horizon), _downgrade_sugestao)
        total += n
    return update, total


def downgrade_confianca_fallback(
    output: ParecerPlanejadorOutput, e5_data: Mapping[str, Any], workspace_id: str
) -> tuple[ParecerPlanejadorOutput, int]:
    """Rebaixa ``confianca alta→media`` de itens ancorados em ``$.if_monte_carlo.*``
    quando as premissas do Monte Carlo estão em fallback. Nunca bloqueia (A28.l11)."""
    if not _premissas_parciais(e5_data):
        return output, 0
    update, total = _downgraded_buckets(output)
    if not total:
        return output, 0
    logger.warning(
        "parecer_confianca_rebaixada_premissa_fallback",
        extra={"workspace_id": workspace_id, "count": total},
    )
    return output.model_copy(update=update), total


# ----------------------------------------------------------------------
# (2) Filtro 3-vias de campos_faltantes_pediria_se_iterasse
# ----------------------------------------------------------------------


def _classify_campo(
    campo: CampoFaltante, e5_data: Mapping[str, Any]
) -> tuple[Optional[str], Optional[str]]:
    """``(reason, alias_path)`` — reason ``None`` = genuinamente ausente (mantém)."""
    if campo.field_path is None:
        return None, None  # path coercido (ADR-292) — motivo carrega o sinal, mantém
    if walk_path(e5_data, campo.field_path) is not None:
        return REASON_SPURIOUS, None
    alias = FIELD_PATH_ALIASES.get(campo.field_path)
    if alias is not None and walk_path(e5_data, alias) is not None:
        return REASON_WRONG_PATH, alias
    return None, None


def _audit_entry(campo: CampoFaltante, reason: str, alias: Optional[str] = None) -> dict:
    """Entrada PII-safe p/ ``_meta.field_request_audit`` (path estrutural + motivo LLM)."""
    motivo = campo.motivo
    if alias:
        motivo = f"{campo.motivo} [reanotado: dado presente em {alias}]"
    entry: dict[str, Any] = {"field_path": campo.field_path, "motivo": motivo, "reason": reason}
    if alias:
        entry["alias_path"] = alias
    return entry


def filter_campos_faltantes(
    output: ParecerPlanejadorOutput, e5_data: Mapping[str, Any], workspace_id: str
) -> tuple[ParecerPlanejadorOutput, list[dict]]:
    """Filtro 3-vias (A28.l11): remove pedido espúrio/path errado antes de gravar
    ``PlannerFieldRequest``; mantém o genuinamente ausente. Retorna (output, audit)."""
    campos = output.campos_faltantes_pediria_se_iterasse
    if not campos:
        return output, []
    kept: list[CampoFaltante] = []
    audit: list[dict] = []
    for campo in campos:
        reason, alias = _classify_campo(campo, e5_data)
        if reason is None:
            kept.append(campo)
            continue
        audit.append(_audit_entry(campo, reason, alias))
        logger.warning(reason, extra={"workspace_id": workspace_id, "field_path": campo.field_path})
    if not audit:
        return output, []
    return output.model_copy(update={"campos_faltantes_pediria_se_iterasse": kept}), audit


def guardrails_summary(*, confianca_rebaixada: int, audit: list[dict]) -> dict:
    """Telemetria dos guardrails — ``needs_review_triggered`` é ``False`` por construção
    (critério de aceite A28.l11: nenhum guardrail marca needs_review)."""
    return {
        "confianca_rebaixada": confianca_rebaixada,
        "field_requests_spurious": sum(1 for a in audit if a["reason"] == REASON_SPURIOUS),
        "field_requests_wrong_path": sum(1 for a in audit if a["reason"] == REASON_WRONG_PATH),
        "needs_review_triggered": False,
    }


__all__ = [
    "FIELD_PATH_ALIASES",
    "REASON_SPURIOUS",
    "REASON_WRONG_PATH",
    "downgrade_confianca_fallback",
    "filter_campos_faltantes",
    "guardrails_summary",
]
