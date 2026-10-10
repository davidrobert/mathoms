---
id: ADR-446
type: adr
title: "Soft time limit encerra o run — nenhum stage começa depois do prazo"
status: Decidido
date: "2026-10-09"
relates_to:
  - "[[ADR-357]]"
  - "[[ADR-443]]"
  - "[[ADR-270]]"
  - "[[ADR-297]]"
  - "[[ADR-172]]"
  - "[[ADR-173]]"
  - "[[ADR-323]]"
  - "[[ADR-291]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 446"
  - "soft time limit"
  - "prazo do run"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/backend
---

# ADR-446 — Soft time limit encerra o run: nenhum stage começa depois do prazo

> Co-design 2026-10-08/09 com `sre-devops` (semântica de finalização e escopo) e
> `product-designer` (copy). Nasce `Decidido` porque o enforcement é teste no mesmo PR.
> Emenda a [[ADR-270]] (o retry do `LLMService` não retenta o fim de prazo), a
> [[ADR-443]] (o fim de prazo é a única exceção que atravessa o executor), a
> [[ADR-357]] (a parada é do decisor; o invariante paramétrico fica intacto) e corrige a
> [[ADR-297]] (`time_limit` não reentrega).

## Contexto

`run_pipeline_task` roda com `soft_time_limit=3000`, `time_limit=3600` e `acks_late`. O
soft limit existe para a task se encerrar a tempo; medido em 2026-10-08, ele não
encerrava nada:

1. `SoftTimeLimitExceeded` (billiard) é `Exception` pura. `orchestrator._run_stage` o
   achatava em `StageResult(success=False)`: stage obrigatório só parava com
   `stop_on_error`, e o degradável virava `degraded` e o próximo começava.
2. Dentro de chamada LLM o sinal chega embrulhado — `InstructorRetryException
   -[cause]-> RetryError -[cause]-> InternalServerError -[context]-> AnthropicError
   -[context]-> SoftTimeLimitExceeded`. O `LLMService.call` o classificava
   `provider_error` (retryable) e refazia a chamada; o instructor 1.15.1 retenta
   qualquer exceção por dentro do `create()`.
3. No `extract_with_llm` o sinal estoura no `as_completed` da thread principal, e o
   `shutdown(wait=True)` do pool fazia a chamada LLM de **todo** documento pendente
   antes de a exceção seguir. As threads do pool nunca recebem o sinal; com stream, o
   timeout do httpx vale por leitura e não limita uma geração em voo.
4. O hard limit mata o filho **sem** `on_failure`; o pai faz ack (`acks_on_failure_or_timeout`
   default) e não há redelivery. O run fica `running` até `detect_stuck_runs` flipá-lo
   para `heartbeat_timeout` 15–20 min depois — motivo errado, e o `LLMCallLog` adiado do
   stage em curso se perde ([[ADR-173]]).
5. O billiard conta o limite a partir do ACK do job e confere a cada 1s: o sinal chega
   em `ack + limite + [0, 1s]`.

## Decisão

1. **O prazo é objeto do run** (`pipeline/run_deadline.py::RunDeadline`), capturado na
   1ª linha da task a partir de `request.timelimit[1] or soft_time_limit` — o `3000`
   nunca é duplicado. Quem observa o sinal o **dispara** (`trip()`, visível a todas as
   threads); o relógio é rede de segurança e vence `SIGNAL_GRACE_S` (5s) **depois** do
   sinal. Vencendo antes, o run pararia e o post-processing abriria com o sinal
   pendente, que cairia dentro da criação do relatório.
2. **Regra de parada.** Prazo observado ⇒ nenhum stage começa, qualquer que seja a
   criticidade e o `stop_on_error`. Quem decide é o loop, como no cancel.
   `_run_stage` e `_run_stage_once` deixam o fim de prazo passar — é a única exceção ao
   achatamento da [[ADR-443]]. `pipeline/` reconhece o sinal por `sys.modules`, sem
   importar `celery`.
3. **Desfecho por evidência** ([[ADR-357]] §5). O stage interrompido e os que não
   rodaram viram não-entrega **pela própria criticidade**, com `reason_class=timeout` e
   `output_summary.time_limit` (`detection`, `not_started`).
   - Obrigatório ⇒ `failed`, `failure_reason=time_limit_exceeded`, `failed_at_stage`. Só
     o 1º obrigatório é gravado, e run que já falhou não ganha registro novo.
   - Só degradáveis e E5 alcançável ⇒ `partial_failure` sem campo de falha
     ([[ADR-357]] §3), com post-processing (relatório). Todos os degradáveis que não
     rodaram ficam `degraded`: o banner diz "o restante está completo" contando-os.
   - `needs_review` entregue vence o prazo. `failure_reason` nomeia a **1ª** falha do run.
4. **Choke-point LLM** (emenda [[ADR-270]], aditiva). Checagem pura na 1ª linha do
   `call`; no `except` do retry, fim de prazo relança `RunTimeLimitExceededError`
   tipado e dispara o prazo, sem classificar. Na função que o instructor chama a cada
   tentativa: recusa no início, read timeout capado ao tempo restante e checagem por
   chunk que fecha o stream. O prazo chega pelos hooks do run
   (`LLMBudgetService.run_deadline`), o canal que todo stage LLM já recebe.
5. **Thread principal não engole o fim de prazo**: o pool do E2-llm cancela os
   pendentes no aborto (`cancelling_thread_pool`), e os `except Exception: pass` de
   `pipeline/live_progress.py` relançam só o fim de prazo.
6. **Telemetria**: `ERROR mathoms.pipeline.run_time_limit_exceeded`, uma vez por run
   (`stage`, `detection`, `caused_failure`, `elapsed_s`, `budget_s`, `tier`). Ticket em
   toda ocorrência; ≥2 em 60 min é pipeline degradado (runbook `stuck_pipeline_runs`).
7. **Copy**: "O processamento atingiu o tempo limite"; "prazo" fica fora (já tem três
   sentidos no produto). No `FailedRunCard`, "Reprocessar a partir de" vira a ação
   primária para `time_limit_exceeded` e `heartbeat_timeout`.

**Exceção escopada a "o classificador não caminha a cadeia da exceção".** A regra
existe porque um bug levantado dentro de `except LLMError` seria lido como falha do
provedor. `is_time_limit` caminha `__cause__` **e** `__context__`, mas só casa o marcador
de prazo: o sinal só aparece nos elos `__context__` (item 2), e com ele disparado o prazo
venceu para o run inteiro — bug dentro do tratamento do sinal também é fim de prazo.

## Alternativas rejeitadas

- **Sempre `failed`.** Reproduz o incidente da [[ADR-357]] quando o parecer — último e
  mais longo stage — estoura com o E5 completo, e cria E5 sem `Report` que o
  `from_stage` não refaz.
- **Só relançar em `_run_stage`.** Inerte no caso dominante: LLM e pool (itens 2 e 3).
- **Margem preditiva** (não iniciar stage se faltarem N s). Falha cedo o run que
  terminaria e cria um segundo botão que deriva. O soft limit já é a margem.
- **`task_acks_on_failure_or_timeout=False`** para ganhar redelivery: re-executa 1h com
  orçamento novo e re-paga LLM a cada hora.
- **Handler de `task_failure` no processo pai**: dispara antes do kill, com o filho vivo
  e possivelmente segurando o write-lock.

## Consequências

- O run que estoura o tempo termina em segundos, com motivo — não ~25 min depois.
- Stage que engoliu o sinal e **entregou** segue com a disposição normal; a saída pode
  ter lacuna silenciosa (ex.: analisador que capturou o sinal). Residual aceito.
- O executor HTTP (shell Go) só para o loop do lado do Celery; o subprocess remoto
  segue até o timeout do shell (classe da [[ADR-323]]).

## §Deferimento (2026-10-09)

1. **Hard kill nomeado em ≤5 min.** `detect_stuck_runs` consulta
   `AsyncResult(celery_task_id)` dos runs `running`; `FAILURE` com `TimeLimitExceeded`
   ⇒ flip imediato para `time_limit_exceeded` (CAS em `status` + `celery_task_id`,
   stage_log `running`→`failed`). Dono: `sre-devops`. Retomar: no próximo PR que tocar o
   watchdog ([[ADR-172]]) ou na 1ª ocorrência de `heartbeat_timeout` com hard kill no
   log. `detection=hard_kill` > 0 depois disso mede o buraco que sobrar aqui.
2. **Prazo no contrato do shell Go** (`deadline_remaining_s`). Dono: `senior-cto`.
   Retomar antes de o shell virar o executor default.
3. **Durabilidade por documento do E2-llm**: o rollback descarta extração já paga.
   Dono: `data-engineer` + `prompt-engineer`. Retomar se `time_limit_exceeded`
   recorrer no mesmo workspace.

## Critério de aceite

- `backend/tests/test_soft_time_limit_encerra_run.py`, pela composição de produção: a
  matriz do item 3 (obrigatório × degradável, durante × fronteira), shell Go,
  `needs_review`, 1ª falha, evento único, `on_failure` e fiação na task.
- `tests/unit/pipeline/test_llm_run_deadline_guard.py`: as quatro guardas do item 4 e o
  E2-llm sem chamada ao provedor por documento pendente.
- Mutações provadas: cada guarda desligada reprova o seu teste (14 no total).
