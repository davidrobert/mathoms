# Runbook — Data Lineage: migrations das Ondas 1 (F1) e F5

> **ADRs:** [[ADR-278]] (data_source + FK) · [[ADR-282]] (override natural_key v2) · [[ADR-279]] (edge table F5) · [[ADR-280]] (contexto)
> **Migrations cobertas:** `adr282_override_natural_key.py` · `adr278_data_source.py` (#564) · `adr278fk_data_source_fk.py` · `adr279edges_artifact_lineage_edge.py` (A25.l3) · 2-fases `amount`/`natural_key` (🔜 futuras)
> **Afeta:** `data_source`, `pipeline_artifacts.data_source_id`, `transaction_overrides`, `artifact_lineage_edge`
> **Prerequisito:** PITR habilitado (ver §RPO/RTO) · `MATHOMS_FERNET_KEY` confirmada
> **Owner:** SRE on-call.
> **Janela alvo:** RTO de rollback ≤ 30min (rollback de deploy, dado íntegro) · RPO 0 (DDL não perde dado).

---

## Por que este runbook existe

A Onda 1 do Data Lineage ([[PLAN-data-lineage]]) endurece o contrato E2 e generaliza a
origem do artefato (`document_id` → fonte plugável) via uma família de migrations
aditivas. Duas delas já estão em `main`; a terceira (FK Postgres-only) é materializada
nesta lane. O risco operacional concentra-se em **uma** migration — o FK
`pipeline_artifacts.data_source_id`, que faz `VALIDATE CONSTRAINT` sobre tabela de alto
volume. Este runbook fixa o procedimento por fase (pré-check de integridade, aplicação,
pós-check, rollback, critério de abortar) para que a aplicação em produção não dependa de
memória.

Este runbook é **rollback de deploy** (schema íntegro, RTO ≤30min), **não DR** (perda de
dado, RTO ≤4h). Para DR e custódia da chave Fernet, ver
[disaster_recovery.md](disaster_recovery.md); o template de aplicação single-migration
está em [f9_3_alembic_upgrade.md](f9_3_alembic_upgrade.md).

## Escopo & como usar

Execute as fases na ordem **A → B → C**; cada fase é independente e tem o próprio
rollback. As fases A e B já estão aplicadas em produção (mergeadas) — ficam aqui para o
mapa de rollback. A fase C é a que esta lane introduz. Em **SQLite** (dev/CI) todas as
migrations Postgres-only são **no-op** por design (o FK não existe lá — o model mantém
`data_source_id` plain; integridade via app layer, [[ADR-278]]).

## RPO/RTO & janela PITR

- **RPO 0** nesta operação — são migrations DDL (e backfill idempotente), não perdem dado.
- **RTO de rollback ≤ 30min** — cada fase reverte por `alembic downgrade` (não exige restore).
- **Snapshot pré-deploy obrigatório** — ver [disaster_recovery.md](disaster_recovery.md)
  §2 (`pg_dump -Fc`); **não duplicar** o procedimento aqui. Registre o `recovery_target_time`
  (ou LSN) imediatamente **antes** do upgrade — ponto de PITR caso o rollback por downgrade
  não baste.

---

## Fase A — `adr282_override_natural_key` (override K4 v2)

Alinha o 3º hash (`TransactionOverride`) ao K4 v2 ([[ADR-282]]). Já em `main`.

### A.1 Pré-check
- `alembic current` aponta para a revision anterior a `adr282overridenk`.

### A.2 Aplicar
- `cd backend && alembic upgrade adr282overridenk`

### A.3 Pós-check
```sql
\d transaction_overrides   -- coluna/índice natural_key v2 presentes
-- rows backfilled == total elegível (sem órfão de identidade)
```

### A.4 Rollback
- `alembic downgrade -1` (reversível; ver docstring da migration para limites).

### A.5 Critério de abortar
- Backfill deixa contagem divergente → abortar, investigar identidade de override.

---

## Fase B — `adr278_data_source` (tabela + coluna + backfill)

Cria `data_source` + `pipeline_artifacts.data_source_id` nullable indexada + backfill
idempotente `kind='document'` ([[ADR-278]]). Já em `main` (#564).

### B.1 Pré-check
- `alembic current` == `adr282overridenk`.

### B.2 Aplicar
- `alembic upgrade adr278datasource`

### B.3 Pós-check
```sql
-- 1 data_source kind='document' por workspace com E2+document_id:
SELECT COUNT(*) FROM data_source WHERE kind = 'document';
-- data_source_id setado em todas as rows E2-com-document_id:
SELECT COUNT(*) FROM pipeline_artifacts WHERE data_source_id IS NOT NULL;
-- sem data_source duplicado por chave natural:
SELECT workspace_id, kind, institution_code, external_account_ref, COUNT(*)
FROM data_source
GROUP BY 1,2,3,4 HAVING COUNT(*) > 1;   -- DEVE ser vazio
```

### B.4 Rollback
- `alembic downgrade -1` (dropa índice + coluna + tabela).

### B.5 Critério de abortar
- Duplicado por chave natural → abortar (viola o unique pretendido pelo FK futuro).

---

## Fase C — FK `data_source_id` → `data_source.id` (`ON DELETE SET NULL`)

Materializa o FK deferido da fase B ([[ADR-278]]), **Postgres-only**, via
`ADD CONSTRAINT … NOT VALID` + `VALIDATE CONSTRAINT` em transações **separadas**
(`autocommit_block`): o `ADD` é instantâneo e libera o `ACCESS EXCLUSIVE` antes do scan do
`VALIDATE` (que roda sob `SHARE UPDATE EXCLUSIVE` e **não bloqueia** leitura/escrita).
Migration: `backend/alembic/versions/adr278fk_data_source_fk.py`.

### C.1 Pré-check de integridade (GATE — aborta se falhar)
```sql
-- (Vetor A) órfão real: data_source_id aponta para id inexistente. VALIDATE falha
-- a migration inteira se houver UM. A própria migration remedia (SET NULL idempotente)
-- antes do ADD, mas confirme:
SELECT COUNT(*) FROM pipeline_artifacts pa
LEFT JOIN data_source ds ON ds.id = pa.data_source_id
WHERE pa.data_source_id IS NOT NULL AND ds.id IS NULL;          -- DEVE ser 0

-- (Vetor B) canário de tenancy: o FK garante EXISTÊNCIA, não workspace. Enforcement
-- de tenancy é app-layer; este SELECT documenta o invariante para a F3+.
SELECT COUNT(*) FROM pipeline_artifacts pa
JOIN data_source ds ON ds.id = pa.data_source_id
WHERE pa.workspace_id <> ds.workspace_id;                       -- DEVE ser 0
```
Se o Vetor A `> 0` e não confiar na remediação embutida, rode:
```sql
UPDATE pipeline_artifacts pa SET data_source_id = NULL
WHERE pa.data_source_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM data_source ds WHERE ds.id = pa.data_source_id);
```

### C.2 Aplicar
- Registrar `recovery_target_time` (PITR). `alembic upgrade adr278datasourcefk`.
- A constraint nasce `NOT VALID` (já protege escritas novas) e em seguida é `VALIDATE`-ada
  (scan do legado sob lock fraco). Registre a **duração do VALIDATE** para capacity.

### C.3 Pós-check
```sql
-- FK presente e VALIDADA (não 'NOT VALID'):
SELECT conname, convalidated FROM pg_constraint
WHERE conrelid = 'pipeline_artifacts'::regclass AND contype = 'f'
  AND conname = 'fk_pipeline_artifacts_data_source_id';         -- convalidated = true
\d pipeline_artifacts   -- mostra '... ON DELETE SET NULL'
-- re-rodar o SELECT de órfão da C.1: continua 0.
```
Em SQLite: nada a verificar — o FK não existe lá por design ([[ADR-278]], model plain).

### C.4 Rollback
- `alembic downgrade adr278datasource` → `DROP CONSTRAINT IF EXISTS` (instantâneo, não
  revarre). No-op em SQLite. Schema volta íntegro — restore só se corrupção (→ DR).

### C.5 Critério de abortar
- `VALIDATE` falha (órfão não remediado) → a transação aborta sozinha, o FK **não**
  materializa, o app segue com integridade app-layer. Investigar órfão, remediar (C.1),
  re-aplicar. Não force.

---

## Fase D — 2-fases `amount` / `natural_key` (cutover)

> 🔜 **Futura (A24)** — migrations ainda não existem. Esta seção fixa o *contrato de
> rollback* antecipadamente; **não execute**. Quando a 2ª fase (`valor`→`amount` cutover
> de leitores; obrigatoriedade de `natural_key`) nascer, esta lane futura troca este
> placeholder pelo procedimento real (Pré-check/Aplicar/Pós-check/Rollback/Abortar).

---

## Fase E — `adr279edges` (tabela derivada `artifact_lineage_edge`, F5 · A25.l3)

Cria a tabela do índice reverso field-level ([[ADR-279]]): edges derivadas do
`_lineage` E5 pelo hook pós-run (`_run_post_processing` → `lineage_edge_writer`),
retenção **N=1 por workspace** (B6). Tabela **derivada/rebuildável** — nunca fonte
primária (auditoria histórica usa o `_lineage` inline em `pipeline_artifacts`), o que
torna esta fase a de menor risco do runbook: perda total da tabela se reconstrói com
1 run do pipeline por workspace.

### E.1 Pré-check
- `alembic current` == revision anterior (`a170rtf00001`).

### E.2 Aplicar
- `cd backend && alembic upgrade adr279edges`
- Em Postgres: FKs (`workspaces`/`pipeline_runs`/`documents` inline; `data_source`
  via `ADD CONSTRAINT` — tabela nasce vazia, instantâneo) + índices
  `(workspace_id, run_id)` e `(workspace_id, source_document_id)` via
  `CREATE INDEX CONCURRENTLY` fora de transação (`autocommit_block`). Em SQLite:
  índices simples, FK de `data_source` não materializa (coluna plain, app layer).

### E.3 Pós-check
```sql
\d artifact_lineage_edge   -- tabela + 2 índices + FKs presentes
-- População ocorre no próximo run bem-sucedido de cada workspace (hook best-effort);
-- tabela vazia logo após o upgrade é o estado esperado.
SELECT COUNT(*) FROM artifact_lineage_edge;
```

### E.4 Rollback
- `alembic downgrade a170rtf00001` → `DROP TABLE` (instantâneo; dado é derivado,
  RPO 0 por definição — rebuild via run do pipeline).

### E.5 Critério de abortar
- Nenhum específico: tabela nova e vazia. Falha de DDL → investigar e re-aplicar;
  o produto segue funcionando sem a tabela (hook é best-effort, loga warning).

---

## Tabela-resumo

| Fase | Migration | Reversível? | Mecanismo de rollback | Postgres-only? | Status |
|------|-----------|-------------|------------------------|----------------|--------|
| A | `adr282_override_natural_key` | Sim | `downgrade -1` | Não | ✅ em `main` |
| B | `adr278_data_source` | Sim | `downgrade -1` (drop col/índice/tabela) | Não | ✅ #564 |
| C | `adr278fk_data_source_fk` | Sim | `downgrade` → `DROP CONSTRAINT IF EXISTS` | **Sim** (no-op SQLite) | 🚧 esta lane |
| D | `amount`/`natural_key` 2-fases | — | — | — | 🔜 futura (A24) |
| E | `adr279edges_artifact_lineage_edge` | Sim | `downgrade` → `DROP TABLE` (derivada, rebuildável) | Não (FKs/CONCURRENTLY só no PG) | 🚧 A25.l3 |

## Operação futura — recriar índice em escala (`CONCURRENTLY`)

`ix_pipeline_artifacts_data_source_id` foi criado **simples** (fase B, precedente
[[ADR-275]]/[[ADR-282]]). Se algum dia precisar recriá-lo em produção sob carga (ex.:
índice parcial/composto), use `CREATE INDEX CONCURRENTLY` + `DROP INDEX CONCURRENTLY`
**fora de transação** (`autocommit_block` se via Alembic; ou `psql` direto). Isto **não**
faz parte da migration do FK — é procedimento operacional, registrado aqui por completude.

## Referências

- [[ADR-278]] — `data_source` + `SourceRef` + FK (rationale do `ON DELETE SET NULL`).
- [[ADR-282]] — identidade v2 do `TransactionOverride`.
- [[PLAN-data-lineage]] — plano dono (Onda 1, guard-rail G-e).
- [disaster_recovery.md](disaster_recovery.md) — DR ≠ rollback; custódia Fernet; `pg_dump`.
- [f9_3_alembic_upgrade.md](f9_3_alembic_upgrade.md) — template de aplicação single-migration.
