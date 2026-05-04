"""Configuração do gerador de Suggestion (ADR-153 / ADR-161)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestionGeneratorConfig:
    """Thresholds canônicos das regras de Suggestion. Refinar com financial-planner."""

    # v1 ─────────────────────────────────────────────────────────────────
    reserva_target_meses: int = 6
    trs_target_pct: float = 4.0
    trs_drift_tolerance_pct: float = 0.15
    alocacao_drift_pp: float = 10.0
    aporte_min_pct_meta: float = 0.7  # rate (% of meta, not money — ADR-090 ok)
    dolar_drift_pp: float = 15.0

    # v2 (ADR-161) ──────────────────────────────────────────────────────
    endividamento_max_pct_patrimonio: float = 30.0  # percentage (not money — ADR-090 ok)
    taxa_poupanca_drop_pp_per_quarter: float = 5.0
    taxa_poupanca_consecutive_quarters: int = 2
    seguros_renda_pj_threshold_brl: float = (
        50_000.0  # threshold (BRL constant, ratio-of-position context — ADR-090 ok)
    )
    concentracao_max_pct: float = 40.0
    lifestyle_creep_inflation_multiplier: float = 1.5
    lifestyle_creep_months: int = 6
    renda_passiva_target_ratio: float = 0.30
    renda_passiva_min_progresso_if_pct: float = 50.0
