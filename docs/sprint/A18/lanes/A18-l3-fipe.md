---
id: A18.l3
type: lane
title: "Comprovantes de Bem — L3 FIPE refresh assíncrono via BrasilAPI"
sprint: A18
status: planned
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
  - status/planned
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
