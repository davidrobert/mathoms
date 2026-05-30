---
id: ADR-274
type: adr
title: "Auditoria de acesso + política de retenção LGPD"
status: Decidido
phase: A21 (l7 + l8)
date: "2026-05-30"
relates_to:
  - "[[ADR-095]]"
  - "[[ADR-115]]"
  - "[[ADR-110]]"
supersedes: []
superseded_by: []
aliases: ["ADR 274"]
tags:
  - area/security
  - area/persistence
  - area/backend
  - status/decidido
  - type/adr
  - methodology/lgpd
---

# ADR-274 — Auditoria de acesso + política de retenção LGPD

**Status:** Decidido (A21 · l7 + l8) • **Data:** 2026-05-30 •
**Planos:** [[PLAN-launch-trust]] §F2-G2 (l7) + §F2-G3 (l8)

**Contexto:** o launch BR exige (a) **LGPD Art.37** — registrar *quem* acessou
dado sensível *de quem* e *quando* (l7); (b) **LGPD Art.18** — export/deleção
do titular com retenção declarada por base legal (l8). O export
(`lgpd_export_service.py` + `DataExportRequest`) e a auto-deleção
(`POST /me/delete-request`, soft + 30d + cron hard-delete preservando audit
anonimizado) **já estão implementados e testados**. O gap real é **leitura
auditada** (Art.37) e **política de retenção declarada + enforçada** para o
próprio log de auditoria. [[ADR-095]] D3/D4 pré-especificou ambos, mas com uma
tabela nova (`access_audit_log`) que nunca foi construída e que duplicaria a
`audit_logs` já existente ([[ADR-115]]). Esta ADR fecha o gap reusando a infra
existente e **supersede ADR-095 D3 (audit de leitura) e D4 (retenção)**;
D1/D2/D5 (crypto app-level, não-crypto de valores, masking de logs) permanecem
em vigor.

**Decisão:**

**D1 — Reusar `audit_logs`, não criar `access_audit_log`.** A tabela
`audit_logs` ([[ADR-115]]) já é append-only, multi-tenant (`workspace_id` FK
CASCADE), com `actor_user_id`, `action`, `resource_type`, `resource_id`,
`ip_address`, `user_agent`, `details` (JSON), `created_at`. Leituras de dado
sensível gravam **novas `action`** de leitura na mesma tabela. Particionamento
por tempo é follow-up **gated por volume** (~50M linhas), não escopo de A21.

**D2 — Hook por dependency FastAPI em rotas sensíveis + test-guard OpenAPI.**
Leitura sensível registra via uma dependency curada
(`record_access_audit(action, resource_type)`) anexada às rotas que servem
CPF / valores / conteúdo financeiro (`api/reports.py`, `api/transactions.py`,
`api/family_members.py`, `api/documents.py`). Um teste sobre o snapshot OpenAPI
enforça **default invertido anti-drift**: rota `GET` classificada como sensível
**precisa** ter a dependency **ou** estar numa allowlist justificada
(rota benigna). Granularidade **per-access cru em v1** (sem dedup);
janela de colapso (não amostragem) é follow-up gated por volume.

**D3 — Escrita síncrona via helper `services/audit.py`, assíncrona se ferir
SLO.** A v1 grava síncrono no request path (mesmo padrão de mutação,
`audit_log_sync`). Se a latência p95 das rotas quentes (relatório) regredir
além do SLO, migrar a escrita de leitura para o event-bus síncrono
(`dispatch_sync`, [[ADR-115]]) ou fila — decisão gated por medição, não
antecipada.

**D4 — Anti-PII por allowlist tipada, não blocklist.** O `details` da `action`
de leitura é um `AccessAuditDetails` (Pydantic `extra="forbid"`) com campos
**fechados** (`method`, `route`, `query_keys`) — **nunca** CPF, valor
monetário, nome ou conteúdo de extrato. `route` é o **template** da rota
(`/.../{report_id}`), não o path com IDs reais; `query_keys` são só as
**chaves** ordenadas, não os valores. Um **teste de guarda de escrita
obrigatório** (`assert_pii_free`) rejeita payload contendo padrão de
CPF/valor. Inverte a blocklist frágil de `internal_ops/audit.py`
(`_FORBIDDEN_KEYS`) para o caso de leitura: só passa o que está declarado.

**D5 — Retenção diferenciada read vs. mutation, declarada e enforçada.**
Beat Celery diário **dedicado** `purge_expired_audit_logs` apaga **somente**
linhas de `action` de leitura com `created_at < now() - 365d`, em lotes
(`LIMIT 10000`), e grava 1 linha meta-audit `action=audit.purge`
`{deleted_count, cutoff_date}`. **Nunca** toca audit de mutação (base legal +
prazo distintos). Codado + agendado **agora**, mesmo em pré-prod (no-op
seguro até haver volume). Doc-only é insuficiente — Art.18 exige enforcement.

**Contrato de retenção LGPD (declarado):**

| Dado | Ação | Prazo | Base legal |
|------|------|-------|------------|
| Audit de **leitura** (`*.read`/`*.download`) | apaga | 365 dias | Art.37 (rastreabilidade de acesso) — interesse legítimo + segurança |
| Audit de **mutação** (`document.upload`, `*.delete`, `storage.purge`, `workspace.export`) | retém / anonimiza ator | indefinido (apenas anonimiza `actor_user_id` na deleção do titular) | Art.16 / dever de prestação de contas |
| Dado financeiro do titular (`pipeline_artifacts`, `documents.*_content`, contas) | apaga | 24h úteis pós-pedido (soft + 30d grace na auto-deleção) | Art.18 (esquecimento) |
| PII em `content_json` (CPF, nome) | criptografa em repouso | enquanto ativo | Art.46 (segurança) — [[ADR-095]] D1, **mantida** |
| `DataExportRequest` (artefato de export) | apaga | TTL do pacote (já implementado) | Art.18 (portabilidade) |

**Interação l7 ↔ l8 (resolvida):** a deleção do titular **não** apaga o audit
log — anonimiza `actor_user_id` (FK SET NULL já existente) e mantém a linha.
O purge de retenção (D5) é o único caminho que remove audit, e só read-audit
após 365d. Mutation-audit sobrevive ao purge (teste explícito).

**Alternativas consideradas:**
- *Tabela `access_audit_log` nova ([[ADR-095]] D3):* rejeitada — duplica
  `audit_logs`, dois caminhos de escrita/consulta, dois schemas de retenção.
- *Blocklist de chaves proibidas no `details`:* rejeitada — frágil
  (campo novo vaza por omissão); allowlist `extra="forbid"` falha-fecha.
- *Retenção doc-only sem beat:* rejeitada — Art.18 exige enforcement coded.
- *Sampling de leitura:* rejeitado em v1 — Art.37 quer rastreabilidade
  completa; colapso por janela é o caminho de escala, não amostragem.

**Consequências:**
- ✅ Art.37 (acesso auditado) + Art.18 (export/deleção/retenção) explícitos.
- ✅ Um único modelo de audit, um contrato de retenção coerente.
- ✅ Anti-PII falha-fecha (allowlist tipada + teste de guarda).
- ⚠️ Escrita síncrona de leitura adiciona 1 INSERT por GET quente — mitigável
  por async se ferir SLO (D3).
- ⚠️ Índices compostos `(workspace_id, created_at)` + `(actor_user_id, created_at)`
  (migration `adr274auditidx`, substituem o índice single em `created_at`)
  para consulta de incident-response e purge eficientes. Pré-prod (tabela
  vazia) usa `CREATE INDEX` simples — instantâneo; em escala de produção a
  recriação deve usar `CREATE INDEX CONCURRENTLY` em janela dedicada
  (follow-up gated por volume).
- ❌ Particionamento e colapso de leitura ficam como follow-up gated por volume.

**Implementação (A21):** l7 — `services/access_audit.py` (dependency +
`AccessAuditDetails` + `assert_pii_free`), `READ_ACCESS_ACTIONS` em
`services/audit.py`, deps anexadas em reports/transactions/family_members/
documents/planner_review, test-guard `test_access_audit.py`, migration
`adr274auditidx`. l8 — `purge_expired_audit_logs` (beat diário em `worker.py`),
test `test_purge_audit_logs.py`. Export + auto-deleção já existiam
(`test_lgpd_self_service.py`).
