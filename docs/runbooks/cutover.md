# Runbook — Cutover `MATHOMS_USE_DB_ARTIFACTS` para workspaces existentes

> ADR-082, ADR-083, ADR-096 · Plano de migração §4.6 + §16
> Objetivo: migrar workspaces de `DiskArtifactStore` para `DBArtifactStore` sem perda de dados nem regressão de performance.

---

## 1. Pré-requisitos (não negociáveis)

Antes de qualquer cutover:

1. **Fases 1-4 do plano completas e em produção** ([_scratch/plano_migracao_artifacts_db.md](../../_scratch/plano_migracao_artifacts_db.md)):
   - Tabela `pipeline_artifacts` existe (migration `p4q5r6s7t8u9`).
   - `DBArtifactStore` testado (660+ testes backend verdes).
   - `backfill_artifacts_from_disk.py` testado em workspace de staging.
   - Feature flag `MATHOMS_USE_DB_ARTIFACTS` exposta no `backend/app/core/config.py`.
2. **Observabilidade** (ADR-096, §16 do plano):
   - `_scratch/compare_disk_vs_db.py` funcionando.
   - Métricas Prometheus expostas em `/metrics`.
   - Dashboard Grafana (ou equivalente) carregando os 5 painéis.
   - Alertas configurados e testados (fire + resolve).
3. **Backup recente** do DB de produção (`pg_dump` ou `sqlite3 mathoms.db .dump`).
4. **Runbook lido pelo oncall** — esta página.

> ⚠️ Se qualquer item acima falhar, **aborte** e escale para a liderança
> técnica. Cutover incompleto com dados truncados é irreversível sem restore.

---

## 2. Cronologia operacional

```
T-24h  → validação em workspace piloto + dashboard carregado
T-0    → flip da flag + pipeline completo no piloto
T+48h  → job nightly compare ativo + monitorar alertas
T+1sem → se nenhum alerta, expandir para próximos workspaces
T+30d  → remover processed/ em disco (fallback expira)
```

---

## 3. T-24h — Validação piloto

Escolher **1 workspace** de teste (preferir um com histórico pequeno para
começar — menor raio de explosão).

```bash
# 1. Backup do workspace piloto
sqlite3 mathoms.db ".dump" > _scratch/backup_pre_cutover_$(date +%Y%m%d).sql

# 2. Backfill idempotente (dry-run primeiro)
.venv/bin/python -m backend.app.scripts.backfill_artifacts_from_disk \
    --dry-run --workspace-id <uuid-piloto>

# Inspecionar saída — nenhum erro; contagens batem com `processed/`.

# 3. Aplicar backfill
.venv/bin/python -m backend.app.scripts.backfill_artifacts_from_disk \
    --apply --workspace-id <uuid-piloto>

# 4. Verificar paridade disk ↔ DB
.venv/bin/python _scratch/compare_disk_vs_db.py \
    --workspace-id <uuid-piloto> --strict

# Deve retornar 0 (sem diffs estruturais).

# 5. Confirmar dashboards
# Abrir Grafana → dashboard "cutover"
# Métricas: artifact_write_count, pipeline_run_duration, artifact_diff_count
# Verificar que alertas estão configurados e receiver (PagerDuty/Slack) responde
```

**Critério de abortar T-24h:**
- Backfill retorna erros em > 1% dos artefatos
- `compare_disk_vs_db` reporta diffs estruturais
- Dashboard não carrega

---

## 4. T-0 — Cutover do piloto

**Janela recomendada:** fora do horário de pico; avisar stakeholders.

```bash
# 1. Ativar flag globalmente
export MATHOMS_USE_DB_ARTIFACTS=true
# Redeploy backend + celery worker

# 2. Rodar pipeline completo no workspace piloto
curl -X POST "https://fin/api/workspaces/<uuid-piloto>/pipeline/run" \
    -H "Authorization: Bearer <token>" \
    -d '{"incremental": false}'

# 3. Acompanhar dashboard por 30 min
# - pipeline_run_duration_seconds{store="db"}: dentro de baseline × 1.5
# - pipeline_run_failed_total{use_db="true"}: 0
# - artifact_read_missing: 0

# 4. Comparação pós-run
.venv/bin/python _scratch/compare_disk_vs_db.py \
    --workspace-id <uuid-piloto> --strict
```

**Critérios de abortar T-0 (reverter imediatamente):**

| Alerta | Ação |
|--------|------|
| `CutoverRegression` (p95 > baseline × 1.5 por 15min) | `MATHOMS_USE_DB_ARTIFACTS=false` + redeploy |
| `ArtifactReadMissing` > 0 | Investigar antes de próximo workspace |
| `PipelineFailureSpike` (2× taxa de falha normal) | Reverter imediatamente |
| `compare_disk_vs_db` reporta diff | Pausar cutover; investigar |

**Reverter:**

```bash
# 1. Desativar flag
export MATHOMS_USE_DB_ARTIFACTS=false
# Redeploy

# 2. Pipeline volta a usar DiskArtifactStore
#    processed/ em disco ainda existe (fallback intacto)

# 3. Se DB tem dados errados: não é preciso limpar
#    (próximo run apenas não os usa; compare pode limpar manualmente)

# 4. Investigar root cause antes de nova tentativa
```

---

## 5. T+48h — Job nightly + expansão

Se T-0 + 48h sem alertas:

```bash
# 1. Agendar job nightly de paridade
# Exemplo: cron no servidor (ou Celery beat)
# 0 3 * * * .venv/bin/python _scratch/compare_disk_vs_db.py --workspace-id <uuid> | mail -s "cutover-diff" oncall@...

# 2. Se 7 dias consecutivos sem diff: marcar workspace como "migrado"
# 3. Repetir processo para próximo workspace (escalar tamanho aos poucos)
```

**Ordem recomendada de rollout:**

1. 1 workspace pequeno (~10 docs) de teste → 48h
2. 1 workspace médio (~50 docs) → 48h
3. Lote de 5 workspaces similares → 1 semana
4. Todos os restantes em lote → 2 semanas
5. Remover `processed/` em disco após 30 dias sem incidente

---

## 6. T+30d — Limpeza

Após 30 dias sem incidente no último workspace migrado:

```bash
# 1. Verificar que pipeline_artifacts tem dados para todos os workspaces
.venv/bin/python - <<'PY'
from backend.app.core.database import SyncSessionLocal
from backend.app.models import Workspace, PipelineArtifact
from sqlalchemy import func, select
with SyncSessionLocal() as s:
    rows = s.execute(
        select(Workspace.id, func.count(PipelineArtifact.id))
        .outerjoin(PipelineArtifact, PipelineArtifact.workspace_id == Workspace.id)
        .group_by(Workspace.id)
    ).all()
    for ws_id, n in rows:
        marker = "OK" if n > 0 else "VAZIO"
        print(f"{ws_id}: {n} artefatos [{marker}]")
PY

# 2. Workspaces com 0 artefatos: investigar antes de apagar processed/

# 3. Apagar processed/ por workspace (com backup)
for ws in <lista uuids>; do
    tar -czf backup_processed_${ws}.tar.gz storage/${ws}/processed/
    rm -rf storage/${ws}/processed/
done

# 4. Atualizar `reset_documents.py` e `e_reset.py` para não criar processed/ mais
# (já removido do hot path pela Fase 4.1; aqui é limpeza dos dados)
```

---

## 7. Troubleshooting

### "Pipeline falha com `KeyError: 'E3'` após ativar a flag"

Causa: algum consumidor ainda olha `processed/E3_reconciled/` em disco.

Fix: grep por referências não-migradas (`document_pipeline_sync`, endpoints
de report). Refactor para consultar `pipeline_artifacts` via store/repo.

### "compare_disk_vs_db reporta diff em floats"

Causa: arredondamento `float` → `Decimal` na leitura via domain models.

Fix: aceitável se |Δ| < tolerância configurada (default 0.01 BRL).
Diffs persistentes > tolerância: investigar serializador.

### "DBArtifactStore levanta `IntegrityError` com UNIQUE violation"

Causa: upsert não reaproveitando row (run_id/stage/key duplicada com
`document_id` diferente).

Fix: verificar `DBArtifactStore.write` usa upsert por `(pipeline_run_id,
stage, artifact_key)`. Logs em `PipelineArtifactRepository`.

### "Backfill cria runs sintéticas em workspaces com histórico"

Causa esperada: `backfill_artifacts_from_disk.py` cria `PipelineRun` sintética
se workspace não tem nenhuma run existente. Documentado em ADR-082.

Ação: aceitável — a run sintética é marcada `completed` e não afeta UI.

---

## 8. Referências

- [plano_migracao_artifacts_db.md §4.6 + §16](../../_scratch/plano_migracao_artifacts_db.md)
- [ADR-082 — PipelineArtifact](../DECISIONS.md#adr-082--pipelineartifact-artefatos-computacionais-no-banco)
- [ADR-083 — ArtifactStore](../DECISIONS.md#adr-083--artifactstore-abstração-de-io-para-artefatos)
- [ADR-096 — Observabilidade de cutover](../DECISIONS.md#adr-096--observabilidade-de-cutover)
- [SETUP.md §10 — Migração em curso](../SETUP.md#10-arquitetura-em-desenvolvimento)
