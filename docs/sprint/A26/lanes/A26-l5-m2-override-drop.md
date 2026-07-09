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
> **Bloqueada por [[A26.l4]]** (override v2 ON + gate auditável) + gates G1/G2/G2b/G3 + PITR +
> **go/no-go do owner**. Co-design `data-engineer` (migration) + `sre-devops` (runbook).
> **Maior risco da sprint — cortável sem dó para A27** se a janela de tráfego for curta.
> Nunca forçar sob gate apertado: perda irreversível de identidade de override.

## Decisão 2026-07-09 — CORTADA do fechamento A26/A27; deferida owner-gated

**Decisão do owner (2026-07-09), conforme precedência de corte da [[MOC-sprint-a27]]
("cortável sem dó").** Esta lane **não bloqueia** A26→`done` nem A27→`done` — vira
item deferido do plano [[PLAN-data-lineage]], **herdando este gate verbatim**
(G1/G2/G2b/G3 + PITR + go/no-go). Racional: (a) o gate G2/G2b **reiniciou** com o
fix dos órfãos no índice de match (PR #878) e exige ≥1 sprint de janela verde;
(b) pré-trabalho de código obrigatório descoberto pelo runbook (#873): `row_id`
do read-path ainda deriva de `generate_transaction_hash` (PR de migração em
andamento), view `transaction_overrides_active` e índice parcial
`uq_txov_active_rule` dependem da coluna; (c) PITR não confirmado (RUNBOOK §5
trata DR como pendente); (d) custo de manter o dual-read (agora correto) ≈ zero.

**Pré-condições nomeadas para agendar a execução** (todas, sem ordem):
1. Janela G2/G2b ≥1 sprint verde **pós-#878** (`v1_fallback==0 AND v2_match>=1
   AND divergence==0` via `audit_logs`).
2. Pré-trabalho `row_id` → identidade v2 mergeado.
3. PITR/backup confirmado pelo owner (pré-condições sre-devops abaixo).
4. Decisão do owner sobre os 4 órfãos re-casáveis (recuperar exige emenda da
   [[ADR-282]] §5; default: seguem inertes).

Runbook pronto: [`docs/reference/runbooks/override_legacy_drop.md`](../../../reference/runbooks/override_legacy_drop.md)
(#873, com drafts de migration + sentinela G3 em apêndice).

## Objetivo

Remover o estado legado de identidade v1 do override, fechando a convergência para
`natural_key` v2. Drop **na mesma PR** de: coluna `transaction_hash` + UK velha
`uq_override_ws_hash` + função `generate_transaction_hash` (`transaction_service.py`) +
ramo v1/fallback de `override_dual_read.py` + flag `override_natural_key_v2_enabled` vira
no-op. (A [[A25.l1]] §5 cravou: `generate_transaction_hash` deletado na mesma PR da M2.)

## Gate (condições conjuntas, auditáveis — verificar TODAS antes do drop)

- **G1 (estado de dado):** `SELECT count(*) FROM transaction_overrides WHERE
  natural_key_hash IS NULL AND orphaned_at IS NULL` **== 0** (todo override é v2-ancorado
  ou quarentenado). Quarentenados (`orphaned_at IS NOT NULL`) **NÃO bloqueiam** — estado
  terminal permanente ([[ADR-282]] §5).
- **G2 (cobertura — fallback zero COM exercício real):** via [[A26.l4]] — `sum(v1_fallback)==0
  AND sum(v2_match)>=1` por ≥1 sprint sob flag-ON (query sobre `audit_log`).
- **G2b (corretude — NOVO, co-design 2026-07-01, [[ADR-282]] §Emenda item 3):**
  `sum(divergence_count)==0` na janela, via shadow-compare (flag `override_dual_read_shadow_compare`,
  instrumentado pela [[A26.l4]]). G2 sozinho mede **cobertura**, não corretude: o `match`
  retorna no 1º hit v2 sem consultar v1, então override grudado na linha errada deixa
  `v1_fallback==0` (verde falso). Sem G2b, o drop irreversível remove o único fallback que
  mascararia a divergência.
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

- G1/G2/G2b/G3 verdes com snapshot no `SMOKE_TEST_HUMAN.md` (timestamp + contagens).
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
