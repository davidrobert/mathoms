"""Destino de leitura do item do parecer — derivado, nunca escolhido pela prosa (A40.l117).

`section_id` responde *"onde, neste relatório, o leitor vê este assunto por extenso"*.
Não é proveniência: essa já é servida por ``ancoras[].path`` com precisão de folha
([[ADR-296]]), e publicar uma segunda resposta mais grossa à mesma pergunta era o que
produzia destino contraditório.

**Os dois mapas apontam para CARD, não para seção.** Card muda de seção — a [[A40.l34]]
moveu teto/capacidade PGBL da S8 para a `S_IRPF_OTIMIZACAO` —, e mapa direto para
`section_id` teria envelhecido calado naquele PR. Aqui ele quebra ruidosamente (o card
some do layout) e segue certo quando o card se muda.
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from backend.app.generated.report_layout import LAYOUT

# Terminal da cascata: "este assunto vive no próprio parecer". Nunca mente — a seção
# existe e hospeda o item. O modo de falha aceito é *não dizer nada*, nunca *dizer outra
# coisa*: por isso o render suprime o auto-ponteiro em vez de imprimi-lo.
DESTINO_FALLBACK = "S_parecer"

# Camada 1 — raiz da evidência com SEDE VISUAL ÚNICA. Critério de admissão, objetivo e
# auditável contra o layout: a raiz é renderizada por **um** card/chart. Raiz de
# ARMAZENAMENTO fica fora (`$.investimentos`, `$.patrimonio`, `$.ratios`,
# `$.fluxo_caixa`): o conteúdo delas se espalha por S1/S3/S4, e é por isso que item
# ancorado nelas cai no tema.
#
# A âncora é enganosa em duas classes, com viés de direção fixa, e a allowlist é o que
# as contém: (a) IMÓVEL — não há raiz "imóveis" no que o modelo cita, então âncora-primeiro
# mandaria todo item de imóvel para S3/S1 e nunca para a S4; (b) DENOMINADOR — o item fala
# de cobertura e cita o divisor (`total_*`).
_RAIZ_COM_SEDE: Mapping[str, str] = {
    "$.exposicao_cambial": "exposicao_cambial",
    "$.reserva_emergencia": "reserva_emergencia",
    "$.endividamento": "endividamento",
    "$.consumo_consciente": "consumo_consciente",
    "$.real_estate": "real_estate_yield",
    # Prefixo FUNDO de propósito. Medido: `InvestimentosClasseCard` — o único que exibia
    # `total_imoveis_investimento` — **não é montado em seção nenhuma** (substituído em
    # A11), e `AlocacaoAtualVsAlvoCard` (S3) declara imóvel físico **fora** da base que
    # compara. Mandar para a S3 mandaria o leitor a uma seção que diz "isto não está
    # aqui"; a S4 publica `concentracao_pct`, que é o peso que ele procura.
    "$.investimentos.total_imoveis_investimento": "real_estate_yield",
    "$.investimentos.n_imoveis_total": "real_estate_yield",
    "$.if_monte_carlo": "projecao_3cenarios",
    "$.passive_income": "renda_passiva",
    "$.irpf_kpis": "aliquota_efetiva_dual_gauge",
    "$.previdencia_pgbl": "pgbl_capacidade",
    "$.protecao_patrimonial": "protecao_apolices",
}

# Camada 2 — tema declarado. `Proteção` é lacuna por eixo do layout (2.5 = o que está
# CONTRATADO; S9 = o que FALTA), então risco e sugestão vão ao gap; a métrica de proteção
# é a exceção e sai por `_METRICA_PARA_CARD`.
#
# **Nenhum tema roteia para a S4** — ela só se alcança pela camada 1, via `$.real_estate`.
# É consequência aceita, não esquecimento: a alternativa seria inventar um tema "Imóveis"
# fora do enum da [[ADR-207]]. O acoplamento sai de graça: a S4 renderiza sse
# `data.real_estate` existe, que é exatamente a raiz que a roteia.
_TEMA_PARA_CARD: Mapping[str, str] = {
    "Proteção": "hero_gap_protecao",
    "Alocação": "alocacao_atual_vs_alvo",
    "Renda passiva": "renda_passiva",
    "Liquidez": "reserva_emergencia",
    "Custo tributário": "pgbl_capacidade",
    "Saúde de balanço": "patrimonio_categorias",
    "Diagnóstico de dados": "despesas_doughnut",
    "Equilíbrio presente-futuro": "equilibrio_cerbasi",
    "Convergência metodológica": "top5_decisoes",
}

# `Metrica` não tem `ancoras` por schema, e `metrica_key` é discriminador MELHOR que a
# âncora: ela nomeia a GRANDEZA, e destino de leitura é função da grandeza — por isso esta
# tabela não precisa da exceção de imóvel que a rota por âncora precisa.
_METRICA_PARA_CARD: Mapping[str, str] = {
    "taxa_poupanca_recorrente": "equilibrio_cerbasi",
    "reserva_cobertura_meses": "reserva_emergencia",
    "alocacao_renda_fixa": "alocacao_atual_vs_alvo",
    "concentracao_imobiliaria": "patrimonio_categorias",
    "exposicao_cambial": "exposicao_cambial",
    "carteira_trs": "kpi_rentabilidade",
    "taxa_endividamento": "endividamento",
    "if_progresso": "projecao_3cenarios",
    "if_prazo_ano": "projecao_3cenarios",
    "despesas_nao_categorizadas": "despesas_doughnut",
    # O CONTRATADO, não a lacuna: prêmio pago sobre cobertura vigente. Mandá-lo à S9
    # publicaria uma medida do que EXISTE sob o cabeçalho do que FALTA — erro de
    # categoria, e é por ele que a `S_PROTECAO` entrou no vocabulário do parecer.
    "protecao_custo_premio": "protecao_kpi_hero",
    "renda_passiva_cobertura": "renda_passiva",
    "aliquota_efetiva_ir": "aliquota_efetiva_dual_gauge",
    # Sem card próprio por desenho ([[ADR-420]] §D3 o cria sem limiar nem card). O destino
    # é onde o leitor vê o ASSUNTO — a composição do patrimônio —, não um card que o exiba.
    "imobilizacao_patrimonial": "patrimonio_categorias",
}

# `PontoForte` sem tema: os pontos fortes são renderizados na síntese.
_CARD_PONTO_FORTE_SEM_TEMA = "pontos_fortes"

# Seção oculta é destino MORTO — pior que o status quo, porque manda o leitor a uma seção
# que aquele relatório não imprime. Estes são os quatro componentes com early-return
# medidos em `frontend/src/components/report/sections/`; o destino degrada para a seção
# viva mais próxima em vez de apontar para o vazio.
_GATE_DE_SECAO: Mapping[str, str] = {
    "S4": "real_estate",
    "S_IRPF_RENDA": "irpf_kpis",
    "S_IRPF_OTIMIZACAO": "irpf_kpis",
    "S_PROTECAO": "protecao_patrimonial",
}
_DEGRADACAO: Mapping[str, str] = {
    "S4": "S1",
    "S_IRPF_RENDA": "S8",
    "S_IRPF_OTIMIZACAO": "S8",
    "S_PROTECAO": "S9",
}


def _viva(secao: str, e5_data: Optional[Mapping] = None) -> bool:
    """Sem payload para julgar não degrada — ausência de sinal não é sinal."""
    chave = _GATE_DE_SECAO.get(secao)
    if chave is None or e5_data is None:
        return True
    return bool(e5_data.get(chave))


def card_para_secao() -> dict[str, str]:
    """Derivado do layout a cada chamada — impede as tabelas de envelhecer caladas."""
    return {ident: secao for secao, ident in _pares_card_secao() if ident}


def _pares_card_secao():
    for section in LAYOUT.estrategico.sections:
        for item in list(section.cards or []) + list(section.charts or []):
            yield section.id, getattr(item, "id", None)


def _por_raiz(paths: Sequence[Optional[str]]) -> Optional[str]:
    """Longest-prefix sobre a allowlist. Prefixo até onde a sede é única, nunca a raiz crua."""
    for path in paths:
        if not path:
            continue
        casa = max((r for r in _RAIZ_COM_SEDE if path.startswith(r)), key=len, default=None)
        if casa:
            return _RAIZ_COM_SEDE[casa]
    return None


def resolve_destino(
    *,
    tema_canonico: Optional[str] = None,
    ancora_paths: Sequence[Optional[str]] = (),
    metrica_key: Optional[str] = None,
    e5_data: Optional[Mapping] = None,
) -> tuple[str, str]:
    """``(section_id, passo)`` — passo nomeia o ramo, para telemetria e para o gate."""
    mapa = card_para_secao()
    for card, passo in _candidatos(tema_canonico, ancora_paths, metrica_key):
        if card and card in mapa:
            return _degradado(mapa[card], passo, e5_data)
    return DESTINO_FALLBACK, "fallback"


def _candidatos(
    tema: Optional[str] = None,
    paths: Sequence[Optional[str]] = (),
    metrica: Optional[str] = None,
) -> tuple[tuple[Optional[str], str], ...]:
    """A cascata, em ordem. `sintese` só para `PontoForte` — sem tema e sem métrica."""
    ramos = (
        (_METRICA_PARA_CARD.get(metrica or ""), "metrica_key"),
        (_por_raiz(paths), "raiz_com_sede"),
        (_TEMA_PARA_CARD.get(tema or ""), "tema"),
    )
    if tema is None and metrica is None:
        return (*ramos, (_CARD_PONTO_FORTE_SEM_TEMA, "sintese"))
    return ramos


def _degradado(secao: str, passo: str, e5_data: Optional[Mapping] = None) -> tuple[str, str]:
    if _viva(secao, e5_data):
        return secao, passo
    return _DEGRADACAO.get(secao, DESTINO_FALLBACK), f"{passo}+degradado"


__all__ = ["DESTINO_FALLBACK", "card_para_secao", "resolve_destino"]
