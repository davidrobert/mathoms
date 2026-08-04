---
id: A42.l10
type: lane
title: "Misclassificação na classificação amplifica o carrier de duplicação"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l10-misclassificacao-amplifica-carrier
adrs:
  - "[[ADR-081]]"
depends_on:
  - "[[A41.l2]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
  - area/backend
---

# A42.l10 — `misclassificacao-amplifica-carrier` (LC07)

> **Origem:** [[LEDGER-CERTIFY-active]] §r4 2026-08-04 — LC07 (Médio, P1).

> **Depende de [[A41.l2]]**, que é dona dos mesmos arquivos (o roteador de documentos
> e o classificador) e está `planned` numa sprint `candidate`. Isto é uma dependência
> sobre algo **não liberado** — legítima, mas precisa estar escrita para não virar
> dead-lock silencioso: enquanto a [[A41.l2]] não for promovida, esta lane não é
> pegável, mesmo que a [[A42]] seja promovida antes.

## Problema

Um documento de conta corrente foi classificado como outro tipo, foi escalado ao
caminho de LLM por consequência, e rendeu dezenas de lançamentos de conta corrente
por uma rota que não era a dele. Isso **amplifica** o carrier de duplicação
cross-documento: cria uma segunda perna da mesma conta, com proveniência diferente,
que o razão trata como conta distinta.

**A relação causal precisa ser dita com cuidado, e o §r4 já a mediu:** a
misclassificação **amplifica, não causa**. Com classificação perfeita a classe
**permanece**, porque o banco emite legitimamente extrato mensal e consolidado anual
da mesma conta. Quem fecha a classe é a [[A42.l5]] (chave period-free); esta lane
reduz a **incidência** e tem um ganho colateral relevante: classificação correta manda
o documento ao parser determinístico, e a perna de LLM **deixa de existir** — o que
elimina de origem o par nativo↔escalado que produz as ocorrências medidas hoje.

Por isso esta lane **não bloqueia** a [[A40.l2]] nem a [[A42.l5]], e nenhuma delas
depende dela.

## Decisão

1. **Corrigir o discriminador de tipo** para o layout que falhou, com fixture
   sintética do layout real (PII-zero).
2. **Não** compensar no razão. A tentação é filtrar a jusante; isso mascara a causa e
   deixa o defeito ativo para o próximo layout. A correção é na classificação.
3. **Coordenar com a [[A41.l2]]**: ela reescreve o caminho de chamada de LLM desses
   mesmos arquivos e move a classificação para o ponto único de chamada. Fazer esta
   lane depois evita reescrever o mesmo trecho duas vezes; se a [[A41.l2]] for
   `cancelled`, esta lane **absorve** a parte de roteamento necessária e declara a
   absorção.

## Critério de aceite

- Teste de regressão **antes** do fix, com fixture do layout que falhou: o documento é
  classificado no tipo correto e roteado ao parser determinístico.
- O documento deixa de ser escalado ao caminho de LLM — verificado por ausência de
  chamada no corpus, não por inspeção manual.
- **Nenhuma compensação a jusante:** grep prova que não há filtro novo no razão para
  cobrir este caso.
- Contagem de ocorrências de duplicação cross-documento **antes e depois**, declarada.
  A expectativa é redução de incidência, **não** zero — a classe latente permanece e é
  escopo da [[A42.l5]]. Reivindicar zero aqui seria colher o resultado de outra lane.
