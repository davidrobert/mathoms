---
id: A18.l3
type: lane
title: "Comprovantes de Bem — L3 FIPE refresh assíncrono via BrasilAPI"
sprint: A18
status: shipped
ship_prs:
  - "https://github.com/davidrobert/mathoms/pull/431"
  - "https://github.com/davidrobert/mathoms/pull/433"
ship_date: "2026-05-22"
priority: P2
branch_slug: a18-l3-fipe
depends_on:
  - "[[A18.l1]]"
parallel_with:
  - "[[A18.l2]]"
adrs:
  - "[[ADR-239]]"
prompt: "[[TRACK-a18-l3-fipe-refresh]]"
tags:
  - type/lane
  - sprint/a18
  - status/shipped
  - priority/p2
  - area/pipeline
  - area/persistence
---

# A18.L3 — FIPE refresh assíncrono (BrasilAPI)

> **Onda 3 de 3** em [[MOC-sprint-a18]]. Lane infraestrutural: integração open-source via BrasilAPI, cache em `market_rates` ([[ADR-135]]), **lookup nunca síncrono** no upload — Celery task.

## Objetivo

Modelar valor de mercado FIPE atualizado para veículos no relatório. **Pré-requisito:** L1 (CRLV) já criou tabela `vehicles.fipe_code`; L2 (apólice) já popula `fipe_code` quando vem no doc.

## Por que BrasilAPI (decidido em [[ADR-239]] D5)

- Open-source comunitário (zero lock-in)
- $0 custo runtime
- API estável e ativa
- Sem auth/contract
- Endpoint direto `/fipe/preco/v1/<code>` quando `fipe_code` já conhecido (90% dos casos quando apólice presente)

## Critério de aceite

- Migration Alembic adiciona `market_rates.reference_month` (ex.: `'2026-12'`) — FIPE muda mensalmente.
- `series_type='fipe_vehicle'` aceito em `market_rates` schema.
- `FipeLookupClient` via Protocol/adapter ([[ADR-097]] D2) — facilita teste com `InMemoryFipeLookup`.
- **Lookup é assíncrono** — Celery task `refresh_fipe_value(fipe_code, ano_modelo)` enfileirada por hook pós-write em `DBArtifactStore`.
- Cache hit (TTL = 30 dias após `reference_month`) → retorna; miss → HTTP BrasilAPI + persiste.
- Stage E1.5c tolera `fipe_status in {fresh, stale_acceptable, pending_refresh, missing}` — só `missing` em veículo ativo bloqueia (passa por `needs_review`).
- **Cron job Janeiro/<ano>** atualiza Dezembro/<ano-1> para todos `fipe_codes` ativos em `vehicles` — base para IRPF do exercício seguinte.
- Goldens: cenário (a) FIPE conhecido → cache hit; (b) FIPE conhecido + cache miss → mock HTTP retorna valor; (c) FIPE desconhecido → `needs_review`.
- Teste unitário valida que stage **não bloqueia** em HTTP — sincronia degradada falha imediatamente.
- FIPE codes do batch real: 827125-9 (NMAX 2024), 8271020 (NMAX 2018), 15253 (Toro 2022).
- Catálogo `institutions` ganha entry `brasilapi` (`category='reference_data'`).

## Coordenação

L1 (CRLV) precisa estar em `main` (tabela `vehicles` existe). Paralela a L2 (apólice) — não competem por arquivos. Pode ser puxada por agente distinto de L2.

## Detalhe operacional

[[TRACK-a18-l3-fipe-refresh]].

## Entrega — V1 (P1 + P2)

V1 entregue em 2 PRs squash-mergeados em `main` (CI verde):

- **P1** [#431](https://github.com/davidrobert/mathoms/pull/431) — `FipeLookupClient` Protocol + `InMemoryFipeLookup` (fake determinístico) + `BrasilAPIFipeClient` (adapter HTTP) + Celery task `refresh_fipe_value` (backoff exponencial 120s→960s) + 24 testes parser/validation/InMemory + 13 testes cache flow/persist (37 verde).
- **P2** [#433](https://github.com/davidrobert/mathoms/pull/433) — Celery beat `fipe-refresh-annual` (cron `15-Jan 03:00 UTC`) + batch enfileira todos `fipe_codes` distintos ativos + `read_fipe_cache` helper consumido por A19 (status fresh|stale_acceptable|pending_refresh) + 9 testes (46 verde no agregado FIPE).

## Débitos rastreados — V2 (não bloqueiam shipping)

- **P3 — Hook E5 que enfileira refresh em cache miss**. V1 só consulta cache via `read_fipe_cache`; ProtecaoAnalyzer (A19) usa `pending_refresh` quando ausente. Hook que dispara `refresh_fipe_value.delay()` automaticamente em miss fica para quando houver evidência de necessidade (owner reporta valores defasados).
- **Goldens BrasilAPI mock HTTP**. V1 tem 37 testes da função pura + cache flow com `InMemoryFipeLookup`; goldens com `httpx_mock` cobrindo response real BrasilAPI (3 cenários ADR-239 G6 — cache hit, miss+HTTP, fipe desconhecido) ficam como sub-PR.
- **Catálogo `institutions.brasilapi`**. Entry `category='reference_data'` documentada na ADR-239 D5 mas não seedada — usado apenas em logs (`source='brasilapi'` em `market_rates.source`). Migrar quando houver caso de uso para exibir provedor no relatório.
- **Stage E1.5c propaga `fipe_status`** para `baseline.veiculos_consolidados[]` — V2; hoje o helper é consumido apenas pelo A19 P3 ProtecaoAnalyzer runner via `read_fipe_cache`.
