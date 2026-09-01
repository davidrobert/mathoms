"""Órfãos de domínio do catálogo de KPI — métricas publicadas SEM alvo, por decisão. Extraído de ``kpi_target_catalog`` quando ele chegou a 499 linhas (teto de 500 do CLAUDE.md §Code style) e o rationale de cada órfã já respondia por ~1/4 do arquivo. Consumidores: ``build_kpi_targets`` (monta o alvo vazio) e o gate da [[ADR-419]] §D4, via ``ORFAOS_DOMINIO_KEYS``."""

from __future__ import annotations

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


#: Órfãs por decisão, derivadas da tupla — nunca à mão. Consumidor: gate de [[ADR-419]] §D4.
ORFAOS_DOMINIO_KEYS: tuple[str, ...] = tuple(chave for chave, *_ in _ORFAOS_DOMINIO)


__all__ = ["ORFAOS_DOMINIO_KEYS", "_ORFAOS_DOMINIO"]
