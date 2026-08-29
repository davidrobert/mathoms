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

from pipeline.domain.services.narrativas.format_helpers import fmt_percent, pluralize
from pipeline.domain.services.patrimonio_sign_guard import motivo_supressao_do_patrimonio
from pipeline.domain.services.risk_trigger_registry import RiskTrigger, build_risk_triggers

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
        """Deriva os limiares do registro de gatilho ([[ADR-419]] §D1), não de default inline."""
        gatilhos = build_risk_triggers(scoring)
        return cls(
            reserva_minima_meses=gatilhos["reserva_cobertura_meses"].limiar,
            endividamento_maximo_pct=gatilhos["taxa_endividamento"].limiar,
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
    # Chave do KPI no vocabulário do catálogo ([[ADR-419]] §D2). Declarada por quem LÊ o
    # limiar — regra que pare de derivar do registro perde o campo e o gate de cobertura
    # fica vermelho sozinho. `None` para regra que não compara limiar: `seguro_vida` é
    # predicado booleano de gap ([[ADR-240]] KPI F) e `rentabilidade_nao_medida` é
    # sentinela `== "N/D"`; pôr número nelas seria a regressão que [[ADR-387]] e
    # [[ADR-191]] §D5 proíbem.
    kpi_key: Optional[str] = None
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
            "kpi_key": self.kpi_key,
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


# ADR-395 §D7 — o mesmo estado que a S_PROTECAO publica. Ler outro predicado
# aqui só mudaria a contradição do RV6-20 de casa.
_GAP_VIDA_RETENCAO: dict[str, str] = {
    "sem family_members": "composição da família",
    "dependentes_irpf_sem_cadastro": (
        "idade e dependência econômica dos dependentes declarados no IRPF"
    ),
}


def _sem_gap_vida(rationale: str, detalhe: str) -> PontoUrgenteItem | None:
    """Gap fechado: ou o conselho não se aplica, ou falta o cadastro que o decide."""
    faltante = _GAP_VIDA_RETENCAO.get(rationale)
    if faltante is not None:
        return _item_seguro_vida(
            detalhe,
            "pendente_de_dado",
            origem="cadastro_familia",
            dado_faltante=faltante,
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

    def __init__(
        self,
        config: PontosUrgentesConfig | None = None,
        gatilhos: Mapping[str, RiskTrigger] | None = None,
    ) -> None:
        self._config = config or PontosUrgentesConfig()
        self._gatilhos = gatilhos if gatilhos is not None else build_risk_triggers({})

    def analyze(
        self,
        ratios: dict[str, Any],
        reserva: dict[str, Any],
        patrimonio: dict[str, Any],
        protecao: dict[str, Any] | None = None,
    ) -> list[PontoUrgenteItem]:
        cfg = self._config
        out: list[PontoUrgenteItem] = []

        # Polaridade INVERTIDA em relação à reserva excessiva: este item autoriza
        # AUMENTAR liquidez, então o conservador é o extremo INFERIOR — ele deve
        # continuar disparando, e pode passar a disparar onde não disparava.
        # Morre a MAGNITUDE, nunca o item ([[ADR-412]] §D7).
        # Fallback é a MEDIDA, nunca zero: payload legado sem piso publicado
        # dispararia "reserva insuficiente" em todo run.
        cobertura = (
            _safe_float(reserva.get("piso_cobertura_meses", reserva.get("cobertura_meses", 0)))
            if reserva
            else 0.0
        )
        suprimida = bool((reserva or {}).get("motivo_supressao"))
        if cobertura < cfg.reserva_minima_meses:
            out.append(
                PontoUrgenteItem(
                    prioridade="Alta",
                    acao="Reforçar reserva de emergência",
                    impacto=_impacto_reserva(cobertura, cfg.reserva_minima_meses, suprimida),
                    prazo="Imediato",
                    code="reserva_insuficiente",
                    kpi_key="reserva_cobertura_meses",
                )
            )

        endiv = _safe_float(ratios.get("taxa_endividamento_pct", 0)) if ratios else 0.0
        if endiv > cfg.endividamento_maximo_pct:
            out.append(
                PontoUrgenteItem(
                    prioridade="Alta",
                    acao="Reduzir endividamento",
                    impacto=(
                        f"Taxa de endividamento em {fmt_percent(endiv)} — "
                        f"meta < {fmt_percent(cfg.endividamento_maximo_pct)}"
                    ),
                    prazo="Próximo trimestre",
                    code="endividamento_alto",
                    kpi_key="taxa_endividamento",
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

        item = _concentracao_item(ratios, patrimonio, self._gatilhos)
        if item is not None:
            out.append(item)

        return out


# Nunca `prazo="Imediato"`: a [[ADR-340]] §Emenda fecha a meta como **direcional via
# aporte, sem exigir liquidação de imóvel**. Prometer prazo imediato para ação que não
# existe é alarme falso — o defeito que esta lane existe para evitar, cometido na regra
# nova. E a copy nomeia iliquidez e risco de ativo único, nunca rendimento do imóvel:
# esse é o eixo do `spread_critico`, e replicá-lo aqui daria duas prescrições para o
# mesmo fato.
def _concentracao_item(
    ratios: dict[str, Any] | None,
    patrimonio: dict[str, Any] | None,
    gatilhos: Mapping[str, RiskTrigger],
) -> PontoUrgenteItem | None:
    gatilho = gatilhos.get("concentracao_imobiliaria")
    conc = _num_ou_none((ratios or {}).get("concentracao_imobiliaria"))
    if gatilho is None or conc is None or not gatilho.rompido(conc):
        return None
    # Herda a supressão por atribuição: com a base da carteira produtiva suprimida, o
    # percentual existe mas não é verificável — vai para o balde de retenção em vez de
    # afirmar concentração sobre denominador amputado ([[ADR-412]]).
    suprimido = motivo_supressao_do_patrimonio(patrimonio) is not None
    return _item_concentracao(conc, gatilho, suprimido)


def _item_concentracao(conc: float, gatilho: RiskTrigger, suprimido: bool) -> PontoUrgenteItem:
    severo = gatilho.severo(conc)
    return PontoUrgenteItem(
        prioridade="Alta" if severo else "Média",
        acao="Reduzir concentração imobiliária",
        impacto=_impacto_concentracao(conc, gatilho.limiar, severo, suprimido),
        prazo="Próximo trimestre",
        code="concentracao_imobiliaria_alta",
        kpi_key="concentracao_imobiliaria",
        elegibilidade="nao_verificavel" if suprimido else "computavel",
    )


def _impacto_concentracao(conc: float, limiar: float, severo: bool, suprimido: bool) -> str:
    if suprimido:
        return (
            "Parte da carteira produtiva está sem dono identificado — o percentual "
            "exato depende de atribuir essas posições."
        )
    grau = "acima do limite" if severo else "acima da referência"
    return (
        f"{fmt_percent(conc)} da carteira produtiva em imóveis, {grau} de "
        f"{fmt_percent(limiar)} — patrimônio pouco líquido e exposto a ativo único. "
        "O ajuste é direcional, via destino dos próximos aportes."
    )


def _num_ou_none(valor: Any) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return float(valor)


# A prosa morre no PRODUTOR, e a MESMA frase existe em `scripts/analyze_finances.py`
# — consertar só aqui instalaria divergência stage↔legado ([[ADR-412]] §Emenda E2).
def _impacto_reserva(cobertura: float, minimo: float, suprimida: bool) -> str:
    if suprimida:
        return (
            f"Abaixo do mínimo de {minimo:.0f} meses. O quanto falta depende de "
            "identificar o titular das posições sem dono."
        )
    return f"Cobertura atual de {cobertura:.0f} meses — abaixo do mínimo de {minimo:.0f}"
