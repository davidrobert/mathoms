"""SummariesNarrator — seção ``summaries.s1..s10`` (A6d.3.2).

Extraído de ``scripts/generate_narratives.build_narrativas`` (linhas 823-886
do legado). Produz 10 parágrafos curtos (um por dimensão: patrimônio,
score, carteira, imóveis, EUA, cambial, IF, PJ, riscos, decisões).

Função pura sobre ``metrics`` + ``family`` + ``NarrativasContext``.
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import (
    clause,
    fmt_currency,
    fmt_num,
    fmt_percent,
    fmt_usd,
    pluralize,
)


class SummariesNarrator:
    """Narra ``summaries.s1..s10`` — parágrafos por dimensão financeira."""

    def __init__(self, ctx: NarrativasContext):
        self._ctx = ctx

    def narrate(
        self,
        metrics: dict[str, Any],
        family: dict[str, Any],
        riscos_nomes: list[str],
        decisoes: list[str],
    ) -> dict[str, str]:
        """Retorna ``{"s1": str, ..., "s10": str}``."""
        ctx = self._ctx
        M = metrics
        _endereco = family.get("endereco", {}) or {}

        # PD-02: cláusulas condicionais (sem "residência na ", " como contador",
        # "pendente para ."). PD-06: empty-state de viagens (sem "0 viagens/ano
        # entre R$ 0,00 e R$ 0,00").
        _rua = _endereco.get("rua", "")
        _residencia_loc = f" na {_rua}" if _rua else ""
        _viagens = M.get("viagens_anuais_estimadas", 0)
        _custo_min = M.get("custo_viagem_minimo", 0)
        _custo_max = M.get("custo_viagem_maximo", 0)
        _viagens_clause = (
            f"Orçamento anual de viagens estimado em {fmt_num(_viagens, 0)} viagens/ano "
            f"com custo unitário entre {fmt_currency(_custo_min)} e {fmt_currency(_custo_max)}. "
            if _viagens and (_custo_min or _custo_max)
            else "Padrão de viagens não identificado automaticamente neste período. "
        )
        _contador_nome = M.get("contador_nome", "")
        _contador_canal = f" {M['contador_canal']}" if M.get("contador_canal") else ""
        _contador_clause = (
            f"{_contador_nome} como contador "
            f"({fmt_currency(M['contador_mensal'])}/mês{_contador_canal}). "
            if _contador_nome
            else ""
        )
        _holding_clause = clause(
            "Avaliação de holding patrimonial pendente para ", M.get("holding_prazo", "")
        )

        _n_dec = len(decisoes)
        _dec_label = pluralize(
            _n_dec, "decisão estratégica prioritária", "decisões estratégicas prioritárias"
        )
        s10 = (
            (
                f"{_n_dec} {_dec_label}: iniciar aporte mensal de {fmt_currency(M['meta_aporte_mensal'])} "
                f"({fmt_currency(M['aporte_cofrinhos'])} Cofrinhos, {fmt_currency(M['aporte_ipca_plus'])} IPCA+, "
                f"{fmt_currency(M['aporte_ivvb11'])} IVVB11, {fmt_currency(M['aporte_wise_usd'])} Wise USD), "
                + ", ".join(decisoes[1:4])
                + "."
            )
            if _n_dec > 3
            else (
                f"{_n_dec} {_dec_label}: iniciar aporte mensal de "
                f"{fmt_currency(M['meta_aporte_mensal'])}."
            )
        )

        return {
            "s1": (
                f"Patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])} com {fmt_percent(M['pct_investivel'])} investível ({fmt_currency(M['patrimonio_investivel'])}). "
                f"Imóveis representam {fmt_percent(M['pct_imoveis_bruto'])} do total, com residência própria de {fmt_currency(M['residencia'])} e imóveis de investimento somando "
                f"{fmt_currency(M['imoveis_investimento'])}. Endividamento de {fmt_percent(M['taxa_endividamento'])} sobre o bruto."
            ),
            "s2": (
                f"Score financeiro de {fmt_num(M['score'])}/10 ({M['score_label']}). Pontos fortes: taxa de poupança recorrente de {fmt_percent(M['taxa_poupanca'])}, "
                f"cobertura de {fmt_num(M['cobertura_meses'])} meses de despesas e endividamento controlado. Receita total no período de {fmt_currency(M['receita_total'])} "
                f"com {fmt_percent(M['pct_receita_pj'])} proveniente de PJ, {fmt_percent(M['pct_receita_aluguel'])} de aluguel, "
                f"{fmt_percent(M['pct_receita_clt'])} de CLT e {fmt_percent(M['pct_receita_outras'])} de outras fontes."
            ),
            "s3": (
                f"Carteira diversificada entre {M['diversificacao']} categorias de ativos. "
                f"{ctx.titular_nome} mantém {fmt_currency(M[ctx.key_inv_titular])} distribuídos entre {M[ctx.key_inst_titular]}. "
                f"{ctx.conjuge_nome} possui {fmt_currency(M[ctx.key_inv_conjuge])} concentrados em {M[ctx.key_inst_conjuge]}."
            ),
            "s4": (
                f"{M['n_imoveis']} {pluralize(M['n_imoveis'], 'imóvel', 'imóveis')} no portfólio: residência{_residencia_loc} ({fmt_currency(M['residencia'])}), "
                f"apartamentos alugados com renda de {fmt_currency(M['receita_aluguel_anual'])}/ano ({fmt_currency(M['receita_aluguel'] / M['n_meses_periodo'] if M['n_meses_periodo'] else 0)}/mês). "
                f"Yield bruto dos imóveis de investimento estimado em {fmt_num(M['yield_imoveis_pct'])}% (receita/valor total)."
            ),
            # ADR-168 cleanup (Sprint A10.1): s5 reescrito sem EUA. Antes
            # citava custo fase F1/F2, sobra mensal e viagens-EUA — todas
            # chaves dead-data do Modo USA removido em A8.4 PR4. Refoca
            # em viagens genéricas (chart vivo) + sobra de fluxo de caixa.
            "s5": (
                f"{_viagens_clause}"
                f"Receita recorrente de {fmt_currency(M['receita_recorrente_mensal'])}/mês cobre as despesas mensais médias "
                f"de {fmt_currency(M['despesa_mensal_media'])}, gerando sobra para aportes e reserva de viagens."
            ),
            "s6": (
                f"Exposição cambial: {fmt_usd(M['wise_usd'])} em Wise, {fmt_usd(M['bofa_usd'])} em Bank of America. "
                f"Total {fmt_usd(M['poupanca_cambial_actual_usd'])}. "
                f"Meta pré-EUA de {fmt_usd(M['poupanca_cambial_meta_usd'])} com gap de {fmt_usd(M['poupanca_cambial_gap_usd'])} — "
                f"ritmo de {fmt_currency(M['aporte_cambial_mensal'])}/mês na Wise alcança a meta em {M['meses_para_cambial']} meses."
            ),
            "s7": (
                f"Meta de independência financeira de {fmt_currency(M['if_meta'])} em {M['if_ano']}. "
                f"Gap atual de {fmt_currency(M['if_gap'])} com prazo realista de {fmt_num(M['if_prazo_anos'])} anos "
                f"à taxa de aporte {fmt_currency(M['meta_aporte_mensal'])}/mês e retorno real {fmt_num(M['if_retorno_real_pct'], 0)}% a.a. "
                f"Renda passiva estimada ({fmt_num(M['taxa_retirada_segura_pct'], 0)}% retirada segura): {fmt_currency(M['renda_passiva_4pct'])}/mês."
            ),
            "s8": (
                f"{M['regime_obs']} (alíquota efetiva {fmt_percent(M['das_aliquota_pct'])}). "
                f"DAS mensal estimado em {fmt_currency(M['das_mensal_estimado'])} ({fmt_currency(M['das_anual_estimado'])}/ano) "
                f"sobre receita PJ anualizada de {fmt_currency(M['receita_pj_anual'])}. "
                f"{_contador_clause}"
                f"{_holding_clause}"
                "Obrigações fiscais EUA (FBAR, Form 8938, PFIC) requerem CPA expatriado antes da mudança."
            ),
            "s9": _summary_s9(M, riscos_nomes),
            "s10": s10,
        }


# ADR-192 T01 D4: empty state coerente — workspace sem Risk cadastrado não pode
# render "0 riscos prioritários: . Cobertura recomendada: R$ 0-0M em seguro term."
_S9_EMPTY = (
    "Nenhum risco prioritário cadastrado para este workspace. "
    "Mapeie suas exposições críticas (seguros de vida, invalidez, sucessório, "
    "compliance internacional) na tela /plano para destravar a análise de cobertura."
)
_S9_COBERTURA_FALLBACK = (
    "Cobertura recomendada: faixa a definir após mapeamento de dependentes e renda líquida. "
)


def _s9_cobertura_line(M: Mapping[str, Any]) -> str:
    minimo = M.get("seguro_vida_minimo") or 0
    maximo = M.get("seguro_vida_maximo") or 0
    if minimo <= 0 and maximo <= 0:
        return _S9_COBERTURA_FALLBACK
    return (
        f"Cobertura recomendada: R$ {minimo // 1_000_000}-{maximo // 1_000_000}M em seguro term. "
    )


def _summary_s9(M: Mapping[str, Any], riscos_nomes: list[str]) -> str:
    if not riscos_nomes:
        return _S9_EMPTY
    nomes_top3 = ", ".join(riscos_nomes[:3])
    n_label = pluralize(len(riscos_nomes), "risco prioritário", "riscos prioritários")
    return (
        f"{len(riscos_nomes)} {n_label}: {nomes_top3}. "
        "Seguros de vida e invalidez inexistentes — classificados como urgentes. "
        f"{_s9_cobertura_line(M)}"
        "Planejamento sucessório em estágio inicial."
    )
