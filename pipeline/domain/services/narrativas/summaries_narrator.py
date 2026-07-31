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
            "s4": _summary_s4(M, _residencia_loc),
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
        f"Carteira diversificada entre {M['diversificacao']} categorias de ativos. "
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
# tributário não se estima carga fiscal. A40.l4 estende ao texto do s8 —
# `das_aliquota_pct` vinha de default hardcoded 6% (a fonte fiscal saiu de
# `config/` em A7.2b), e "alíquota efetiva 6%" parece calculado.
_S8_REGIME_PENDENTE = (
    "Perfil tributário PJ pendente — informe regime, anexo e CNAE para "
    "estimar a carga fiscal da pessoa jurídica."
)
_S8_REGIME_SEM_LABEL = "Regime PJ não informado"


def _s8_das_clause(M: Mapping[str, Any]) -> str:
    """Cláusula DAS — ``''`` quando não há alíquota de fonte fiscal vigente."""
    aliquota = M.get("das_aliquota_pct")
    if aliquota is None:
        return ""
    return (
        f" (alíquota efetiva {fmt_percent(aliquota)}). "
        f"DAS mensal estimado em {fmt_currency(M['das_mensal_estimado'])} "
        f"({fmt_currency(M['das_anual_estimado'])}/ano) sobre receita PJ anualizada "
        f"de {fmt_currency(M['receita_pj_anual'])}."
    )


def _s8_regime_head(M: Mapping[str, Any]) -> str:
    regime = (M.get("regime_obs") or "").strip()
    das = _s8_das_clause(M)
    if regime:
        return f"{regime}{das}" if das else ensure_period(regime)
    return f"{_S8_REGIME_SEM_LABEL}{das}" if das else _S8_REGIME_PENDENTE


def _summary_s8(M: Mapping[str, Any], contador_clause: str, holding_clause: str) -> str:
    """s8 — regime PJ + DAS (suprimido sem fonte fiscal) + contador + holding."""
    tail = f"{contador_clause}{holding_clause}".strip()
    head = _s8_regime_head(M)
    return f"{head} {tail}" if tail else head


# A37.l8 (FIN-03): 1 zero no fim da série pode ser corte de extrato/recebimento
# no mês seguinte — sinal de vacância exige ≥2 meses sem entrada (co-design
# financial-planner 2026-07-22).
_VACANCIA_MIN_MESES = 2


def _summary_s4(M: Mapping[str, Any], residencia_loc: str) -> str:
    """s4 — imóveis: aluguel recorrente atual (janela estável) + âncora IRPF, sem yield %."""
    n = M["n_imoveis"]
    base = (
        f"{n} {pluralize(n, 'imóvel', 'imóveis')} no portfólio: residência{residencia_loc} "
        f"({fmt_currency(M['residencia'])}), imóveis de investimento somando "
        f"{fmt_currency(M['imoveis_investimento'])}. "
    )
    return base + _s4_aluguel_clause(M) + _s4_ancora_irpf(M)


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
