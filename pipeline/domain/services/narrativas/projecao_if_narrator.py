"""Narrativa da projeção de IF (S7 · chart ``projecao_3cenarios``).

Separado de ``charts_narrator`` por responsabilidade: os quatro estados
publicáveis do cone (faixa completa, adverso censurado, mediana censurada, sem
Monte Carlo) têm regra de copy própria — ADR-361.
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import fmt_currency, fmt_percent

_MESES_PT = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


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


def _fmt_mes_ano(iso: str | None) -> str:
    """``"2026-03-01"`` → ``"março de 2026"``; ausência vira string vazia."""
    if not iso or len(iso) < 7:
        return ""
    ano, mes = iso[:4], iso[5:7]
    if not mes.isdigit() or not 1 <= int(mes) <= 12:
        return ""
    return f"{_MESES_PT[int(mes) - 1]} de {ano}"


_MOTIVO_PRAZO_VENCIDO = "prazo declarado já venceu"


def _oracao_sem_prazo_declarado(M: Mapping[str, Any]) -> str:
    """Ausência do alvo: nomeia o insumo que falta, não a nossa incapacidade."""
    # `prob = 0` seria aritmeticamente correto e inútil (ADR-361 D8): afirma
    # "nenhuma simulação atinge" quando o que houve é que a pergunta não se
    # aplica. Cada motivo tem a sua saída, senão o vazio interrompe sem ensinar.
    # O estado vem do `motivo` que o payload PUBLICA; re-derivá-lo aqui a partir
    # de `declarado_em`/`ano_alvo` poria a decisão em dois lugares.
    if M.get("mc_motivo_sem_prazo_declarado") == _MOTIVO_PRAZO_VENCIDO:
        return (
            f"O prazo que você declarou em {_fmt_mes_ano(M.get('mc_declarado_em'))} terminou "
            f"em {M.get('mc_ano_alvo_declarado')}, e não medimos probabilidade contra data "
            f"vencida. Declare um prazo novo na sua meta de independência financeira"
        )
    return (
        "Você ainda não respondeu em quantos anos quer chegar à meta, e sem esse prazo "
        "não há probabilidade a publicar. Defina o prazo na sua meta de independência "
        "financeira"
    )


def _oracao_prazo_truncado(M: Mapping[str, Any], prob_txt: str) -> str:
    """Prazo declarado além da janela: o número medido é PISO, não teto."""
    # P(T <= 40) <= P(T <= 50): truncar a janela só remove sucessos, nunca
    # adiciona. Chamar de teto seria publicar um número que diz medir uma coisa
    # e mede outra — o defeito que esta lane existe para matar.
    janela = M.get("mc_horizonte_simulado_anos") or 40
    return (
        f"Você declarou {M.get('mc_prazo_declarado_anos')} anos e a simulação cobre "
        f"{janela}. A chance publicada ({prob_txt}) é a de chegar até o {janela}º ano, "
        f"não até a sua data — é um piso: os cenários que chegam depois ficam de fora"
    )


def _oracao_prazo_declarado(M: Mapping[str, Any]) -> str:
    """Oração da probabilidade, com o dono e a data do alvo declarados."""
    # ADR-369 D2: antes o sujeito era ambíguo ("até os 60 anos") e a idade vinha
    # da saída do próprio projetor — o usuário lia a data como nossa. A
    # aritmética fica visível (2026 + 15 = 2041), então não sobra pergunta sobre
    # a origem do ano; e "das simulações" impede ler a fração como certeza.
    prob = M.get("mc_prob_if_ate_prazo_declarado")
    if prob is None:
        return _oracao_sem_prazo_declarado(M)
    prob_txt = _fmt_probabilidade(prob)
    if M.get("mc_prazo_declarado_truncado"):
        return _oracao_prazo_truncado(M, prob_txt)
    return (
        f"Os {M.get('mc_prazo_declarado_anos')} anos que você declarou em "
        f"{_fmt_mes_ano(M.get('mc_declarado_em'))} fixam a sua data em "
        f"{M.get('mc_ano_alvo_declarado')}. Até lá, {prob_txt} das simulações alcançam a meta"
    )


def _faixa_cenarios(M: Mapping[str, Any]) -> str:
    """Extremos da faixa quando existem; vazio quando censurados."""
    # Rótulo de percentil nunca foi para copy user-facing porque "P10" é o ano
    # mais cedo (favorável) enquanto `caminho_p10` é o patrimônio mais baixo
    # (adverso). ADR-369 D1 levou o nome do cenário para dentro do contrato, e a
    # copy passou a ler igual ao payload em vez de traduzi-lo aqui.
    favoravel = M.get("mc_ano_if_cenario_favoravel")
    adverso = M.get("mc_ano_if_cenario_adverso")
    if favoravel and adverso:
        return f", entre {favoravel} no cenário favorável e {adverso} no adverso"
    if favoravel:
        return f", a partir de {favoravel} no cenário favorável"
    return ""


def _projecao_com_central(M: Mapping[str, Any], ctx: NarrativasContext, renda: str) -> str:
    """Mediana publicável: faixa + prazo declarado, e o adverso fora do horizonte."""
    # O separador é ponto, não ponto-e-vírgula: o `;` amarrava a oração à faixa
    # de cenários, e a data declarada não pertence ao cone — é do cliente.
    cauda = ""
    if M.get("mc_ano_if_cenario_adverso_censurado") and M.get("mc_horizonte_simulado_anos"):
        cauda = (
            f" Nas simulações mais lentas a meta fica além dos "
            f"{M['mc_horizonte_simulado_anos']} anos projetados."
        )
    return (
        f"Cenário central: meta em {M['mc_ano_if_cenario_central']}{_faixa_cenarios(M)}. "
        f"{_oracao_prazo_declarado(M)}.{cauda} " + renda
    )


def _projecao_sem_central(M: Mapping[str, Any], ctx: NarrativasContext, renda: str) -> str:
    """Mediana censurada — a má notícia é dita, não substituída pelo determinístico."""
    # Sem este ramo, `central = None` cairia na frase determinística ("a
    # trajetória aponta a meta para X"): a mais otimista do relatório, exatamente
    # no plano em que a mediana não chega. O sujeito é o plano, não a pessoa, e a
    # afirmação vem datada e condicionada ao aporte de hoje.
    horizonte = M.get("mc_horizonte_simulado_anos") or 40
    prob_h = M.get("mc_prob_if_ate_horizonte_simulado")
    fatia = f"{_fmt_probabilidade(prob_h)} das simulações chegam lá" if prob_h else ""
    meio = f" — {fatia}" if fatia else ""
    return (
        f"Na maior parte dos cenários simulados a meta não é atingida dentro dos "
        f"{horizonte} anos projetados{meio}. É a leitura do plano de hoje, não uma "
        f"previsão: as alavancas são o aporte mensal e o tamanho da meta — elevar o "
        f"risco da carteira não é a terceira, porque alarga a faixa nos dois "
        f"sentidos. {_oracao_prazo_declarado(M)}. " + renda
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
    # ADR-369 D2: o roteamento passou a depender só do CONE. Antes exigia também
    # probabilidade + idade-meta, então um cone válido sem alvo caía na frase
    # determinística — a mais otimista — em vez de publicar o cone e declarar a
    # ausência do alvo, que é o que a oração do prazo faz agora.
    if M.get("mc_ano_if_cenario_central"):
        return _projecao_com_central(M, ctx, renda)
    if M.get("mc_ano_if_cenario_central_censurado"):
        return _projecao_sem_central(M, ctx, renda)
    return _projecao_deterministica(M, ctx, renda)
