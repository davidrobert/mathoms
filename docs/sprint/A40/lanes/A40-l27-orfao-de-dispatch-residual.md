---
id: A40.l27
type: lane
title: "Órfão de dispatch: varredura de beat, cancel de `resuming` e read path de failure_reason"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1265
ship_date: "2026-08-07"
priority: P1
branch_slug: a40-l27-orfao-de-dispatch-residual
adrs:
  - "[[ADR-359]]"
  - "[[ADR-172]]"
# satisfeito em #1241 (`resuming` no tipo `pipelinerunstatus`)
depends_on:
  - "[[A40.l19]]"
parallel_with:
  - "[[A40.l21]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
---

# A40.l27 — `orfao-de-dispatch-residual`

> ✅ **Entregue em 2 PRs, 2026-08-07:** `f394068d` (#1263, varredura + cancel de
> `resuming`), `cd6fde12` (#1265, read path + [[runbook-stuck-pipeline-runs]]).
>
> **Um verde-falso no §Critério de aceite, achado pelo co-design `sre-devops`.** A guarda
> de status do cancel é **duplicada** — `cancel_run.py` (use case) e `pipeline_service.py`
> (service) — e esta lane nomeia só a segunda. Corrigir uma faria o teste de service passar
> **com o endpoint ainda respondendo 409**. As duas passaram a ler a mesma constante, e o
> teste do critério vai pelo **endpoint**.
>
> **Três premissas corrigidas na execução.** (1) O relógio de `resuming` **não pode** ser
> `started_at` (é do run original, horas antes): o predicado seria sempre verdadeiro e
> mataria resume legítimo lento em `_prepare_run_context` — a alternativa que a [[ADR-359]]
> §Alternativas rejeitou nominalmente. `_flip_run_to_resuming` passou a stampar
> `last_heartbeat_at` como relógio de entrada-no-estado. (2) `paused_at_stage` deixou de ser
> zerado no flip: era a única cópia durável do ponto de pausa, e zerá-la tornava
> `_stages_after_paused(None)` → `[]` → `_mark_run_completed`, i.e. **run reportando sucesso
> sem executar nada**. (3) `_check_no_active_run` e `_heal_undispatched_run` também
> filtravam só `pending`, então trigger durante um resume **legítimo** criava um segundo
> executor no mesmo workspace.
>
> **A premissa de detecção do §Decisão item 2 é falsa sob fila funda.** Não há `task_routes`:
> o reaper compete com `pipeline.run` (`task_time_limit=3600`) na fila `celery` com
> `worker_concurrency=2`. Dois runs longos o famintam por ~1h, então "beat 300s + threshold"
> é o **melhor** caso, não o pior. Mitigado com `expires: 240`; o runbook declara o limite e
> dá o caminho SQL manual. Fila dedicada é lane própria.
>
> **A mutação para `UPDATE` incondicional passou** com todos os testes da primeira rodada —
> eles *nomeavam* a atomicidade sem exercitá-la. Daí os 2 testes de corrida (dispatcher grava
> o id primeiro; worker avança o status primeiro).
>
> **Débito nomeado, sem dono:** `_is_cancelled` aborta só em `cancelled` e `_finalize_run`
> só early-returna em `cancelled`/`needs_review`, então o worker vivo **sobrescreve** o
> `failed` do reaper de volta para `completed`, e o "Reprocessar" do usuário cria um
> **segundo executor** escrevendo artefatos. Hoje coberto só por procedimento humano no
> §5 do runbook — merece deferimento datado com dono.
>
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
- [[runbook-stuck-pipeline-runs]] referenciado no §12 Referências de
  [RUNBOOK.md](../../../reference/RUNBOOK.md) (esse **hub** não tem frontmatter, logo
  não é wikilink-ável; o runbook novo tem, e é).
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
