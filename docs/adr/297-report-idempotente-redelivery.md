---
id: ADR-297
type: adr
title: "Report idempotente sob redelivery do Celery — índice único parcial + guarda terminal"
status: Decidido
phase: "audit-r2 · REL-03"
date: "2026-06-18"
relates_to:
  - "[[ADR-131]]"
  - "[[ADR-172]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 297"
  - "REL-03"
tags:
  - area/reliability
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 52
---

# ADR-297 — Report idempotente sob redelivery do Celery

**Status:** Decidido (audit-r2 · REL-03) • **Data:** 2026-06-18 • **Relaciona** [[ADR-131]] (Report→artifact por FK), [[ADR-172]] (heartbeat / crash-recovery)

## Contexto

`run_pipeline_task` roda com `acks_late=True` + `reject_on_worker_lost=True` (`backend/app/tasks/pipeline_task.py`; globais em `worker.py`). O ack só ocorre ao fim do run; se o worker morre antes (OOM em stage LLM, `time_limit=3600`, kill), o broker reentrega a mensagem e **o run inteiro re-executa**, chamando `_create_report_from_output` de novo.

`reports` não tinha unicidade em `(workspace_id, pipeline_run_id)` e `_create_report_from_output` fazia `db.add` + `db.commit` cego → **dois Reports para o mesmo run** (relatório duplicado na UI + custo de LLM dobrado). `_mark_run_started` também setava `status=running` sem checar estado terminal. Achado REL-03 da auditoria r2.

## Decisão

1. **Índice único parcial** `ux_reports_workspace_pipeline_run` em `reports (workspace_id, pipeline_run_id) WHERE pipeline_run_id IS NOT NULL` (migration `rel03reportuniq`). Backstop à prova de corrida — independe de ordem entre workers concorrentes. Parcial porque `pipeline_run_id` é nullable (`ON DELETE SET NULL`); Reports órfãos coexistem. Precedente cross-DB: `ux_documents_workspace_content_hash` ([[ADR-081]] dedupe).
2. **`_create_report_from_output` captura `IntegrityError`**, faz rollback e trata como sucesso idempotente (o Report existente é válido).
3. **Guarda de estado terminal em `_mark_run_started`**: redelivery de run em `{completed, failed, partial_failure, cancelled}` não re-executa o pipeline. `running`/`resuming`/`pending`/`needs_review` passam — crash-recovery e resume legítimos precisam re-entrar. A guarda é otimização (evita custo de LLM); o índice único é a garantia.

## Alternativas consideradas

- **Só a guarda terminal (sem índice).** Rejeitada: tem TOCTOU entre o read do status e o insert do Report — dois workers concorrentes ainda duplicariam. O índice fecha a corrida no nível do banco.
- **`get_or_create` no Report.** Rejeitada: a checagem-então-insere reintroduz a janela de corrida; deixar o banco rejeitar e capturar `IntegrityError` é o padrão idempotente correto.
- **Desligar `acks_late`.** Rejeitada: `acks_late` é necessário para crash-recovery (ADR-172). A duplicidade é o preço a pagar e se resolve com idempotência, não removendo a entrega-no-mínimo-uma-vez.

## Consequências

- ✅ Redelivery não duplica Report; relatório e custo de LLM permanecem únicos por run.
- ✅ Migração detecta duplicatas pré-existentes e aborta com mensagem clara (não apaga dado do usuário).
- ⚠️ Duplicatas legadas (se houver) precisam de limpeza manual antes de migrar — explícito no erro.
