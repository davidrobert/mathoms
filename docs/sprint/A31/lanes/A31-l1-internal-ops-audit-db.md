---
id: A31.l1
type: lane
title: "audit do console interno persistido em tabela internal_ops_audit (7B.5)"
sprint: A31
plan: PLAN-internal-admin
status: shipped
ship_pr: 819
ship_date: "2026-07-07"
priority: P1
branch_slug: a31-l1-internal-ops-audit-db
adrs: ["[[ADR-309]]", "[[ADR-116]]", "[[ADR-275]]"]
depends_on: []
parallel_with: ["[[A31.l2]]"]
tags:
  - type/lane
  - sprint/a31
  - status/shipped
  - priority/p1
  - area/internal-ops
  - area/db
---

# A31.l1 — `internal-ops-audit-db` (modelo + migration + sink transacional + testes)

## Problema

Audit de mutação de operador vive em `logs/internal_ops_audit.log` (JSONL
local): adulterável com a credencial da app, invisível a SQL, fora de
backup/PITR, e com semântica de commit-separado que registra operação que
rollbackou. Pré-requisito de F7F-Remote (7B.5). Decisões fechadas em
[[ADR-309]] — **ler a ADR antes de codar**; esta lane só operacionaliza.

## Escopo

### 1. Modelo + migration

- `backend/app/models/internal_ops_audit.py` — `InternalOpsAudit`
  (`internal_ops_audit`): `id String(36)` uuid pk, `action String(64)`,
  `actor String(100) NOT NULL`, `target_type String(64) | None`,
  `target_id String(255) | None`, `result String(16)` default `ok`,
  `details JSON` (genérico — SQLite dev), `created_at DateTime(tz)`.
  Índice único: `(created_at)` — UI só lê "últimas N" (DE: sem índices
  especulativos; `actor`/`action` entram quando a UI ganhar filtro).
- Migration Alembic: create_table + índice inline (tabela nova = sem
  CONCURRENTLY); `downgrade` = drop_table (documentar: descarta audit
  acumulado). Quando dialect=postgresql **e** role da app configurado:
  `REVOKE UPDATE, DELETE` / grant INSERT+SELECT (sre-devops guardrail 1);
  senão, registrar passo no runbook de deploy. Teste de migration com
  `pytestmark = pytest.mark.migration` (ADR-210).

### 2. Sink transacional (audit.py)

- `append_audit(record: AuditRecord, db: AsyncSession)` → `db.add(row)` na
  sessão da operação; commit único do endpoint fecha mutação + audit.
  Mapeamento `AuditRecord.timestamp` (ISO str) → `created_at` na fronteira;
  `_redact`/`_FORBIDDEN_KEYS` continuam aplicados ANTES de persistir.
- `append_audit_autonomous(record)` — exceção nomeada (ADR-309 §3) para
  `ops.login`/`ops.login_failed`/`ops.logout` (endpoints session-less):
  `SyncSessionLocal` própria, transação curta; falha emite `CRITICAL` em
  `mathoms.internal_ops.audit` (sem PII no payload) e re-raise.
- Remover `_write_lock`, `audit_log_path`, escrita em arquivo e o param
  `path` de `read_audit` (ganho ADR-111; sem dual-write). Linha meta-audit
  `action=audit.migration` gravada pelo próprio upgrade da migration (ou
  primeiro boot) marcando o corte; arquivo legado renomeado
  `internal_ops_audit.log.pre-7b5` fica como arquivo-morto ≥30d (manual,
  runbook — está fora do git).
- `read_audit(limit)` vira query `ORDER BY created_at` (preservar a ordem
  atual do contrato: mais recentes por último) — DTO de `GET /admin/audit`
  **byte-idêntico**; snapshot OpenAPI não deve mudar (se mudar, algo está
  errado).

### 3. Call-sites (mecânico)

15 services em `backend/app/services/internal_ops/*.py` passam `db` (já em
escopo — todos fazem `flush()` e o endpoint commita) + `login.py` migra as
3 chamadas para `append_audit_autonomous`. Nenhuma outra mudança de
comportamento nos services (varredura da ADR-309 §3: só login audita falha).

### 4. Testes (o maior custo escondido — DE)

- Fixture `audit_path` (`backend/tests/internal_ops/conftest.py`) vira
  fixture de leitura em DB; ~10 arquivos com `read_audit(path=...)`
  refatoram para asserção via DB de teste (**DB nunca mocado** — SQLite
  in-memory/Alembic-aware, TESTING.md).
- **Teste de atomicidade (prova executável da ADR):** operação que muta +
  audita, exception forçada pós-`append_audit` e pré-commit → zero rows em
  `internal_ops_audit` E zero mutação.
- **Teste de paridade que ENUMERA os paths (KR1):** 15 services + 3 eventos
  de login — cada mutação gera exatamente 1 row com shape esperado. Gate
  contra service que não passe pela função central.
- Hard-fail de `append_audit_autonomous` (fake de session que levanta, não
  MagicMock) → login aborta + CRITICAL emitido.
- Purge job do produto (ADR-275) **não** toca `internal_ops_audit` (teste
  explícito).
- Teste de contrato: repositório/módulo de audit não expõe UPDATE/DELETE.

### 5. Docs

- ADR-309 flip `Proposto` → `Decidido (A31)` no merge; regenerar
  `python3 dev/build_doc_index.py --inline` (ADR_INDEX reflete Decidido).
- Plano INTERNAL_ADMIN: marcar 7B.5 entregue **e emendar o guardrail**
  "troca só do sink" (§guardrails IA-0, ~linha 100) apontando
  [[ADR-309]] §Decisão 2 — a semântica de commit mudou intencionalmente;
  sem a emenda o plano afirma invariante revogado.
- Runbook: passo de deploy do REVOKE + arquivo-morto + o que fazer quando
  audit CRITICAL dispara. `DB_SCHEMA_REFERENCE.md` regenerado.

## Critérios de aceite

1. ADR-309 mergeada como Proposto ANTES do PR de implementação (gate P1);
   flip para Decidido no merge do PR.
2. Teste de atomicidade + teste de paridade enumerando 15+3 paths verdes.
3. Migration upgrade+downgrade limpos em SQLite e (quando disponível)
   Postgres; marker `migration`.
4. `GET /admin/audit` com DTO idêntico (snapshot OpenAPI sem diff).
5. Redação `_FORBIDDEN_KEYS` coberta por teste no path DB.
6. Zero referência a `audit_log_path`/`path=` no código de produção.
7. Backfill do JSONL **fora de escopo** (Won't — follow-up condicional a
   F7F-Remote). PR mergeado em `main` (squash) com CI verde.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `backend/app/services/internal_ops/audit.py` | Sink a trocar (AuditRecord, append_audit, read_audit) |
| `backend/app/models/audit_log.py` | Padrão de modelo (String(36) pk, JSON, índices) — NÃO reusar a tabela |
| `backend/app/api/admin/login.py` | 3 call-sites session-less → autonomous |
| `backend/app/api/admin/metrics.py:67` | `GET /admin/audit` (paridade DTO) |
| `backend/tests/internal_ops/conftest.py` | Fixture `audit_path` a migrar |
| `backend/app/core/database.py` | `SyncSessionLocal` (autonomous) |
| `docs/adr/309-audit-do-console-interno-persistido-em-tabela.md` | Decisões fechadas |
