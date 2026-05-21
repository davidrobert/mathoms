---
id: TRACK-a15-fu3-onda2-backfill
type: track
title: "Track A15 FU-3 Onda 2 — Backfill total_dividas → rows Debt + audit log"
sprint: A15
plan: PLAN-imovel-financiado
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: data-engineer
tags:
  - type/track
  - sprint/a15
  - status/ready
  - area/db
  - area/migration
  - area/backend
---

# Track A15 FU-3 Onda 2 — Backfill total_dividas → Debt rows

> **Lane:** Sprint A15 · **Plano canônico:**
> [PLAN-imovel-financiado](../../../archive/IMOVEL_FINANCIADO-2026-05-20.md) §Onda 2
> · **ADR canônica:** [[ADR-227]] §D6
> · **Branch prefix:** `agent/a15-fu3-onda2-backfill/*`
> · **Pré-requisito externo:** Onda 1 mergeada em `main` (tabelas `debt` + `property_market_value` existem)
> · **Bloqueia:** Onda 3 (calculator) — recomendado rodar backfill em dogfood antes do calculator novo, evita goldens E5 quebrarem por mudança de dados.

## Briefing

Script de **backfill em stage separado** da Alembic ([[ADR-227]] §D6 + CLAUDE.md §"Backfill é stage separado"). Extrai `total_dividas` agregado por membro do `baseline_patrimonial` existente → cria rows `Debt` com `source='baseline_irpf_migration'`, `tipo='outro'`, `needs_review=true`, `property_id=NULL`.

**Não tenta heurística** para atribuir property — falso-positivo garantido com >1 imóvel. Usuário linka manualmente via UI batch review (Onda 5).

**Idempotência via partial unique index** criado na Onda 1: `(workspace_id, migration_source_key) WHERE source='baseline_irpf_migration'`. Re-run é no-op por workspace já migrado.

**Audit log obrigatório** em `storage/<workspace>/logs/debt_migration_audit.json` (gitignored). Dry-run é default; persiste só com `--apply`.

## Critério de aceite (do plano §Onda 2)

- [ ] Script `dev/backfill_debt_from_baseline.py` com flags:
  - `--workspace-id <id>` (obrigatório, ou `--all-workspaces`)
  - `--dry-run` (default true — reporta o que faria, não persiste)
  - `--apply` (persiste; mutuamente exclusivo com `--dry-run`)
  - `--audit-dir <path>` (default `storage/<workspace>/logs/`)
- [ ] Audit JSON com schema mínimo: `{workspace_id, run_at, dry_run, members: [{key, total_dividas_brl, created_debt_id, action}]}`. `action ∈ {would_create, created, skipped_already_migrated, skipped_zero}`.
- [ ] Idempotência: 1ª run `--apply` persiste; 2ª run `--apply` no-op por partial unique index; 3ª run `--dry-run` reporta `skipped_already_migrated`.
- [ ] Test integration com workspace seed:
  - Workspace com 2 membros (titular + cônjuge), ambos com `total_dividas > 0` → 2 rows Debt criadas.
  - Workspace com 0 dívidas → 0 rows; script reporta `skipped_zero`.
  - Workspace já migrado → re-run no-op.
- [ ] Runbook em [docs/reference/RUNBOOK.md](../../../reference/RUNBOOK.md) §"Backfill de Debt".
- [ ] Workspace dogfood `5@5.com` migrado em `--dry-run` + audit log inspecionado em PR review; depois `--apply` em commit separado dentro do mesmo PR (ou PR sequencial).
- [ ] `pre-commit run --all-files` verde.

## Arquivos esperados

**Novos:**

- `dev/backfill_debt_from_baseline.py` (script CLI)
- `backend/tests/integration/test_backfill_debt_from_baseline.py` (test com fixtures seed)
- Entrada em [docs/reference/RUNBOOK.md](../../../reference/RUNBOOK.md) §Backfill de Debt

**Editados:**

- Nenhum em runtime (script standalone).

## Decisões já fechadas (do co-design 2026-05-19)

- **Backfill é stage separado** (CLAUDE.md §"Backfill é stage separado") — Migration Alembic na Onda 1 só `CREATE TABLE` (zero UPDATE). Backfill em N workspaces vira lock + replication lag se feito na Alembic.
- **Não tenta heurística** de atribuição a property (regex `'%financiamento%' OR '%imobiliário%'`) — `data-engineer` + `product-designer` convergiram: falso-positivo garantido com >1 imóvel; usuário linka via UI batch review (Onda 5).
- **`tipo='outro'`** em rows de migration — não tenta inferir tipo de descrição. Usuário ajusta no batch review.
- **`needs_review=true`** sempre — toda Debt extraída do baseline exige confirmação humana antes de afetar `investivel_efetivo` (gate na Onda 3 do calculator).
- **`migration_source_key = f"{workspace_id}_{member_key}"`** — chave de idempotência consumida pelo partial unique index criado na Onda 1.
- **Dry-run default** — anti-pattern de migration destrutiva acidental. `--apply` exigido explicitamente.
- **Audit log JSON estruturado** em `storage/<workspace>/logs/` (gitignored) — paridade com pattern de outros scripts de migration (CLAUDE.md §Logging).

## Testes (comandos exatos)

```bash
# Dry-run em workspace seed
python3 dev/backfill_debt_from_baseline.py --workspace-id <seed-id> --dry-run
# verificar storage/<seed-id>/logs/debt_migration_audit.json gerado

# Apply em workspace seed
python3 dev/backfill_debt_from_baseline.py --workspace-id <seed-id> --apply

# Re-run apply é no-op
python3 dev/backfill_debt_from_baseline.py --workspace-id <seed-id> --apply
# audit log mostra todos `skipped_already_migrated`

# Test integration
pytest backend/tests/integration/test_backfill_debt_from_baseline.py -q
pytest backend/tests -q   # paridade
pre-commit run --all-files
```

## Riscos

- **R1** — Workspace com vários IRPFs (multi-ano) pode ter `total_dividas` acumulado de forma errada no baseline. **Mitigação:** baseline E1.5c consume `baseline_patrimonial-1.5_consolidated` que já é deduplicado por [[ADR-225]] (canonicalizer cascade). Test integration com fixture multi-ano cobre.
- **R2** — `Decimal` → `int cents` conversion deve usar `int(Decimal(...) * 100)` com floor/round explícito. Floor implícito do `int()` truncaria 999.999 → 99999 cents (deveria ser 99999 ou 100000?). **Mitigação:** test com valores fracionários (R$ 1.234,56 → 123456 cents). Pattern de [`backend/app/models/`](../../../../backend/app/models/) já consagrado.
- **R3** — Script roda em todos os workspaces de prod simultaneamente quando `--all-workspaces`. **Mitigação:** flag exige confirmação explícita + audit log per-workspace; runbook recomenda rodar 1 workspace por vez em produção (dogfood primeiro).
- **R4** — Audit log em `storage/<workspace>/logs/` é gitignored, pode ser apagado em cleanup. **Mitigação:** runbook documenta backup do audit log antes de `--apply` em prod.

## Ligações

- Plano canônico: [PLAN-imovel-financiado](../../../archive/IMOVEL_FINANCIADO-2026-05-20.md) §Onda 2
- ADR canônica: [[ADR-227]] §D6
- Sprint MOC: [[MOC-sprint-a15]]
- Onda 1 (pré-req): [a15-fu3-onda1-schema](a15-fu3-onda1-schema.md)
- Onda 3 (próximo): [a15-fu3-onda3-calculator](a15-fu3-onda3-calculator.md) — runtime começa aqui, ideal rodar backfill em dogfood antes
- ADRs relacionados: [[ADR-225]] (canonicalizer cascade), [[ADR-090]] (cents)
- CLAUDE.md §"Backfill é stage separado"
- Pattern reuso: scripts em `dev/` similares (não em `scripts/` — não é stage de pipeline)
