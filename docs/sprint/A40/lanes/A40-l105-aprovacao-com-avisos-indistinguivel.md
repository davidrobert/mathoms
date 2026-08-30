---
id: A40.l105
type: lane
title: "Aprovação-com-avisos é indistinguível de nunca-ter-pausado no desfecho do run, e é o desfecho que alimenta o banner de qualidade"
sprint: A40
status: open
priority: P2
branch_slug: a40-l105-aprovacao-com-avisos-indistinguivel
owner: sre-devops
depends_on: []
adrs: ["[[ADR-404]]"]
tags: [type/lane, sprint/a40, status/open, priority/p2, area/pipeline]
---

# A40.l105 — `aprovacao-com-avisos-indistinguivel`

> **Origem:** `PV12-03` da rodada unificada **U4** ([[PIPELINE-REVIEWS-active]] §r12).

## O defeito

`backend/app/services/report_run_outcome.py` — `_runs_with_degraded_stage` filtra
`status == 'degraded'` **e nada mais**. Um run que **pausou** em conferência, foi
aprovado com avisos e retomou sai `complete`, byte-idêntico a um run que nunca pausou.
No `U4`: 6 avisos, 0 erros, pausa aprovada — desfecho `complete`.

## O que o cético rebaixou, e por que a lane sobrevive assim mesmo

O enunciado original dizia que o banner **afirma limpo** no PDF que circula fora de casa.
**Isso é falso neste relatório:** a `CleanBar` só é alcançada depois de
`if (signals.count > 0) return <SignalsAlert/>`, e os **5** documentos em revisão deste
workspace entram nessa contagem — a barra "sem pendências" **não renderiza**.

**O defeito é do predicado, não do sintoma de hoje.** Ele depende de um segundo sinal
(documentos em revisão) para não mentir; num workspace com zero documentos pendentes e uma
pausa aprovada com avisos, a `CleanBar` renderiza.

## Critério de aceite

- [ ] O desfecho distingue `nunca pausou` de `pausou e foi aprovado com avisos`.
- [ ] **Controle positivo:** montar o banner com `runOutcome='complete'`, **zero**
      documentos em revisão e uma pausa aprovada com avisos. Se a `CleanBar` renderizar
      hoje, a severidade sobe; se algum outro sinal a segurar, permanece contingente e a
      lane declara isso.
