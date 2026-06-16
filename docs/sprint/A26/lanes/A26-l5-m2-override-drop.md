---
id: A26.l5
type: lane
title: "M2-B — drop destrutivo do estado legado de identidade do override (Fase E)"
sprint: A26
plan: PLAN-data-lineage
status: blocked
priority: P2
branch_slug: m2-override-drop
adrs:
  - "[[ADR-282]]"
depends_on:
  - "[[A26.l4]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a26
  - status/blocked
  - priority/p2
  - area/data-lineage
  - area/infra
---

# A26.l5 — `m2-override-drop` (Regime B · DESTRUTIVO IRREVERSÍVEL · cortável p/ A27)

> **Plano:** [[PLAN-data-lineage]] · executa a "Fase E" do [[ADR-282]] (M2 destrutiva).
> **Bloqueada por [[A26.l4]]** (override v2 ON + gate auditável) + gates G1/G2/G3 + PITR +
> **go/no-go do owner**. Co-design `data-engineer` (migration) + `sre-devops` (runbook).
> **Maior risco da sprint — cortável sem dó para A27** se a janela de tráfego for curta.
> Nunca forçar sob gate apertado: perda irreversível de identidade de override.

## Objetivo

Remover o estado legado de identidade v1 do override, fechando a convergência para
`natural_key` v2. Drop **na mesma PR** de: coluna `transaction_hash` + UK velha
`uq_override_ws_hash` + função `generate_transaction_hash` (`transaction_service.py`) +
ramo v1/fallback de `override_dual_read.py` + flag `override_natural_key_v2_enabled` vira
no-op. (A [[A25.l1]] §5 cravou: `generate_transaction_hash` deletado na mesma PR da M2.)

## Gate (3 condições conjuntas, auditáveis — verificar TODAS antes do drop)

- **G1 (estado de dado):** `SELECT count(*) FROM transaction_overrides WHERE
  natural_key_hash IS NULL AND orphaned_at IS NULL` **== 0** (todo override é v2-ancorado
  ou quarentenado). Quarentenados (`orphaned_at IS NOT NULL`) **NÃO bloqueiam** — estado
  terminal permanente ([[ADR-282]] §5).
- **G2 (fallback zero COM exercício real):** via [[A26.l4]] — `sum(v1_fallback)==0 AND
  sum(v2_match)>=1` por ≥1 sprint sob flag-ON.
- **G3 (sentinela de código):** `dev/check_no_legacy_override_hash.py` (novo) falha se
  `transaction_hash`/`generate_transaction_hash` reaparecer em `backend/app`/`pipeline`.

## Escopo

- **Migration Alembic destrutiva** (`pytestmark = pytest.mark.migration`):
  - `upgrade`: `SET lock_timeout`; **hard-assert de G1 embutido** (re-roda o count e
    `raise RuntimeError` se ≠ 0 — defesa em profundidade); drop UK + índice + coluna.
  - `downgrade`: `raise RuntimeError` explicando irreversibilidade + caminho PITR (NÃO
    `pass`, NÃO `NotImplementedError`). Sem `IF EXISTS` defensivo (one-shot deve falhar
    ruidoso em re-run).
- Deletar `generate_transaction_hash` + ramo v1 do dual-read + flag no-op (mesma PR).
- `make update-openapi-snapshot` se `transaction_hash` era exposto em `TransactionOverrideResponse`.
- **Confirmar antes do drop:** o read-path já devolve `natural_key_hash` como key opaca do
  FE (`row_id`), não `generate_transaction_hash` — senão o FE perde o match. Item de aceite.
- **Runbook "Fase E"** (`docs/reference/runbooks/`, espelha `pipeline_rollback.md`, 11
  seções): pré-condições/gates, backup/PITR, execução gate-then-drop (janela de segundos),
  verificação pós-deploy sem rollback, contingência (restore PITR/snapshot com perda),
  observação 1h+24h, sign-off do owner, histórico de staging.

## Pré-condições operacionais (sre-devops — bloqueadores duros)

- **Backup pré-drop obrigatório:** `pg_dump` dados + `pg_dump -s` schema, sha256, não-vazio.
  PITR confirmado (LSN registrado) OU explicitamente "N/A → RPO = ts do snapshot".
  Retenção 30d, purge documentado (LGPD).
- **Confirmar capacidade PITR do Postgres (Coolify)** — `RUNBOOK §5` trata DR como pendente.
- **Janela:** baixo tráfego + freeze de escrita de override; snapshot→count→drop em segundos.
- **In-place** (não blue/green — teatro para drop irreversível single-tenant).
- **Go/no-go: owner do produto** assina com evidência anexada (counts, histórico de
  fallback, dogfood verde); SRE/agente executa após sign-off.

## Critério de aceite

- G1/G2/G3 verdes com snapshot no `SMOKE_TEST_HUMAN.md` (timestamp + contagens).
- Migration exercitada em **staging** antes da prod; hard-assert testado (fixture com 1
  override legado não-quarentenado → migration aborta); `downgrade` testado para `raise`.
- Model SQLAlchemy não referencia mais a coluna **no mesmo PR**; ORM lê override sem erro.
- Pós-drop: `\d` confirma coluna sumiu; `/health` 2xx; goldens E3/E4/E5 + view-model verdes;
  `check_no_legacy_override_hash.py` verde no `main`; read-path devolve `natural_key_hash` como key.
- Backup + PITR-check + sign-off do owner registrados no runbook antes do merge.
- **[[ADR-282]] flippa `Proposto → Decidido (A26)`** no merge (fecha a Fase E).
- Postmortem obrigatório se a contingência for acionada.

## Owner

Agente da lane; co-design `data-engineer` (migration/gate) + `sre-devops` (runbook/PITR).
Go/no-go do **owner do produto** (drop irreversível com dado de tenant).
