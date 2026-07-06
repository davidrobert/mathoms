"""PontosFortesAnalyzer — pontos fortes da situação financeira (Sessão A5c).

Extrai ``analyze_pontos_fortes`` (e5_analyze.py:1694) em domain service
puro. Identifica 5-8 pontos fortes a partir de score/ratios/patrimônio/
fluxo/reserva/goals.

Checks (cada um pode gerar 0 ou 1 ponto):
1. Taxa de poupança (forte >=min; disciplinada 15-min; abaixo disso sem ponto).
2. Endividamento (mínimo <5%; controlado <max).
3. Reserva de emergência (excelente >= alvo do perfil de renda; adequada >=6).
4. Patrimônio diversificado (>=4 categorias com valor).
5. Colchão patrimonial (robusto >=24 meses; sólido >=12) — suprimido quando a
   reserva já gerou ponto (mesma família de cobertura em meses; A28.l10).
6. Progresso IF (>=20%).
7. Patrimônio bruto >= R$1M.

Curadoria (A28.l10): o ponto "Score Financeiro Positivo" foi removido — era
circular (referencia apenas o próprio score, já exibido no gauge S1).

Fallback: "Análise em Andamento" quando nenhum dispara.

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
class PontosFortesConfig:
    """Thresholds para pontos fortes.

    Source no legado: ``scoring.json::thresholds_alertas``.
    """

    poupanca_forte_min_pct: float = 30.0
    endividamento_max_pct: float = 20.0
    patrimonio_bruto_relevante: float = 1_000_000.0
    progresso_if_min_pct: float = 20.0

    @classmethod
    def from_scoring(cls, scoring: dict | None = None) -> "PontosFortesConfig":
        cfg = (scoring or {}).get("thresholds_alertas") or {}
        return cls(
            poupanca_forte_min_pct=_safe_float(cfg.get("pontos_fortes_taxa_poupanca_min_pct", 30)),
            endividamento_max_pct=_safe_float(cfg.get("endividamento_maximo_pct", 20)),
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class PontoForteItem:
    titulo: str
    descricao: str
    icone: str

    def to_dict(self) -> dict:
        return {"titulo": self.titulo, "descricao": self.descricao, "icone": self.icone}


# =============================================================================
# Service
# =============================================================================


class PontosFortesAnalyzer:
    """Gera lista de pontos fortes a partir de múltiplas métricas."""

    def __init__(self, config: PontosFortesConfig | None = None) -> None:
        self._config = config or PontosFortesConfig()

    def analyze(
        self,
        *,
        score: dict[str, Any],
        ratios: dict[str, Any],
        patrimonio: dict[str, Any],
        fluxo: dict[str, Any],
        reserva: dict[str, Any],
        goals: dict[str, Any],
    ) -> list[PontoForteItem]:
        cfg = self._config
        out: list[PontoForteItem] = []
        # `score` fica na assinatura por compat de call-site, mas não gera ponto:
        # "Score Financeiro Positivo" era circular (só referencia o próprio score,
        # já exibido no gauge S1) — suprimido em A28.l10.
        _ = score

        # 2. Poupança
        taxa_poup = _safe_float((ratios or {}).get("taxa_poupanca_recorrente_pct", 0))
        if taxa_poup > cfg.poupanca_forte_min_pct:
            out.append(
                PontoForteItem(
                    titulo="Taxa de Poupança Elevada",
                    descricao=(
                        f"Poupança recorrente de {taxa_poup:.1f}% da renda — "
                        f"acima da referência de {cfg.poupanca_forte_min_pct:.0f}%."
                    ),
                    icone="savings",
                )
            )
        elif taxa_poup > 15:
            out.append(
                PontoForteItem(
                    titulo="Disciplina de Poupança",
                    descricao=(
                        f"Taxa de poupança de {taxa_poup:.1f}% demonstra hábito "
                        "consistente de guardar dinheiro."
                    ),
                    icone="savings",
                )
            )

        # 3. Endividamento
        endiv = _safe_float((ratios or {}).get("taxa_endividamento_pct", 0))
        if endiv < cfg.endividamento_max_pct:
            if endiv < 5:
                out.append(
                    PontoForteItem(
                        titulo="Endividamento Mínimo",
                        descricao=(
                            f"Taxa de endividamento de apenas {endiv:.1f}% do "
                            "patrimônio bruto — excelente controle de dívidas."
                        ),
                        icone="shield",
                    )
                )
            else:
                out.append(
                    PontoForteItem(
                        titulo="Endividamento Controlado",
                        descricao=(
                            f"Taxa de endividamento de {endiv:.1f}% — "
                            f"abaixo do teto de {cfg.endividamento_max_pct:.0f}%."
                        ),
                        icone="shield",
                    )
                )

        # 4. Reserva — cobertura relativa ao alvo do perfil de renda
        #    (CLT 6 · mista 12 · PJ-dominante 18; FORMULAS.md §Reserva-alvo, A28.l1).
        cobertura = _safe_float((reserva or {}).get("cobertura_meses", 0))
        meses_alvo = _safe_float((reserva or {}).get("meses_alvo", 0)) or 12.0
        reserva_emitida = cobertura >= 6
        if cobertura >= meses_alvo:
            out.append(
                PontoForteItem(
                    titulo="Reserva de Emergência Excelente",
                    descricao=(
                        f"Cobertura de {cobertura:.0f} meses de custo essencial — "
                        f"no alvo de {meses_alvo:.0f} meses do perfil de renda."
                    ),
                    icone="emergency",
                )
            )
        elif cobertura >= 6:
            out.append(
                PontoForteItem(
                    titulo="Reserva de Emergência Adequada",
                    descricao=(
                        f"Cobertura de {cobertura:.0f} meses protege contra imprevistos "
                        f"(alvo do perfil: {meses_alvo:.0f} meses)."
                    ),
                    icone="emergency",
                )
            )

        # 5. Diversificação
        categorias = (patrimonio or {}).get("categorias", []) or []
        n_cat = sum(1 for c in categorias if _safe_float((c or {}).get("valor", 0)) > 0)
        if n_cat >= 4:
            out.append(
                PontoForteItem(
                    titulo="Patrimônio Diversificado",
                    descricao=(
                        f"Patrimônio distribuído em {n_cat} categorias — "
                        "reduz risco de concentração."
                    ),
                    icone="diversification",
                )
            )

        # 6. Colchão patrimonial — mesma família de cobertura em meses da reserva:
        # emitir os dois é redundante (dedup semântico A28.l10); reserva vence.
        cobertura_desp = 0.0
        if not reserva_emitida:
            cobertura_desp = _safe_float((ratios or {}).get("cobertura_despesas_meses", 0))
        if cobertura_desp >= 24:
            out.append(
                PontoForteItem(
                    titulo="Colchão Patrimonial Robusto",
                    descricao=(
                        f"Patrimônio investível cobre {cobertura_desp:.0f} meses "
                        "de despesas — margem de segurança ampla."
                    ),
                    icone="patrimony",
                )
            )
        elif cobertura_desp >= 12:
            out.append(
                PontoForteItem(
                    titulo="Patrimônio Investível Sólido",
                    descricao=(
                        f"Patrimônio investível cobre {cobertura_desp:.0f} meses "
                        "de despesas correntes."
                    ),
                    icone="patrimony",
                )
            )

        # 7. Progresso IF — FP-002 alias defensivo. Adapter passa
        # `goals={"if_pct": IFProjection.if_pct}` (paridade com nome
        # canônico do IFProjector); legado lia `progresso_pct` que nunca
        # era populado, deixando o ponto forte dormente.
        progresso = _safe_float(
            (goals or {}).get("if_pct") or (goals or {}).get("progresso_pct") or 0
        )
        if progresso >= cfg.progresso_if_min_pct:
            out.append(
                PontoForteItem(
                    titulo="Caminho para Independência Financeira",
                    descricao=f"Já atingiu {progresso:.0f}% da meta de independência financeira.",
                    icone="target",
                )
            )

        # 8. Patrimônio relevante
        bruto = _safe_float((patrimonio or {}).get("bruto", 0))
        if bruto >= cfg.patrimonio_bruto_relevante:
            out.append(
                PontoForteItem(
                    titulo="Patrimônio Acima de R$ 1M",
                    descricao=(
                        "Patrimônio bruto consolidado acima de R$ 1 milhão "
                        "demonstra trajetória de acumulação consistente."
                    ),
                    icone="patrimony",
                )
            )

        # Fallback
        if not out:
            out.append(
                PontoForteItem(
                    titulo="Análise em Andamento",
                    descricao="Pontos fortes serão identificados após consolidação de dados.",
                    icone="info",
                )
            )

        return out
