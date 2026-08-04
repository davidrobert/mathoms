---
id: A42.l12
type: lane
title: "Estado de extração do documento: predicado único e lista de stages derivada do registry"
sprint: A42
status: planned
priority: P2
branch_slug: a42-l12-predicado-unico-de-extracao
adrs:
  - "[[ADR-093]]"
  - "[[ADR-342]]"
depends_on:
  - "[[A42.l2]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p2
  - area/backend
  - area/pipeline
---

# A42.l12 — `predicado-unico-de-extracao` (RV4-15, RV4-19)

> **Origem:** [[PIPELINE-REVIEWS-active]] §r4 2026-08-04 — RV4-15, RV4-19 (ambos P2).
> **Nasceu do split da [[A42.l6]]** em 2026-08-04, por decisão do `senior-cto`: é
> agregado próprio, com forma de ADR, bloqueio e reversibilidade distintos da metade de
> política de store.

> **Depende de [[A42.l2]] — e a dependência é a razão de ser do split.** A l2 cria um
> **terceiro estado** de verificabilidade: extraiu, não escalou, e **não** está
> verificado. Se esta lane escrever o predicado contra o mundo de **dois** estados
> (escalado / não-escalado) e a l2 aterrissar depois, o predicado classifica "extraído
> mas não verificado" como extraído pleno e **acende o selo de qualidade sobre
> conservação não provada**. Seria o falso-verde da tese da sprint, produzido pela lane
> que existe para matá-lo — e é a **mesma forma** do achado que esta lane conserta (stub
> satisfaz predicado). Ordem invertida entrega pior que hoje.

## Problema

1. **Predicado de "extraído" que aceita stub.** Um consumidor considera o documento
   extraído **sem inspecionar o payload**, então o stub de escalação satisfaz a
   condição: limpa a marca de revisão e liga o selo. Os outros dois consumidores do
   mesmo fato **inspecionam** o payload. Três leitores, duas semânticas — e a divergência
   é silenciosa porque as três respostas são plausíveis isoladamente.
2. **Lista de stages de extração hardcoded.** O sincronizador conhece três stages e
   desconhece os criados depois de três ADRs: documentos efetivamente extraídos ficam
   marcados como "sem extrato", e o status é promovido incondicionalmente.

## Decisão

1. **Predicado único** `documento_foi_extraido(payload)`, extraído para um só lugar e
   consumido pelos três leitores. Um stub **nunca** satisfaz. O predicado tem de tratar
   o **terceiro estado** que a [[A42.l2]] cria: "extraído e não verificado" é extraído
   para fins de roteamento, mas **não** liga selo de qualidade — são duas perguntas
   diferentes que hoje compartilham um booleano.
2. **Derivar a lista de stages do registry**, mais teste de completude que **falhe na
   próxima ADR** que adicionar stage de extração. O teste é o ponto: sem ele o defeito
   volta na próxima adição, e essa já é a segunda vez.
3. **Onde o predicado mora é decisão de boundary.** Ele cruza `backend/` e `pipeline/`,
   e `pipeline/**` não importa framework — logo a implementação vai para o lado do
   domínio e o backend consome, não o inverso. Declarar na ADR, não improvisar no PR.

## Critério de aceite

- **Um único predicado no repo** — grep prova a unicidade; os três leitores chamam o
  mesmo.
- Teste com **stub explícito** ⇒ predicado falso, marca de revisão **não** limpa, selo
  **não** acende.
- Teste com payload no **terceiro estado** de verificabilidade (extraído, não escalado,
  não verificado) ⇒ roteamento prossegue **e** o selo não acende. **Sem este teste o
  split não vale** — é ele que prova que a ordem l2 → l12 foi respeitada.
- Teste de completude de stages que **falha** se um stage de extração novo não for
  registrado — verificado adicionando um stage fictício.
- Nenhum documento efetivamente extraído marcado como "sem extrato" no corpus.
