---
id: ADR-309
type: adr
title: "Audit do console interno persistido em tabela própria (7B.5)"
status: Proposto
date: "2026-07-07"
relates_to: ["[[ADR-116]]", "[[ADR-275]]", "[[ADR-111]]"]
tags:
  - type/adr
  - status/proposto
  - area/internal-ops
  - area/db
---

# ADR-309 — Audit do console interno persistido em tabela própria (7B.5)

**Status:** Proposto · **Data:** 2026-07-07

## Contexto

O console interno ([[ADR-116]]) audita mutações de operador em arquivo JSONL
(`logs/internal_ops_audit.log`) — imutável só por convenção, invisível a SQL,
fora de backup/PITR. [[A30.l1]] tornou o audit **hard-fail contratual**
(falha de audit = falha da operação). 7B.5 (plano INTERNAL_ADMIN) prevê a
migração para tabela como pré-requisito de F7F-Remote. Co-design 2026-07-07:
`senior-cto` + `data-engineer` + `sre-devops` + `product-manager`.

Existe `audit_logs` do produto ([[ADR-275]]): workspace/user-scoped, FKs com
`ON DELETE CASCADE`/`SET NULL`, purge job de audit de leitura. Operador do
console **não é `user`** (auth yaml separada) e a operação pode não ter
workspace.

## Decisão

1. **Tabela nova `internal_ops_audit`** — sem FK (actor é username de
   operador; `target_id` polimórfico string). Reusar `audit_logs` misturaria
   políticas de retenção irreconciliáveis e o `CASCADE` de workspace apagaria
   o audit da própria operação destrutiva. Schema: `id String(36)` uuid,
   `action String(64)`, `actor String(100) NOT NULL`, `target_type`/
   `target_id` nullable, `result String(16)`, `details JSON` (genérico, não
   JSONB — SQLite dev), `created_at DateTime(tz)` (renomeia `timestamp` na
   fronteira DB). Índice único no MVP: `(created_at DESC)` — a UI só lê
   "últimas N"; índices por `actor`/`action` entram quando houver filtro.
2. **Audit na MESMA transação da operação**: `append_audit(record, db:
   AsyncSession)` faz `db.add(row)`; o commit único do endpoint fecha mutação
   + audit ("audit existe ⟺ ação aconteceu"). Os services já recebem `db` e
   fazem `flush()` — a mudança de assinatura é mecânica nos call-sites.
   **Mudança de comportamento intencional**: a semântica antiga (audit
   commitado mesmo com rollback da operação) era limitação do arquivo, não
   decisão; esta ADR emenda o guardrail "troca só do sink" do plano
   INTERNAL_ADMIN. Outbox rejeitado (audit vai para o mesmo Postgres).
3. **Exceção nomeada — eventos session-less**: `ops.login`,
   `ops.login_failed` e `ops.logout` (endpoints sem `Depends(get_db)`;
   `login_failed` precisa sobreviver ao 401) usam
   `append_audit_autonomous(record)` — `SyncSessionLocal` própria, transação
   curta. Varredura dos demais call-sites confirmou: nenhum outro audita
   falha que deva sobreviver a rollback (falhas retornam `OpResult.failure`
   sem auditar).
4. **Imutabilidade real em prod**: `REVOKE UPDATE, DELETE` (grant
   INSERT/SELECT) no role da app — aplicado quando dialect=postgresql;
   runbook de deploy documenta. Código não expõe path de UPDATE/DELETE
   (teste de contrato). Sem trigger no MVP (nice-to-have).
5. **Retenção indefinida (mínimo 5 anos), sem purge** — linha "mutação" do
   contrato [[ADR-275]] D5; o purge job de leitura não toca esta tabela
   (teste explícito). LGPD: minimizar PII de titular no `details` na origem
   (ids opacos > email); remoção cirúrgica futura é follow-up gated por
   requisito legal, não purge.
6. **Sem dual-write, sem backfill** (decisão PM): cutover atômico do sink;
   JSONL vira arquivo-morto (`.pre-7b5`, manter ≥30d), linha meta-audit
   `action=audit.migration` marca o corte. Backfill = follow-up condicional
   a F7F-Remote.

## Consequências

- `_write_lock` (threading) removido — serialização passa ao Postgres; ganho
  [[ADR-111]].
- Falha de audit passa a abortar a operação via rollback natural; DB
  indisponível bloqueia o console — aceitável: toda operação do console já
  depende do DB. `append_audit_autonomous` que falha emite `CRITICAL` em
  `mathoms.internal_ops.audit` (sem PII) — é page, não ticket.
- Audit entra no PITR/backup do DB (upgrade de DR vs `logs/` local).
- Testes: fixture `audit_path` (monkeypatch de arquivo) migra para asserção
  em DB; ~10 arquivos de teste com `read_audit(path=...)` refatoram na mesma
  lane — é o maior custo escondido da migração.
- `read_audit` vira query (ordem/limit preservados — paridade do DTO de
  `GET /admin/audit`); `DB_SCHEMA_REFERENCE.md` regenerado.

## Alternativas rejeitadas

- **Reusar `audit_logs`**: FK semanticamente falsa, CASCADE apaga audit de
  purge, conflito de retention (ver Decisão 1).
- **Commit-separado (write-ahead)**: preservaria registro forense de
  operação que nunca aconteceu; a atomicidade real custa zero dado o padrão
  flush/commit existente.
- **Fallback file-on-DB-error + replay**: over-engineering; diverge
  audit↔operação para proteger operações que já não rodam sem DB.
- **Partitioning/purge**: volume <10k rows/ano não justifica.
