---
id: ADR-131
type: adr
title: "`Report` referencia `pipeline_artifact` por FK (drop `analysis_json_path`)"
status: Decidido
date: "2026-04-25"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 131"]
tags:
  - area/frontend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 113
---

# ADR-131 — `Report` referencia `pipeline_artifact` por FK (drop `analysis_json_path`)

**Status:** Decidido • **Data:** 2026-04-25 • **Supersedes** parte de
[ADR-078](#adr-078--render-nativo-react--e6-como-exportador-standalone) (a
seção F9 que decidiu persistir `analysis_json_path` em disco como
fonte de verdade do relatório React).

**Contexto:** A migration F9 (`d3e4f5a6b7c8`) adicionou
`reports.analysis_json_path` apontando para
`processed/E5_analysis/<...>-5_analysis.json` no filesystem do tenant.
Era a fonte que `GET /reports/{id}/data` consumia para renderizar o
relatório nativo React e que `pdf_renderer.py` exportava via
Playwright.

Em 2026-04-24 dois commits do mesmo dia colidiram silenciosamente:

1. **A6c (`f7b824e`, manhã)** removeu o `MaterializationBridge` —
   passou a valer literalmente que com `USE_DB_ARTIFACTS=True`
   (default desde A6c, [ADR-106](#adr-106--opt-in-db-artifacts-por-workspace--dbartifactstore-no-celery-task-a6b)/[ADR-107](#adr-107--remoção-de-materializationbridge-e-stage_runner_compat-a6c1-2)),
   o stage E5 grava o artefato **apenas** em `pipeline_artifacts`. O
   filesystem deixou de receber o JSON.
2. **ADR-129 (`94f693d`, noite)** reescreveu `_create_report_from_output`
   para depender de `processed/E5_analysis/*-5_analysis.json` —
   arquivo que A6c havia tornado inexistente.

Resultado: pipelines marcavam `completed` sem inserir linha em
`reports`; UI ficava vazia. A Fatia 1 (commit `6112f7f`) restaurou o
fluxo materializando o JSON em disco a partir do DB no momento da
criação do `Report`. Mas isso é remédio, não cura: continua
acoplando o relatório a um arquivo no tenant_root, e a próxima
mudança no caminho de gravação reabre a mesma classe de bug.

Alternativas consideradas:

- **(a) Manter `analysis_json_path` + materialização sob demanda
  (Fatia 1 atual).** Funciona, mas mantém duas fontes de verdade
  (DB + disco) e exige writer materializar para que reader leia. Toda
  vez que algum stage tocar no caminho, o bug ressurge.
- **(b) FK `analysis_artifact_id` → `pipeline_artifacts.id`.** Único
  ponto de verdade. Reader lê `content_json` direto do DB; nenhum
  filesystem.
- **(c) Coluna `analysis_json` JSON no próprio Report.** Duplica o
  payload (já está em `pipeline_artifacts`). Pior — precisa sincronizar
  com o artifact se este for editado por reprocessamento.

**Decisão:** **(b)** — `Report.analysis_json_path` (Text) é
substituído por `Report.analysis_artifact_id` (Integer FK) com
`ON DELETE SET NULL`. Coluna `size_bytes` também é removida (deriva
do payload se algum dia precisar). Backfill SQL durante upgrade liga
Reports existentes ao artifact do mesmo `pipeline_run_id` quando
existe. Reports cujo run não tem artefato no DB ficam com FK NULL —
endpoint retorna 404, mesma UX do legado quando o arquivo de disco
não existia.

`get_report_data` lê `report.analysis_artifact.content_json`
diretamente. `pdf_renderer.py` permanece inalterado: já recebia URL
do React (`/reports/[id]`) e navegava — toda a leitura de JSON
acontece pelo endpoint via FK.

Migration `v0w1x2y3z4a5` em 3 passos com `batch_alter_table`
(SQLite-friendly):

1. Adiciona coluna `analysis_artifact_id` + FK constraint.
2. `UPDATE reports SET analysis_artifact_id = (SELECT pa.id FROM
   pipeline_artifacts pa WHERE pa.pipeline_run_id =
   reports.pipeline_run_id AND pa.stage='E5' AND
   pa.artifact_key='analise_financeira' LIMIT 1)` — backfill SQL
   puro, sem código Python.
3. Drop `analysis_json_path` e `size_bytes`.

Os snapshots `_table_pre`/`_table_intermediate`/`_table_post`
declaram a FK explicitamente para que o batch SQLite preserve a
constraint ao rebuildar a tabela; downgrade simétrico restaura as
colunas e drop a FK.

**Consequências:**

- ✅ **Single source of truth.** Relatório, artifact e linhagem
  vivem todos no DB. Não há mais "criar Report" ↔ "materializar
  arquivo" como duas operações separadas que podem dessincronizar.
- ✅ **Stateless puro** ([ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6))
  no caminho de leitura: o handler de
  `GET /reports/{id}/data` faz uma query (com `lazy=joined`) e
  serializa. Zero filesystem, zero contexto por tenant_root.
- ✅ **Estruturalmente impossível** repetir a regressão de
  2026-04-24: não existe mais "writer escreve em A, reader lê de B".
- ✅ **PDF export inalterado.** `pdf_renderer.py` lê via React route,
  que chama o endpoint via FK — herda o caminho correto de graça.
- ⚠️ Reports pré-A6c sem artifact no DB ficam com `FK NULL` →
  endpoint retorna 404. Em produção há 2 Reports nesse estado (os do
  backfill da Fatia 1 já foram recuperados; futuros backfills do
  script `backfill_reports_from_artifacts.py` continuam funcionando
  para runs `completed` órfãos).
- ⚠️ Frontend perde exibição de tamanho do relatório em
  `/reports`. Aceito — é UX cosmético, não havia caso de uso
  declarado, e recomputar size para cada item da lista exigiria
  fetchar todos os artifacts (anti-performant).
- ❌ Migration de produção é irreversível em prática (downgrade
  restaura schema, não restaura `analysis_json_path` original que foi
  perdido). Aceito por ser ambiente de desenvolvimento; mais limpo
  agora vale do que opcionalidade futura.

Relaciona-se a: [ADR-078](#adr-078--render-nativo-react--e6-como-exportador-standalone)
(F9 — substitui premissa de filesystem),
[ADR-082](#adr-082--pipelineartifact-artefatos-computacionais-no-banco) (modelo `pipeline_artifacts`),
[ADR-106](#adr-106--opt-in-db-artifacts-por-workspace--dbartifactstore-no-celery-task-a6b) / [ADR-107](#adr-107--remoção-de-materializationbridge-e-stage_runner_compat-a6c1-2)
(A6c — bridge removido que motivou a regressão),
[ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6)
(stateless — agora aplicável ao read path do relatório),
[ADR-129](#adr-129--descontinuação-completa-do-renderer-html-server-side)
(introdução do reader filesystem-based agora removido).
