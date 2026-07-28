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


# Tiers de confiança do diagnóstico por cobertura de categorização (ADR-353 D1).
NAO_IDENTIFICADO_PARCIAL_PCT = 10.0
NAO_IDENTIFICADO_INSUFICIENTE_PCT = 30.0


def _despesas_por_categoria(fluxo: dict) -> dict:
    """janela_12m.despesas_por_categoria first, fallback top-level (ADR-353 D2)."""
    j12m = (fluxo or {}).get("janela_12m") if isinstance(fluxo, dict) else None
    if isinstance(j12m, dict) and j12m.get("despesas_por_categoria"):
        return j12m["despesas_por_categoria"]
    return (fluxo or {}).get("despesas_por_categoria") or {}


def _nao_identificado_share_pct(fluxo: dict) -> float:
    """% de despesa nao_identificado sobre Σ despesas_por_categoria; Σ≤0 → 0 (ADR-353 D2)."""
    despesas = _despesas_por_categoria(fluxo)
    total = sum(_safe_float(v) for v in despesas.values())
    if total <= 0:
        return 0.0
    return _safe_float(despesas.get("nao_identificado", 0)) / total * 100


def _confianca_nivel(share_pct: float) -> str:
    if share_pct > NAO_IDENTIFICADO_INSUFICIENTE_PCT:
        return "insuficiente"
    if share_pct > NAO_IDENTIFICADO_PARCIAL_PCT:
        return "parcial"
    return "alta"


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


def _fallback_item() -> DiagnosticoItem:
    return DiagnosticoItem(
        padrao="Análise em andamento",
        evidencia="Dados insuficientes para diagnóstico comportamental",
        mudanca_sugerida="Consolidar mais meses de dados",
    )


def _atencao_item(share_pct: float) -> DiagnosticoItem:
    """Item de atenção do tier parcial — puxa o usuário a categorizar (ADR-353 D1)."""
    return DiagnosticoItem(
        padrao="Ponto cego nos gastos",
        evidencia=(
            f"{share_pct:.0f}% das despesas ainda estão sem categoria — "
            "comportamento não observado nessa fatia."
        ),
        mudanca_sugerida="Categorizar as maiores despesas sem categoria para fechar o diagnóstico.",
    )


def _insuficiente_item(share_pct: float) -> DiagnosticoItem:
    """Substitui os padrões quando a cobertura é insuficiente (>30%, ADR-353 D1)."""
    return DiagnosticoItem(
        padrao="Diagnóstico indisponível — cobertura insuficiente",
        evidencia=(
            f"{share_pct:.0f}% das despesas ainda estão sem categoria; com essa "
            "fatia fora da leitura, apontar padrões seria enganoso."
        ),
        mudanca_sugerida="Categorize as despesas sem categoria para liberar o diagnóstico.",
    )


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

        return self._apply_confianca_gate(out, fluxo)

    def _apply_confianca_gate(
        self, out: list[DiagnosticoItem], fluxo: dict
    ) -> list[DiagnosticoItem]:
        """Degrada a densidade por cobertura de categorização (ADR-353 D1/D2)."""
        share = _nao_identificado_share_pct(fluxo)
        nivel = _confianca_nivel(share)
        if nivel == "insuficiente":
            return [_insuficiente_item(share)]
        if nivel == "parcial":
            out.append(_atencao_item(share))
        if not out:
            out.append(_fallback_item())
        return out

    def confianca(self, fluxo: dict) -> dict[str, str | float]:
        """Campo sibling diagnostico_confianca (ADR-353 D3)."""
        share = _nao_identificado_share_pct(fluxo)
        return {
            "nivel": _confianca_nivel(share),
            "share_nao_identificado_pct": round(share, 1),
        }
