"""PontosUrgentesAnalyzer — ações urgentes (Sessão A5c · Fase 8).

Extrai ``analyze_pontos_urgentes`` (e5_analyze.py:1990) em domain service
puro. Gera lista ordenada de :class:`PontoUrgenteItem` a partir de
ratios + reserva + patrimônio:

- Reserva < mínimo_meses → "Reforçar reserva de emergência".
- Endividamento > máximo_pct → "Reduzir endividamento".
- Seguro de vida — condicional ao payload ``protecao_patrimonial`` (A28.l6):
  omitido quando há apólice vigente com bem ``pessoa``; copy diferenciada
  quando só há cobertura de bens (auto/residencial); copy legada ("nenhuma
  apólice identificada") apenas quando não há apólice vigente alguma.
- Rentabilidade "N/D" → "Consolidar dados de rentabilidade".

Função pura. Config tipada (R9/ISP).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional

from pipeline.domain.services.narrativas.format_helpers import pluralize

# ADR-365 — dois eixos ORTOGONAIS. `origem_premissa` diz de onde vem o fato;
# `elegibilidade` diz se o produto consegue avaliá-lo. Um eixo só embutiria
# ranking de confiança invertido: fato de cadastro é declaração de 1ª mão do
# dono, enquanto fato derivado do baseline IRPF é defasado 1-2 anos (ADR-305).
# Prova da ortogonalidade: `dependentes_menores_18` é (cadastro_familia,
# computavel) e `conjuge_sem_renda_propria` é (cadastro_familia, degenerada).
OrigemPremissa = Literal["cadastro_familia", "documento_ingerido", "derivado_e5"]

# `degenerada` é TRANSITÓRIO (ADR-365 §D6): marca predicado que não discrimina
# por defeito de produtor, não categoria de domínio. Sai quando
# `renda_propria_brl` tiver produtor real.
Elegibilidade = Literal["computavel", "nao_verificavel", "degenerada", "pendente_de_dado"]


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


# `code` é identidade estável por regra (ADR-365 §D3), pré-condição de qualquer
# ordenação: `build_default_tarefas_status` chaveia por POSIÇÃO, então reordenar
# sem id remapearia o status registrado pelo dono para outra tarefa — mesma
# classe do RV4-02. Também é a chave natural que `dev/golden_diff.py` usa para
# não cair em diff posicional.
@dataclass(frozen=True)
class PontoUrgenteItem:
    prioridade: str
    acao: str
    impacto: str
    prazo: str
    code: str = ""
    origem_premissa: OrigemPremissa = "derivado_e5"
    elegibilidade: Elegibilidade = "computavel"
    # Nomeia o dado ausente para a copy — a copy NUNCA nomeia o valor do enum
    # (ADR-365 §D5). `None` quando não há dado faltante a pedir.
    dado_faltante: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "prioridade": self.prioridade,
            "acao": self.acao,
            "impacto": self.impacto,
            "prazo": self.prazo,
            "code": self.code,
            "origem_premissa": self.origem_premissa,
            "elegibilidade": self.elegibilidade,
            "dado_faltante": self.dado_faltante,
        }


# =============================================================================
# Seguro de vida — condicional a apólices vigentes (A28.l6 · ADR-240)
# =============================================================================


_ACAO_SEGURO_VIDA = "Contratar seguro de vida e invalidez"


# A40.l10 · ADR-365 §D4 + RULE-elegibilidade-da-recomendacao: até 2026-08-06 este
# item decidia por conta própria ("existe apólice vigente com bem `pessoa`?") e
# ignorava o gap de proteção. Resultado medido: "Contratar seguro de vida" era
# emitido para TODO workspace sem apólice de pessoa, inclusive titular solteiro
# sem dependente econômico — conselho errado, não default conservador, no item
# mais vendável do card. Passa a mapear o predicado canônico da ADR-240 (KPI F),
# derrubando de 2 para 1 os produtores dele. Note que o predicado canônico é mais
# ESTREITO: exige cobertura de `vida`, não qualquer bem `pessoa` — apólice de
# acidentes sem vida deixa de suprimir o item (verdadeiro-positivo antes oculto).
_GAP_VIDA_TAXONOMIA: dict[str, tuple[OrigemPremissa, Elegibilidade]] = {
    "dependentes_menores_18": ("cadastro_familia", "computavel"),
    "passivo_acima_30_pct_patrimonio": ("derivado_e5", "computavel"),
    # Tautológico enquanto `protecao_wiring` fixar `renda_propria_brl = 0`
    # (ADR-240 §D3): dispara para todo workspace com cônjuge.
    "conjuge_sem_renda_propria": ("cadastro_familia", "degenerada"),
}


def _gap_vida(protecao: Mapping[str, Any]) -> dict[str, Any] | None:
    for gap in protecao.get("gap_qualitativo") or []:
        if isinstance(gap, dict) and gap.get("categoria") == "vida":
            return gap
    return None


# ADR-240 §Emenda 2026-08-08 — "nenhuma apólice identificada" é afirmação sobre
# o patrimônio do cliente e vai no `impacto` do item mais vendável do plano.
# Dizê-la olhando só o que foi extraído de documento é falso para quem cadastrou
# apólice em `/protecao` sem subir o PDF.
def _detalhe_apolices(protecao: Mapping[str, Any]) -> str:
    """Descreve o universo de apólices conhecido, sem afirmar vazio indevidamente."""
    vigentes = protecao.get("apolices_vigentes") or []
    if vigentes:
        n = len(vigentes)
        return (
            f"{n} {pluralize(n, 'apólice vigente cobre', 'apólices vigentes cobrem')} bens "
            "(auto/residencial), sem cobertura de vida identificada"
        )
    escopo = protecao.get("escopo_cobertura") or {}
    if escopo.get("categorias_somente_no_cadastro"):
        return "sem cobertura de vida entre as apólices cadastradas"
    return "nenhuma apólice identificada"


def _seguro_vida_item(protecao: dict[str, Any] | None) -> PontoUrgenteItem | None:
    """Item de seguro de vida derivado de ``gap_qualitativo`` (ADR-240 KPI F)."""
    if protecao is None:
        # Caller legado sem wiring: o conselho existe, a premissa é inavaliável.
        return _item_seguro_vida("nenhuma apólice identificada", "nao_verificavel")
    gap = _gap_vida(protecao)
    if gap is None:
        return _item_seguro_vida("nenhuma apólice identificada", "nao_verificavel")
    detalhe = _detalhe_apolices(protecao)
    if not gap.get("flag"):
        return _sem_gap_vida(str(gap.get("rationale") or ""), detalhe)
    origem, eleg = _GAP_VIDA_TAXONOMIA.get(
        str(gap.get("rationale") or ""), ("derivado_e5", "nao_verificavel")
    )
    return _item_seguro_vida(detalhe, eleg, origem=origem)


def _sem_gap_vida(rationale: str, detalhe: str) -> PontoUrgenteItem | None:
    """Gap fechado: ou o conselho não se aplica, ou falta o cadastro que o decide."""
    if rationale == "sem family_members":
        return _item_seguro_vida(
            detalhe,
            "pendente_de_dado",
            origem="cadastro_familia",
            dado_faltante="composição da família",
        )
    # "sem gatilho" (nenhuma dependência econômica) e "apolice_vida_ativa" não
    # são retenção: o conselho não existe, logo não há o que declarar (ADR-167).
    return None


def _item_seguro_vida(
    detalhe: str,
    elegibilidade: Elegibilidade,
    *,
    origem: OrigemPremissa = "derivado_e5",
    dado_faltante: Optional[str] = None,
) -> PontoUrgenteItem:
    return PontoUrgenteItem(
        prioridade="Alta",
        acao=_ACAO_SEGURO_VIDA,
        impacto=f"Proteção patrimonial da família — {detalhe}",
        prazo="Imediato",
        code="seguro_vida",
        origem_premissa=origem,
        elegibilidade=elegibilidade,
        dado_faltante=dado_faltante,
    )


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
        protecao: dict[str, Any] | None = None,
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
                    code="reserva_insuficiente",
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
                    code="endividamento_alto",
                )
            )

        seguro = _seguro_vida_item(protecao)
        if seguro is not None:
            out.append(seguro)

        # Rentabilidade não medida.
        if ratios and ratios.get("rentabilidade_pct") == "N/D":
            out.append(
                PontoUrgenteItem(
                    prioridade="Média",
                    acao="Consolidar dados de rentabilidade dos investimentos",
                    impacto=("Sem dados de performance, impossível otimizar alocação"),
                    prazo="Próximo trimestre",
                    # `computavel`, não `pendente_de_dado`: a premissa É verificável
                    # — o item dispara PORQUE `rentabilidade_pct == "N/D"`, e o
                    # conselho é justamente suprir o dado. Marcá-lo pendente o
                    # esconderia do ranking sendo ele o mais acionável.
                    code="rentabilidade_nao_medida",
                )
            )

        return out
