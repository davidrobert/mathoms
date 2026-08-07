---
id: ADR-367
type: adr
title: "Ordem do plano por irreversibilidade: tier constante por regra, e o alvo da reserva gradua sem mover o gatilho"
status: Proposto
date: "2026-08-07"
relates_to: ["[[ADR-365]]", "[[ADR-328]]", "[[ADR-179]]"]
tags:
  - type/adr
  - status/proposto
  - area/report
  - phase/a40
---

# ADR-367 — Ordem do plano por irreversibilidade

## Contexto

A ordem dos itens de `pontos_urgentes` — a lista que o relatório apresenta como
"o que fazer" — é **a ordem literal das linhas `out.append`** em
`PontosUrgentesAnalyzer.analyze`: reserva, endividamento, seguro, rentabilidade.
Não há critério; há sequência de escrita. É a metade de RV3-07 que a [[A40.l10]]
ainda não fechou (a outra metade, "a fila de `Decision` não tem critério", foi
medida como falsa — [[ADR-179]] tem critério em SQL, ver §Emenda 2026-08-05 dela).

O painel de 2026-08-06 fixou a ordem defensável em **4 tiers por
irreversibilidade**. Esta ADR encoda isso e corrige **três premissas** daquele
painel que a medição de 2026-08-07 derrubou.

## Decisão

### D1 — Tier é constante por regra, indexado por `code`

O vocabulário é ordinal e fechado:

| Tier | Nome | `code` |
|---|---|---|
| T0 | ruína (dano irreversível) | — *hoje vazio, ver D4* |
| T1 | fragilidade (choque força crédito caro) | `reserva_insuficiente` |
| T2 | alavancagem | `endividamento_alto` |
| T3 | otimização | `rentabilidade_nao_medida` |

`seguro_vida` é **T0 quando há dependência econômica** e não é emitido quando não
há ([[ADR-365]] §D4: ausência de gatilho não é retenção) — o `code` é o mesmo nos
dois casos, então o mapa é por `code` e o tier de `seguro_vida` é T0.

**Por que constante, e não computado:** computar tier sobre `taxa_endividamento_pct`
ou `cobertura_meses` amarraria a ordem a duas variáveis cuja **medição** é
contestada — `taxa_endividamento_pct` é `dívidas/patrimônio bruto` enquanto
`config/scoring.json` declara "% renda mensal comprometida". Ordem encodada sobre
número mal rotulado tem aparência de rigor e não tem rigor.

**Onde:** `sorted(out, key=...)` no `return` de `analyze` — único ponto de saída.
O sort é **estável** (default de Python), e vem **antes** de
`partition_pontos_urgentes`, que preserva ordem relativa: ordenar depois
ordenaria só o array ranqueado e deixaria `pontos_urgentes_retidos` na ordem de
escrita.

**Efeito medido no corpus dogfood: nenhum.** Os 2 itens presentes
(`endividamento_alto` T2, `rentabilidade_nao_medida` T3) já saem nessa ordem. O
valor desta decisão é encodar o critério, não mudar o output de hoje — e vale
dizer isso em voz alta em vez de deixar o leitor supor que houve ganho visível.

### D2 — O alvo da reserva gradua a prioridade; o piso decide a existência

O item `reserva_insuficiente` continua sendo **emitido** por
`cobertura < piso` (6 meses). O que muda é a **prioridade dentro do item**:

- `cobertura < piso` → **Alta** / "Imediato"
- `piso ≤ cobertura < meses_alvo` → **Média** / "Próximo trimestre"

**Por que o piso não vira o alvo.** Piso é sobrevivência: abaixo dele um choque
força crédito caro (irreversível — daí T1). Alvo é acumulação: acima do piso é
custo de oportunidade, reversível por disciplina. Colapsar os dois destrói a
calibragem do card — e a medição mostra que o dano seria grande: `_perfil_por_pct`
**nunca retorna `clt_estavel`**, então `meses_alvo ∈ {12, 18}` e o piso real do
alvo é **12**, não 6. Trocar o gatilho pelo alvo cru alertaria "Alta/Imediato"
toda família com 6–12 meses de cobertura — enquanto `avaliacao_liquidity`, **no
mesmo payload**, rotula essa faixa como adequada.

`meses_alvo` **já chega** ao analyzer: `e5_analyzer_adapter` passa o mesmo dict de
`ReservaEmergenciaCalculator.calculate` sem projeção. Zero wiring novo. Fallback
`or 12.0` segue o precedente de `pontos_fortes_analyzer`.

**A copy nomeia o perfil**, não só o número — "abaixo do alvo de 18 meses para
renda predominantemente PJ" —, porque o alvo varia e um número sem base é a classe
de defeito que a A37.l9 fechou.

### D3 — As duas superfícies de cor da reserva ancoram no alvo, no mesmo PR

`HeroKpiGrid` **já imprime** "Meta 18m (perfil de renda)" a partir de `meses_alvo`,
mas decide a **cor** (`reservaTone`) e o **rótulo** (`reservaLabel`) com constantes
`3/6/12` que nunca leem o alvo. Resultado hoje: 8 meses com alvo 18 aparece
**verde/"adequada"** com a sub-linha dizendo "Meta 18m". O card se contradiz
**sozinho**, antes de qualquer mudança desta ADR.

`ReservaEmergenciaCard` repete os mesmos limiares. Ancorar só um deixa o card
grande verde ao lado do KPI corrigido — por isso os dois vão no mesmo PR.

**Nenhuma das duas tem teste hoje**: as duas suítes que montam `HeroKpiGrid`
passam `reserva={undefined}`, então `ReservaKpi` nunca renderiza valor. O PR
escreve o primeiro.

### D4 — T0 fica declarado e vazio, e isso é dito no artefato

O T0 de dívida (carry-trade: custo do passivo > retorno esperado) **não é
encodado**. O predicado existe em `suggestion_rules.rule_endividamento_perigoso`
e lê `endividamento.custo_medio_pct_aa`, campo **sem produtor** — o E5 hardcoda
`taxa_juros: None` e nunca lê a tabela `debts`.

**Tier que nunca dispara é pior que tier ausente:** ensina o leitor que "não
apareceu dívida cara" significa "não há dívida cara", que é falso-negativo
silencioso na única decisão em que as três metodologias convergem. Então o T0 é
declarado como **inerte por falta de produtor**, não implementado vazio.

### D5 — Não há helper compartilhado com `suggestion_rules` para endividamento

O painel prescreveu "extrair o critério para **um** helper puro compartilhado com
`suggestion_rules`". A medição derruba isso para o endividamento e o mantém, com
ressalva, para a reserva:

- **`suggestion_rules` não tem eixo de tier.** Tem `severity`
  (`info|warning|danger`), e o ranking vive em `suggestion_generator._SEVERITY_RANK`
  (severidade desc → valor desc, cap 8). Severidade e irreversibilidade são eixos
  **diferentes**; reusar um como se fosse o outro é o erro que esta ADR evita.
- **Os critérios de endividamento medem coisas diferentes**: o analyzer usa
  `ratios.taxa_endividamento_pct > 20`; a regra usa
  `endividamento.percentual_patrimonio > 30` **ou** carry-trade. Fundi-los seria
  mudar fórmula — fora de escopo por decisão da própria lane.
- **A gradação da reserva poderia ser compartilhada, mas o outro lado está
  dormente:** `rule_reserva_insuficiente` lê `reserva["meses_cobertura"]` e o
  produtor emite `cobertura_meses` (é o RV3-09, dono [[A40.l5]]). Compartilhar
  helper com um lado que nunca dispara produz gate verde-falso. **Decisão:** o
  critério fica no analyzer; a extração para helper comum é **condicionada** ao
  fechamento do RV3-09.

## Consequências

- **A ordem passa a ser propriedade do domínio, não da ordem de escrita.** Regra
  nova precisa declarar seu tier; sem entrada no mapa, o gate falha.
- **`build_default_tarefas` renumera** (`n = i+1`) quando a ordem muda. Relatórios
  já emitidos não são afetados — `Report.tasks_snapshot_json` congela o estado por
  relatório. O status registrado pelo dono **não** depende dessa ordem (vive em
  `Task.number`, DB; ver [[A40.l10]] §Pré-condição refutada).
- **O parecer lê `$.pontos_urgentes` raw**, então a ordem muda o *anchoring* do
  LLM. Nenhum item some — não há cap nesse bloco.
- **`clt_estavel` (6 meses) é dead config**: inalcançável por qualquer input, em
  `_DEFAULT_MESES_ALVO` e em `config/scoring.json`. Esta ADR **não** o remove
  (é cleanup de outra lane), mas registra que o valor 6 no config não descreve
  nenhum workspace.
- **`perfil_renda = "indefinido"`** não existe em `PERFIL_RENDA_LABELS` do card, e
  o tooltip imprime a string crua. Achado colateral, registrado com destino na lane.

## Alternativas consideradas

1. **Tier computado sobre a métrica** — rejeitada em D1: amarra a ordem a
   `taxa_endividamento_pct`, cuja unidade declarada e cálculo divergem.
2. **Alvo do perfil como gatilho** — rejeitada em D2: com piso real 12, alertaria
   "Imediato" a faixa que o mesmo payload chama de adequada.
3. **Campo `tier` no item do payload** — rejeitada: custo de schema + golden +
   snapshot para um valor derivável de `code`, e cria a possibilidade de item com
   `tier` inconsistente com o `code`.
4. **Ordenar em `partition_pontos_urgentes`** — rejeitada: ordenaria só os
   ranqueados e deixaria os retidos na ordem de escrita.
5. **Helper único com `suggestion_rules`** — rejeitada para endividamento (eixos e
   fórmulas diferentes) e **condicionada** para reserva (D5).

## Regra de domínio

[[RULE-ordem-do-plano-por-irreversibilidade]] — tiers, gradação e enforcers.
