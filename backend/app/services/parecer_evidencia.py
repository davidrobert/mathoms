"""Citação verificada E5→E6 — guardrail 3 camadas do evidencia_path (ADR-279 §E · F4)."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Iterator, Optional

from pipeline.llm.prompts.parecer_planejador import PROMPT_VERSION
from pipeline.llm.schemas.parecer_planejador import ParecerPlanejadorOutput
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

logger = logging.getLogger("mathoms.llm.parecer_planejador")

# Entra no composite de compute_cache_key — bump invalida caches pré-F4.
# "2" (ADR-292): coerção de evidencia_path inválido → None muda o output
# persistido (path-filtro que antes virava reask agora vira null + missing_path).
EVIDENCIA_VERIFICATION_VERSION = "2"

_EVIDENCIA_MODE_ENV = "MATHOMS_PARECER_EVIDENCIA_MODE"
_VALID_MODES = ("warn", "strict")

# Ancorada em R$ — percentuais, anos, datas e multiplicadores sem R$ ficam fora.
_MONEY_RE = re.compile(
    r"R\$\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi)\b)?"
)

# Faixa monetária inventada ("R$ 250-300 mil", "R$ 260 a 520 mil") — telemetria
# KR2 do PLAN-suggestion-lifecycle (ADR-290 F2): faixa só é legítima quando o
# campo-fonte é faixa (ver _LEGIT_RANGE_PATH_PREFIXES).
_RANGE_RE = re.compile(r"R\$\s*[\d.,]+\s*(?:-|–|\ba\b|\baté\b)\s*(?:R\$\s*)?[\d.,]+")

# Paths cujo valor é legitimamente faixa/banda (percentis Monte Carlo, cenários,
# projeções) — suprimem a camada value_mismatch (mitigação do risco R3 do plano;
# escolha validada com prompt-engineer 2026-06-12). Escalares exatos
# (reserva_emergencia, endividamento, patrimonio) ficam FORA por design.
_LEGIT_RANGE_PATH_PREFIXES = (
    "$.if_monte_carlo",
    "$.cenarios_conjuge",
    "$.passive_income",
    "$.ratios.rentabilidade",
)


def _is_legit_range_path(path: str) -> bool:
    return path.startswith(_LEGIT_RANGE_PATH_PREFIXES)


_LAYERS = ("missing_path", "whitelist_miss", "resolve_null", "value_mismatch")
_REASON_TO_LAYER = {
    "path_not_whitelisted": "whitelist_miss",
    "value_null": "resolve_null",
    "value_absent": "resolve_null",
}
_MAX_NUMERIC_LEAVES = 50


@dataclass(frozen=True)
class MoneyToken:
    """Token monetário extraído da prosa — sempre em cents int (ADR-090)."""

    cents: int
    half_step_cents: int  # 0 = match exato; >0 = intervalo [cents-h, cents+h)


@dataclass
class EvidenciaVerification:
    """Agregado + detalhe por-path da verificação (telemetria F4)."""

    verified: int = 0
    failed: int = 0
    failures_by_layer: dict[str, int] = field(default_factory=lambda: dict.fromkeys(_LAYERS, 0))
    entries: list[dict] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)  # "tipo:índice:camada"
    # KR2/KR4 (ADR-290 F2) — denominador p/ taxa de mismatch + faixa inventada
    # em campo escalar (drift de prompt 1.3.0 → 1.4.0).
    money_tokens_total: int = 0
    range_in_scalar_count: int = 0

    def summary(self, *, needs_review_triggered: bool, items_dropped: int = 0) -> dict:
        return {
            "evidencia_verified": self.verified,
            "evidencia_failed": self.failed,
            "failures_by_layer": dict(self.failures_by_layer),
            "money_tokens_total": self.money_tokens_total,
            "range_in_scalar_count": self.range_in_scalar_count,
            # ADR-295: itens removidos pelo enforcement per-item no strict (auditável).
            "items_dropped": items_dropped,
            "prompt_version": PROMPT_VERSION,
            "needs_review_triggered": needs_review_triggered,
        }


def resolve_evidencia_mode(manifest_mode: str) -> str:
    """Modo efetivo: env override > manifest > 'warn' (default fail-open)."""
    env_mode = os.environ.get(_EVIDENCIA_MODE_ENV, "").strip().lower()
    mode = env_mode or (manifest_mode or "warn").strip().lower()
    return mode if mode in _VALID_MODES else "warn"


def verify_evidencia(
    *, output: ParecerPlanejadorOutput, drill: PlannerDrillDown
) -> EvidenciaVerification:
    """Camadas 1-3 sobre riscos + sugestões; ``drill`` é instância dedicada."""
    result = EvidenciaVerification()
    for item_type, index, prose_fields, path in _iter_items(output):
        tokens = _extract_money_tokens(prose_fields)
        result.money_tokens_total += len(tokens)
        if path is None or not _is_legit_range_path(path):
            result.range_in_scalar_count += _count_ranges(prose_fields)
        if not tokens and path is None:
            continue
        failed_layer = "missing_path" if path is None else _check_item(drill, tokens, path)
        _record(result, item_type=item_type, index=index, path=path, layer=failed_layer)
    return result


def _iter_items(
    output: ParecerPlanejadorOutput,
) -> Iterator[tuple[str, int, list[Optional[str]], Optional[str]]]:
    """(item_type, índice, campos de prosa, evidencia_path) por item verificável."""
    for i, risco in enumerate(output.riscos):
        yield "risco", i, [risco.descricao, risco.evidencia], risco.evidencia_path
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        for i, sug in enumerate(getattr(output, horizon)):
            yield horizon, i, [sug.acao], sug.evidencia_path


def _check_item(drill: PlannerDrillDown, tokens: list[MoneyToken], path: str) -> Optional[str]:
    """None = verificado; senão o nome da camada que falhou."""
    tool_result = drill.get_e5_jsonpath(path)
    if not tool_result.found:
        return _REASON_TO_LAYER.get(tool_result.reason or "", "resolve_null")
    if _is_legit_range_path(path):
        # Campo-fonte é faixa/banda legítima — value_mismatch suprimido (R3).
        return None
    if not tokens:
        return None
    leaves = _numeric_leaves(tool_result.value)
    if any(_token_matches(t, leaf) for t in tokens for leaf in leaves):
        return None
    return "value_mismatch"


def _record(
    result: EvidenciaVerification,
    *,
    item_type: str,
    index: int,
    path: Optional[str],
    layer: Optional[str],
) -> None:
    outcome = layer or "verified"
    result.entries.append(
        {"item_type": item_type, "item_index": index, "path": path, "outcome": outcome}
    )
    if layer is None:
        result.verified += 1
        return
    result.failed += 1
    result.failures_by_layer[layer] += 1
    result.violations.append(f"{item_type}:{index}:{layer}")
    # NUNCA logar o valor — só camada + path (PII/byte-identidade).
    logger.warning(
        "parecer_evidencia_violation",
        extra={"layer": layer, "path": path, "item": f"{item_type}[{index}]"},
    )


# ----------------------------------------------------------------------
# Extração de tokens monetários da prosa
# ----------------------------------------------------------------------


def _extract_money_tokens(prose_fields: list[Optional[str]]) -> list[MoneyToken]:
    tokens: list[MoneyToken] = []
    for text in prose_fields:
        if not text:
            continue
        tokens.extend(_token_from_match(m) for m in _MONEY_RE.finditer(text))
    return tokens


def _count_ranges(prose_fields: list[Optional[str]]) -> int:
    """Faixas R$ X–Y na prosa de item cujo campo-fonte não é faixa legítima."""
    return sum(len(_RANGE_RE.findall(text)) for text in prose_fields if text)


def _token_from_match(m: re.Match) -> MoneyToken:
    integer, decimals, mult = m.group(1), m.group(2), m.group(3)
    base = Decimal(integer.replace(".", ""))
    if decimals:
        base += Decimal(decimals) / (Decimal(10) ** len(decimals))
    if not mult:
        return MoneyToken(cents=_to_cents(base), half_step_cents=0)
    factor = Decimal(1_000) if mult == "mil" else Decimal(1_000_000)
    half_step = factor / (Decimal(10) ** len(decimals or "")) / 2
    return MoneyToken(cents=_to_cents(base * factor), half_step_cents=_to_cents(half_step))


def _to_cents(value: Decimal) -> int:
    return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _token_matches(token: MoneyToken, leaf_cents: int) -> bool:
    """Exato em cents; abreviado = meia-casa-significativa: [c-h, c+h)."""
    if token.half_step_cents == 0:
        return token.cents == leaf_cents
    lower = token.cents - token.half_step_cents
    upper = token.cents + token.half_step_cents
    return lower <= leaf_cents < upper


# ----------------------------------------------------------------------
# Folhas numéricas do valor resolvido (camada 3)
# ----------------------------------------------------------------------


def _numeric_leaves(value: Any) -> list[int]:
    """Cents int de cada folha numérica — ``Decimal(str(v))``, nunca float (ADR-090)."""
    leaves: list[int] = []
    _collect_numeric_leaves(value, leaves)
    return leaves


def _collect_numeric_leaves(value: Any, leaves: list[int]) -> None:
    if len(leaves) >= _MAX_NUMERIC_LEAVES or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        leaves.append(_to_cents(Decimal(str(value))))
    elif isinstance(value, str):
        _append_str_leaf(value, leaves)
    for child in _children(value):
        _collect_numeric_leaves(child, leaves)


def _children(value: Any) -> tuple:
    if isinstance(value, dict):
        return tuple(value.values())
    if isinstance(value, list):
        return tuple(value)
    return ()


def _append_str_leaf(value: str, leaves: list[int]) -> None:
    try:
        leaves.append(_to_cents(Decimal(value)))
    except InvalidOperation:
        return


__all__ = [
    "EVIDENCIA_VERIFICATION_VERSION",
    "EvidenciaVerification",
    "MoneyToken",
    "resolve_evidencia_mode",
    "verify_evidencia",
]
