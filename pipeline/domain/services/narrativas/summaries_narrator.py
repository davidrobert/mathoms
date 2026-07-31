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
    APORTE_SEM_DISTRIBUICAO,
    carteira_diversificacao_frase,
    clause,
    ensure_period,
    fmt_aporte_distribuicao,
    fmt_currency,
    fmt_num,
    fmt_percent,
    fmt_usd,
    pluralize,
)


def _fmt_usd_por_banco(por_banco: Mapping[str, Any] | None) -> str:
    """Enumera saldos USD por banco em ordem decrescente de valor (PD-12)."""
    entries = [
        (banco, valor)
        for banco, valor in (por_banco or {}).items()
        if isinstance(valor, (int, float)) and valor > 0
    ]
    if not entries:
        return "nenhum saldo em moeda estrangeira identificado no período"
    entries.sort(key=lambda kv: (-kv[1], kv[0]))
    return ", ".join(f"{fmt_usd(valor)} em {banco}" for banco, valor in entries)


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

        # PD-02: cláusulas condicionais (sem " como contador", "pendente para
        # ."). PD-06: empty-state de viagens (sem "0 viagens/ano entre R$ 0,00
        # e R$ 0,00").
        _viagens = M.get("viagens_anuais_estimadas", 0)
        _custo_min = M.get("custo_viagem_minimo", 0)
        _custo_max = M.get("custo_viagem_maximo", 0)
        _viagens_clause = (
            f"Orçamento anual de viagens estimado em {fmt_num(_viagens, 0)} viagens/ano "
            f"com custo unitário entre {fmt_currency(_custo_min)} e {fmt_currency(_custo_max)}. "
            if _viagens and (_custo_min or _custo_max)
            else "Padrão de viagens não identificado automaticamente neste período. "
        )
        _contador_clause = _s8_contador_clause(M)
        _holding_clause = clause(
            "Avaliação de holding patrimonial pendente para ", M.get("holding_prazo", "")
        )

        _n_dec = len(decisoes)
        _dec_label = pluralize(
            _n_dec, "decisão estratégica prioritária", "decisões estratégicas prioritárias"
        )
        # A37.l2 (PD-01): mesma guard de distribuição do charts.top5_decisoes.
        _parcelas = fmt_aporte_distribuicao(M.get("aporte_distribuicao"))
        _divisao = f" ({_parcelas})" if _parcelas else f" {APORTE_SEM_DISTRIBUICAO}"
        s10 = (
            (
                f"{_n_dec} {_dec_label}: iniciar aporte mensal de "
                f"{fmt_currency(M['meta_aporte_mensal'])}{_divisao}, "
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
                f"Imóveis representam {fmt_percent(M['pct_imoveis_bruto'])} do patrimônio bruto, com residência própria de {fmt_currency(M['residencia'])} e imóveis de investimento somando "
                f"{fmt_currency(M['imoveis_investimento'])}. Endividamento de {fmt_percent(M['taxa_endividamento'])} sobre o bruto."
            ),
            "s2": (
                f"Score financeiro de {fmt_num(M['score'])}/10 ({M['score_label']}). Pontos fortes: taxa de poupança recorrente de {fmt_percent(M['taxa_poupanca'])}, "
                f"cobertura de {fmt_num(M['cobertura_meses'])} meses de despesas e endividamento controlado. Receita total no período de {fmt_currency(M['receita_total'])} "
                f"com {fmt_percent(M['pct_receita_pj'])} proveniente de PJ, {fmt_percent(M['pct_receita_aluguel'])} de aluguel, "
                f"{fmt_percent(M['pct_receita_clt'])} de CLT e {fmt_percent(M['pct_receita_outras'])} de outras fontes."
            ),
            "s3": _summary_s3(M, ctx),
            # A37.l8 (FIN-03): aluguel recorrente atual + âncora IRPF + sinal de
            # vacância; sem yield % (único yield da S4 é o RealEstateYieldCard).
            "s4": _summary_s4(M),
            # ADR-168 cleanup (Sprint A10.1): s5 reescrito sem EUA. Antes
            # citava custo fase F1/F2, sobra mensal e viagens-EUA — todas
            # chaves dead-data do Modo USA removido em A8.4 PR4. Refoca
            # em viagens genéricas (chart vivo) + sobra de fluxo de caixa.
            "s5": (
                f"{_viagens_clause}"
                f"Receita recorrente de {fmt_currency(M['receita_recorrente_mensal'])}/mês cobre as despesas mensais médias "
                f"de {fmt_currency(M['despesa_mensal_media'])}, gerando sobra para aportes e reserva de viagens."
            ),
            # A37.l14 (PD-12): enumeração dinâmica de contas USD (antes Wise/BofA
            # hardcoded — 3ª conta entrava no total mas sumia da lista).
            # A40.l4: "Meta pré-EUA" era resíduo do Modo USA (ADR-168) — o
            # cleanup da A10.1 tirou do s5 e esqueceu no vizinho.
            "s6": (
                f"Exposição cambial: {_fmt_usd_por_banco(M.get('usd_saldos_por_banco'))}. "
                f"Total {fmt_usd(M['poupanca_cambial_actual_usd'])}. "
                f"Meta de reserva cambial de {fmt_usd(M['poupanca_cambial_meta_usd'])} com gap de {fmt_usd(M['poupanca_cambial_gap_usd'])} — "
                f"ritmo de {fmt_currency(M['aporte_cambial_mensal'])}/mês alcança a meta em {M['meses_para_cambial']} meses."
            ),
            "s7": (
                f"Meta de independência financeira de {fmt_currency(M['if_meta'])} em {M['if_ano']}. "
                f"Gap atual de {fmt_currency(M['if_gap'])} com prazo realista de {fmt_num(M['if_prazo_anos'])} anos "
                f"à taxa de aporte {fmt_currency(M['meta_aporte_mensal'])}/mês e retorno real {fmt_num(M['if_retorno_real_pct'], 0)}% a.a. "
                f"Renda passiva estimada ({fmt_num(M['taxa_retirada_segura_pct'], 0)}% retirada segura): {fmt_currency(M['renda_passiva_4pct'])}/mês."
            ),
            "s8": _summary_s8(M, _contador_clause, _holding_clause),
            "s9": _summary_s9(M, riscos_nomes),
            "s10": s10,
        }


# Chaves de ``summaries`` sem seção de destino no layout (A40.l4 · ADR-355).
# CV9 exige que toda chave emitida ou tenha destino declarado ou esteja aqui
# COM razão — sem isso, chave nova nasce órfã e ninguém percebe. É fato do
# produtor (não do layout), por isso vive aqui.
ORPHAN_SUMMARY_KEYS: dict[str, str] = {
    "s2": (
        "parágrafo de SCORE financeiro; a S2 do layout é Fluxo de Caixa. "
        "Destino semântico seria a S1 (que já hospeda o score_gauge) ou uma "
        "seção de score própria — decisão de produto, não de lowercase."
    ),
    "s5": (
        "viagens + sobra mensal; a S5 saiu do layout com o Modo USA (ADR-168). "
        "Conteúdo pertence aos cards de orçamento/consumo da S2."
    ),
    "s6": (
        "exposição cambial; a S6 saiu do layout com o Modo USA (ADR-168). "
        "O card `exposicao_cambial` vive na S1."
    ),
}


# Sem cônjuge, ``ctx.conjuge_nome`` é ``""``: a segunda frase saía sem sujeito
# e com espaço órfão ("... .  possui R$ 0,00 ...").
def _summary_s3(M: Mapping[str, Any], ctx: NarrativasContext) -> str:
    """s3 — carteira: titular sempre; cônjuge só quando existe na família."""
    base = (
        f"{carteira_diversificacao_frase(M['diversificacao'])}"
        f"{ctx.titular_nome} mantém {fmt_currency(M[ctx.key_inv_titular])} "
        f"distribuídos entre {M[ctx.key_inst_titular]}."
    )
    if not ctx.conjuge_nome:
        return base
    return (
        f"{base} {ctx.conjuge_nome} possui {fmt_currency(M[ctx.key_inv_conjuge])} "
        f"concentrados em {M[ctx.key_inst_conjuge]}."
    )


# ADR-236 §D5 já adota este registro no card `impostos_pj`: sem perfil
# tributário não se estima carga fiscal. A40.l4 (co-design financial-planner
# 2026-07-31) estende ao s8 e vai além — nenhum número fiscal do s8 é
# estimado:
#
# 1. A alíquota efetiva vinha de `FISCAL["das_simples"]["aliquota_efetiva_pct"]`
#    (default 6%). A própria fonte legada se desmente ("estimativa para Anexo V
#    típico … usar tabela completa com RBT12"): 6% só vale na 1ª faixa
#    (RBT12 ≤ R$ 180k). Na faixa do ICP a efetiva é 11-14% — subestimava ~2×,
#    no sentido que infla sobra de caixa e capacidade de aporte.
# 2. A base era `receita_pj_anual` = pró-labore + lucros distribuídos (ADR-330),
#    dinheiro que entrou na conta PF. DAS incide sobre faturamento bruto (RBT12).
#    ADR-236 §Emenda CTO-05 já proibiu essa derivação.
# 3. O card irmão `impostos_pj`, na MESMA seção S8, publica receita bruta +
#    tributos + carga + fator-R pela cascata canônica. Um segundo estimador só
#    pode concordar (redundante) ou discordar (defeito publicado).
#
# Logo: o s8 declara regime DECLARADO e DAS RECOLHIDO (categoria E4
# `das_simples`, fato de extrato); carga e alíquota são da cascata, e o s8
# não as reafirma.
_S8_REGIME_PENDENTE = (
    "Perfil tributário PJ pendente — informe regime, anexo e CNAE para "
    "estimar a carga fiscal da pessoa jurídica."
)


# `regime_obs` NUNCA é vazio: vem de `trib_cfg["regime_label"]` e
# `_regime_to_label(None, …)` devolve "Perfil tributário incompleto"
# (pipeline_adapter.py). Ramificar por string de label deixava
# `_S8_REGIME_PENDENTE` inalcançável e publicava o rótulo pelado, sem CTA. O
# sinal de ausência é `tributario.regime is None`.
def _s8_regime_head(M: Mapping[str, Any]) -> str:
    if M.get("regime_declarado") is None:
        return _S8_REGIME_PENDENTE
    return ensure_period((M.get("regime_obs") or "").strip()) or _S8_REGIME_PENDENTE


def _s8_das_recolhido_clause(M: Mapping[str, Any]) -> str:
    """DAS observado nos extratos — ``''`` sem balde recolhido no período."""
    recolhido = M.get("das_recolhido_periodo") or 0
    if recolhido <= 0:
        return ""
    meses = M.get("n_meses_periodo") or 0
    janela = f" ({meses} {pluralize(meses, 'mês', 'meses')} de extrato)" if meses else ""
    return f"DAS recolhido no período: {fmt_currency(recolhido)}{janela}. "


# `contador_mensal` não existe em `bundle["tributario"]` (só `contador_nome`,
# `holding_prazo_meses`, `regime*`, `cascata`) — o `get(..., 0)` publicava
# honorário fabricado "R$ 0,00/mês". E `contador_nome` é nome de TERCEIRO
# (pessoa física, com frequência): papel, não nome (ADR-319).
def _s8_contador_clause(M: Mapping[str, Any]) -> str:
    """``''`` sem contador cadastrado; valor só quando há honorário informado."""
    if not M.get("contador_nome"):
        return ""
    mensal = M.get("contador_mensal") or 0
    if mensal <= 0:
        return "Contador cadastrado. "
    canal = f" {M['contador_canal']}" if M.get("contador_canal") else ""
    return f"Contador cadastrado ({fmt_currency(mensal)}/mês{canal}). "


def _summary_s8(M: Mapping[str, Any], contador_clause: str, holding_clause: str) -> str:
    """s8 — regime declarado + DAS recolhido + contador + holding. Zero estimativa."""
    tail = f"{_s8_das_recolhido_clause(M)}{contador_clause}{holding_clause}".strip()
    head = _s8_regime_head(M)
    return f"{head} {tail}" if tail else head


# A37.l8 (FIN-03): 1 zero no fim da série pode ser corte de extrato/recebimento
# no mês seguinte — sinal de vacância exige ≥2 meses sem entrada (co-design
# financial-planner 2026-07-22).
_VACANCIA_MIN_MESES = 2


# A40.l4 (ADR-319): a residência era citada por logradouro (``endereco.rua``)
# — endereço é PII dura e este parágrafo passou a ser entregue na S4.
def _summary_s4(M: Mapping[str, Any]) -> str:
    """s4 — imóveis: aluguel recorrente atual (janela estável) + âncora IRPF, sem yield %."""
    return _s4_portfolio_head(M) + _s4_aluguel_clause(M) + _s4_ancora_irpf(M)


# `n_imoveis` vem do E5 (`investimentos`) e os valores vêm de `patrimonio` —
# fontes distintas que divergem: "0 imóveis no portfólio: residência (R$ 800k)"
# é contradição na mesma frase. Sem contagem confiável, descreve-se o valor sem
# afirmar quantidade (A40.l4, medido no render).
def _s4_portfolio_head(M: Mapping[str, Any]) -> str:
    n = M["n_imoveis"] or 0
    residencia = M.get("residencia") or 0
    investimento = M.get("imoveis_investimento") or 0
    valores = (
        f"residência ({fmt_currency(residencia)}), imóveis de investimento "
        f"somando {fmt_currency(investimento)}. "
    )
    if n > 0:
        return f"{n} {pluralize(n, 'imóvel', 'imóveis')} no portfólio: {valores}"
    if residencia <= 0 and investimento <= 0:
        return "Nenhum imóvel identificado no portfólio. "
    return f"Portfólio imobiliário sem contagem consolidada: {valores}"


def _s4_aluguel_clause(M: Mapping[str, Any]) -> str:
    recorrente = M.get("aluguel_mensal_recorrente") or 0
    if recorrente <= 0:
        total = M.get("receita_aluguel") or 0
        if total > 0:
            # Payload sem série mensal: cita o total do período, sem anualizar.
            return f"Renda de aluguel de {fmt_currency(total)} acumulada no período analisado."
        return "Sem renda de aluguel identificada nos extratos do período."
    janela = M.get("aluguel_janela_meses") or 0
    janela_txt = f"mediana dos últimos {janela} {pluralize(janela, 'mês', 'meses')} com recebimento"
    sem_entrada = M.get("aluguel_meses_sem_entrada") or 0
    if sem_entrada >= _VACANCIA_MIN_MESES:
        return (
            f"Último aluguel recorrente observado: {fmt_currency(recorrente)}/mês ({janela_txt}); "
            f"sem entrada de aluguel nos últimos {sem_entrada} meses — possível vacância ou venda."
        )
    return f"Aluguel recorrente atual de {fmt_currency(recorrente)}/mês ({janela_txt})."


def _s4_ancora_irpf(M: Mapping[str, Any]) -> str:
    valor = M.get("aluguel_anual_irpf") or 0
    if valor <= 0:
        return ""
    ano = M.get("aluguel_irpf_ano_ref")
    rotulo = f"IRPF {ano}" if ano else "IRPF"
    return f" Âncora {rotulo}: {fmt_currency(valor)}/ano recebidos de aluguéis."


# ADR-192 T01 D4: empty state coerente — workspace sem Risk cadastrado não pode
# render "0 riscos prioritários: . Cobertura recomendada: R$ 0-0M em seguro term."
# A37.l14 (PD-07): linguagem de produto — sem rota interna "/plano" nem "workspace".
# A40.l4: sem CTA. Este texto passa a imprimir ACIMA do <EmptyState> da S9, que
# já traz o call-to-action; duplicar o CTA com wording diferente confunde.
_S9_EMPTY = (
    "Nenhum risco prioritário cadastrado neste relatório — sem exposições "
    "mapeadas (vida, invalidez, sucessório, compliance internacional) não há "
    "análise de cobertura."
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


_S9_GAP_VIDA = "Seguros de vida e invalidez inexistentes — classificados como urgentes. "


# ``protecao_gap_vida`` vem de ``protecao_patrimonial.gap_qualitativo``
# (categoria ``vida``, ADR-240). ``None`` = sem apólices analisadas: não
# sabemos, então não afirmamos.
def _s9_gap_vida_line(M: Mapping[str, Any]) -> str:
    """Afirmação de ausência de cobertura só com sinal de gap (A40.l4)."""
    return _S9_GAP_VIDA if M.get("protecao_gap_vida") is True else ""


def _summary_s9(M: Mapping[str, Any], riscos_nomes: list[str]) -> str:
    if not riscos_nomes:
        return _S9_EMPTY
    nomes_top3 = ", ".join(riscos_nomes[:3])
    n_label = pluralize(len(riscos_nomes), "risco prioritário", "riscos prioritários")
    return (
        f"{len(riscos_nomes)} {n_label}: {nomes_top3}. "
        f"{_s9_gap_vida_line(M)}"
        f"{_s9_cobertura_line(M)}"
        "Planejamento sucessório em estágio inicial."
    )
