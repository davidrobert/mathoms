"""ChartsNarrator — seção ``charts`` (A6d.3.2).

Extraído de ``scripts/e5n_narrativas.build_narrativas`` (linhas 887-1128
do legado). Produz narrativas de ``context`` + ``conclusion`` para 20
charts do relatório — paridade 100% com legado.

Função pura sobre ``metrics`` + ``family`` + ``NarrativasContext``.

A6g.2 — T2.a: ``narrate()`` 284 → 23 linhas via extração de 6 métodos
privados por grupo de charts. Strings preservadas byte-a-byte; ordem
de inserção no dict final mantida (insertion-order do Python 3.7+).
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import (
    fmt_currency,
    fmt_num,
    fmt_percent,
    fmt_usd,
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
            **self._narrate_fase_eua(M),
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
                "conclusion": (
                    f"A classificação '{M['score_label']}' reflete melhora na taxa de poupança "
                    "recorrente e redução da razão endividamento/patrimônio."
                ),
            },
            "patrimonio_doughnut": {
                "context": (
                    f"Distribuição do patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])} entre {M['diversificacao']} categorias de ativos, "
                    "mostrando concentração em imóveis e peso relativo dos investimentos financeiros."
                ),
                "conclusion": (
                    f"Imóveis respondem por {fmt_percent(M['pct_imoveis_bruto'])} do patrimônio"
                    + (
                        f" — acima do ideal de {fmt_percent(M['threshold_imovel_pct'])}. "
                        if _imovel_acima
                        else ". "
                    )
                    + f"Aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} em ativos financeiros devem melhorar essa proporção."
                ),
            },
            "alocacao_atual": {
                "context": (
                    f"Atual distribuição dos ativos financeiros ({fmt_currency(M[ctx.key_inv_titular] + M[ctx.key_inv_conjuge])}) "
                    "entre classes de investimento: renda fixa, ações, fundos multimercado e estruturados."
                ),
                "conclusion": (
                    f"{ctx.titular_nome} diversificado em {M[ctx.key_inst_titular]}; {ctx.conjuge_nome} concentra em {M[ctx.key_inst_conjuge]}. "
                    f"Recomendação: gradualmente adicionar alocação de ações ({M['aloc_instrumentos_rv']}) para atingir {M['equity_alvo_min']}-{M['equity_alvo_max']}% de equity."
                ),
            },
            "alocacao_alvo": {
                "context": (
                    f"Alocação estratégica recomendada para os ativos financeiros, considerando horizonte de {M['anos_para_if_calculo']} anos até IF e tolerância ao risco médio."
                ),
                "conclusion": (
                    f"Alvo: {M['aloc_rf_pct']}% Renda Fixa ({M['aloc_instrumentos_rf']}), {M['aloc_acoes_pct']}% Ações ({M['aloc_instrumentos_rv']}), "
                    f"{M['aloc_imoveis_pct']}% Imóveis/REITs, {M['aloc_liquidez_pct']}% Liquidez/USD. "
                    f"Aportes de {fmt_currency(M['meta_aporte_mensal'])}/mês priorizarão renda fixa, com rebalanceamento {M['aloc_rebalanceamento']}."
                ),
            },
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
    def _narrate_projecao_if(
        self,
        M: dict[str, Any],
        ctx: NarrativasContext,
    ) -> dict[str, Any]:
        _yield_potencial_min = M.get("yield_imoveis_potencial_pct_min") or 0
        _yield_potencial_max = M.get("yield_imoveis_potencial_pct_max") or 0
        if _yield_potencial_min or _yield_potencial_max:
            _yield_potencial_clause = (
                f" com potencial de {fmt_num(_yield_potencial_min)}-{fmt_num(_yield_potencial_max)}% "
                "após otimização de contratos"
            )
        else:
            _yield_potencial_clause = ""
        return {
            "projecao_3cenarios": {
                "context": (
                    f"Projeção do patrimônio investível até atingir a meta de {fmt_currency(M['if_meta'])}, "
                    f"considerando aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} e retorno real anual de {fmt_num(M['if_retorno_real_pct'], 0)}%."
                ),
                "conclusion": (
                    f"Meta será atingida em {M['if_ano']}, quando {ctx.titular_nome} terá {M[ctx.key_idade_titular_if]} anos. "
                    f"Renda passiva estimada será {fmt_currency(M['renda_passiva_4pct'])}/mês ({fmt_percent(M['pct_renda_passiva_meta'])} da meta de {fmt_currency(M['if_renda_passiva_meta'])}/mês)."
                ),
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
                    f"Renda passiva atual de {fmt_currency(M['renda_passiva_4pct'])}/mês ({fmt_percent(M['pct_renda_passiva_meta'])} da meta). "
                    f"Faltam {fmt_currency(M['if_renda_passiva_meta'] - M['renda_passiva_4pct'])}/mês — patrimônio de {fmt_currency(M['if_meta'])} (meta {M['if_ano']}) "
                    f"geraria {fmt_currency(M['if_renda_passiva_meta'])}/mês com TRS de {fmt_num(M['if_trs_pct'], 0)}%."
                ),
            },
            "yield_imoveis": {
                "context": (
                    f"Análise de yield bruto dos imóveis de investimento (valor total {fmt_currency(M['imoveis_investimento'])}) "
                    "versus aluguel recebido mensalizado."
                ),
                "conclusion": (
                    f"Yield atual de {fmt_num(M['yield_imoveis_pct'])}%{_yield_potencial_clause}. "
                    "Imóveis funcionam como hedge inflacionário e fonte de renda complementar."
                ),
            },
            "top15_ativos": {
                "context": (
                    f"Ranking dos 15 maiores ativos financeiros individuais da família, totalizando {fmt_currency(M['patrimonio_investivel'])} em investimentos."
                ),
                "conclusion": _conclusion_top15_ativos(M),
            },
            "impostos_pj": {
                "context": (
                    f"Carga tributária da PJ de {ctx.titular_nome}: receita anualizada de {fmt_currency(M['receita_pj_anual'])}, "
                    f"enquadrada no {M['regime_obs']} (alíquota efetiva {fmt_percent(M['das_aliquota_pct'])})."
                ),
                "conclusion": (
                    f"DAS estimado em {fmt_currency(M['das_mensal_estimado'])}/mês ({fmt_currency(M['das_anual_estimado'])}/ano). "
                    f"Lucro presumido (32%) define base tributável de {fmt_currency(M['receita_pj_anual'] * 0.32)} para cálculo do PGBL "
                    f"(dedução de até 12%). Contador {M['contador_nome']} em funcionamento. "
                    f"Avaliação de holding patrimonial pendente para {M['holding_prazo']}."
                ),
            },
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
            return {
                "context": "Cenário de estresse não aplicável a este workspace.",
                "conclusion": "",
            }
        aporte = _cm_aportes[0] if _cm_aportes else 0
        prazo = _cm_prazos[0]
        ano_if = _cm_anos[0] if _cm_anos else ""
        fator = M.get("cm_fator_reduzido", 0)
        prazo_base = M.get("if_prazo_anos", 0)
        delta_anos = prazo - prazo_base if prazo_base else 0
        return {
            "context": (
                f"Cenário de estresse 'Sem renda do cônjuge'. "
                f"Premissas: meta IF de {fmt_currency(M['if_meta'])}, "
                f"patrimônio investível de {fmt_currency(M['patrimonio_investivel'])}, "
                f"retorno real de {fmt_num(M['if_retorno_real_pct'], 0)}% a.a. "
                f"Atualmente {ctx.conjuge_nome} contribui com {fmt_currency(M['cm_salario_clt_brl'])}/mês."
            ),
            "conclusion": (
                f"<strong>Sem renda do cônjuge:</strong> aporte cai para "
                f"{fmt_currency(aporte)}/mês ({fmt_num(fator * 100, 0)}% do aporte-base). "
                f"IF em {fmt_num(prazo, 0)} anos ({ano_if})"
                + (
                    f" — custo de oportunidade de +{fmt_num(delta_anos, 0)} anos em relação ao cenário base."
                    if delta_anos > 0
                    else "."
                )
            ),
        }

    # ── Grupo 4: Fase F1/F2 nos EUA (charts 16-18) ─────────────────────
    def _narrate_fase_eua(self, M: dict[str, Any]) -> dict[str, Any]:
        return {
            "custos_f1f2": {
                "context": (
                    f"Estimativa de custos mensais na fase {M['f1f2_visto']} nos EUA: tuition + living + viagens BR = {fmt_currency(M['custo_fase_f1f2'])}/mês."
                ),
                "conclusion": (
                    f"Sobra projetada: {fmt_currency(M['sobra_mensal_f1f2'])}/mês ({fmt_currency(M['receita_recorrente_mensal'])} - {fmt_currency(M['custo_fase_f1f2'])})."
                ),
            },
            "viagens": {
                "context": (
                    "Padrão de despesas com viagens identificado nos extratos, estimando frequência e custo médio."
                ),
                "conclusion": (
                    f"Viagens para EUA estimadas em {fmt_currency(M['custo_viagem_minimo'])}-{fmt_currency(M['custo_viagem_maximo'])} por viagem. "
                    f"Frequência média de {fmt_num(M['viagens_anuais_estimadas'], 0)} viagens/ano para acompanhamento do processo {M['f1f2_visto']}."
                ),
            },
            "cenarios_cambiais": {
                "context": (
                    f"Exposição cambial atual ({fmt_usd(M['poupanca_cambial_actual_usd'])}) e meta pré-EUA ({fmt_usd(M['poupanca_cambial_meta_usd'])}), "
                    f"considerando câmbio de R$ {fmt_num(M['cambio_usd_brl'], 2)}/USD."
                ),
                "conclusion": (
                    f"Gap de {fmt_usd(M['poupanca_cambial_gap_usd'])} com aporte atual de {fmt_currency(M['aporte_cambial_mensal'])}/mês em Wise, "
                    f"atingindo meta em {M['meses_para_cambial']} meses. "
                    "Risco mitigado por diversificação USD/EUR, renda PJ em BRL e flexibilidade de data de mudança."
                ),
            },
        }

    # ── Grupo 5: Riscos + decisões (charts 19-20) ──────────────────────
    def _narrate_riscos_decisoes(
        self,
        M: dict[str, Any],
        riscos: list[dict[str, Any]],
        _riscos_top3: list[dict[str, Any]],
        decisoes: list[str],
    ) -> dict[str, Any]:
        return {
            "bubble_riscos": {
                "context": (
                    f"Identificação de {len(riscos)} riscos críticos de compliance e proteção ao plano IF, com probabilidade e impacto."
                ),
                "conclusion": (
                    "Riscos prioritários: "
                    + ", ".join(
                        f"({i+1}) {r.get('nome', '')} ({r.get('prob', '')} prob., {r.get('impacto', '')} impacto)"
                        for i, r in enumerate(_riscos_top3)
                    )
                    + f". Ação: CPA expatriado + seguro term R$ {M['seguro_vida_minimo'] // 1_000_000}-{M['seguro_vida_maximo'] // 1_000_000}M."
                ),
            },
            "top5_decisoes": {
                "context": (
                    f"{len(decisoes)} decisões estratégicas de curto prazo (6-12 meses) para otimizar a trajetória até IF."
                ),
                "conclusion": (
                    f"Prioridade 1: Aporte mensal {fmt_currency(M['meta_aporte_mensal'])} com divisão "
                    f"({fmt_currency(M['aporte_cofrinhos'])} Cofrinhos, {fmt_currency(M['aporte_ipca_plus'])} IPCA+, "
                    f"{fmt_currency(M['aporte_ivvb11'])} IVVB11, {fmt_currency(M['aporte_wise_usd'])} Wise USD). "
                    + ". ".join(f"Prioridade {i+2}: {d}" for i, d in enumerate(decisoes[1:5]))
                    + "."
                ),
            },
        }
