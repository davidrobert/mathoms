---
id: A40.l25
type: lane
title: "Honestidade do cone de IF: precisão de exibição e sigma apresentado como premissa auditada"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l25-honestidade-do-cone-if
adrs:
  - "[[ADR-361]]"
  - "[[ADR-360]]"
  - "[[ADR-219]]"
  - "[[ADR-237]]"
depends_on: []
parallel_with:
  - "[[A40.l11]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l25 — `honestidade-do-cone-if`

> **Residual nomeado de duas ADRs, não achado novo.** O que sobra aqui é o que a
> [[ADR-360]] §Deferimento item 1 e a [[ADR-361]] (#1162) §Deferimento item 5
> deixaram explicitamente aberto depois de fecharem determinismo (#1156),
> sentinela de não-convergência (#1158) e censura de percentil (#1162). Sem lane,
> o residual vive só em §Deferimento de ADR — invisível ao `SPRINT_CURRENT`,
> portanto não pescável.
>
> Entra na A40 por casar com a **KR-E** (honestidade da recomendação): as duas
> faces são números que afirmam precisão ou procedência que não têm.

## Problema

Duas faces independentes, mesmo arquivo-alvo (`if_monte_carlo.py` + superfícies
de exibição), por isso uma lane só.

### 1. Precisão de exibição acima da precisão do estimador

O cone é reprodutível desde a [[ADR-360]], mas continua sendo **estimativa**: a
dispersão amostral medida é ~1,2% na série a `n = 50 000` (era 2,4% a 10k), e o
erro-padrão da proporção a `p ≈ 0,3` é ~0,21 pp. Hoje:

- **Probabilidade sai em inteiro** (`_fmt_probabilidade` no Python,
  `formatProbability` no TS) — "31%" contra "cerca de 30%". Ninguém planeja
  diferente entre 31% e 33%; a diferença é entre prometer precisão inexistente e
  comunicar magnitude. A [[ADR-361]] manteve o inteiro **de propósito**, porque
  mudar exige paridade Python↔TS (§Deferimento item 5 dela).
- **As séries do cone não estão declaradas fora do catálogo de citação.** Hoje
  elas não são citáveis por acidente (`_is_money_leaf` não casa lista de pares),
  não por decisão. Se alguém tornar a folha citável, o parecer pode escrever
  "R$ 11.037.269,90" sobre um número com ±1,2%.

### 2. `sigma_usado: 0.11` é constante de código apresentada como premissa

`_SIGMA_POR_PERFIL` (0,07 / 0,11 / 0,15) existe em `if_monte_carlo.py` e é **dead
code**: o adapter E5 nunca passa `sigma_anual` e nunca lê `premissas_economicas`
— apesar de a [[ADR-219]] D5 ter construído a tabela versionada exatamente para
isso. O payload publica `sigma_usado` ao lado de `premissas_economicas` no mesmo
bloco de auditoria, o que insinua procedência que o número não tem.

**Ordem de magnitude:** a largura do cone — sua mensagem inteira — vem desse
`sigma`. Erro de premissa domina o erro amostral que a [[ADR-360]] reduziu de
2,4% para 1,2%. Foi a [[ADR-237]] §E que adiou a parametrização por perfil; o
follow-up nunca aterrissou.

## Escopo

1. Probabilidade em **faixa de 5 pp** ("cerca de 30%") nas três superfícies que a
   publicam — card de S7, narrador determinístico, âncora do parecer — com
   paridade Python↔TS provada por teste. Mantém os guards `<1%` / `>99%`; 0 e 1
   literais seguem exatos.
2. Declarar as séries do cone **fora do catálogo de citação** por decisão
   explícita (não por acidente de predicado), com teste que falha se voltarem.
3. `sigma_anual` passa a vir de `premissas_economicas` quando houver premissa
   vigente; sem ela, o payload **declara o fallback** em vez de publicar a
   constante como se fosse auditada. `_SIGMA_POR_PERFIL` ou ganha consumidor ou
   é deletado — dead code que parece configuração é pior que ausência.

## Critério de aceite

- Nenhuma superfície imprime probabilidade do MC com precisão melhor que 5 pp;
  teste de paridade Python↔TS sobre a mesma entrada.
- `build_citation_catalog` não produz âncora para `caminho_p10/p50/p90`, com
  teste que falha se a folha virar citável.
- `sigma_usado` no payload vem acompanhado de procedência (`global` /
  `workspace_override` / `fallback_codigo`), no padrão de `fonte_origem` que a
  [[ADR-219]] já usa em `premissas_economicas.classes[]`.
- `_SIGMA_POR_PERFIL` tem consumidor **ou** não existe mais; gate de dead code
  não regride.
- Verificação renderizada (navegador ou `pdftotext`) da S7 — exigência do
  §Débito de método desta sprint: a lane não fecha sobre inferência de código.
- Se mudar número exibido: `mc_version` bumpa e a mudança entra na nota de
  recalibração — especificada e **autorizada** em [[ADR-360]] §Nota one-shot de
  recalibração (2026-08-05; fecha `OWNER-GATED-active.md` #45). Critério: nota
  in-section em S7 (não rodapé), gatilho por `mc_version` do report anterior do
  workspace (ausente/`"2.0"` ⇒ mostra; sem report anterior ⇒ nunca mostra), par
  ano-antigo→ano-novo explícito, direção sempre "mais conservador" declarada,
  causa em linguagem de cliente ("recalibração do modelo", nunca "sua carteira
  mudou").

## Fora de escopo

- Determinismo do cone — fechado pela [[ADR-360]] (#1156).
- Percentil censurado / truncamento de `int(np.percentile)` — fechados pela
  [[ADR-361]] (#1162).
- Sentinela 999 em `idade_meta_usada` — fechada em #1158.
- Aposentar de vez o ano do MC como manchete: a [[ADR-361]] já resolveu o caso
  em que o ano **não existe** (censura declarada). Reduzir o ano publicado a
  faixa quando ele existe é decisão editorial de S7 e depende de `product-designer`
  — não abre aqui sem brief.
