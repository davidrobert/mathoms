# Runbook: F9.3 — Alembic stage rename migration (`q5r6s7t8u9v0`)

> **✅ CONCLUÍDO/HISTÓRICO (2026-05-05, PR #53).** A migração F9.3 foi validada
> e aplicada; F9.5 (hard-fail de literais legados, #720) pressupõe este estado.
> Mantido como referência para restores de backup pré-F9.3 e para o padrão de
> migração de rename em massa — **não é procedimento pendente**.

**ADR:** ADR-093
**Migration:** `backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py`
**Afeta:** `pipeline_artifacts.stage`, `pipeline_stage_logs.stage`
**Prerequisito:** F9.1 + F9.2 concluídas (app já usa nomes descritivos)

---

## 1. Pré-check — verificar stages no banco

Antes de aplicar, confirme que todas as linhas existentes usam apenas as
chaves legadas conhecidas (ou já são descritivas de uma run anterior):

```sql
-- Execute no banco de produção:
SELECT DISTINCT stage FROM pipeline_artifacts ORDER BY stage;
SELECT DISTINCT stage FROM pipeline_stage_logs ORDER BY stage;
```

Os valores devem ser um subconjunto de `STAGE_RENAME.keys()` definidas na
migration (ex.: `E3`, `E5`, `E5.N`…) **ou** dos valores descritivos
(ex.: `reconcile_transactions`, `analyze_finances`…). Qualquer outro valor
indica um residual de F9.2 que deve ser resolvido antes de prosseguir.

A migration tem uma pre-check automática que aborta com `RuntimeError` se
encontrar stage desconhecido — mas confirmar manualmente antes economiza
um rollback.

---

## 2. Backup obrigatório

```bash
# SQLite (dev/staging):
sqlite3 mathoms.db ".dump" > _scratch/backup_pre_f93_$(date +%Y%m%d_%H%M%S).sql

# PostgreSQL (produção):
pg_dump $MATHOMS_DATABASE_URL -Fc -f _scratch/backup_pre_f93_$(date +%Y%m%d_%H%M%S).dump
```

Verifique que o arquivo foi criado e tem tamanho > 0 antes de continuar.

---

## 3. Aplicar a migration

```bash
cd backend
# Confirme que vai rodar no banco correto:
MATHOMS_DATABASE_URL="<url>" alembic current

# Aplique:
MATHOMS_DATABASE_URL="<url>" alembic upgrade head
```

Saída esperada:
```
INFO  [alembic.runtime.migration] Running upgrade p4q5r6s7t8u9 -> q5r6s7t8u9v0, ...
```

Se a migration abortar com `RuntimeError: Unknown stage values in ...`, volte
ao passo 1 e resolva os stages desconhecidos.

---

## 4. Pós-check — confirmar rename

```sql
-- Todos os valores devem ser descritivos agora:
SELECT DISTINCT stage FROM pipeline_artifacts ORDER BY stage;
SELECT DISTINCT stage FROM pipeline_stage_logs ORDER BY stage;
```

Nenhuma linha deve ter valor legado (`E3`, `E5`, `E1.5`, etc.).

---

## 5. Rollback

Se algo der errado após a migration:

```bash
# Reverter um passo:
cd backend
MATHOMS_DATABASE_URL="<url>" alembic downgrade -1

# Ou restaurar do backup (SQLite):
cp mathoms.db mathoms.db.post_f93_broken
sqlite3 mathoms.db ".restore '_scratch/backup_pre_f93_<timestamp>.sql'"

# Ou restaurar do backup (PostgreSQL):
pg_restore --clean -d $MATHOMS_DATABASE_URL _scratch/backup_pre_f93_<timestamp>.dump
```

O `downgrade` restaura todos os nomes legados corretamente — é seguro usar
antes de restaurar o backup se o schema ainda está íntegro.
