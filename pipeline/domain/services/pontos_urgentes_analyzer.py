"""PontosUrgentesAnalyzer — ações urgentes (Sessão A5c · Fase 8).

Extrai ``analyze_pontos_urgentes`` (e5_analyze.py:1990) em domain service
puro. Gera lista ordenada de :class:`PontoUrgenteItem` a partir de
ratios + reserva + patrimônio:

- Reserva < mínimo_meses → "Reforçar reserva de emergência".
- Endividamento > máximo_pct → "Reduzir endividamento".
- Sem seguro (não há como inferir hoje — sempre adiciona).
- Rentabilidade "N/D" → "Consolidar dados de rentabilidade".

Função pura. Config tipada (R9/ISP).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return 0.0


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class PontosUrgentesConfig:
    reserva_minima_meses: float = 6.0
    endividamento_maximo_pct: float = 20.0

    @classmethod
    def from_scoring(cls, scoring: dict | None = None) -> "PontosUrgentesConfig":
        cfg = (scoring or {}).get("thresholds_alertas") or {}
        return cls(
            reserva_minima_meses=_safe_float(cfg.get("reserva_minima_meses", 6)),
            endividamento_maximo_pct=_safe_float(cfg.get("endividamento_maximo_pct", 20)),
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class PontoUrgenteItem:
    prioridade: str
    acao: str
    impacto: str
    prazo: str

    def to_dict(self) -> dict:
        return {
            "prioridade": self.prioridade,
            "acao": self.acao,
            "impacto": self.impacto,
            "prazo": self.prazo,
        }


# =============================================================================
# Service
# =============================================================================


class PontosUrgentesAnalyzer:
    """Gera lista de ações urgentes com base em métricas."""

    def __init__(self, config: PontosUrgentesConfig | None = None) -> None:
        self._config = config or PontosUrgentesConfig()

    def analyze(
        self,
        ratios: dict[str, Any],
        reserva: dict[str, Any],
        patrimonio: dict[str, Any],
    ) -> list[PontoUrgenteItem]:
        cfg = self._config
        out: list[PontoUrgenteItem] = []

        cobertura = _safe_float(reserva.get("cobertura_meses", 0)) if reserva else 0.0
        if cobertura < cfg.reserva_minima_meses:
            out.append(
                PontoUrgenteItem(
                    prioridade="Alta",
                    acao="Reforçar reserva de emergência",
                    impacto=(
                        f"Cobertura atual de {cobertura:.0f} meses — "
                        f"abaixo do mínimo de {cfg.reserva_minima_meses:.0f}"
                    ),
                    prazo="Imediato",
                )
            )

        endiv = _safe_float(ratios.get("taxa_endividamento_pct", 0)) if ratios else 0.0
        if endiv > cfg.endividamento_maximo_pct:
            out.append(
                PontoUrgenteItem(
                    prioridade="Alta",
                    acao="Reduzir endividamento",
                    impacto=(
                        f"Taxa de endividamento em {endiv:.1f}% — "
                        f"meta < {cfg.endividamento_maximo_pct:.0f}%"
                    ),
                    prazo="Próximo trimestre",
                )
            )

        # Seguro — sempre adicionado (no legado há comentário "nenhuma apólice
        # identificada"; há backlog para inferir via E2-llm no futuro).
        out.append(
            PontoUrgenteItem(
                prioridade="Alta",
                acao="Contratar seguro de vida e invalidez",
                impacto=(
                    "Proteção patrimonial da família — "
                    "nenhuma apólice identificada"
                ),
                prazo="Imediato",
            )
        )

        # Rentabilidade não medida.
        if ratios and ratios.get("rentabilidade_pct") == "N/D":
            out.append(
                PontoUrgenteItem(
                    prioridade="Média",
                    acao="Consolidar dados de rentabilidade dos investimentos",
                    impacto=(
                        "Sem dados de performance, impossível otimizar alocação"
                    ),
                    prazo="Próximo trimestre",
                )
            )

        return out
