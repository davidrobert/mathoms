"""Narrativa da projeção de IF (S7 · chart ``projecao_3cenarios``).

Separado de ``charts_narrator`` por responsabilidade: os quatro estados
publicáveis do cone (faixa completa, adverso censurado, mediana censurada, sem
Monte Carlo) têm regra de copy própria — ADR-361.
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import fmt_currency, fmt_percent


def _fmt_probabilidade(prob: float) -> str:
    """Paridade com formatProbability do S7 (ADR-237): guards <1% / >99%."""
    if prob <= 0:
        return "0%"
    if prob >= 1:
        return "100%"
    if prob < 0.01:
        return "<1%"
    if prob > 0.99:
        return ">99%"
    return f"{round(prob * 100)}%"


def _chance_ate_idade_meta(M: Mapping[str, Any], ctx: NarrativasContext) -> str:
    """Oração da probabilidade, com o horizonte dela declarado (idade-meta)."""
    # Horizonte próprio, diferente do horizonte de 40 anos dos percentis — os
    # dois nunca aparecem na mesma oração sem rótulo (ADR-361).
    prob_txt = _fmt_probabilidade(M["mc_prob_if_ate_idade_meta"])
    aprox = "" if prob_txt[0] in "<>" else "~"
    return (
        f"{aprox}{prob_txt} de chance de {ctx.titular_nome} alcançá-la até os "
        f"{M['mc_idade_meta']} anos"
    )


def _faixa_cenarios(M: Mapping[str, Any]) -> str:
    """Extremos da faixa quando existem; vazio quando censurados."""
    # Rótulo de percentil não vai para copy user-facing: "P10" é o ano mais cedo
    # (favorável) enquanto `caminho_p10` é o patrimônio mais baixo (adverso) — o
    # mesmo sufixo aponta para lados opostos.
    p10, p90 = M.get("mc_p10_ano_if"), M.get("mc_p90_ano_if")
    if p10 and p90:
        return f", entre {p10} no cenário favorável e {p90} no adverso"
    if p10:
        return f", a partir de {p10} no cenário favorável"
    return ""


def _projecao_com_central(M: Mapping[str, Any], ctx: NarrativasContext, renda: str) -> str:
    """Mediana publicável: faixa + chance, e o adverso fora do horizonte se for."""
    cauda = ""
    if M.get("mc_p90_censurado") and M.get("mc_horizonte_anos"):
        cauda = (
            f" Nas simulações mais lentas a meta fica além dos "
            f"{M['mc_horizonte_anos']} anos projetados."
        )
    return (
        f"Cenário central: meta em {M['mc_p50_ano_if']}{_faixa_cenarios(M)}; "
        f"{_chance_ate_idade_meta(M, ctx)}.{cauda} " + renda
    )


def _projecao_sem_central(M: Mapping[str, Any], ctx: NarrativasContext, renda: str) -> str:
    """Mediana censurada — a má notícia é dita, não substituída pelo determinístico."""
    # Sem este ramo, `p50 = None` cairia na frase determinística ("a trajetória
    # aponta a meta para X"): a mais otimista do relatório, exatamente no plano
    # em que a mediana não chega. O sujeito é o plano, não a pessoa, e a
    # afirmação vem datada e condicionada ao aporte de hoje.
    horizonte = M.get("mc_horizonte_anos") or 40
    prob_h = M.get("mc_prob_if_ate_horizonte")
    fatia = f"{_fmt_probabilidade(prob_h)} das simulações chegam lá" if prob_h else ""
    meio = f" — {fatia}" if fatia else ""
    return (
        f"Na maior parte dos cenários simulados a meta não é atingida dentro dos "
        f"{horizonte} anos projetados{meio}. É a leitura do plano de hoje, não uma "
        f"previsão: as alavancas são o aporte mensal e o tamanho da meta — elevar o "
        f"risco da carteira não é a terceira, porque alarga a faixa nos dois "
        f"sentidos. {_chance_ate_idade_meta(M, ctx)}. " + renda
    )


def _projecao_deterministica(M: Mapping[str, Any], ctx: NarrativasContext, renda: str) -> str:
    """Sem Monte Carlo: aritmética do ritmo atual, nunca promessa."""
    # ADR-361 checava a sentinela 999; o #1158 aposentou a sentinela e o
    # determinístico agora emite ausência (`if_ano is None`), então o guard lê o
    # contrato novo em vez do valor legado.
    if M.get("if_ano") is None or M.get(ctx.key_idade_titular_if) is None:
        return (
            "Com as premissas atuais (aporte e retorno reais), a trajetória "
            "determinística não projeta um ano para a meta. " + renda
        )
    return (
        f"Em cenário sem variação de mercado, a trajetória projetada aponta a meta para "
        f"{M['if_ano']}, quando {ctx.titular_nome} tiver {M[ctx.key_idade_titular_if]} anos. "
        + renda
    )


def narrate_projecao_if_conclusion(M: Mapping[str, Any], ctx: NarrativasContext) -> str:
    renda = (
        f"Hoje, a renda passiva estimada pela regra de retirada é {fmt_currency(M['renda_passiva_4pct'])}/mês "
        f"({fmt_percent(M['pct_renda_passiva_meta'])} da meta de {fmt_currency(M['if_renda_passiva_meta'])}/mês)."
    )
    tem_prob = M.get("mc_prob_if_ate_idade_meta") is not None and M.get("mc_idade_meta")
    if M.get("mc_p50_ano_if") and tem_prob:
        return _projecao_com_central(M, ctx, renda)
    if M.get("mc_p50_censurado") and tem_prob:
        return _projecao_sem_central(M, ctx, renda)
    return _projecao_deterministica(M, ctx, renda)
