---
id: A42.l27
type: lane
title: "O counter de lock mede o holder, que nunca espera: o write-lock do SQLite não tem instrumento, e o dev roda fora do envelope"
sprint: A42
status: open
priority: P1
branch_slug: a42-l27-write-lock-medido-no-engine
owner: sre-devops
depends_on: []
adrs: ["[[ADR-445]]", "[[ADR-256]]", "[[ADR-172]]", "[[ADR-359]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/backend, area/persistence, area/observability]
---

# A42.l27 — `write-lock-medido-no-engine`

> **Origem:** [[ADR-445]], co-design de `senior-cto` e `sre-devops` em 2026-10-08, sobre medição
> em dogfood. Executa a D2, a D3 e o H3 da D4.
>
> **Entrega parcial — os três PRs abaixo dizem o que pode sair já e o que espera.**
> - **PR1 (guardas):** livre agora.
> - **PR2 (instrumento):** só depois do merge do **#2081**, que também mexe em
>   `backend/app/core/database.py`. A baseline só vale se for medida depois do merge do
>   **#2072** e do **#2073**.
> - **PR3 (lineage):** espera o PR2, porque é ele que mede.
>
> Esta amarra cita os PRs pelo número, não a [[A42.l7]], porque essa lane continua `open` depois
> do #2072.

## O que está medido

A sessão do stage segura o write-lock do SQLite desde o 1º `store.write` até o commit
([[ADR-445]] §Contexto). No run `40d1af2a`, isso cobriu 74% do tempo de stage, e todas as 66
escritas de outras conexões dentro das janelas falharam. O instrumento que devia ver isso, o
`mathoms.db.lock_retry_count` ([[ADR-256]] §3), registrou **0** eventos no mesmo run em que
houve 18 `database is locked`. Ele cronometra o `_get` do próprio store, ou seja, o holder, que
nunca espera.

O dev roda fora do envelope seguro. O worker nativo e o smoke sobem com `--concurrency=2` sobre
SQLite, o que permite dois runs de workspaces diferentes no mesmo arquivo. Nenhum guarda
impede subir beat sobre SQLite, onde o heartbeat cega e o watchdog marcaria `failed` um run vivo.
O lock não tem resposta própria: vira 500 em texto puro.

## Escopo

**PR1 — guardas do envelope (D3)**

1. O beat recusa subir quando o dialect é `sqlite` (via `beat_init`).
2. Worker nativo e smoke sobre SQLite sobem com `--concurrency=1`, e a fila Celery fica isolada
   por worktree (o Redis 6379/0 é compartilhado).
3. Handler `503 db_busy` com `Retry-After`, no formato da [[ADR-359]], **só** para condição de
   lock. No SQLite, `no such column` também é `OperationalError` e tem de continuar 500.
4. Seção "envelope SQLite" em `docs/reference/runbooks/dev_environment.md` e no §11.4 do
   RUNBOOK, com estes pontos:
   - 1 worker, sem beat, 1 run por vez;
   - upload ou edição durante um run recebe 503;
   - run travado não é colhido, e um cancel não aterrissa dentro da janela: reinicie o worker
     nativo e só então cancele.

**PR2 — instrumento (D2)**

5. Listeners no engine, ao lado de `attach_sqlite_pragmas`: `mathoms.db.write_lock_held` e
   `mathoms.db.write_lock_wait`, com os campos e limiares da [[ADR-445]] D2. Os campos
   descrevem a forma (verbo, tabela, `uow`), nunca valores (mesma regra do #2081). O
   heartbeat se declara best-effort via `execution_options`.
6. Remover `_with_lock_telemetry` e o `lock_retry_count` do `DBArtifactStore`. Essa remoção é o
   único toque nesse arquivo: a [[A42.l6]] é dona do contrato do store.
7. Transformar o harness de lock do #2072 em gate de classe: o teste falha em qualquer
   `timed_out` que não seja best-effort.
8. Reescrever os gatilhos 1 e 3 da issue #446 sobre o instrumento. A decisão sobre D continua
   com o dono ([[ADR-445]] D5).

**PR3 — lineage (H3)**

9. Re-medir `materialize_lineage_edges` sem eco SQL. Se `held_ms` p100 passar de 1 s, montar as
   rows antes do DELETE e gravar com `executemany` Core **na mesma transação**. Lote com commit
   intermediário está proibido.

## Critério de aceite

1. Cada guarda do PR1 ganha um teste de regressão escrito antes do fix: beat sobre SQLite aborta
   (e sobre Postgres sobe); o 503 casa lock e não casa `no such column`.
2. **O instrumento enxerga a classe.** Num SQLite em arquivo, um harness com holder explícito
   (sessão que segura o lock durante um I/O falso) deve emitir:
   - `write_lock_held` com `held_ms` igual ou maior que o I/O falso;
   - `write_lock_wait` com `timed_out` para o writer de fora.
   Contrafactual: em `main`, o mesmo harness emite 0 `lock_retry_count`.
3. **Baseline publicada**, de um run de dogfood feito depois do #2072 e do #2073:
   - `held_ms` (p50, p95, máx.) e contagens de `waited`/`timed_out` por `uow`;
   - nenhum parâmetro nem valor nos campos.
4. Com o envelope ligado (concurrency 1, sem beat), esse run tem 0 `timed_out`
   não-best-effort.
5. O PR3 mostra o número antes e depois, medido sem eco, e o teste de DELETE+INSERT atômico
   continua verde.

## Fora do escopo

- Write-behind de artefatos (opção A): adiado com gatilho na [[ADR-445]] §Deferimentos.
- Commit que falha, CAS do watchdog e sessão de config: [[A42.l28]].
- Upload/reclassify e engine síncrono em handler `async`: [[A42.l29]].
