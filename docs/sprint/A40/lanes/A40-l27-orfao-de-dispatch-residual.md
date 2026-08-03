---
id: A40.l27
type: lane
title: "Órfão de dispatch: varredura de beat, cancel de `resuming` e read path de failure_reason"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l27-orfao-de-dispatch-residual
adrs:
  - "[[ADR-359]]"
  - "[[ADR-172]]"
depends_on:
  - "[[A40.l19]]"
parallel_with:
  - "[[A40.l21]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/pipeline
---

# A40.l27 — `orfao-de-dispatch-residual`

> Onda 3 da A40. Fecha o recorte que a [[ADR-359]] deferiu com data (2026-08-03)
> ao mergear #1154 — **não é reabertura de decisão**: o vocabulário e os
> invariantes já estão `Decidido`. É o resíduo operacional que ficou sem dono.

## Por que existe uma lane e não só o §Deferimentos da ADR

A ADR-359 fechou a classe "run existe no DB e nenhum executor existe" pela porta
síncrona: dispatch falha alto, o caller compensa, e `_check_no_active_run` cura o
órfão no instante do bloqueio. O que **não** fechou é o resíduo assíncrono — e um
dos três itens é hoje o **único estado inescapável do sistema**, o que não
sobrevive como bullet no rodapé de uma ADR já `Decidido`.

## Problema

### 1. Órfão em `resuming` é inescapável (o item grave)

`resume_pipeline_run` flippa `needs_review` → `resuming` e só então despacha. Com
a ADR-359 a falha de dispatch **reverte** a pausa, então o caminho novo está
coberto. O resíduo é morte do processo entre o flip e o dispatch, que deixa:

| campo | valor | consequência |
| --- | --- | --- |
| `status` | `resuming` | fora do predicado de `fin.detect_stuck_runs` (filtra `running`) |
| `celery_task_id` | não-NULL (stale do run original) | invisível ao discriminante de órfão |
| `last_heartbeat_at` | não-NULL (stale) | idem |

Somado: `cancel_pipeline_run` **recusa** (aceita só `pending`/`running`) e
`is_run_active` retorna `True` para sempre. Nem o índice parcial
`ux_pipeline_runs_ws_active` nem `_check_no_active_run` cobrem `resuming` — então
o zumbi **não bloqueia, só nunca morre**. Nenhuma superfície o mata.

### 2. `fin.detect_stuck_runs` não vê pendente sem dono

O detector da [[ADR-172]] seleciona `status='running' AND last_heartbeat_at IS NOT
NULL AND last_heartbeat_at < cutoff`. Run que morreu entre o INSERT e o dispatch
está `pending` com heartbeat NULL — invisível. A cura síncrona da ADR-359 pega
esse caso **quando o usuário tenta disparar de novo**; a varredura o pega sem
depender de ação do usuário.

### 3. `failure_reason` é coluna write-only desde 2026-05

A [[ADR-172]] decidiu "UI consome `failure_reason` e mostra mensagem honesta". O
campo não está em `PipelineRunResponse` e `rg 'failure_reason|failureReason'
frontend/src` retorna zero. A ADR-359 acabou de adicionar **três** valores ao
vocabulário (`dispatch_failed`, `run_setup_failed`, `dispatch_unconfirmed`) — sem
read path, os três são legíveis só por SQL direto, e a distinção que eles compram
não chega a operador nem a usuário.

## Decisão (recortes já fixados pela ADR-359, não reabrir)

1. **Predicado ancorado no contrato de dispatch, não em `pending`.** Constante
   nomeada cobrindo os estados pré-dispatch não-terminais (`pending`,
   `resuming`), e `cancel_pipeline_run` passa a aceitar `resuming` no mesmo PR.
2. **Threshold próprio e curto** (`MATHOMS_UNDISPATCHED_RUN_THRESHOLD_MINUTES`,
   já existe com default 2min na cura síncrona). **Não reusar os 15min** da
   [[ADR-172]]: aquele número está calibrado para *stage genuinamente lento*,
   semântica que aqui não existe. Detecção worst-case = beat 300s + threshold.
3. **`dispatch_unconfirmed`** (já em `ALL_REASONS`) é o motivo da varredura —
   distinto de `dispatch_failed`, que é a compensação síncrona. Colapsar os dois
   destrói o sinal de postmortem.
4. **`failure_reason` em `PipelineRunResponse`** + `make update-openapi-snapshot`.
5. **`docs/reference/runbooks/stuck_pipeline_runs.md`**, cobrindo os três valores
   novos **+ `heartbeat_timeout`**, que também nunca ganhou runbook (a ADR-172
   escreveu "runbook trivial (just retry)" e não criou). A bifurcação é
   obrigatória: *broker fora ⇒ suba o broker, órfãos se curam no próximo trigger*
   vs. *worker vivo com fila funda ⇒ **não cancele**, espere*. Sem ela o operador
   cancela run legítimo.

## Por que depende da [[A40.l19]]

O tipo `pipelinerunstatus` no DB **não tem `resuming`** (tabela do §Problema da
l19). Um predicado que compara contra `resuming` funciona em SQLite e é quebra
armada em Postgres — a mesma classe que a l19 existe para pagar. Não consertar o
enum aqui: PR próprio, é dela.

**Amarra:** se a l19 for cortada ou escorregar de sprint, esta lane entrega os
itens 2–5 e **declara o item 1 como não-entregue** em vez de shipar predicado que
quebra no cutover.

## Coordenação com a [[A40.l21]]

O item 4 toca `schemas/pipeline.py` + os readers de status no frontend — as mesmas
superfícies que a l21 (leitores tolerantes a `partial_failure`). `parallel_with`,
não `depends_on`: se a l21 estiver em vôo, esta rebaseia sobre ela pelo critério
de arquivo-compartilhado da sprint.

## Critério de aceite

- Run enfileirado com sucesso (`celery_task_id` não-NULL) **nunca** é marcado
  `dispatch_unconfirmed` — é o invariante que a pré-geração do task_id
  ([[ADR-359]] §4) compra, e sem esse teste a varredura descarta trabalho
  legítimo em fila funda.
- Órfão em `resuming` é **cancelável** e é colhido pela varredura.
- `UPDATE` atômico filtrando o status esperado, com checagem de `rowcount`
  (padrão `_flip_stuck_run_atomic`) — nunca incondicional.
- `failure_reason` aparece no snapshot OpenAPI e tem ≥1 reader no frontend.
- Runbook referenciado no §12 Referências de
  [RUNBOOK.md](../../../reference/RUNBOOK.md) (o arquivo não tem frontmatter, logo
  não é wikilink-ável).
- Severidade de log `WARNING` com contagem no reaper, espelhando `_log_stuck_run`.
  **Nada em `CRITICAL`** — não há pager para acordar ([[ADR-359]] §7).

## Fora desta lane

- **`--inline` no CLI via `task_always_eager`** — deferimento 4 da [[ADR-359]].
  Sem demanda; foreground, operador quer o bloqueio.
- **Copy de `_ACTIVE_RUN_MESSAGE`** — escopo de `product-designer`. Exigência que
  fica: nenhuma mensagem manda o usuário esperar por algo que nunca vai acontecer.
- **Os outros 2 sites `mark-then-dispatch`** (`api/me.py`,
  `api/categorization_rules.py`): falham alto, mas não compensam a linha pendente.
  Mesma classe, severidade menor — débito nomeado no §Consequências da [[ADR-359]].
