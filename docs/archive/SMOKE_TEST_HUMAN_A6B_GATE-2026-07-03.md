# [ARQUIVADO 2026-07-03] Smoke Test Humano — conteúdo do gate A6b.5 → A6c

> Extraído de `docs/reference/SMOKE_TEST_HUMAN.md` em 2026-07-03 (decisão do
> owner na triagem do audit-vault r6, finding F03). O gate foi **executado e
> aprovado** (A6b→A6c concluídas em 2026-04/05); a §4.7 auditava a
> coexistência disco↔DB que [[ADR-212]] removeu — `DiskArtifactStore`, a flag
> `use_db_artifacts_override`, o campo `artifact_store_mode` no `/health` e
> `dev/compare_disk_vs_db.py` não existem mais. O runbook vivo (checks gerais
> + §4.9 override v2 + registro de snapshots) permanece em
> `docs/reference/SMOKE_TEST_HUMAN.md`.

## Cabeçalho original (A6b.5 · ADR-103)

> **Quem executa:** David Robert (owner do projeto)
> **Objetivo:** Validar end-to-end o sistema antes da remoção do bridge (A6c).
> **Bloqueante para:** A6c (deletar `MaterializationBridge` + `stage_runner_compat`).
> **Resultado esperado:** Todos os checks passam → decisão explícita: "Aprovado para A6c" ou "Bloqueado — bug #X".

## 4.7 Cutover DB — Opt-in por Workspace (5 checks — core A6b)

- [x] **A7.1** `GET /health` retorna `artifact_store_mode: "disk"` por padrão
- [x] **A7.2** Ativar `use_db_artifacts_override = TRUE` para o workspace smoke:
  ```bash
  sqlite3 mathoms-smoke.db "UPDATE workspaces SET use_db_artifacts_override=1 WHERE name='Smoke Premium';"
  ```
- [x] **A7.3** Re-rodar pipeline → `GET /health` mostra `artifact_store_mode: "db"` para este workspace
- [x] **A7.4** Tabela `pipeline_artifacts` no DB tem entradas para o run
- [x] **A7.5** `python dev/compare_disk_vs_db.py <ws_id> --strict` retorna ≥99% paridade

## 5. Decisão Final (formato do gate A6c)

**Data do teste:** _______________

**Executado por:** _______________

**Checks aprovados:** _____ / 46

**Bugs encontrados:**
| ID | Severidade | Descrição | Stack/evidência |
|----|-----------|-----------|-----------------|
|    |           |           |                 |

**Decisão:**

- [x] ✅ **APROVADO para A6c** — todos os checks P0 passaram, bugs encontrados são P1/P2
- [ ] ❌ **BLOQUEADO** — bug(s) P0 impedem A6c: _______________

**Assinatura (David):** _______________

## Troubleshooting: compare_disk_vs_db reporta divergência

Divergências **esperadas** (não são bugs):
- `_meta.confidence` / `_meta.notes` em artefatos E2-llm
- `created_at` / `updated_at` (timestamp de escrita diferente entre DB e disco)
- Ordem de listas JSON (transações, investimentos) — E3-E7 são order-insensitive

Divergências **que são bugs**:
- Key presente em disco mas ausente no DB (stage não escreveu via store)
- Conteúdo divergente em campos monetários ou de transações

## 7. Após aprovação — A6c

Quando o sinal humano for dado (checkbox §5 marcado ✅), executar:

```bash
# A6c — Remove bridge (somente após aprovação)
python dev/commit.py -m "refactor: remove MaterializationBridge + stage_runner_compat (A6c)"
```

Arquivos a deletar (A6c):
- `pipeline/stage_runner_compat.py`
- `pipeline/materialization_bridge.py`
- `main(root_dir)` legado dos 7 scripts determinísticos

Atualizar docs: ARCHITECTURE §17.3, CHANGELOG, CLAUDE.md.
