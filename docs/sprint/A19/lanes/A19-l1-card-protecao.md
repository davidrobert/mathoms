---
id: A19.l1
type: lane
title: "S_PROTECAO — L1 Card 4º pilar AUVP no relatório (KPIs + 3 subgrupos + reposicionamento)"
sprint: A19
status: shipped
ship_prs:
  - "https://github.com/davidrobert/mathoms/pull/430"
  - "https://github.com/davidrobert/mathoms/pull/432"
  - "https://github.com/davidrobert/mathoms/pull/435"
  - "https://github.com/davidrobert/mathoms/pull/436"
ship_date: "2026-05-22"
priority: P1
branch_slug: a19-l1-card-protecao
depends_on: []
parallel_with: []
adrs:
  - "[[ADR-240]]"
prompt: "[[TRACK-a19-l1-card-protecao]]"
tags:
  - type/lane
  - sprint/a19
  - status/shipped
  - priority/p1
  - area/report
  - area/methodology
  - methodology/auvp
  - methodology/cerbasi
---

# A19.L1 — Card S_PROTECAO (4º pilar AUVP)

> **Onda única** em [[MOC-sprint-a19]]. Lane que entrega o card S_PROTECAO no relatório React posicionado **entre S2 (Reserva) e S4 (Patrimônio)** seguindo ordem AUVP. 4 KPIs V1, 3 subgrupos visuais, linguagem CRC.

## Objetivo

Materializar 4º pilar AUVP (Proteção) como card no relatório nativo React. Consome dados ingeridos pela Sprint A18 (CRLV + Apólices + FIPE). Sem A18 em `main`, card não tem o que renderizar.

## KPIs entregues (V1)

1. **G — Prêmio total anual + decomposição** (hero) — pizza por tipo (auto/residencial/vida-V2/saúde-V2)
2. **B — % renda anual em prêmios** — faixas Cerbasi (1-5%)
3. **F — Seguros ausentes** (qualitativo) — gating heurístico vida + saúde
4. **C — Gap de cobertura por bem** (auto V1) — `(valor_fipe - lmi_brl) / valor_fipe`

KPIs descartados V1 (movidos para V2 condicional):
- A (% patrimônio coberto) — denominador problemático
- D (multi-corretor warning) — vira nota neutra
- E (bônus em risco) — exige histórico de renovação

## Critério de aceite

- Card S_PROTECAO renderizado no relatório React posicionado entre S2 (Reserva) e S4 (Patrimônio).
- 4 KPIs (G/B/F/C) calculados e exibidos com faixas de sinal corretas ([[ADR-240]] D3).
- 3 subgrupos visuais (Bens / Pessoas / PJ); Pessoas e PJ com placeholder em V1.
- Linguagem CRC validada — zero verbo prescritivo ("deve", "precisa", "recomendamos"). Manual review obrigatório.
- Hierarquia tipográfica idêntica aos outros pilares S2/S3/S4 — S_PROTECAO não é "extras".
- Status de vigência visível por apólice (vigente/vencendo em 30d/vencida).
- Cross-link textual para S8 Previdência ("componente de proteção para beneficiários").
- KPI F vida usa `family_members.json` ([[ADR-127]]); sem dados, flag não dispara (degrada gracioso).
- Schema `protecao_patrimonial.schema.json` validado pelo hook pós-write [[ADR-212]].
- Fórmulas registradas em `docs/reference/FORMULAS.md` antes de implementar.
- Codegen `report_layout.yaml` ([[ADR-076]]) verde — TS + Python regenerados.
- Goldens E2E: 3 cenários — (a) só seguros de bens (caso owner), (b) sem nenhuma apólice (placeholder + F flag), (c) apólice combinada (subgrupo Bens com 2 linhas).
- E6-parecer ([[ADR-199]]) ganha narrativa de proteção quando KPI F flag — extensão prompt persona AUVP/Cerbasi.

## Pré-requisitos rígidos

- Sprint A18 inteira em `main` (L1 CRLV + L2 apólice + L3 FIPE).
- [[ADR-240]] mergeada como `Proposto`.

## Detalhe operacional

[[TRACK-a19-l1-card-protecao]].
