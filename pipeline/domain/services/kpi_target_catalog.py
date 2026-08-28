"""Alvo de KPI tem procedência declarada — o LLM seleciona, não autora (§r7 PE-2/FP-6).

O parecer publicava ``metricas[].target`` como string livre do LLM. Medido em dois
runs sobre payload byte-idêntico (``ratios.concentracao_imobiliaria = 34.86`` nos
dois), o alvo migrou de ``< 30%`` para ``< 35%`` — **atravessando o valor
observado**: violação virou conformidade sem nada ter mudado no patrimônio. E o
limiar canônico do repo para esse conceito é 50% ([[ADR-340]]), então os dois
números do LLM estavam errados, em direções opostas.

Este módulo é o leitor único do limiar **na rota do `target` publicado** — não do
repo. Os leitores pré-existentes de ``endividamento_maximo_pct``
(``pontos_fortes_analyzer``, ``pontos_urgentes_analyzer``, com default inline
duplicado) permanecem; unificá-los é trabalho à parte. O que esta rota evita é uma
**quarta** cópia, nascendo no backend.

Duas procedências, com precedência declarada — **alvo da família vence doutrina do
produto** (co-design financial-planner: na metodologia dona da métrica o desvio só
existe contra o alvo declarado, e publicar número mais frouxo que o compromisso da
família é o produto absolvendo-a da própria meta):

- ``goal_declarado`` — a família escolheu (``goals.*``, ``reserva_emergencia.meses_alvo``).
- ``limiar_canonico`` — doutrina do produto em config/código, vale para toda família.

Alvo sem fonte única é **órfão**: publica ``limiar=None`` + ``motivo`` legível, nunca
um número inventado. Órfão é fato esperado, não anomalia — não vira ``needs_review``
(usar o canal de retenção para o caso comum queima o canal), e a métrica continua
publicada como observacional para não perder o sinal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional

from pipeline.domain.services.bases_financeiras import BaseFinanceira
from pipeline.domain.services.diagnostico_comportamental_analyzer import (
    NAO_IDENTIFICADO_PARCIAL_PCT,
)
from pipeline.domain.services.exposicao_cambial_analyzer import (
    THRESHOLD_VERDE_PCT,
    base_declarada_do_pct,
    veredito_suprimido,
)
from pipeline.domain.services.real_estate_metrics import RealEstateConfig

#: Vocabulário fechado de KPI. O LLM escolhe uma destas chaves; não inventa alvo.
#: Regra de admissão (A40.l89): admite-se chave quando **(a)** existe fonte
#: determinística única para o limiar, **ou (b)** a ausência de alvo é ela própria
#: regra de domínio decidida e vale publicar ao usuário. Nunca um número escolhido
#: na hora — e nunca uma chave de escape genérica, que seria (a) com outro nome:
#: métrica fora deste enum não é emitível, e é esse o cap estrutural da [[ADR-399]].
METRICA_KEYS = (
    "taxa_poupanca_recorrente",
    "reserva_cobertura_meses",
    "alocacao_renda_fixa",
    "concentracao_imobiliaria",
    "exposicao_cambial",
    "carteira_trs",
    "taxa_endividamento",
    "if_progresso",
    "if_prazo_ano",
    "despesas_nao_categorizadas",
    "protecao_custo_premio",
    "renda_passiva_cobertura",
    "aliquota_efetiva_ir",
)

PROCEDENCIA_GOAL = "goal_declarado"
PROCEDENCIA_CANONICO = "limiar_canonico"


@dataclass(frozen=True)
class KpiTarget:
    """Alvo de um KPI com procedência auditável — ``limiar is None`` ⇒ órfão."""

    # `motivo` diz por que é órfão e é o texto que a UI mostra no lugar do alvo.
    # `rotulo` é o nome publicado da métrica: fica aqui, e não no LLM, porque
    # rótulo autorado não é gateável — e o rótulo carrega domínio. O caso que
    # obriga: cobrir 100% da despesa *essencial* é o marco de segurança, não a
    # independência (que se mede contra o custo de vida total); publicar
    # "cobertura da renda passiva" sem o qualificador ensina a família a se
    # declarar independente cedo demais.
    observado_path: str
    base: str
    unidade: str
    rotulo: str
    limiar: Optional[float] = None
    operador: Optional[str] = None
    procedencia: Optional[str] = None
    ref: Optional[str] = None
    motivo: Optional[str] = None

    # O estado `limiar=42.0, procedencia=None` — número sem fonte auditável — é
    # exatamente o defeito que esta ADR existe para impedir, e era representável:
    # os dois invariantes da suíte olhavam `procedencia`/`motivo` sem pinar
    # `limiar`. Só `_orfao()` produzia `procedencia=None`, então o consumidor não
    # conseguia distinguir "órfão" de "número órfão de fonte" pela chave errada.
    def __post_init__(self) -> None:
        resolvido = self.limiar is not None
        acompanhantes = {
            "operador": self.operador,
            "procedencia": self.procedencia,
            "ref": self.ref,
        }
        faltando = [nome for nome, v in acompanhantes.items() if (v is None) == resolvido]
        if faltando or resolvido == (self.motivo is not None):
            raise ValueError(
                f"KpiTarget inconsistente em {self.observado_path!r}: "
                f"limiar={self.limiar!r} exige "
                f"{'operador+procedencia+ref e motivo=None' if resolvido else 'motivo e operador/procedencia/ref=None'}; "
                f"got operador={self.operador!r} procedencia={self.procedencia!r} "
                f"ref={self.ref!r} motivo={self.motivo!r}"
            )


# Cobertura da renda passiva sobre a despesa essencial. O limiar 100 não é doutrina
# escolhida: é o **ponto fixo da própria razão** (numerador = denominador), o único
# número que não seria uma escolha. Base declarada porque o payload tem dois
# denominadores de despesa essencial — `fluxo_caixa.despesa_mensal_essencial` e
# `reserva_emergencia.custo_essencial_mensal`. Não é o FP-6 (lá eram dois
# *conceitos* sob o mesmo nome): são as mesmas categorias em janelas distintas, e os
# dois consumidores já preferem 12m.
COBERTURA_ESSENCIAL_ALVO_PCT = 100.0

# Limiar que vive em constante de código/config; `ref` aponta o leitor único.
# Tupla: (chave, observado_path, base, unidade, rotulo, limiar, operador, ref)
_CANONICOS = (
    (
        "despesas_nao_categorizadas",
        "$.diagnostico_confianca.share_nao_identificado_pct",
        "despesa_total",
        "pct",
        "Despesas não identificadas (% do total, 12m)",
        NAO_IDENTIFICADO_PARCIAL_PCT,
        "<",
        "diagnostico_comportamental_analyzer.NAO_IDENTIFICADO_PARCIAL_PCT",
    ),
)

# Órfãos por DECISÃO de domínio, não por lacuna de implementação — publicar número
# aqui seria regressão, não melhoria:
#
# - `carteira_trs` — [[ADR-191]] §D5: TRS efetiva é yield observado e não tem
#   comparador. O parecer publicou "≥ IPCA+4%" e depois "≥ 6% real": 4% vs 6% real,
#   e ambos comparam yield de fluxo com retorno TOTAL (yield + ganho de capital),
#   induzindo "vender growth para perseguir dividend yield" — o erro de iniciante
#   que a métrica existe para evitar.
# - `protecao_custo_premio` — [[ADR-387]] proíbe afirmar capital ideal sem segurado,
#   dependência econômica e inventário confirmados. O publicado ("≥ 60 meses de
#   renda") era 2 a 4× mais frouxo que o canon (10× renda anual × fator + dívidas),
#   na única métrica cujo erro é irreversível para terceiros (os dependentes).
#   A chave chamava-se `protecao_cobertura` e **nomeava um conceito que o payload
#   não publica**: não existe agregado de capital segurado no schema — por desenho,
#   é a própria ADR-387. O que `pct_renda_anual` entrega é prêmio/renda, carga do
#   seguro no orçamento. Medido: 6.022,27 / 0,005686 ⇒ renda ≈ 1,06 MM, logo é
#   **razão 0–1**, e estava declarada `pct`: quem lesse pelo contrato publicaria
#   0,0057% no lugar de 0,57%, erro de 100× que nenhum gate via. Cobertura de
#   capital continua sendo tratada qualitativamente por `gap_qualitativo`.
# - `taxa_poupanca_recorrente` — RV2-24: `poupanca_referencia_pct` (25) e
#   `pontos_fortes_taxa_poupanca_min_pct` (30) descrevem o mesmo conceito sem
#   precedência declarada. O resolver NÃO escolhe: escolher seria inventar regra de
#   domínio com carimbo de procedência — pior que o alvo do LLM por parecer autoritativo.
# - `if_progresso` — o alvo é o par (ano declarado, 100%); o ano sozinho promete
#   estado futuro sem a probabilidade do cone, que a persona proíbe (R20).
# - `if_prazo_ano` — mesma razão pelo outro lado. O ano declarado (2041) é
#   `goal_declarado` legítimo, mas o "atual" só existe como percentil de um cone
#   estocástico, e `if_monte_carlo` intercala a flag `_censurado` ao lado de cada
#   ano de propósito ([[ADR-361]]). Uma linha `alvo 2041 / atual 2036` descarta a
#   censura **e** a probabilidade, e transforma mediana de simulação em medição. O
#   par honesto (prob × prazo) já é publicado pela narrativa.
# - `aliquota_efetiva_ir` — "monitorar tendência" **é** a regra: alíquota efetiva é
#   descritiva, não normativa, e o limiar dependeria do regime (PJ vs CLT). Admitida
#   por (b): a ausência de alvo é a decisão, e o sinal vale publicado.
#
# Tupla: (chave, observado_path, base, unidade, rotulo, motivo)
_ORFAOS_DOMINIO = (
    # `trs_pct` não existe em `ratios.rentabilidade` — o campo é `valor_pct`
    # ([[ADR-191]] §D3). Pior que erro de digitação: `trs_pct` é o nome da chave de
    # **saque** (`goals.trs_pct`, [[ADR-191]] §Emenda 2026-08-14), então o path errado
    # importava a colisão de nomes para dentro do catálogo. Path que não resolve é a
    # mesma classe de defeito que o alvo fabricado (`analyze_finances.py` §kpi_targets).
    (
        "carteira_trs",
        "$.ratios.rentabilidade.valor_pct",
        "patrimonio_gerador",
        "pct_aa",
        "Rentabilidade da carteira (TRS efetiva)",
        "rentabilidade observada não tem alvo canônico (ADR-191 §D5)",
    ),
    (
        "protecao_custo_premio",
        "$.protecao_patrimonial.pct_renda_anual",
        # LÍQUIDA, não ativa: `_pct_renda` divide por `renda_anual_liquida_brl`
        # (`protecao_analyzer.py:470`), resolvida IRPF-first por
        # `resolve_renda_anual_liquida`. Declarar "ativa" era o modo de falha que a
        # [[ADR-399]] existe para impedir — observado de uma base sob rótulo de outra.
        "renda_anual_liquida",
        # E é razão 0–1, não `pct`: 6.022,27 / 0,005686 ⇒ renda ≈ 1,06 MM. Sob `pct`
        # o leitor publicaria 0,0057% no lugar de 0,57% — o mesmo modo de falha do
        # rótulo de base, um andar abaixo, na unidade.
        "ratio_0_1",
        "Custo dos seguros sobre a renda anual",
        "capital ideal exige inventário de proteção confirmado (ADR-387)",
    ),
    # QUINTO órfão por decisão de domínio, e o único que já teve alvo publicado. O
    # catálogo afirmava `operador="<="` sobre o par (atual, alvo): **menos** renda fixa
    # que o alvo estaria conforme. Falso nas três metodologias de referência e falso na
    # direção que machuca — família sub-protegida em drawdown vende ativo de risco na
    # baixa. Ficava mascarado porque o `observado_path` usava predicado de filtro e
    # nunca resolvia; consertar o path sem o operador ATIVARIA o comparador errado com
    # o selo do produto ([[A40.l89]] §Fecho, achado N1; co-design `financial-planner`).
    #
    # Nenhum operador escalar diz a verdade aqui: desvio de alocação é bidirecional e
    # **soma zero** entre classes comparáveis (denominador único), com sub e
    # sobrealocação diferindo em natureza, urgência e remédio. Um teto ou um piso
    # colapsa os dois. E a banda de ±2pp do motor NÃO serve de régua: é piso de
    # ACIONABILIDADE (a [[ADR-400]] a reusa literalmente assim) e a [[ADR-141]]
    # §Emenda item 10 difere a calibração relativa para pós-dogfood — publicá-la como
    # `limiar_canonico` promoveria limiar interno a doutrina sem a doutrina existir.
    #
    # A linha segue publicada como observacional, com o observado em ponto fixo: o alvo
    # declarado não some do produto, ele vive no card Alocação · Atual vs Alvo (S3) com
    # direção, desvio assinado, severidade e destino do próximo aporte. O que sai é uma
    # cópia escalar de menor resolução — e é justamente ela que não sabe dizer a verdade.
    #
    # Efeito colateral, e não é pequeno: sem comparador, dois estados que fabricariam
    # conformidade deixam de existir — carteira líquida zero (`_pct_of` devolve 0,0 e
    # "0% ≤ 44,4%" leria conforme) e supressão declarada pela [[ADR-394]]/[[ADR-400]],
    # em que o produtor se recusa a julgar o desvio e o comparador o recriaria por
    # outra porta. Os dois estão VIVOS na fixture do golden hoje.
    (
        "alocacao_renda_fixa",
        "$.goals.alocacao_alvo.derived.renda_fixa_atual_pct",
        "carteira_liquida",
        "pct",
        "Alocação em renda fixa (carteira líquida)",
        "desvio de alocação é bidirecional e soma zero entre classes; acompanhado por "
        "severidade e destino do próximo aporte, no card Alocação · Atual vs Alvo",
    ),
    (
        "taxa_poupanca_recorrente",
        "$.ratios.taxa_poupanca_recorrente_pct",
        "receita_recorrente",
        "pct",
        "Taxa de poupança recorrente (12m)",
        "duas fontes divergentes para o mesmo limiar (RV2-24)",
    ),
    (
        "if_progresso",
        "$.goals.if_pct",
        "patrimonio_alvo",
        "pct",
        "Progresso rumo à independência financeira",
        "progresso rumo à IF é acompanhado pelo cone, não por alvo pontual",
    ),
    (
        "if_prazo_ano",
        "$.if_monte_carlo.ano_if_cenario_central",
        "cone_monte_carlo",
        "ano",
        "Ano projetado da independência (cenário central)",
        "ano de IF é percentil de cone; alvo pontual promete estado futuro sem a probabilidade",
    ),
    (
        "aliquota_efetiva_ir",
        "$.ratios.aliquota_efetiva_ir_pct",
        "renda_anual_familiar",
        "pct",
        "Alíquota efetiva de IR (consolidada)",
        "alíquota efetiva é descritiva; o alvo depende do regime e não é canônico",
    ),
)


def _leaf(payload: Mapping[str, Any], *caminho: str) -> Any:
    no: Any = payload
    for chave in caminho:
        if not isinstance(no, Mapping):
            return None
        no = no.get(chave)
    return no


def _num(valor: Any) -> Optional[float]:
    return float(valor) if isinstance(valor, (int, float)) and not isinstance(valor, bool) else None


def _orfao(observado_path: str, base: str, unidade: str, rotulo: str, motivo: str) -> KpiTarget:
    return KpiTarget(
        observado_path=observado_path, base=base, unidade=unidade, rotulo=rotulo, motivo=motivo
    )


# A reserva tem DOIS denominadores e publica qual usou: `_base_from_window` cai para
# `despesa_mensal_media` quando não há despesa essencial documentada
# (`reserva_emergencia_calculator.py:333-350`). Fixar "essencial" no catálogo declarava
# base essencial sobre despesa TOTAL em todo workspace no fallback — e o discriminador
# já estava no payload, a um `_leaf` de distância ([[A40.l80]] §Correções C14).
# Chave ausente é artefato de série anterior ([[ADR-412]] §D8): responde com o nome do
# campo que carrega o valor, que não afirma essencialidade.
_BASE_POR_DENOMINADOR = {
    "custo_essencial": "despesa_essencial_mensal",
    "despesa_total": "despesa_mensal_media",
}
_BASE_DENOMINADOR_INDETERMINADO = "despesas_mensais"


def _base_da_reserva(e5: Mapping[str, Any]) -> str:
    declarado = _leaf(e5, "reserva_emergencia", "base_denominador")
    return _BASE_POR_DENOMINADOR.get(declarado, _BASE_DENOMINADOR_INDETERMINADO)


# DOUTRINA, não declaração da família — por isso `limiar_canonico`. `meses_alvo` sai de
# `scoring.json::reserva_emergencia._base_calculo.meses_alvo_por_perfil_renda`, chaveado
# por perfil **derivado da composição de renda observada**
# (`reserva_emergencia_calculator._perfil_por_pct`), e não há leitor de
# `Goal(RESERVA_EMERGENCIA)` em `pipeline/` — o goal existe só no backend. Carimbar
# `goal_declarado` punha a doutrina usando o crachá da família, e a precedência da
# [[ADR-399]] D2 (declarado vence doutrina) passaria a operar sobre uma mentira, na
# direção que absolve. Quando o Goal virar legível aqui, volta a `goal_declarado` — e aí
# a precedência significa o que promete. Achado da sessão da [[A40.l90]].
def _reserva(e5: Mapping[str, Any]) -> KpiTarget:
    meses = _num(_leaf(e5, "reserva_emergencia", "meses_alvo"))
    path, base = "$.reserva_emergencia.cobertura_meses", _base_da_reserva(e5)
    rotulo = "Cobertura da reserva de emergência"
    if meses is None:
        return _orfao(path, base, "meses", rotulo, "alvo de reserva não computado para este perfil")
    return KpiTarget(
        observado_path=path,
        base=base,
        unidade="meses",
        rotulo=rotulo,
        limiar=meses,
        operador=">=",
        procedencia=PROCEDENCIA_CANONICO,
        ref="scoring.json::reserva_emergencia._base_calculo.meses_alvo_por_perfil_renda",
    )


# `carteira_produtiva_fixa`, NUNCA a string livre `"carteira_produtiva"`: aquela não é
# membro do enum, e o vizinho mais próximo (`carteira_produtiva_familia`) vale 5,6× MENOS
# no dogfood — 13.000.000 contra 73.000.000. O produtor do número já declara a base certa
# em `ratios.base_concentracao_imobiliaria`; duas declarações divergentes para o MESMO
# `observado_path` é o C14 (declarada ≠ usada) na entrada que o #1782 criou para
# desambiguar.
def _concentracao_imobiliaria(alerta_pct: float) -> KpiTarget:
    return KpiTarget(
        observado_path="$.ratios.concentracao_imobiliaria",
        base=BaseFinanceira.carteira_produtiva_fixa.value,
        unidade="pct",
        rotulo="Concentração imobiliária (carteira produtiva)",
        limiar=alerta_pct,
        operador="<",
        procedencia=PROCEDENCIA_CANONICO,
        ref="RealEstateConfig.concentracao_alerta_pct ([[ADR-340]])",
    )


# Pareamento enforçado em pontos_urgentes_analyzer.py — mesma razão, mesmo limiar.
def _endividamento(scoring: Mapping[str, Any]) -> KpiTarget:
    alertas = scoring.get("thresholds_alertas") or {}
    maximo = _num(alertas.get("endividamento_maximo_pct"))
    path, base = "$.ratios.taxa_endividamento_pct", "patrimonio_bruto"
    rotulo = "Taxa de endividamento (% do patrimônio bruto)"
    if maximo is None:
        return _orfao(path, base, "pct", rotulo, "limiar de endividamento ausente do scoring")
    return KpiTarget(
        observado_path=path,
        base=base,
        unidade="pct",
        rotulo=rotulo,
        limiar=maximo,
        operador="<=",
        procedencia=PROCEDENCIA_CANONICO,
        ref="scoring.json::thresholds_alertas.endividamento_maximo_pct",
    )


# `status != "ok"` suprime a linha inteira em vez de publicar o número: sob
# `sem_irpf`/`gerador_zero`/`sem_dados_essencial` a razão cai para perto de zero por
# falta de insumo, não por falta de renda passiva — e "0% de cobertura" é a leitura
# mais assustadora que o relatório sabe emitir. Ausência declarada > zero medido.
_COBERTURA_ARGS = (
    "$.ratios.rentabilidade.cobertura_despesa_essencial_pct",
    "despesa_essencial_mensal_12m",
    "pct",
    "Renda passiva sobre a despesa essencial",
)


def _cobertura_medida(e5: Mapping[str, Any]) -> bool:
    rent = _leaf(e5, "ratios", "rentabilidade")
    if not isinstance(rent, Mapping) or rent.get("status") != "ok":
        return False
    return _num(rent.get("cobertura_despesa_essencial_pct")) is not None


def _renda_passiva_cobertura(e5: Mapping[str, Any]) -> KpiTarget:
    path, base, unidade, rotulo = _COBERTURA_ARGS
    if not _cobertura_medida(e5):
        return _orfao(*_COBERTURA_ARGS, "cobertura da renda passiva não medida neste período")
    return KpiTarget(
        observado_path=path,
        base=base,
        unidade=unidade,
        rotulo=rotulo,
        limiar=COBERTURA_ESSENCIAL_ALVO_PCT,
        operador=">=",
        procedencia=PROCEDENCIA_CANONICO,
        ref="kpi_target_catalog.COBERTURA_ESSENCIAL_ALVO_PCT",
    )


# Cobertura incompleta SUPRIME o comparador, não só o veredito. O produtor já se recusa
# a julgar quando o universo é parcial ([[ADR-403]]: `tier` vira `indeterminado` e o
# componente declara `cobertura: indeterminado`), mas o limiar seguia publicado com
# `limiar_canonico` — o que faria o parecer afirmar "0% contra ≥ 10%" com o selo de
# autoridade do produto sobre uma medida que o produtor não julgou. É pior que o alvo
# autorado pelo LLM, porque o carimbo é do produto. Achado da sessão da [[A40.l90]].
def _exposicao_cambial(e5: Mapping[str, Any]) -> KpiTarget:
    bloco = _leaf(e5, "exposicao_cambial")
    path = "$.exposicao_cambial.pct_investivel_financeiro"
    base = base_declarada_do_pct(bloco)
    rotulo = "Exposição cambial (% da carteira financeira da família)"
    if veredito_suprimido(bloco):
        return _orfao(path, base, "pct", rotulo, "exposição cambial sem cobertura apurada")
    return KpiTarget(
        observado_path=path,
        base=base,
        unidade="pct",
        rotulo=rotulo,
        limiar=THRESHOLD_VERDE_PCT,
        operador=">=",
        procedencia=PROCEDENCIA_CANONICO,
        ref="exposicao_cambial_analyzer.THRESHOLD_VERDE_PCT",
    )


def _tabelados() -> dict[str, KpiTarget]:
    canonicos = {
        chave: KpiTarget(
            observado_path=path,
            base=base,
            unidade=unidade,
            rotulo=rotulo,
            limiar=limiar,
            operador=operador,
            procedencia=PROCEDENCIA_CANONICO,
            ref=ref,
        )
        for chave, path, base, unidade, rotulo, limiar, operador, ref in _CANONICOS
    }
    orfaos = {
        chave: _orfao(path, base, unidade, rotulo, motivo)
        for chave, path, base, unidade, rotulo, motivo in _ORFAOS_DOMINIO
    }
    return {**canonicos, **orfaos}


def _alerta_concentracao(override: Optional[float] = None) -> float:
    if override is not None:
        return override
    return float(RealEstateConfig().concentracao_alerta_pct)


# `concentracao_alerta_pct` entra por parâmetro (e não é lido de um global) porque é
# overridável por workspace via ConfigStore ([[ADR-134]]) — só o produtor conhece a
# config efetiva.
def build_kpi_targets(
    e5: Mapping[str, Any],
    *,
    scoring: Mapping[str, Any],
    concentracao_alerta_pct: Optional[float] = None,
) -> dict[str, dict[str, Any]]:
    """Resolve o alvo de cada KPI do vocabulário a partir do payload E5 + config."""
    alerta = _alerta_concentracao(concentracao_alerta_pct)
    alvos: dict[str, KpiTarget] = {
        "reserva_cobertura_meses": _reserva(e5),
        "concentracao_imobiliaria": _concentracao_imobiliaria(alerta),
        "taxa_endividamento": _endividamento(scoring),
        "renda_passiva_cobertura": _renda_passiva_cobertura(e5),
        "exposicao_cambial": _exposicao_cambial(e5),
        **_tabelados(),
    }
    return {chave: asdict(alvo) for chave, alvo in alvos.items()}


__all__ = [
    "METRICA_KEYS",
    "PROCEDENCIA_CANONICO",
    "PROCEDENCIA_GOAL",
    "KpiTarget",
    "build_kpi_targets",
]
