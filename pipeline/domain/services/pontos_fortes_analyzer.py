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

from pipeline.domain.services.narrativas.format_helpers import fmt_percent


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
                    # A prosa NÃO nomeia o limiar (A40.l90 · [[ADR-419]]). O catálogo
                    # declara `taxa_poupanca_recorrente` **órfã por decisão**:
                    # `poupanca_referencia_pct` (25) e `pontos_fortes_taxa_poupanca_min_pct`
                    # (30) descrevem o mesmo conceito sem precedência declarada, e o
                    # resolver se recusa a arbitrar — escolher seria inventar regra de
                    # domínio. Esta linha vai para o exec context como afirmação da
                    # própria E5, então dizer "acima da referência de 30%" entregava ao
                    # modelo um limiar que o produtor canônico se recusa a publicar. O
                    # gatilho segue em 30; o que sai é a AFIRMAÇÃO do número.
                    descricao=f"Poupança recorrente de {fmt_percent(taxa_poup)} da renda.",
                    icone="savings",
                )
            )
        elif taxa_poup > 15:
            out.append(
                PontoForteItem(
                    titulo="Disciplina de Poupança",
                    descricao=(
                        f"Taxa de poupança de {fmt_percent(taxa_poup)} demonstra hábito "
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
                            f"Taxa de endividamento de apenas {fmt_percent(endiv)} do "
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
                            f"Taxa de endividamento de {fmt_percent(endiv)} — "
                            f"abaixo do teto de {cfg.endividamento_max_pct:.0f}%."
                        ),
                        icone="shield",
                    )
                )

        # 4. Reserva — cobertura relativa ao alvo do perfil de renda
        #    (CLT 6 · mista 12 · PJ-dominante 18; FORMULAS.md §Reserva-alvo, A28.l1).
        cobertura = _safe_float((reserva or {}).get("cobertura_meses", 0))
        meses_alvo = _safe_float((reserva or {}).get("meses_alvo", 0)) or 12.0
        avaliacao = str((reserva or {}).get("avaliacao_liquidity", "")).strip().lower()
        reserva_emitida = cobertura >= 6
        # C5-C1: reserva muito acima do alvo (motor marca "Excessiva", ou ≥2× o alvo) não
        # é "no alvo" — reconhece a robustez mas sinaliza o excedente realocável em vez de
        # celebrar over-provisioning (custo de oportunidade; UX-06/FIN-03).
        # O segundo braço avalia no EXTREMO CONSERVADOR: com fatia sem dono, a
        # cobertura medida infla, e "≥2× o alvo" dispararia sobre número que a
        # atribuição não sustenta ([[ADR-412]] §D7).
        piso = _safe_float((reserva or {}).get("piso_cobertura_meses", cobertura))
        prescricao_suprimida = bool((reserva or {}).get("motivo_supressao"))
        excessiva = avaliacao == "excessiva" or (meses_alvo > 0 and piso >= meses_alvo * 2)
        if excessiva:
            out.append(
                PontoForteItem(
                    titulo="Reserva de Emergência Robusta",
                    descricao=_descricao_reserva_robusta(
                        cobertura, meses_alvo, prescricao_suprimida
                    ),
                    icone="emergency",
                )
            )
        elif cobertura >= meses_alvo:
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

        # 6. Autonomia financeira (ADR-335) — runway do patrimônio financeiro
        # (sem imóvel ilíquido). Mesma família de cobertura em meses da reserva:
        # emitir os dois é redundante (dedup semântico A28.l10); reserva vence.
        autonomia = 0.0
        if not reserva_emitida:
            autonomia = _safe_float(
                (ratios or {}).get(
                    "autonomia_financeira_meses",
                    (ratios or {}).get("cobertura_despesas_meses", 0),
                )
            )
        if autonomia >= 24:
            out.append(
                PontoForteItem(
                    titulo="Autonomia Financeira Ampla",
                    descricao=_descricao_autonomia(autonomia, prescricao_suprimida, ampla=True),
                    icone="patrimony",
                )
            )
        elif autonomia >= 12:
            out.append(
                PontoForteItem(
                    titulo="Autonomia Financeira Sólida",
                    descricao=_descricao_autonomia(autonomia, prescricao_suprimida, ampla=False),
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


_PENDENCIA = "Quanto movimentar depende de identificar o titular das posições sem dono."


# A prosa determinística morre no PRODUTOR ([[ADR-412]] §Emenda E3): regra
# pós-LLM não alcança texto que já saiu pronto daqui. Some a MAGNITUDE e a
# prescrição; o título e `meses_alvo` sobrevivem — eles não dependem do
# numerador contaminado.
def _descricao_reserva_robusta(cobertura: float, meses_alvo: float, suprimida: bool) -> str:
    if suprimida:
        return f"Acima do alvo de {meses_alvo:.0f} meses do perfil. {_PENDENCIA}"
    return (
        f"Cobertura de {cobertura:.0f} meses, acima do alvo de {meses_alvo:.0f} "
        "meses do perfil — o excedente pode ser realocado para a classe mais defasada."
    )


def _descricao_autonomia(autonomia: float, suprimida: bool, *, ampla: bool) -> str:
    if suprimida:
        cauda = "margem de segurança ampla." if ampla else "margem de segurança sólida."
        return f"Patrimônio financeiro cobre as despesas correntes com {cauda} {_PENDENCIA}"
    if ampla:
        return f"Patrimônio financeiro cobre {autonomia:.0f} meses de despesas — margem ampla."
    return f"Patrimônio financeiro cobre {autonomia:.0f} meses de despesas correntes."
