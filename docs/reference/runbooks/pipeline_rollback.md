# Runbook — Pipeline Rollback (pós-sunset `MATHOMS_USE_DB_ARTIFACTS`)

> **ADR:** [[ADR-212]] (Proposto · 2026-05-14) · supersede do runbook de
> rollback flip-flag descrito em [[ADR-118]].
> **Lane:** [[A12.sunset-disk-artifact]] — este runbook é **PR1.5**,
> pré-requisito obrigatório de PR3 (deleção de `DiskArtifactStore`).
> **Owner:** SRE on-call.
> **Janela alvo:** RTO ≤30min · RPO ≤24h.
> **Procedure exercitada em staging:** ☐ (gate operacional — confirmar
> antes de mergear PR3).

---

## Por que este runbook existe

Pré-[[ADR-212]], rollback do pipeline era trivial: `MATHOMS_USE_DB_ARTIFACTS=false`
+ redeploy → caminho `DiskArtifactStore` voltava a operar. Janela ~5min.

Pós-PR3, a flag e o caminho disco **não existem mais**. Rollback exige:
- Snapshot DB pré-deploy (gate de deploy, não opcional).
- Revert de PR via Git.
- Migration downgrade quando aplicável.
- Restore de snapshot quando há corrupção em `pipeline_artifacts`.

Janela cresce para ~30min, mas o modo de falha é previsível e o
decision tree abaixo reduz tempo de diagnóstico em incidente real.

---

## 1. Pré-requisitos (gate de deploy, não negociável)

Antes de **qualquer deploy** que toque o pipeline (`backend/app/tasks/pipeline_task.py`,
`backend/app/services/db_artifact_store.py`, `pipeline/**`, ou migration que afete
`pipeline_artifacts` / `workspaces` / `pipeline_runs` / `pipeline_stage_logs`):

```bash
# 1. Snapshot DB — Postgres (produção)
pg_dump \
  --table=pipeline_artifacts \
  --table=workspaces \
  --table=pipeline_runs \
  --table=pipeline_stage_logs \
  -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  > "/var/backups/mathoms/pre-deploy-$(date -u +%Y%m%dT%H%M%SZ).sql"

# 2. Sanity check do snapshot
test -s "/var/backups/mathoms/pre-deploy-*.sql" || { echo "SNAPSHOT VAZIO — aborta deploy"; exit 1; }

# 3. Counts de referência (registrar para validação pós-rollback)
psql -c "SELECT count(*) FROM pipeline_artifacts" -t > /tmp/pre-deploy-artifact-count.txt
psql -c "SELECT count(*) FROM pipeline_runs WHERE completed_at > now() - interval '24 hours'" -t > /tmp/pre-deploy-run-count.txt
```

**Retenção do snapshot:** ≥14 dias (cobre janela típica de incidente
detectado tardiamente). Cleanup automatizado via cron — fora de escopo
deste runbook.

> ⚠️ Sem snapshot, **rollback de corrupção é impossível**. CI/CD do
> deploy deve falhar se o passo de snapshot não retornar 0.

---

## 2. Detecção — gatilhos que disparam este runbook

Acione rollback quando **qualquer** das condições abaixo for verdadeira:

### 2.1. Anomalia em logs estruturados (`mathoms.pipeline`)

```bash
# Logs com severidade ≥ERROR no namespace pipeline, últimos 30 min
# (substitua pelo backend de logs em uso — Loki, CloudWatch, etc.)
kubectl logs -l app=mathoms-worker --since=30m | grep '"level":"ERROR".*"logger":"mathoms.pipeline'
```

**Critério de acionamento:**
- ≥5 erros únicos por workspace distinto, **OU**
- ≥1 erro contendo `IntegrityError`, `OperationalError`, `JSONDecodeError` em
  `db_artifact_store.write` / `db_artifact_store.read_latest`.

### 2.2. Taxa de falha de runs

```sql
-- Runs failed nos últimos 60 minutos vs baseline 7d
WITH recent AS (
  SELECT count(*) AS failed FROM pipeline_runs
  WHERE status = 'failed' AND completed_at > now() - interval '1 hour'
),
baseline AS (
  SELECT count(*) / 168.0 AS hourly_avg FROM pipeline_runs
  WHERE status = 'failed' AND completed_at > now() - interval '7 days'
)
SELECT recent.failed, baseline.hourly_avg,
  CASE WHEN recent.failed > GREATEST(2 * baseline.hourly_avg, 3) THEN 'ROLLBACK_CANDIDATE'
       ELSE 'OK' END AS verdict
FROM recent, baseline;
```

**Critério de acionamento:** `verdict = 'ROLLBACK_CANDIDATE'`.

### 2.3. Corrupção em `pipeline_artifacts.content_json`

```sql
-- Sample 100 rows recentes e verifica que content_json é JSON válido
SELECT id, stage, artifact_key FROM pipeline_artifacts
WHERE created_at > now() - interval '1 hour'
ORDER BY random() LIMIT 100;
-- Inspecione manualmente algumas; se JSONDecodeError aparece nos logs,
-- assume corrupção sistêmica até prova em contrário.
```

**Critério de acionamento:** ≥1 row com `content_json` inválido **OU**
≥1 stage com schema_version inesperado.

### 2.4. Healthcheck do worker

```bash
# /health do backend e endpoint Celery
curl -sf https://api.mathoms.ai/health/celery | jq '.celery_workers, .queue_depth'
```

**Critério de acionamento:** `celery_workers == 0` por >2min, **OU**
`queue_depth > 1000` por >5min com workers ativos.

---

## 3. Decision tree

```
┌─ ALERTA DETECTADO (§2)
│
├─ Escopo do incidente?
│
├─ A. Corrupção localizada em 1 workspace
│  └─ Restore por workspace (§4.1) — RTO ~5min · blast radius mínimo
│
├─ B. Regressão global (>5% runs failed em 1h)
│  └─ Revert PR via Git (§4.2) — RTO ~15min · sem perda de dados
│  └─ Se PR4 já está em produção:
│     └─ + Migration downgrade (§4.3) — +5min, recria coluna nullable
│
├─ C. Corrupção sistêmica em pipeline_artifacts (JSON inválido,
│      FK órfã, schema_version inconsistente)
│  └─ Restore full do snapshot (§4.4) — RTO ~30min · perda de dados
│      do intervalo entre snapshot e incidente (RPO ≤24h)
│
├─ D. Bug determinístico em código (não envolve corrupção de dados)
│  └─ Fix-forward — não usa este runbook. Patch + deploy normal.
│  └─ Se houver dúvida, freeze pipeline (§5) enquanto investiga.
│
└─ E. Worker não responde, queue saturada
   └─ Restart workers + check Redis (§4.5). Não envolve rollback de
      código.
```

---

## 4. Procedures de rollback

### 4.1. Restore por workspace (escopo localizado)

```bash
# 1. Identifique workspace afetado nos logs
WS_ID="<uuid do workspace>"
SNAP="/var/backups/mathoms/pre-deploy-<ts>.sql"

# 2. Freeze runs do workspace
psql -c "UPDATE workspaces SET frozen_at = now() WHERE id = '$WS_ID'"

# 3. Drop dados pós-incidente do workspace
psql <<SQL
DELETE FROM pipeline_artifacts WHERE workspace_id = '$WS_ID' AND created_at > '<deploy_ts>';
DELETE FROM pipeline_stage_logs WHERE pipeline_run_id IN (
  SELECT id FROM pipeline_runs WHERE workspace_id = '$WS_ID' AND created_at > '<deploy_ts>'
);
DELETE FROM pipeline_runs WHERE workspace_id = '$WS_ID' AND created_at > '<deploy_ts>';
SQL

# 4. Restaure rows do workspace a partir do snapshot
# (extrai apenas o subset relevante; psql restore filtrado)
pg_restore --table=pipeline_artifacts --table=pipeline_runs --table=pipeline_stage_logs \
  --data-only "$SNAP" | grep -E "workspace_id.*$WS_ID" | psql -d "$DB_NAME"

# 5. Unfreeze + smoke test
psql -c "UPDATE workspaces SET frozen_at = NULL WHERE id = '$WS_ID'"
# Run smoke test em workspace canário separado (não no afetado) primeiro.
```

> ⚠️ Restore por workspace **não toca outros workspaces** — operação
> minimiza blast radius. Use sempre quando o incidente é claramente
> localizado.

### 4.2. Revert PR via Git (regressão de código)

```bash
# 1. Identifique o PR culpado
gh pr list --state merged --limit 10 --json number,title,mergedAt

# 2. Crie PR de revert
gh pr revert <N>   # alternativa: git revert <merge-commit> + git push

# 3. Mergeia o revert com fast-track
gh pr merge <REVERT_PR_N> --squash --admin   # admin requer autorização explícita do owner em incidente

# 4. Aguarde deploy automático completar (CI/CD)
# 5. Smoke test em workspace canário
```

**Tempo típico:** 15min do detect ao revert deployado. Bypass de `--admin`
exige justificativa registrada em postmortem.

### 4.3. Migration downgrade (PR4 — drop coluna)

Se o incidente envolve PR4 ([[ADR-212]] §PR4 que dropa
`workspaces.use_db_artifacts_override`), o revert do código não
basta — a coluna precisa ser recriada para que `Workspace` ORM não
quebre ao ler.

```bash
# 1. Após revert do PR4 mergeado em main:
cd backend
alembic downgrade -1   # recria coluna nullable=True (sem dados — estrutura apenas)

# 2. Verifique
psql -c "\\d workspaces" | grep use_db_artifacts_override
```

> ⚠️ Dados de `use_db_artifacts_override` **são perdidos**. Em PR4 o
> guard pre-check assegurava que `count(*) = 0` no momento do upgrade —
> se necessário restaurar overrides hipotéticos, popular manualmente
> via SQL após downgrade.

### 4.4. Restore full do snapshot (corrupção sistêmica)

Procedimento destrutivo — usar **apenas** quando corrupção está
distribuída em múltiplos workspaces e restore por workspace é inviável.

```bash
SNAP="/var/backups/mathoms/pre-deploy-<ts>.sql"

# 1. Freeze ABSOLUTO do pipeline (§5)
# 2. Backup do estado atual ANTES de sobrescrever
pg_dump --table=pipeline_artifacts --table=pipeline_runs --table=pipeline_stage_logs \
  > "/var/backups/mathoms/pre-restore-$(date -u +%Y%m%dT%H%M%SZ).sql"

# 3. Truncate + restore das 4 tabelas
psql <<SQL
BEGIN;
TRUNCATE pipeline_stage_logs, pipeline_runs, pipeline_artifacts RESTART IDENTITY CASCADE;
-- workspaces preserva (estrutura imutável; só counts de override são afetados pelo snapshot)
COMMIT;
SQL

pg_restore --data-only --table=pipeline_artifacts --table=pipeline_runs \
  --table=pipeline_stage_logs "$SNAP" | psql -d "$DB_NAME"

# 4. Validação (§6)
```

**RPO:** dados pós-snapshot são perdidos. Comunique stakeholders +
abra postmortem obrigatório.

### 4.5. Worker/Redis recovery (não-rollback)

```bash
# Worker não responde:
kubectl rollout restart deployment/mathoms-worker
kubectl logs -l app=mathoms-worker --tail=100

# Queue saturada (Redis):
redis-cli -h "$REDIS_HOST" llen celery
# Se >5000 e workers OK: scale workers temporariamente
kubectl scale deployment/mathoms-worker --replicas=8
# Após drain: voltar para baseline (replicas=2)
```

---

## 5. Freeze do pipeline (escape hatch)

Quando o diagnóstico não é claro mas a regressão é grave, freeze imediato
do pipeline reduz blast radius enquanto investiga:

```bash
# Opção A — Pausa via flag de produto (canónica)
psql -c "UPDATE feature_flags SET enabled = false WHERE key = 'pipeline.enabled'"

# Opção B — Desliga workers (mais agressivo, queue acumula)
kubectl scale deployment/mathoms-worker --replicas=0
```

**Comunicação obrigatória** em #ops-incidents (Slack) + email para
on-call lead. Janela de freeze não-comunicada >15min é violação de SLO.

---

## 6. Validação pós-rollback

Após **qualquer** procedure de rollback:

```bash
# 1. Smoke test em workspace canário (não no incidente)
WS_CANARY="<uuid de workspace de teste/staging>"
curl -X POST https://api.mathoms.ai/v1/pipeline/run \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"workspace_id\":\"$WS_CANARY\",\"skip_llm\":true}"

# 2. Aguarde 30min com monitoramento ativo
# 3. Verifique counts pós-rollback vs pre-deploy
psql -c "SELECT count(*) FROM pipeline_artifacts" -t
diff /tmp/pre-deploy-artifact-count.txt <(psql -c "SELECT count(*) FROM pipeline_artifacts" -t)
# Diff esperado: zero ou positivo (não negativo).

# 4. Unfreeze
psql -c "UPDATE feature_flags SET enabled = true WHERE key = 'pipeline.enabled'"

# 5. Observação contínua por 1h após unfreeze
```

**Critério de "rollback OK":** smoke test verde + counts coerentes +
sem alertas no `mathoms.pipeline` por 30min consecutivos.

---

## 7. Pós-incidente

Toda operação deste runbook **exige postmortem** em
`docs/incidents/YYYY-MM-DD-<slug>.md` (template em
[docs/reference/runbooks/incidents/](incidents/)). Itens mandatórios:

1. Timeline (deploy → detect → rollback → unfreeze).
2. Root cause (5 whys).
3. Blast radius — quantos workspaces, quantas runs afetadas.
4. Snapshot usado (timestamp + path).
5. Janela RTO real vs alvo (≤30min).
6. RPO real (perda de dados) — quando aplicável.
7. Action items — sempre incluir: (a) reproduzir incidente em staging,
   (b) test de regressão se aplicável, (c) gate de CI se for
   regressão de código que passou.

---

## 8. Diferenças vs runbook legado ([[ADR-118]] cutover)

| Aspecto | Legado (ADR-118) | Atual (ADR-212) |
|---|---|---|
| Rollback rápido | `MATHOMS_USE_DB_ARTIFACTS=false` + redeploy (~5min) | Snapshot + revert PR + downgrade (~30min) |
| Pre-deploy gate | Backup recomendado | Snapshot **obrigatório** (CI/CD enforça) |
| Blast radius | Toda app (flag global) | Cirúrgico (por workspace ou por tabela) |
| Modo de falha | Hipotético (nunca exercitado em prod) | Documentado, exercitado em staging |
| Cobertura | Apenas cutover artifact-store | Corrupção, regressão, worker, queue, freeze |

---

## 9. Histórico de exercícios em staging

Atualize sempre que o procedure for exercitado (release prep, drill
trimestral, ou pós-incidente real):

| Data | Operador | Cenário exercitado | Resultado | RTO real |
|---|---|---|---|---|
| YYYY-MM-DD | — | Initial dry-run pre-PR3 merge | — | — |

---

## Referências

- [[ADR-212]] — Sunset `MATHOMS_USE_DB_ARTIFACTS` (canónica)
- [[ADR-118]] — Flip default para `True` (superseded)
- [docs/archive/cutover-2026-05-14.md](../../archive/cutover-2026-05-14.md) — Runbook legado de cutover arquivado
- [docs/reference/runbooks/f9_3_alembic_upgrade.md](f9_3_alembic_upgrade.md) — Padrão de runbook para migrations Alembic
- [docs/reference/runbooks/incidents/](incidents/) — Templates de postmortem
- [docs/_MOC/_generated/ADR_INDEX.md](../../_MOC/_generated/ADR_INDEX.md)
