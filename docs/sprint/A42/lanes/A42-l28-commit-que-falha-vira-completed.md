---
id: A42.l28
type: lane
title: "Commit de stage que falha grava `completed`, o flip do watchdog não reconfere a batida e a sessão de config fica envenenada: o estado do run mente em qualquer engine"
sprint: A42
status: open
priority: P1
branch_slug: a42-l28-commit-que-falha-vira-completed
owner: senior-cto
depends_on: []
adrs: ["[[ADR-445]]", "[[ADR-256]]", "[[ADR-357]]", "[[ADR-172]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/backend, area/pipeline]
---

# A42.l28 — `commit-que-falha-vira-completed`

> **Origem:** [[ADR-445]] D4, do co-design de 2026-10-08. O `senior-cto` classificou os três
> itens como defeitos que valem em qualquer engine e entram agora, sem esperar o resto da
> [[ADR-445]].
>
> **Amarra de entrega parcial:**
> - **Item 2 (CAS do watchdog):** livre agora.
> - **Itens 1 e 3:** o **#2072**, que reescreve os helpers de commit de `pipeline_task.py` e
>   mexe em `run_context_factory.py`, mergeou em 2026-10-08 (`b16d38de`). Parta dele.
> - Os itens 1 e 3 ainda esperam a branch `agent/stage-retry-inerte-inprocess/20261008-1630`,
>   que mexe em `pipeline_task.py`: ou ela mergeia antes, ou a ordem é combinada com a sessão
>   dona.

## O que está lido no código

1. **Commit que falha vira sucesso.** O `_execute_stages_loop` calcula o desfecho **antes** do
   commit. Quando `_commit_and_close_artifact_session` levanta exceção, os três ramos erram:
   - **sucesso:** grava o stage log com esse desfecho (`completed`). O run fica com
     `has_failure`, mas o stage log diz que o stage acabou. O marcador da [[A37.l12]]
     (`_STAGE_DONE_STATUSES`) declara no próprio comentário que *"marker ⇒ artefatos
     persistidos"*, e nesse caminho a premissa é falsa: o redelivery **pula** um stage cujos
     artefatos não existem;
   - **degrade:** o ramo engole a exceção e grava `degraded`, que também entra no marcador. A
     promessa da [[ADR-357]] §6 ("artefatos persistidos") fica falsa;
   - **needs_review:** o ramo engole a exceção e pausa o run pedindo revisão de artefato que
     não foi gravado.

   Hoje o commit quase nunca falha, porque a DML já rodou dentro do stage. Ele falha por lock do
   SQLite com outro holder ([[ADR-445]] H2, ou um run concorrente) e por conflito ou constraint
   no Postgres.
2. **CAS do watchdog sem batida.** O UPDATE de `_flip_stuck_run_atomic` filtra só `id` e
   `status=running`. O filtro `last_heartbeat_at < cutoff` existe apenas no SELECT de
   candidatos. Por isso um flip que perdeu a corrida para uma batida, ou que esperou um lock,
   aterrissa sobre um run que acabou de provar que está vivo (§Emenda 2026-10-08 da
   [[ADR-172]]).
3. **A sessão de config escreve.** O docstring de `run_context_factory` diz *"read-only durante o
   stage (nunca commitar)"*. Mesmo assim, `DBPropertyIdentityResolver` faz flush e commit por
   ela no E1.5c, e o writer de supersessão também grava. Se um flush falha, a sessão fica
   pedindo rollback, e ninguém faz. A partir daí, toda leitura de `ctx.config_store` falha até o
   fim do run.

## Critério de aceite

1. **Teste de regressão antes do fix, um por ramo.** Com o commit injetado para falhar, cada um
   dos três ramos tem de:
   - marcar o stage como `failed`, com motivo nomeado no vocabulário de falha;
   - não deixar marcador de conclusão;
   - fazer o redelivery **re-executar** o stage.

   Em `main`, o teste do ramo de sucesso tem de falhar.
2. **Espelhos do helper de commit:** `artifact_session_factory`, a `artifact_session` do
   pipeline-service e o `cli_run_stage` seguem a mesma regra onde decidem o desfecho.
3. **CAS:** uma batida que aterrissa entre o SELECT e o UPDATE impede o flip. O teste roda com
   engine real.
4. **Sessão de config:** quando o flush de um resolver falha, a sessão faz rollback, a próxima
   leitura de config no mesmo run funciona, e o docstring passa a descrever o que a sessão faz.
5. **Motivo novo:** o motivo de falha aparece na UI pelo contrato de mensagens do frontend.
   Coordenar com a branch `agent/engine-hide-parameters/20261008-1803`, que mexe nesse contrato.

## Fora do escopo

- Instrumento e guardas do SQLite: [[A42.l27]].
- Upload/reclassify: [[A42.l29]].
