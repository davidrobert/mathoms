---
id: ADR-269
type: adr
title: "Dedup de TaskSuggestion via soft-supersede + dedup_key normalizado"
status: Proposto
phase: A17.task-suggestion-dedup
date: "2026-05-23"
relates_to:
  - "[[ADR-074]]"
  - "[[ADR-082]]"
  - "[[ADR-153]]"
  - "[[ADR-186]]"
  - "[[ADR-188]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 266"
  - "Task suggestion dedup"
  - "Supersede e5n_llm"
tags:
  - area/backend
  - area/pipeline
  - phase/a17
  - status/proposto
  - type/adr
---

# ADR-269 — Dedup de TaskSuggestion via soft-supersede + dedup_key normalizado

**Status:** Proposto · **Data:** 2026-05-23 · **Relaciona** [[ADR-074]] (TaskSuggestion queue), [[ADR-082]] (pipeline_artifacts versionado por run_id), [[ADR-153]] (Suggestion aggregate dedup), [[ADR-186]]/[[ADR-188]] (Categorization Learning Loop — padrão de override sticky).

## Contexto

Quando o usuário clica "Processar documentos" em `/pipeline`, o dispatcher Celery `backend/app/tasks/pipeline_task.py::_persist_llm_suggestions` lê o artefato E5N (`stage='analyze_finances'`, chave `tarefas_sugeridas` no payload) e persiste N rows em `task_suggestions` com `source='e5n_llm'`, `source_run_id=<run_id>`.

Proteção atual contra duplicação (`backend/app/tasks/pipeline_task.py` linhas 128-167):

```python
existing = db.execute(
    select(TaskSuggestion).where(
        TaskSuggestion.workspace_id == ws_id,
        TaskSuggestion.source_run_id == run_id,
    )
).scalars().first()
if existing:
    return
```

Essa proteção **só protege retry da mesma Celery task** (mesmo `run_id`). **Não protege clicks repetidos do botão** — cada click cria `run_id` novo e o select por `(workspace_id, source_run_id)` não encontra nada, então re-insere todas as N sugestões. Usuário clicando 3× = 3× as mesmas sugestões pendentes na inbox.

Race cross-run *não* é o problema: `ux_pipeline_runs_ws_active` (partial unique index, migração `i4c5d6e7f8a9`) já serializa runs ativos no mesmo workspace. O problema é serial: Run 1 termina → grava 30 pending; usuário clica de novo (válido); Run 2 grava mais 30; UI mostra 60.

**Caso real** observado em sessão de design (2026-05-23): comparação com [[ADR-153]] `Suggestion` aggregate (mesmo arquivo, função `_persist_aggregate_suggestions`) mostra que aquele **resolve** o mesmo problema via `dedup_key` + `DISMISS_RESPECT_WINDOW_DAYS=90`. `TaskSuggestion` não tem campo equivalente.

## Decisão

Introduzir **dedup_key normalizado + soft-supersede** em `task_suggestions`. Cada `TaskSuggestion` ganha:

1. `dedup_key: str(64)` — `sha256(f"{source}:{normalize(title)}:{category}")[:64]`, com `normalize = lower + strip + colapsar_whitespace`. **NÃO inclui `description`** (LLM varia o rationale entre runs). Inclui `source` no hash para evitar colisão entre fontes futuras (`cross_validation`, `system_rule`).
2. `superseded_at: datetime | NULL` — quando a row foi marcada como obsoleta.
3. `superseded_by_run_id: str(36) | NULL` — qual `pipeline_run_id` produziu o "vencedor" que a tornou obsoleta.

Valor novo no enum aplicação `VALID_SUGGESTION_STATUSES`: `"superseded"`.

Algoritmo do dispatcher, ao processar artefato E5N do `run_id` novo:

```
drafts := [normalize(s) for s in tarefas_sugeridas]   # cada draft tem dedup_key
new_keys := {d.dedup_key for d in drafts}

pendentes_atuais := SELECT * FROM task_suggestions
                    WHERE workspace_id=ws AND source='e5n_llm' AND status='pending'

# 1. Supersede pendentes que NÃO aparecem no run novo
FOR p IN pendentes_atuais WHERE p.dedup_key NOT IN new_keys:
    p.status := 'superseded'
    p.superseded_at := now
    p.superseded_by_run_id := run_id

# 2. Para cada draft do run novo: decide inserir
active_keys := {p.dedup_key for p in pendentes_atuais WHERE p.status='pending'}
recent_dismissed := SELECT dedup_key FROM task_suggestions
                    WHERE workspace_id=ws AND source='e5n_llm'
                      AND status='rejected'
                      AND reviewed_at >= now - 90d

FOR d IN drafts:
    IF d.dedup_key IN active_keys: continue         # já tem pending viva
    IF d.dedup_key IN recent_dismissed: continue    # respeita dismiss window
    INSERT TaskSuggestion(
        workspace_id=ws, source='e5n_llm',
        source_run_id=run_id, status='pending',
        dedup_key=d.dedup_key,
        proposed_payload=d.proposed_payload,
    )
```

Índice parcial (Postgres): `ix_tsugg_ws_dedup_active(workspace_id, dedup_key) WHERE status IN ('pending','approved')`. SQLite (testes): índice plain — comportamento idempotente via lógica aplicação. **NÃO promovemos `dedup_key` a UNIQUE** porque histórico de `approved` + `rejected` + futuras `pending` divide o mesmo key — UNIQUE quebraria audit trail.

## Alternativas consideradas

**(a) UNIQUE puro em `(workspace_id, source, content_hash)`** — rejeitada. Hash literal de string LLM é frágil ("Revisar PGBL Bradesco" vs "Revisar plano PGBL no Bradesco" geram hashes diferentes). Sem normalização robusta, UNIQUE não dedupa o que o usuário percebe como duplicado. Com normalização frágil, bloqueia sugestões legitimamente novas que coincidem com keys históricas.

**(b) Dedup aplicação-level estilo [[ADR-153]] `Suggestion`, sem supersede** — rejeitada como solução isolada. Pendentes antigas continuariam vivas competindo com as novas — inbox cresce monotônica e usuário tem que dismissar cada uma manualmente. O contrato semântico do E5N é "**aqui está a recomendação do último run**", não acúmulo.

**(c) Soft-supersede puro, sem dedup_key + dismiss window** — rejeitada. Sem dedup_key, supersede teria que comparar por título literal (mesmo problema do hash do (a)) ou por payload completo (varia muito). Sem dismiss window, sugestão que o usuário rejeitou re-aparece imediatamente no próximo run.

**(d) Unificar com [[ADR-153]] `Suggestion` aggregate** — rejeitada. Semânticas distintas: `Suggestion` é diagnóstico determinístico do relatório (vida longa, histórico relevante para Plano de Ação, gerado por `SuggestionGenerator` regra-based); `TaskSuggestion` é inbox de proposta LLM efêmera (vida curta, "última versão vence", gerada por E5N narrativas). Compartilhar tabela acopla 2 ciclos de vida e força conditionals no UI. Compartilhar o **padrão** (`dedup_key` + janela `DISMISS_RESPECT_WINDOW_DAYS`) é suficiente e é o que esta ADR propõe.

## Consequências

- **Schema**: 3 colunas novas + 1 índice em `task_suggestions`. Migration reversível. Backfill calcula `dedup_key` para rows existentes em script Python single-shot (~6k rows/mês em escala atual; produção provavelmente <1k totais).
- **Comportamento**: rodar pipeline 2× consecutivos com mesmo artefato E5N produz contagem constante de `task_suggestions(source='e5n_llm', status='pending')`. Run novo "carrega" supersede + insert num único commit.
- **Histórico preservado**: `superseded_at` + `superseded_by_run_id` permitem auditar "qual sugestão substituiu qual". `approved` (já virou Task) e `rejected` (dentro da janela) **não** são supersedidas — audit trail intacto.
- **Respeito ao usuário**: rejeição (`status='rejected'`) dentro de 90 dias bloqueia re-criação do mesmo `dedup_key`. Após 90d, re-cria.
- **Race-safety**: garantida pelo `ux_pipeline_runs_ws_active` que serializa runs ativos no workspace. Transação do dispatcher (`SyncSessionLocal().commit()`) fecha o ciclo.
- **Telemetria** estruturada: `task_suggestion.superseded_count`, `task_suggestion.skipped_recent_dismiss`, `task_suggestion.created_count` por run.
- **Out-of-scope**: tabela `Suggestion` aggregate (ADR-153) **não muda**. Outros writers (`task_suggestion_service.create_suggestion`, `application/task/create_task_suggestion`) não são afetados pelo refactor — só o dispatcher Celery muda. Esses use cases calculam `dedup_key` no save mas não fazem supersede (semântica "criação manual one-shot").

## Critérios de aceite

- [ ] Migration Alembic adiciona `dedup_key`, `superseded_at`, `superseded_by_run_id` + índice. Downgrade reversível.
- [ ] `compute_task_suggestion_dedup_key(source, title, category)` é função pura testada com matriz léxica (caps/whitespace/ordem).
- [ ] Script `dev/backfill_task_suggestion_dedup.py` preenche `dedup_key` para rows existentes + supersede duplicatas pending mais antigas por `(workspace_id, dedup_key)`.
- [ ] `_persist_llm_suggestions` implementa supersede + skip dismiss window. Telemetria estruturada emitida.
- [ ] `VALID_SUGGESTION_STATUSES` aceita `"superseded"`.
- [ ] 6 testes de regressão em `backend/tests/integration/test_task_suggestion_dedup.py` (idempotência cross-run, respeito a dismiss window, preservação de approved, manual unaffected, race-safe via single-active guard, normalização léxica).

## Referências

- [[ADR-074]] — TaskSuggestion como queue de aprovação E5N.
- [[ADR-082]] — `pipeline_artifacts` versionado por `pipeline_run_id` (modelo arquitetural análogo: cada run gera rows novas, leitura faz "latest").
- [[ADR-153]] — `Suggestion` aggregate dedup com `dedup_key` + dismiss window. Padrão sendo replicado aqui.
- [[ADR-186]] / [[ADR-188]] — Categorization Learning Loop, padrão "override do usuário é sticky" (rejeição respeitada por janela).
