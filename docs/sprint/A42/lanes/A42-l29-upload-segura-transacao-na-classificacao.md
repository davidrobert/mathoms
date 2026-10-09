---
id: A42.l29
type: lane
title: "Upload segura a transação de escrita durante a classificação, que pode chamar LLM, e roda síncrono no event loop"
sprint: A42
status: open
priority: P1
branch_slug: a42-l29-upload-segura-transacao-na-classificacao
owner: senior-cto
depends_on: []
adrs: ["[[ADR-445]]", "[[ADR-081]]", "[[ADR-359]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/backend, area/persistence]
---

# A42.l29 — `upload-segura-transacao-na-classificacao`

> **Origem:** [[ADR-445]] D4, holder H2. Forma decidida pelo `senior-cto` no co-design de
> 2026-10-08. Para o `sre-devops`, é P1 também em Postgres.

## O que está lido no código

- **`POST /documents/upload`** processa os arquivos um por um, na mesma transação:
  1. `repo.add(flush=True)` emite o INSERT do documento, e o lock de escrita começa aí;
  2. `_apply_processing_result` → `process_uploaded_document` faz unlock e classificação
     ([[ADR-081]]). A chamada é **síncrona**, roda dentro do handler `async` e pode chamar
     o LLM;
  3. o commit só sai no fim do lote.
- **No SQLite, o pipeline vira vítima.** Durante esse tempo, as escritas do orquestrador
  levantam exceção no lock e derrubam o run (`_record_stage_running`, `_record_stage_result`,
  `_commit_run_outcome`).
- **No Postgres**, a chamada síncrona congela o worker uvicorn, e uma conexão do pool fica
  `idle in transaction` enquanto o LLM responde.
- **Mesmo padrão, a verificar:**
  - `POST /reclassify` (`reclassify_workspace_documents`), apontado pelo inventário estático;
  - engine síncrono dentro de handler `async`: cancel (`cancel_pipeline_run`, conferido),
    trigger (escrita do task-id), resume e regras de categorização. Cada um trava o event loop
    da API inteira por até um `busy_timeout`.
- **Dogfood:** 171 uploads, **0** durante um run. O defeito está latente.

## Decisão de forma (`senior-cto`, 2026-10-08)

- A row `Document` é **commitada antes** da classificação, usando o status `classifying` que
  já existe.
- A classificação roda **fora do event loop**, e o resultado é aplicado numa transação curta.
- Chamadas ao engine síncrono dentro de handler `async` vão para threadpool, ou passam a usar o
  engine async.
- Revisão do `data-engineer`, antes do PR:
  - efeito no dedup fuzzy, que hoje roda depois do INSERT, na mesma transação;
  - `possible_duplicate_of_id`;
  - semântica de lote parcial: alguns documentos commitados, outros não.

## Critério de aceite

1. **Teste de regressão escrito antes do fix**, com SQLite em arquivo e classificação falsa
   lenta. Durante o upload:
   - uma escrita de outra conexão não espera nem falha;
   - outra request é servida, o que prova que o event loop segue responsivo.

   O teste tem de falhar em `main`.
2. Lote parcial com semântica escrita e testada: o documento já commitado e não classificado
   fica `classifying`, e um retry não duplica a row.
3. Um cancel feito durante o lock de um stage não trava o event loop. Ele aterrissa, ou devolve
   `503 db_busy` pelo handler da [[A42.l27]].
4. O reclassify passa a seguir a mesma regra, ou fica provado, com o arquivo e a linha, que já
   seguia.

## Fora do escopo

- O lock que a sessão do stage segura (H1): instrumento e guardas na [[A42.l27]]. O
  write-behind está adiado na [[ADR-445]] §Deferimentos.
