"""DiagnosticoComportamentalAnalyzer — diagnósticos comportamentais
(Sessão A5c · Fase 8).

Extrai ``analyze_diagnostico_comportamental`` (e5_analyze.py:2130) em domain
service puro. Gera lista de ``DiagnosticoItem`` a partir de fluxo + ratios:

- Disciplina de poupança: taxa_poupanca_recorrente > referência → elogia.
- Poupança abaixo do ideal: 0 < taxa < referência → alerta.
- Alta dependência de receita pontual: one_time / total > alerta_pct.
- Fallback: "Análise em andamento" quando nenhum padrão disparou.

Usa janela 12m consistentemente com ``analyze_ratios`` / ``calculate_score``.

Função pura; config tipada (R9/ISP).
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
class DiagnosticoComportamentalConfig:
    """Thresholds para disparar cada diagnóstico.

    Sources no legado:
    - ``poupanca_ref_pct`` ← ``scoring.json::thresholds_alertas.poupanca_referencia_pct``
    - ``receita_one_time_alerta_pct`` ← ``scoring.json::thresholds_alertas.receita_one_time_alerta_pct``
    """

    poupanca_ref_pct: float = 25.0
    receita_one_time_alerta_pct: float = 30.0

    @classmethod
    def from_scoring(cls, scoring: dict | None = None) -> "DiagnosticoComportamentalConfig":
        cfg = (scoring or {}).get("thresholds_alertas") or {}
        return cls(
            poupanca_ref_pct=_safe_float(cfg.get("poupanca_referencia_pct", 25)),
            receita_one_time_alerta_pct=_safe_float(cfg.get("receita_one_time_alerta_pct", 30)),
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class DiagnosticoItem:
    padrao: str
    evidencia: str
    mudanca_sugerida: str

    def to_dict(self) -> dict:
        return {
            "padrao": self.padrao,
            "evidencia": self.evidencia,
            "mudanca_sugerida": self.mudanca_sugerida,
        }


# =============================================================================
# Service
# =============================================================================


class DiagnosticoComportamentalAnalyzer:
    """Gera lista de :class:`DiagnosticoItem` a partir de fluxo + ratios."""

    def __init__(self, config: DiagnosticoComportamentalConfig | None = None) -> None:
        self._config = config or DiagnosticoComportamentalConfig()

    def analyze(
        self,
        fluxo: dict[str, Any],
        ratios: dict[str, Any],
    ) -> list[DiagnosticoItem]:
        cfg = self._config
        out: list[DiagnosticoItem] = []

        # Poupança.
        taxa_poup = _safe_float(ratios.get("taxa_poupanca_recorrente_pct", 0))
        taxa_str = f"{taxa_poup:.1f}".replace(".", ",")
        ref_str = f"{cfg.poupanca_ref_pct:.0f}"
        if taxa_poup > cfg.poupanca_ref_pct:
            out.append(
                DiagnosticoItem(
                    padrao="Disciplina de poupança",
                    evidencia=(
                        f"Taxa de poupança recorrente de {taxa_str}% — "
                        f"acima da referência de {ref_str}%"
                    ),
                    mudanca_sugerida="Manter e automatizar aportes mensais",
                )
            )
        elif taxa_poup > 0:
            out.append(
                DiagnosticoItem(
                    padrao="Poupança abaixo do ideal",
                    evidencia=(f"Taxa de {taxa_str}% — referência mínima: {ref_str}%"),
                    mudanca_sugerida="Revisar despesas variáveis e aumentar aporte",
                )
            )

        # Dependência de receita pontual.
        j12m = fluxo.get("janela_12m") if isinstance(fluxo, dict) else None
        if j12m:
            receita_total = _safe_float(j12m.get("receita_total", 0))
            receita_one_time = _safe_float(j12m.get("receita_one_time", 0))
        else:
            receita_total = _safe_float((fluxo or {}).get("receita_total", 0))
            receita_one_time = _safe_float((fluxo or {}).get("receita_one_time", 0))

        if receita_total > 0:
            one_time_pct = receita_one_time / receita_total * 100
            if one_time_pct > cfg.receita_one_time_alerta_pct:
                out.append(
                    DiagnosticoItem(
                        padrao="Alta dependência de receita pontual",
                        evidencia=(
                            f"{one_time_pct:.0f}% da receita é não-recorrente " "(resgates, vendas)"
                        ),
                        mudanca_sugerida=(
                            "Não contar com receita pontual para orçamento; "
                            "alocar direto para investimentos"
                        ),
                    )
                )

        # Fallback.
        if not out:
            out.append(
                DiagnosticoItem(
                    padrao="Análise em andamento",
                    evidencia="Dados insuficientes para diagnóstico comportamental",
                    mudanca_sugerida="Consolidar mais meses de dados",
                )
            )

        return out
