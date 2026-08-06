"""ChartsNarrator — seção ``charts`` (A6d.3.2).

Extraído de ``scripts/generate_narratives.build_narrativas`` (linhas 887-1128
do legado). Produz narrativas de ``context`` + ``conclusion`` para 20
charts do relatório — paridade 100% com legado.

Função pura sobre ``metrics`` + ``family`` + ``NarrativasContext``.

A6g.2 — T2.a: ``narrate()`` 284 → 23 linhas via extração de 6 métodos
privados por grupo de charts. Strings preservadas byte-a-byte; ordem
de inserção no dict final mantida (insertion-order do Python 3.7+).
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.narrativas.alocacao_narrator import (
    narrate_alocacao_atual_vs_alvo,
)
from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import (
    categorias_ativos_sufixo,
    ensure_period,
    fmt_aporte_contexto,
    fmt_currency,
    fmt_num,
    fmt_percent,
    pluralize,
)
from pipeline.domain.services.narrativas.projecao_if_narrator import (
    narrate_projecao_if_conclusion,
)
from pipeline.domain.services.narrativas.tributario_narrator import (
    narrate_cascata,
    narrate_wise_fiscal_flags,
)

_DIVERSIFICACAO_LINE = (
    "Concentração em poucos ativos reforça importância de aportes contínuos para diversificação."
)


def _conclusion_top15_ativos(M: Mapping[str, Any]) -> str:
    # Quando _find_top_asset não localiza o maior ativo (E4 ausente, dados vazios),
    # omitimos a frase "X é o maior ativo" — evita render "(R$ 0,00 de )".
    nome = (M.get("top_asset_nome") or "").strip()
    valor = M.get("top_asset_valor") or 0
    membro = (M.get("top_asset_membro") or "").strip()
    if not nome or valor <= 0 or not membro:
        return _DIVERSIFICACAO_LINE
    return (
        f"{nome} ({fmt_currency(valor)} de {membro.capitalize()}) é o maior ativo individual. "
        + _DIVERSIFICACAO_LINE
    )


class ChartsNarrator:
    """Narra seção ``charts`` — context+conclusion para cada chart do relatório."""

    def __init__(self, ctx: NarrativasContext):
        self._ctx = ctx

    def narrate(
        self,
        metrics: dict[str, Any],
        family: dict[str, Any],
        riscos: list[dict[str, Any]],
        decisoes: list[str],
    ) -> dict[str, Any]:
        ctx = self._ctx
        M = metrics
        fm = family.get("membros", {}) or {}
        _conj = fm.get(ctx.conjuge_key, {}) or {}
        _riscos_top3 = riscos[:3] if isinstance(riscos, list) else []
        _imovel_acima = M["pct_imoveis_bruto"] > M["threshold_imovel_pct"]

        # Dominant revenue sources (ordenado por valor).
        _fontes_receita = [
            ("PJ", M["receita_pj"], M["pct_receita_pj"]),
            ("CLT", M["receita_clt"], M["pct_receita_clt"]),
            ("aluguel", M["receita_aluguel"], M["pct_receita_aluguel"]),
        ]
        _fontes_receita.sort(key=lambda x: x[1], reverse=True)

        _cm_prazos = M.get("cm_prazos", [])
        _cm_aportes = M.get("cm_aportes", [])
        _cm_anos = M.get("cm_anos_if", [])

        return {
            **self._narrate_patrimonio_aloc(M, ctx, _imovel_acima),
            **self._narrate_fluxo_receita(M, _fontes_receita),
            **self._narrate_projecao_if(M, ctx),
            ctx.key_cenarios_conjuge: self._narrate_cenarios_conjuge(
                M,
                ctx,
                _conj,
                _cm_prazos,
                _cm_aportes,
                _cm_anos,
            ),
            **self._narrate_viagens(M),
            **self._narrate_riscos_decisoes(M, riscos, _riscos_top3, decisoes),
        }

    # ── Grupo 1: Score + patrimônio + alocação (charts 1-4) ────────────
    def _narrate_patrimonio_aloc(
        self,
        M: dict[str, Any],
        ctx: NarrativasContext,
        _imovel_acima: bool,
    ) -> dict[str, Any]:
        return {
            "score_gauge": {
                "context": (
                    f"Indicador geral de saúde financeira da família, com score de {fmt_num(M['score'])}/10 "
                    f"({M['score_label']}). Reflete equilíbrio entre pontos fortes e oportunidades de melhoria."
                ),
                # C2.2: o E5.N não tem baseline (comparisons são injetados só na montagem
                # do view-model) → proibido afirmar tendência ("melhora"/"redução") aqui.
                # Conclusão descritiva, não-comparativa.
                "conclusion": (
                    f"A classificação '{M['score_label']}' resume o equilíbrio entre os pilares "
                    "avaliados: poupança, liquidez, endividamento, diversificação e progresso à independência."
                ),
            },
            "patrimonio_doughnut": {
                "context": (
                    f"Distribuição do patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])}"
                    f"{categorias_ativos_sufixo(M['diversificacao'])}, "
                    "mostrando concentração em imóveis e peso relativo dos investimentos financeiros."
                ),
                "conclusion": (
                    # A37.l9: rótulo de base explícito — pct_imoveis_bruto é
                    # (imóveis investimento + residência) ÷ patrimônio BRUTO.
                    f"Imóveis respondem por {fmt_percent(M['pct_imoveis_bruto'])} do patrimônio bruto"
                    + (
                        f" — acima do ideal de {fmt_percent(M['threshold_imovel_pct'])}. "
                        if _imovel_acima
                        else ". "
                    )
                    + f"Aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} em ativos financeiros devem melhorar essa proporção."
                ),
            },
            # A37.l8 (FIN-05): consome a taxonomia v2 via `aloc_derived` (mesma
            # base do card React); rollup v1 + frase de instituições aposentados.
            "alocacao_atual_vs_alvo": narrate_alocacao_atual_vs_alvo(M),
        }

    # ── Grupo 2: Fluxo + receita + despesa (charts 5-8) ────────────────
    def _narrate_fluxo_receita(
        self,
        M: dict[str, Any],
        _fontes_receita: list[tuple[str, float, float]],
    ) -> dict[str, Any]:
        _top_fonte_nome, _top_fonte_valor, _top_fonte_pct = _fontes_receita[0]
        _sec_fonte_nome, _sec_fonte_valor, _sec_fonte_pct = _fontes_receita[1]
        _ter_fonte_nome, _ter_fonte_valor, _ter_fonte_pct = _fontes_receita[2]
        return {
            "fluxo_mensal": {
                "context": (
                    f"Visão consolidada do fluxo de caixa mensal: receita recorrente de {fmt_currency(M['receita_recorrente_mensal'])}/mês "
                    f"versus despesa média de {fmt_currency(M['despesa_mensal_media'])}/mês."
                ),
                "conclusion": (
                    f"Fluxo líquido total de {fmt_currency(M['fluxo_liquido'])} no período ({M['n_meses_periodo']} meses). "
                    f"Taxa de poupança recorrente de {fmt_percent(M['taxa_poupanca'])} "
                    f"sustenta a meta de aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} para o plano IF."
                ),
            },
            "receita_bar": {
                "context": (
                    f"Composição da receita total de {fmt_currency(M['receita_total'])} por fonte: "
                    f"PJ ({fmt_percent(M['pct_receita_pj'])}), CLT ({fmt_percent(M['pct_receita_clt'])}), "
                    f"aluguel ({fmt_percent(M['pct_receita_aluguel'])}), outras ({fmt_percent(M['pct_receita_outras'])})."
                ),
                "conclusion": (
                    f"Receita {_top_fonte_nome} lidera com {fmt_currency(_top_fonte_valor)} ({fmt_percent(_top_fonte_pct)}), "
                    f"seguida por {_sec_fonte_nome} ({fmt_currency(_sec_fonte_valor)}, {fmt_percent(_sec_fonte_pct)}) "
                    f"e {_ter_fonte_nome} ({fmt_currency(_ter_fonte_valor)}, {fmt_percent(_ter_fonte_pct)}). "
                    "Diversificação de fontes reduz risco de dependência única."
                ),
            },
            "receita_despesa_mensal": {
                "context": (
                    f"Série temporal mensal de receitas ({fmt_currency(M['receita_total'])}/período) versus despesas ({fmt_currency(M['despesa_total'])}/período), "
                    f"resultando em fluxo líquido de {fmt_currency(M['fluxo_liquido'])}."
                ),
                "conclusion": (
                    f"Receita recorrente de {fmt_currency(M['receita_recorrente_mensal'])}/mês e despesa média de {fmt_currency(M['despesa_mensal_media'])}/mês. "
                    f"Taxa de poupança recorrente de {fmt_percent(M['taxa_poupanca'])} valida a sustentabilidade do plano IF."
                ),
            },
            "despesas_doughnut": {
                "context": (
                    f"Distribuição das despesas totais ({fmt_currency(M['despesa_total'])}) entre {M['n_desp_categorias']} categorias, "
                    "destacando a composição de gastos e oportunidades de otimização."
                ),
                "conclusion": (
                    f"Categoria 'não identificado' lidera com {fmt_currency(M['despesas_nao_id'])} ({fmt_percent(M['pct_despesas_nao_id'])}), seguida por impostos "
                    f"({fmt_currency(M['despesas_impostos'])}), moradia ({fmt_currency(M['despesas_moradia'])}) e serviços domésticos "
                    f"({fmt_currency(M['despesas_serv_dom'])}). Prioridade: reclassificar 'não identificado' via melhor rastreamento."
                ),
            },
        }

    # ── Grupo 3: Projeção IF + renda passiva + impostos (charts 9-14) ──
    # ADR-216 Onda 6: chart yield_imoveis descontinuado; bloco removido
    # (S4 agora renderiza RealEstateYieldCard via data.real_estate).
    # A37.l8 (FIN-03): métrica yield_imoveis_pct aposentada — o card é o
    # único yield da S4; o s4 textual cita recorrente + âncora IRPF.
    def _narrate_projecao_if(
        self,
        M: dict[str, Any],
        ctx: NarrativasContext,
    ) -> dict[str, Any]:
        return {
            "projecao_3cenarios": {
                "context": (
                    f"Projeção do patrimônio investível até atingir a meta de {fmt_currency(M['if_meta'])}, "
                    f"considerando aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} e retorno real anual de {fmt_num(M['if_retorno_real_pct'], 0)}%."
                ),
                # A37.l8 (FIN-08): linguagem probabilística via if_monte_carlo —
                # nunca "será atingida" determinístico.
                "conclusion": narrate_projecao_if_conclusion(M, ctx),
            },
            "waterfall_if": {
                "context": (
                    f"Decomposição do gap de independência financeira ({fmt_currency(M['if_gap'])}), mostrando componentes de patrimônio atual, "
                    f"aportes acumulados e rentabilidade esperada até {M['if_ano']}."
                ),
                "conclusion": (
                    f"Gap de {fmt_currency(M['if_gap'])} será fechado por aportes disciplinados "
                    f"({fmt_currency(M['meta_aporte_mensal'])}/mês = {fmt_currency(M['aportes_acum_prazo'])} em {fmt_num(M['if_prazo_anos'], 0)} anos) "
                    f"e rentabilidade real de {fmt_num(M['if_retorno_real_pct'], 0)}% a.a. sobre patrimônio acumulado."
                ),
            },
            "renda_passiva": {
                "context": (
                    f"Barra de progresso da renda passiva mensal em direção à meta de {fmt_currency(M['if_renda_passiva_meta'])}/mês. "
                    f"Cada segmento representa uma fonte: aluguéis, dividendos e rendimentos financeiros."
                ),
                "conclusion": (
                    # A28.l2: é ESTIMATIVA pela regra de retirada sobre o investível
                    # — não a renda observada via IRPF (essa vive no bloco TRS do S7).
                    f"Renda passiva estimada pela regra de retirada segura ({fmt_num(M['taxa_retirada_segura_pct'], 0)}% sobre o investível): {fmt_currency(M['renda_passiva_4pct'])}/mês ({fmt_percent(M['pct_renda_passiva_meta'])} da meta). "
                    f"Faltam {fmt_currency(M['if_renda_passiva_meta'] - M['renda_passiva_4pct'])}/mês — patrimônio de {fmt_currency(M['if_meta'])} (meta {M['if_ano']}) "
                    f"geraria {fmt_currency(M['if_renda_passiva_meta'])}/mês com TRS de {fmt_num(M['if_trs_pct'], 0)}%."
                ),
            },
            "top15_ativos": {
                "context": (
                    f"Ranking dos 15 maiores ativos financeiros individuais da família, totalizando {fmt_currency(M['patrimonio_investivel'])} em investimentos."
                ),
                "conclusion": _conclusion_top15_ativos(M),
            },
            "impostos_pj": narrate_cascata(M.get("tributario_section"), ctx),
            "wise_fiscal_flags": narrate_wise_fiscal_flags(M.get("wise_fiscal_flags"), ctx),
        }

    # ── Cenário de estresse "Sem renda do cônjuge" (ADR-167) ──────────────
    def _narrate_cenarios_conjuge(
        self,
        M: dict[str, Any],
        ctx: NarrativasContext,
        _conj: dict[str, Any],
        _cm_prazos: list,
        _cm_aportes: list,
        _cm_anos: list,
    ) -> dict[str, Any]:
        # ADR-167: 1 cenário universal "Sem renda do cônjuge". Sem dependência
        # de USD/cambio. Quando metrics ainda não populadas (workspace solteiro
        # ou pré-PR2), retorna texto mínimo.
        if not _cm_prazos:
            # A37.l14 (PD-07): "workspace" é jargão interno — copy fala "relatório".
            return {
                "context": "Cenário de estresse não aplicável a este relatório.",
                "conclusion": "",
            }
        aporte = _cm_aportes[0] if _cm_aportes else 0
        prazo = _cm_prazos[0]
        ano_if = _cm_anos[0] if _cm_anos else ""
        fator = M.get("cm_fator_reduzido", 0)
        prazo_base = M.get("if_prazo_anos", 0)
        delta_anos = prazo - prazo_base if (prazo_base and prazo is not None) else 0
        # Prazo ausente (era a sentinela 999): declara a ausência em vez de
        # escrever "IF em N/D anos (N/D)".
        desfecho = (
            "Prazo até a IF não projetável com as premissas deste cenário."
            if prazo is None
            else f"IF em {fmt_num(prazo, 0)} anos ({ano_if})"
            + (
                f" — custo de oportunidade de +{fmt_num(delta_anos, 0)} anos "
                "em relação ao cenário base."
                if delta_anos > 0
                else "."
            )
        )
        return {
            "context": (
                f"Cenário de estresse 'Sem renda do cônjuge'. "
                f"Premissas: meta IF de {fmt_currency(M['if_meta'])}, "
                f"patrimônio investível de {fmt_currency(M['patrimonio_investivel'])}, "
                f"retorno real de {fmt_num(M['if_retorno_real_pct'], 0)}% a.a. "
                f"Atualmente {ctx.conjuge_nome} contribui com {fmt_currency(M['cm_salario_clt_brl'])}/mês."
            ),
            "conclusion": (
                f"Sem renda do cônjuge: aporte cai para "
                f"{fmt_currency(aporte)}/mês ({fmt_num(fator * 100, 0)}% do aporte-base). "
                f"{desfecho}"
            ),
        }

    # ── Grupo 4: Viagens (chart 19) ─────────────────────────────────────
    # ADR-168 cleanup (Sprint A10.1): `custos_f1f2` e `cenarios_cambiais`
    # removidos — eram dead-data específica do Modo USA descontinuado em
    # A8.4 PR4. Apenas `viagens` permanece (chart vivo no report_layout).
    def _narrate_viagens(self, M: dict[str, Any]) -> dict[str, Any]:
        return {
            "viagens": {
                "context": (
                    "Padrão de despesas com viagens identificado nos extratos, estimando frequência e custo médio."
                ),
                "conclusion": (
                    f"Frequência média de {fmt_num(M.get('viagens_anuais_estimadas', 0), 0)} viagens/ano "
                    f"com custo unitário entre {fmt_currency(M.get('custo_viagem_minimo', 0))} e "
                    f"{fmt_currency(M.get('custo_viagem_maximo', 0))} — orçamento incorporado ao planejamento de fluxo de caixa."
                ),
            },
        }

    # ── Grupo 5: Riscos + decisões (charts 19-20) ──────────────────────
    def _narrate_riscos_decisoes(
        self,
        M: Mapping[str, Any],
        riscos: list[dict[str, Any]],
        _riscos_top3: list[dict[str, Any]],
        decisoes: list[str],
    ) -> dict[str, Any]:
        return {
            "bubble_riscos": _narrate_bubble_riscos(M, riscos, _riscos_top3),
            "top5_decisoes": _narrate_top5_decisoes(M, decisoes),
        }


# ADR-192 T01: empty state coerente quando workspace não tem Risk cadastrado
# (evita "Riscos prioritários: . Ação: CPA expatriado + seguro term R$ 0-0M.").
# A37.l14 (PD-07): linguagem de produto — sem rota interna "/plano" nem o
# termo "workspace" em copy user-facing.
_BUBBLE_EMPTY_CONTEXT = (
    "Nenhum risco crítico de compliance ou proteção mapeado para este relatório. "
    "Cadastre as exposições na tela Plano de Ação para destravar o mapa de riscos."
)
_BUBBLE_EMPTY_CONCLUSION = (
    "Sem riscos prioritários cadastrados. Próximo passo: registrar exposições "
    "(seguro de vida, invalidez, sucessório, compliance) na tela Plano de Ação."
)
# A40.l10 (RV4-02): fila vazia dizia "Prioridade 1: Aporte mensal R$ 0,00" —
# afirmava uma prioridade que ninguém registrou. Mesma forma do empty state
# do bubble acima: nomeia a ausência e aponta a tela que a resolve.
_DECISOES_EMPTY_CONCLUSION = (
    "Nenhuma decisão priorizada para os próximos 6 a 12 meses. Registre na tela "
    "Plano de Ação as decisões que pretende executar neste ciclo para que entrem "
    "no ranking do próximo relatório."
)
# Templates de ação indexados por (has_us_exposure, has_seguro_range). ADR-192 T01 D4:
# perfil USA só é assumido quando `has_us_exposure` for explicitamente True.
_ACTION_LINES: dict[tuple[bool, bool], str] = {
    (True, True): "Ação: CPA expatriado + seguro term {range}.",
    (
        True,
        False,
    ): "Ação: CPA expatriado + contratação de seguro term (faixa de cobertura a definir).",
    (False, True): "Ação: contratação de seguro term {range}.",
    (False, False): "Ação: revisar mitigação de cada risco prioritário com corretor habilitado.",
}


def _fmt_seguro_vida_range(M: Mapping[str, Any]) -> str | None:
    minimo = M.get("seguro_vida_minimo") or 0
    maximo = M.get("seguro_vida_maximo") or 0
    if minimo <= 0 and maximo <= 0:
        return None
    return f"R$ {minimo // 1_000_000}-{maximo // 1_000_000}M"


def _format_priority_phrase(riscos_top3: list[dict[str, Any]]) -> str:
    parts = (
        f"({i + 1}) {r.get('nome', '')} ({r.get('prob', '')} prob., {r.get('impacto', '')} impacto)"
        for i, r in enumerate(riscos_top3)
    )
    return f"Riscos prioritários: {', '.join(parts)}"


def _pick_action_line(has_us_exposure: bool, seguro_range: str | None) -> str:
    template = _ACTION_LINES[(has_us_exposure, bool(seguro_range))]
    return template.format(range=seguro_range or "")


def _narrate_bubble_riscos(
    M: Mapping[str, Any],
    riscos: list[dict[str, Any]],
    riscos_top3: list[dict[str, Any]],
) -> dict[str, str]:
    if not riscos_top3:
        return {
            "data_state": "empty",
            "context": _BUBBLE_EMPTY_CONTEXT,
            "conclusion": _BUBBLE_EMPTY_CONCLUSION,
        }
    seguro_range = _fmt_seguro_vida_range(M)
    has_us = bool(M.get("has_us_exposure"))
    return {
        "data_state": "ok",
        "context": (
            f"Identificação de {len(riscos)} {pluralize(len(riscos), 'risco crítico', 'riscos críticos')} "
            "de compliance e proteção ao plano IF, com probabilidade e impacto."
        ),
        "conclusion": f"{_format_priority_phrase(riscos_top3)}. {_pick_action_line(has_us, seguro_range)}",
    }


def _fmt_fila_decisoes(decisoes: list[str]) -> str:
    """Enumera a fila **inteira** a partir da posição 1 (top-5 já cortado a montante)."""
    return ". ".join(f"Prioridade {i + 1}: {d.rstrip('.')}" for i, d in enumerate(decisoes[:5]))


def _narrate_top5_decisoes(M: Mapping[str, Any], decisoes: list[str]) -> dict[str, str]:
    context = (
        f"{len(decisoes)} {pluralize(len(decisoes), 'decisão estratégica', 'decisões estratégicas')} "
        "de curto prazo (6-12 meses) para otimizar a trajetória até IF."
    )
    # Fila vazia não recebe o enquadramento de aporte: com nada priorizado, a
    # meta seria a única frase do card e voltaria a ser lida como a prioridade.
    if not decisoes:
        return {"context": context, "conclusion": _DECISOES_EMPTY_CONCLUSION}
    conclusion = fmt_aporte_contexto(M) + _fmt_fila_decisoes(decisoes)
    return {"context": context, "conclusion": ensure_period(conclusion)}
