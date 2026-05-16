---
id: TRACK-f9-3-alembic-migration
type: track
title: "Track F9.3 — Alembic migration: rename `pipeline_artifacts.stage` em massa"
sprint: F9
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/f9
  - status/consumed
---

# Track F9.3 — Alembic migration: rename `pipeline_artifacts.stage` em massa

> **Lane ID:** F9.3
> **Branch prefix:** `agent/f9-stage-rename/3-alembic/*`
> **Depende de:** F9.2 ✅ (código de produção emite descritivo; lê legado via compat)
> **Paralelo com:** nenhum
> **Conflita com:** qualquer commit em `backend/alembic/versions/`
> **Onda:** F9 (sub-fatia 4/7)
> **Índice de prompts:** [README.md](../../../../README.md)
> **Fonte de verdade:** [ADR-093](../../../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a) · [migration scaffold já em repo](../../../../backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py)

> **Objetivo:** validar e fechar a Alembic migration `q5r6s7t8u9v0_rename_stage_identifiers`
> que reescreve `pipeline_artifacts.stage` e `pipeline_stage_logs.stage` dos
> identificadores legados para os descritivos. Adicionar testes de
> upgrade+downgrade, smoke contra DB de dev, e procedimento de pré-deploy
> documentado.

---

## Por que este slice agora

A migration **já existe** ([backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py](../../../../backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py))
mas está scaffolded — precisa:

1. Bater com `STAGE_RENAME_MAP` atual (pós-ADR-129 sem E6).
2. Ter testes upgrade/downgrade isolados.
3. Procedimento de pré-deploy documentado (backup, sanity check).
4. Janela de manutenção decidida (em dev, irrelevante; em prod, F7+).

Em F9.2 o app passou a **emitir** stage descritivo mas **lê** rows legadas via
`resolve_stage_name`. Esta migration fecha a brecha — após upgrade, todas as
rows estão em descritivo, e `resolve_stage_name` continua aceitando legado
(idempotente).

---

## Regras inegociáveis

1. **Backup obrigatório antes de upgrade em prod.** Migration documenta
   `sqlite3 mathoms.db .dump > backup_pre_f9.sql`. Em dev, opcional mas
   recomendado.
2. **Idempotente.** Re-rodar `alembic upgrade head` após sucesso é no-op.
   Conseguir via `WHERE stage IN (<legacy_keys>)` — descritivos não batem.
3. **Downgrade é simétrico** — mapeia descritivo → legado. Não dropa coluna.
   Se downgrade não for trivialmente reversível, **não** force; documente
   "downgrade requer regenerar artifacts" e bloqueie.
4. **Sanity gate antes do UPDATE:** a migration **lê** `SELECT DISTINCT stage`
   antes de qualquer UPDATE; se aparece valor não mapeado, aborta com
   mensagem clara (não silenciosamente "não-op").
5. **Não toca outras colunas.** Migration é um `UPDATE stage = X WHERE stage = Y` cirúrgico em 2 tabelas. Nada mais.

---

## Entregas

### 1. Validar/atualizar [migration q5r6s7t8u9v0](../../../../backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py)

- Confirmar `STAGE_RENAME` interno bate com `STAGE_RENAME_MAP` em `pipeline/stage_spec.py`. **Não** importe de `pipeline/` (alembic deve ser self-contained — copiar o dict é OK e idiomático).
- Adicionar pré-check: `SELECT DISTINCT stage` antes do UPDATE; abortar se aparecer valor desconhecido (não em `STAGE_RENAME` keys ∪ values).
- `pipeline_stage_logs` (se existe — F9.0 confirmou) tem `UPDATE` simétrico.
- Reports.* — verificar se `Report.stage` (se existir) também precisa rename. F9.0 confirma.

### 2. Testes — `backend/tests/test_stage_rename_migration.py`

5 testes mínimos (do plano ADR-093):

```python
def test_upgrade_renames_pipeline_artifacts_rows(alembic_engine):
    # Insere rows com stage="E3", "E5", "E5.N"
    # Roda upgrade head
    # Asserta stage = "reconcile_transactions", "analyze_finances", "generate_narratives"

def test_upgrade_renames_pipeline_stage_logs_rows(alembic_engine):
    # análogo

def test_upgrade_aborts_on_unknown_stage(alembic_engine):
    # Insere stage="E99-fake"
    # Asserta upgrade levanta erro com mensagem útil

def test_upgrade_is_idempotent(alembic_engine):
    # Roda upgrade duas vezes
    # Asserta segunda invocação no-op

def test_downgrade_restores_legacy_names(alembic_engine):
    # Upgrade + downgrade
    # Asserta volta ao estado inicial
```

Use fixture `alembic_engine` (já no repo? F9.0 confirma; senão criar isolada com SQLite in-memory + Alembic stamp).

### 3. Smoke local

```bash
sqlite3 mathoms.db ".dump" > _scratch/backup_pre_f9.sql

# Inspecionar antes
sqlite3 mathoms.db "SELECT DISTINCT stage FROM pipeline_artifacts;"

# Upgrade
cd backend && alembic upgrade head

# Inspecionar depois
sqlite3 ../mathoms.db "SELECT DISTINCT stage FROM pipeline_artifacts;"
# Esperado: apenas nomes descritivos

# Smoke run da app — abrir relatório existente, conferir que ainda renderiza
# (resolve_stage_name lê descritivo direto; legado não existe mais)
```

### 4. Procedimento de pré-deploy — `docs/reference/runbooks/f9_3_alembic_upgrade.md`

Runbook curto (~50 linhas):
1. Backup obrigatório.
2. `SELECT DISTINCT stage FROM pipeline_artifacts` — confirmar 100% mapeado.
3. Janela de manutenção combinada (em dev: irrelevante; em prod: F7+).
4. `alembic upgrade head` (com timeout esperado em rows grandes).
5. Smoke pós-upgrade.
6. Rollback: `alembic downgrade -1` + restore de backup se necessário.

---

## Sequência de execução

```bash
git fetch origin && git status
git checkout -b agent/f9-stage-rename/3-alembic/$(date +%Y%m%d-%H%M)

# 1. Atualizar migration (pré-check + STAGE_RENAME alinhado com pós-ADR-129)
# 2. Escrever 5 testes em backend/tests/test_stage_rename_migration.py
pytest backend/tests/test_stage_rename_migration.py -q

# 3. Smoke local (mathoms.db dev)
# 4. Escrever docs/reference/runbooks/f9_3_alembic_upgrade.md

# Gate
pre-commit run --all-files
pytest backend/tests -q
pytest tests -q

# Drift
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q

git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] `q5r6s7t8u9v0_rename_stage_identifiers.py` `STAGE_RENAME` interno = `STAGE_RENAME_MAP` em `pipeline/stage_spec.py` (sem E6/E6-final residual).
- [ ] Pré-check rejeita stage desconhecido com mensagem útil.
- [ ] 5 testes em `test_stage_rename_migration.py` verdes.
- [ ] Idempotência: `alembic upgrade head` 2× = no-op na 2ª.
- [ ] Downgrade restaura keys legadas (testado).
- [ ] Smoke local com `mathoms.db` dev: zero erro pós-upgrade; relatório renderiza normal.
- [ ] `docs/reference/runbooks/f9_3_alembic_upgrade.md` documenta procedimento + rollback.
- [ ] BACKLOG + CHANGELOG atualizados.

---

## Rollback criteria — ABORTE se

- Pré-check encontra stage não mapeado em `mathoms.db` dev — provavelmente
  débito de F9.0/F9.2 não fechado. Volte e investigue antes de seguir.
- Downgrade quebra app em smoke (rows ficam em descritivo mas registry espera legado) — significa que `resolve_stage_name` reverso (descritivo → legado) não existe; adicione antes de mergear migration.
- Migration roda mas DB fica inconsistente (algumas rows descritivas, outras legadas) — investigue (provavelmente algum INSERT em meio ao upgrade).

---

## Atualizar documentação (obrigatório, último passo)

1. **`docs/BACKLOG.md`** — lane F9 status: `🚧 F9.0/.1/.2 ✅ · F9.3 ✅ — Alembic migration validada YYYY-MM-DD; F9.4 destravada (scripts/ rename)`.
2. **`docs/CHANGELOG.md`** — entrada datada:
   ```markdown
   ### 2026-MM-DD — F9.3 Alembic stage rename (ADR-093)

   - `backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py`
     valida e renomeia `pipeline_artifacts.stage` + `pipeline_stage_logs.stage`
     dos identificadores legados para descritivos.
   - 5 testes em `backend/tests/test_stage_rename_migration.py`:
     upgrade/downgrade/idempotência/sanity.
   - `docs/reference/runbooks/f9_3_alembic_upgrade.md`: procedimento pré-deploy +
     rollback.
   - Smoke dev: rows do mathoms.db migradas; app continua funcional via
     `resolve_stage_name`.
   ```
3. **`docs/reference/RUNBOOK.md`** — referenciar o novo runbook.
4. **`docs/DECISIONS.md`** ADR-093 — nota datada "F9.3 fechada YYYY-MM-DD".
5. Commit docs separado: `docs(f9): F9.3 alembic + runbook, F9.4 destravada (ADR-093)`.

---

## O que esta fatia NÃO entrega

- **Filenames `scripts/e*.py`** — F9.4.
- **Switch hard-fail no guardrail.** F9.5.
- **Remoção de `STAGE_RENAME_MAP` + aliases.** F9.6.
- **Janela de manutenção em prod.** Em dev (sem prod ainda) o upgrade é local; em F7+, runbook é executado pelo time de deploy.

---

## Referências

- F9.2 (prereq): [track_f9_2_string_literals.md](f9-2-string-literals.md)
- F9.4 (próximo): [track_f9_4_scripts_rename.md](f9-4-scripts-rename.md)
- Migration scaffold: `backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py`
- ADR-093: `docs/DECISIONS.md:2228`
