---
id: TRACK-a18-l3-fipe-refresh
type: track
title: "Track A18 L3 — FIPE refresh assíncrono via BrasilAPI: market_rates extension + Celery task + cron anual"
lane: "[[A18.l3]]"
sprint: A18
status: ready
created_at: "2026-05-21"
consumed_at: null
agent_role: sre-devops
tags:
  - type/track
  - sprint/a18
  - status/ready
  - area/pipeline
  - area/persistence
---

# Track A18 L3 — FIPE refresh assíncrono (BrasilAPI)

> **Lane:** [[A18.l3]] · **ADR canônica:** [[ADR-239]] §D5 · **Pré-requisito:** [[A18.l1]] (CRLV — tabela `vehicles.fipe_code` existe) · **Paralela com:** [[A18.l2]] (apólice)
> · **Branch prefix:** `agent/a18-l3-fipe/*` · **Tamanho estimado:** ~3d eng em 2 PRs

## Briefing

L1 criou `vehicles.fipe_code` (vem do CRLV ou da apólice L2). Esta lane integra **BrasilAPI** para resolver valor de mercado FIPE atualizado. **Lookup nunca síncrono no upload** — Celery task enfileirada por hook pós-write.

## Decisões já fechadas (não reabrir)

- **BrasilAPI** como provedor (open-source comunitário, zero lock-in, $0 custo) — análise comparativa em [[ADR-239]] §Alternativas A3/A4.
- **Extensão `market_rates`** com `series_type='fipe_vehicle'` + nova coluna `reference_month TEXT` (FIPE muda mensalmente).
- **Lookup assíncrono via Celery** — hook pós-write `DBArtifactStore` ([[ADR-212]]) enfileira `refresh_fipe_value(fipe_code, ano_modelo)`. Stage produz `fipe_value=None, fipe_status='pending_refresh'`.
- **`FipeLookupClient` via Protocol/adapter** ([[ADR-097]] D2) — facilita teste com `InMemoryFipeLookup`.
- **Cache TTL 30 dias** após `reference_month` — depois disso, fresh refresh.
- **Cron job Janeiro/<ano>** atualiza Dezembro/<ano-1> para todos `fipe_codes` ativos em `vehicles`.
- Stage E1.5c tolera `fipe_status in {fresh, stale_acceptable, pending_refresh, missing}` — só `missing` em veículo ativo bloqueia.
- `institutions` ganha entry `brasilapi` (`category='reference_data'`).

## Plano (esqueleto — refinar no pickup)

- **P1** — Migration `market_rates.reference_month` + `FipeLookupClient` Protocol + adapter HTTP + cache hit/miss flow + Celery task `refresh_fipe_value`. Teste unitário com `InMemoryFipeLookup` + mock HTTP.
- **P2** — Cron job Janeiro (Celery beat) + integração com stage E1.5c (consolidate_baseline) — propaga `fipe_status` e `valor_mercado_atualizado`. Goldens 3 cenários (cache hit, miss+HTTP, fipe desconhecido).

## Pegadinhas (do co-design data-engineer)

- **Nunca HTTP síncrono no upload** — degradação BrasilAPI 500ms→30s mata UX. Teste unitário deve travar regressão.
- **`reference_month` obrigatório** — FIPE muda mensalmente; cache stale silently wrong.
- **Refresh anual em Janeiro** consulta Dezembro/<ano-1> — base para IRPF do exercício seguinte (alinha com fonte fiscal).
- **BrasilAPI rate limit** não documentado oficialmente — implementar backoff exponencial + fallback `pending_refresh` em 429/5xx.
- **FIPE codes do batch real**: 827125-9 (NMAX 2024), 8271020 (NMAX 2018), 15253 (Toro 2022).

## Critério de aceite (lane completa)

Em [[A18.l3]] §Critério de aceite. Destrava valor de mercado atualizado para veículos.
