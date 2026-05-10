---
id: A11.report-publication
type: lane
title: "Report publication — mês fechado imutável"
sprint: A11
status: shipped
aliases: ["A11.REPORT_PUBLICATION", "A11 report publication"]
priority: P1
depends_on: []
parallel_with: ["[[A11.w2]]", "[[A11.w5]]", "[[A11.competitive-pierre]]"]
adrs_canonical:
  - "[[ADR-187]]"
tags:
  - type/lane
  - sprint/a11
  - status/shipped
  - priority/p1
  - area/report
  - area/methodology
---

# A11.report-publication — Mês fechado imutável

> Lane standalone — promovida de "P0 do learning loop" para lane própria
> em A11 por review `product-manager` sessão 2026-05-10. Mês fechado é
> decisão de produto independente: serve a Decision aggregate, IRPF
> declarado, cenários comparativos, e — quando entrar — a feature
> `cat-learning-loop` em A12.
>
> Decisão arquitetural: [[ADR-187]].

## Origem

Co-design `financial-planner` (sessão 2026-05-10) flagou que
re-categorização retroativa proposta em [[ADR-186]] (learning loop)
viola snapshot do mês fechado AUVP. Sem conceito de imutabilidade
temporal, regra criada em maio mudaria gráficos de janeiro, quebrando
contrato implícito com cliente.

PM moveu para A11 standalone porque: (a) reusabilidade — útil para outras
invariantes além do learning loop; (b) custo baixo (3d eng); (c) cabe
entre W2 e W3 do PLATFORM_REVIEW sem interferir.

## Track ready

[`report-publication-impl`](../tracks/report-publication-impl.md) ✅ ready.

## Branch prefix

`agent/report-publication-impl/<yyyyMMdd-HHmm>`

## Gate

Mergeia em `main` com:

- Migration up/down verde.
- Helper `is_month_closed()` coberto por testes unitários.
- Endpoints `POST/DELETE /workspaces/{ws}/reports/{period}/publish`
  cobertos por testes integration.
- Snapshot OpenAPI atualizado ([[ADR-109]]).
- Doc `docs/reference/REPORT_PUBLICATION.md` criada.
- Banner UI mínimo no relatório aparece quando publicação viva.
- [[ADR-187]] flippada para `Decidido (A11.report-publication)`.

## Status

☐ ready — aguarda pickup
