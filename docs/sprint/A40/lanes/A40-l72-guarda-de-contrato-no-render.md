---
id: A40.l72
type: lane
title: "Guarda de contrato no render: o relatório deixa de fechar 100% sobre payload que viola invariante"
sprint: A40
plan: PLAN-report-trust
status: blocked
priority: P1
branch_slug: a40-l72-guarda-de-contrato-no-render
owner: product-designer
adrs:
  - "[[ADR-145]]"
  - "[[ADR-357]]"
  - "[[ADR-370]]"
depends_on:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p1
  - area/frontend
---

# A40.l72 — `a40-l72-guarda-de-contrato-no-render`

> Item **7a** da Onda 7 do [[PLAN-deterministic-authority]] (RV6-16), aberto como
> lane do [[PLAN-report-trust]]. Nasce `blocked`: o supressor do ponto forte é
> alimentado **exclusivamente** pelo warning tipado da Onda 1, que a [[A40.l66]]
> cria — antes dele, a lane teria de re-derivar o defeito, que é a duplicação de
> fonte de verdade que este plano inteiro existe para matar.

## Problema

No r6 o relatório **fechou 100%** sobre um payload que violava invariante de
domínio. A camada de render não é cúmplice passiva — ela tem três superfícies
que deveriam ter falado e nenhuma falou:

**1. O banner de qualidade é cego a violação de contrato.**
`dataQualitySignals.ts:126-137` declara 5 sinais — `naoIdentificado`,
`needsReviewDocs`, `premissas`, `imoveisPendentes`, `parecerRetidos`. Nenhum é
"o payload contradiz o próprio contrato". Balde de patrimônio negativo
([[ADR-145]]) atravessa os 5 sem tocar em nada, `count` fica 0, e
`ReportDataQualityBanner.tsx:60-62` conclui:

```tsx
if (signals.count > 0) return <SignalsAlert signals={signals} />;
if (!mayAssertCleanQuality(runOutcome)) return null;
return <CleanBar />;
```

`CleanBar` — a afirmação positiva de qualidade — sobre payload inválido.

**2. O card verde celebra o defeito.** `pontos_fortes_analyzer.py:136-144` emite
"Endividamento Mínimo" quando `taxa_endividamento_pct < endividamento_max_pct`.
Com `dividas[]` colapsado pelo seam, a taxa despencou por construção e o ponto
forte foi emitido — impresso ao lado da descrição de alienação fiduciária a valor
cheio. O relatório elogiou o usuário pelo bug.

**3. `patrimonio.imoveis_nao_geradores` não tem superfície.** O único hit no
frontend é a declaração de tipo (`report-analysis.ts:47`). O campo é produzido e
nunca renderizado.

**Não é o `reportContractGuards.ts` que existe hoje.** Apesar do nome, aquele
módulo é de **leitura** (`readScoreData`, `readPremissasEconomicas`,
`readRealEstateData`…): converte `unknown` em shape tipado. Ele não avalia
invariante e não tem onde reportar violação. O guard desta lane é módulo próprio
— conferido contra `main` antes de abrir a lane, porque o 7c do rascunho já
morreu de ser no-op contra código que havia mudado (lição do RV6-20).

## Escopo

**7a-frontend — guard de runtime em módulo próprio.** Avalia invariantes de
contrato do payload ([[ADR-145]]: nenhum dos 7 baldes < 0) e produz **estado
`error`** no `ReportDataQualityBanner`.

Três regras não-negociáveis, cada uma com motivo mecânico:

1. **Não criar 5º banner** (§Anti-decisões do plano) — reusa o
   `ReportDataQualityBanner` com severidade nova; a enumeração de banners é da
   [[A40.l22]].
2. **Violação NÃO incrementa `signals.count`.** O docstring de
   `countActiveSignals` (`dataQualitySignals.ts:139-141`) diz por quê: o `count`
   tem de ser a soma **exata** das linhas que vão renderizar, senão sai
   "1 pendência" com `<ul>` vazia ([[A40.l18]] · [[ADR-357]]). Violação de
   contrato é estado do banner, não item da lista.
3. **`CleanBar` fica inalcançável sob violação** — some o
   `data-testid="data-quality-clean"`. Hoje a única guarda é
   `mayAssertCleanQuality(runOutcome)`, que olha o desfecho do run, não o
   conteúdo do payload: run que **completa com sucesso** sobre payload inválido
   passa por ela.

**7a-produtor — supressor do ponto forte, por fio único.** "Endividamento
Mínimo" (e qualquer ponto forte derivado de agregado sob suspeita) é suprimido
quando o warning tipado da Onda 1 está presente — **e só por isso**. A supressão
consome o warning; **não re-deriva** o defeito com um cross-check próprio
(imóvel financiado × dívida). Um segundo derivador seria uma segunda fonte de
verdade sobre o mesmo fato, divergindo no primeiro caso de borda — exatamente a
classe que o plano fecha. Esta é a razão do `depends_on`.

## Enforcement

WARN-first ([[ADR-357]]/[[ADR-358]]): o estado `error` **declara**; não esconde o
relatório nem bloqueia render. Taxa de disparo medida sobre os payloads r5+r6 e
declarada antes de qualquer aperto. Kill-switch de 1 env var.

**Coordenação declarada com a [[A40.l5]]:** ela é gate **estático** (tsc sobre o
contrato E5→frontend); este é guard de **runtime** sobre o valor. Escopos
disjuntos e complementares — nenhuma das duas absorve a outra, e quem pegar esta
confirma no pickup que o diff não toca a superfície da l5.

## Critério de aceite

- **Prova por mutação:** payload com um balde [[ADR-145]] negativo ⇒ **hoje**
  `CleanBar` renderiza e `signals.count === 0`; pós-fix, banner em `error`,
  `data-testid="data-quality-clean"` **ausente**, e `signals.count` **inalterado**
  (assert explícito sobre o count — sem ele o teste não distingue o fix correto
  do que reintroduz a `<ul>` vazia).
- Mutação do supressor: com o warning tipado presente, "Endividamento Mínimo"
  **não** é emitido; com ele ausente e a mesma taxa baixa, **é** emitido. Prova
  que a supressão está no fio único e não num cross-check paralelo.
- Teste de que o guard **não** dispara sobre payload válido (falso-positivo é o
  modo de falha que ensina o leitor a ignorar o banner).
- Estados novos nos **2 temas** com contraste medido (par `-on-tint`;
  `NAMED_PAIRS` quando o gate não alcança o par), e nos specs de a11y da seção.
- Baseline visual: `frontend-print-visual` é label-gated — rodar explicitamente,
  **inspecionar o PNG no runner Linux** antes de commitar.
- Rebaseline visual e rodada print+a11y **juntas** com o 7d-frontend, se ele
  estiver na mesma janela (mesmo trio
  `ReportDataQualityBanner`/`dataQualitySignals`/CleanBar — separar custa duas
  rodadas de baseline pelo mesmo efeito).

## Fora de escopo

- **Predicado da composição** (donut × tabela) → [[A40.l71]] (7e), que mergeia
  antes por ser enabler sem copy.
- Contagem `needs_review` server-side no payload + snapshot OpenAPI — passo (1)
  da sequência da Onda 7, PR de backend.
- Export/PDF com contagem indisponível mostrando "não apurado" → resíduo da
  [[A40.l22]] (RV6-22).
- Gate de PII do view-model (7f, RV6-17) → [[A40.l6]], dona do critério 4 da
  [[ADR-337]].
- Dar superfície a `patrimonio.imoveis_nao_geradores`: o campo entra no
  invariante 4a da Onda 1 ([[A40.l66]]); **renderizá-lo** é decisão de produto
  com copy própria, e não cabe numa lane de guard.
- Prosa do E5 com decimal en-US renderizada crua (mesmo achado RV6-16, perna
  distinta): é formatação no produtor, não guard de contrato.
