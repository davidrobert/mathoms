---
id: ADR-445
type: adr
title: "Transação de escrita não atravessa I/O lento: o write-lock é medido no engine, o SQLite de dev vira envelope guardado, e o write-behind de artefatos fica adiado com gatilho"
status: Proposto
phase: A42.l27
date: "2026-10-08"
relates_to:
  - "[[ADR-256]]"
  - "[[ADR-173]]"
  - "[[ADR-172]]"
  - "[[ADR-111]]"
  - "[[ADR-241]]"
  - "[[ADR-357]]"
  - "[[ADR-291]]"
  - "[[ADR-359]]"
  - "[[ADR-356]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 445"
  - "envelope SQLite"
  - "write-lock medido no engine"
tags:
  - type/adr
  - status/proposto
  - area/persistence
  - area/pipeline
  - area/backend
---

# ADR-445 — Transação de escrita não atravessa I/O lento

> Co-design 2026-10-08: `senior-cto` (forma, e decisão final depois de uma rodada de escalação
> anti-loop) e `sre-devops` (operação, observabilidade, envelope de dev). Na 1ª rodada o
> `senior-cto` recomendou o write-behind (opção A) já. O `sre-devops` divergiu, e o `senior-cto`
> mudou de posição: prod já é Postgres, e o risco de A recairia no caminho de escrita mais quente
> de prod. Medição na §Contexto; o inventário estático foi conferido à mão onde citado.

## Contexto

A [[ADR-256]] fez do stage a unidade de trabalho, com uma sessão por stage e commit único no fim.
O 1º `store.write` de chave nova adquire o write-lock (`_mark_superseded_previous` emite UPDATE
imediato, depois de autoflushar o INSERT), e o lock fica até esse commit. O SQLite tem um writer
por arquivo, e o WAL só libera leitura. Qualquer outra conexão que escreva na janela espera o
`busy_timeout` (30 s) e cai em `database is locked`. Usar outro engine não resolve. É a 4ª
ocorrência do mecanismo: as duas que originaram a [[ADR-256]], o `llm_call_log` da [[A42.l7]] e o
heartbeat (PR #2073).

**Medição (dogfood local, só leitura).** Fontes: o DB de dogfood em `mode=ro` (130 runs, de
2026-05-15 a 09-01, 1 workspace), o `worker.log` com eco SQL do run `40d1af2a` inteiro e o
`api.log` de 08-29 a 09-01. Da extração saíram só verbo, tabela e timestamp; nenhum parâmetro,
texto ou nome. A janela foi medida de dois jeitos: o limite inferior pelo DB (do 1º artefato do
stage ao commit) dá 465,97 s no `extract_baseline` desse run, e o eco SQL dá 466,0 s.

| holder | medido |
|---|---|
| H1 sessão do stage | 1003 s de 1363 s de stage sob lock (74%). Nos 7 stages longos, o 1º DML é `INSERT pipeline_artifacts`, e só há DML de `pipeline_artifacts`. Em 120 runs, a maior janela por run tem p50 202 s, p90 470 s e máx. 1599 s. O `extract_baseline` passou de 30 s em 86 de 86 execuções. O `extract_statements` não chama LLM e segura 186 de 187 s |
| H2 request de upload/reclassify | estático: `repo.add(flush=True)` emite o INSERT; a classificação vem depois, síncrona, e pode chamar LLM; o commit só sai no fim do lote |
| H3 `materialize_lineage_edges` | 28 s para 33.365 INSERTs numa transação, medido **com o eco SQL ligado**, que infla o tempo. O DELETE abre o lock antes de montar as rows |

| vítima | medido | estado |
|---|---|---|
| `llm_call_log` | 18 de 24 rows perdidas no run. 9 esperaram 30,5 s cada (~4,6 min de stall); as outras 9 falharam em 0,2 s, porque o PRAGMA do heartbeat vazou pelo pool | fix em voo: #2072 ([[ADR-173]] §Emenda 2026-10-08) |
| heartbeat no meio do stage | 48 de 92 escritas em `pipeline_runs` falharam. O maior intervalo entre batidas que aterrissaram foi de 466 s, a própria janela | cego, mas sem consumidor: o dev nativo não sobe beat, e os compose de dev e prod sobem beat com Postgres |
| watchdog | estático: `_flip_stuck_run_atomic` filtra só `status`. Um flip que esperou o lock aterrissa depois do commit do stage | latente em SQLite; o furo de CAS existe em qualquer engine |
| API (GET sensível grava `audit_logs` antes do handler; edição, review, cancel) | 0 escritas dentro das 502 janelas acima de 1 s dos 120 runs. 0 `database is locked` e 0 respostas 5xx no `api.log`. 7 cancels, nenhum dentro de janela | latente: no dogfood há 1 usuário, que espera o run terminar |
| pipeline, vítima de H2 | 171 uploads, nenhum durante run | latente: o orquestrador levanta exceção no lock e derruba o run |
| run concorrente de outro workspace | 1 workspace, 0 stages sobrepostos | latente: o worker nativo e o smoke sobem com `--concurrency=2` |

**O instrumento era cego.** O `mathoms.db.lock_retry_count` ([[ADR-256]] §3) cronometra o `_get`
do próprio store, ou seja, o holder, que nunca espera. Ele registrou **0** eventos no run que teve
18 `database is locked`. Os gatilhos 1 e 3 da issue #446 (migrar para Postgres) leem esse
counter, então nunca dispararam para esta classe.

## Decisão

**D1 — Invariante, em qualquer engine.** Nenhuma transação de escrita fica aberta durante I/O
lento (LLM, parse, rede), e nenhuma acumula volume. Os holders conhecidos são H1, H2 e H3. Todo
holder novo é medido pelo instrumento da D2, nunca por lint: a ordem entre DML e I/O lento é
um sinal dinâmico, não léxico.

**D2 — O lock é medido no engine, não no call-site.** Os listeners entram junto do
`attach_sqlite_pragmas` e cobrem os executores, a API, o console ops, o beat e os testes.

- **Holder**, evento `mathoms.db.write_lock_held`: o 1º DML marca `conn.info` (estado por
  conexão, compatível com a [[ADR-111]]); fecha em commit, rollback ou reset. Campos:
  `held_ms`, `ratio_busy_timeout`, `first_dml` (verbo e tabela, nunca valor), `tables`,
  `outcome`, `dialect`, `uow` (stage, rota, task ou passo pós-run), `run_id`, `workspace_id`.
  INFO a partir de 1 s. WARNING para request da API com 5 s ou mais (qualquer engine) e para
  worker fora de stage com 15 s ou mais (SQLite). O stage fica em INFO, com o `ratio`.
- **Vítima**, evento `mathoms.db.write_lock_wait`, via `handle_error` e cronômetro de DML. Casa
  só condição de lock (`database is locked`, `55P03`, timeout de pool). `timed_out` emite
  WARNING, ou INFO quando o call-site se declara best-effort por `execution_options` (heartbeat).
- O `lock_retry_count` sai no mesmo PR. Os gatilhos 1 e 3 da #446 passam a ler `timed_out`
  não-best-effort e o p95 de `held_ms` e `waited_ms`. O harness de lock do #2072 vira gate de
  classe: falha em qualquer `timed_out` não-best-effort.

**D3 — SQLite é envelope de dev, guardado por código, não por doc.**

- O beat recusa subir sobre SQLite (§Emenda 2026-10-08 da [[ADR-172]]).
- Em SQLite, o worker nativo e o smoke sobem com `--concurrency=1` e fila Celery isolada por
  worktree (o Redis 6379/0 é compartilhado).
- Condição de lock vira 503 `db_busy` com `Retry-After`, no formato da [[ADR-359]].
- O RUNBOOK ganha a seção "envelope SQLite".

**D4 — Defeitos que valem em qualquer engine são obrigatórios agora**, sem esperar o resto:

- Commit que falha nos 3 ramos do loop vira `failed`, com motivo nomeado e sem o marcador de
  conclusão da [[A37.l12]]. Hoje o ramo de sucesso grava `completed`, porque o desfecho é
  calculado antes do commit, e os ramos degrade e needs_review engolem a exceção.
- O CAS do watchdog passa a pôr `last_heartbeat_at < cutoff` no WHERE do flip.
- A sessão de config do run passa a fazer rollback quando o flush dos resolvers falha; o docstring
  dela diz "read-only", e ela escreve.
- Upload e reclassify: a row `Document` é commitada antes da classificação (o status
  `classifying` já existe), e nenhum I/O bloqueante roda no event loop. O mesmo vale para o engine
  síncrono dentro de handler `async` (cancel, trigger, resume, regras).
- Lineage (H3): primeiro re-medir sem eco. Se passar de 1 s, as rows passam a ser montadas antes
  do DELETE, com `executemany` Core na **mesma** transação. Lote com commit intermediário fica
  proibido, porque quebra o DELETE+INSERT atômico.

**D5 — Dogfood em Postgres (opção D) é decisão pendente do dono** e não depende de A. Ela fecha a
classe e dá ao dogfood os defeitos que só aparecem no PG (cadeia de migration, coluna curta,
`VARCHAR(4)`), aos quais hoje ele é cego. A #446 é reescrita para dogfood e smoke, porque a
premissa "prod em SQLite" venceu.

**D6 — O adiamento da [[A42.l7]] fica**: sem A, ele é a defesa do dogfood em SQLite. Sai quando
D aterrissar.

## Alternativas rejeitadas

- **B — commit por documento.** Quebra a atomicidade da [[ADR-256]] e o fallback da
  [[ADR-241]]: o parcial de um run que falhou viraria o "latest". Exigiria marcador de conclusão
  e mudança de schema.
- **Heartbeat no Redis.** Muda o contrato da [[ADR-172]] em prod, e uma eviction `allkeys-lru`
  viraria falso "travado". Tudo isso para curar uma cegueira que não tem consumidor.
- **`locked` como erro retentável.** Re-executa um stage LLM contra uma janela com p50 de 200 s.
- **Estender o lint da [[ADR-256]].** O sinal é dinâmico; o gate é o instrumento da D2.

## Deferimentos datados (2026-10-08)

- **A — write-behind de artefatos.** Dono: `senior-cto`.
  - **Forma já decidida:**
    - buffer interno ao `DBArtifactStore`, sempre ligado nos dois engines, num módulo próprio;
    - não é decorator, porque há 6 `isinstance(store, DBArtifactStore)` em E3/E4 que falhariam
      calados;
    - flush no `before_commit`, mais um `flush_pending()` público;
    - overlay de `read`/`exists`/`list_keys` consultado antes do base-run e do fallback da
      [[ADR-241]];
    - DML de domínio segue a regra "extrair → persistir".
  - **Gatilho:** volta só se o dono **recusar D** e houver pelo menos 1 `timed_out`
    não-best-effort com `uow=stage` em 30 dias. Se D for aceita, A é arquivada.
  - **Aceite obrigatório, se voltar:**
    - guarda `do_orm_execute` contra SELECT direto de `PipelineArtifact` com buffer pendente;
    - 0 `workspace_fallback` de chave gravada no próprio run;
    - artefatos idênticos por hash, antes e depois;
    - drill de SIGKILL no meio do LLM e no meio do commit, em SQLite e em PG;
    - job PG obrigatório;
    - kill switch por env, com dono e remoção em até 30 dias;
    - holder explícito no harness.
- **Reconciliação apólice↔CRLV do `extract_comprovantes_bens`**: hoje depende da ordem dos
  documentos. Dono: `data-engineer`, sem prazo; retomar quando a lane tocar o stage.

**Roteado, sem lane nova:** `store.write` de até 8 threads sobre a mesma `Session`
(`extract_with_llm`) vai para a branch `agent/e2-llm-store-write-main-thread/20261008-2056`,
que já tem o fix commitado; o holder explícito no harness do #2072 vai para a [[A42.l7]].

## Consequências

- Lanes: [[A42.l27]] (D2, D3 e o H3 da D4), [[A42.l28]] (commit, CAS e sessão de config da D4) e
  [[A42.l29]] (upload/reclassify e handler síncrono da D4).
- Ordem: #2072 → #2073 → instrumento (PR próprio, para ter baseline) e guardas → decisão de D.
- Emendas datadas: a [[ADR-256]] §3 é aposentada; a [[ADR-172]] passa a proibir beat sobre SQLite
  e a exigir CAS por cutoff.
- O que fica, enquanto D não aterrissa: no SQLite, o stage longo segue cegando o heartbeat e
  bloqueando escrita alheia por até a janela inteira. Isso fica medido (D2), guardado (D3) e
  com o dono para decidir (D5).
