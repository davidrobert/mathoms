---
id: A26.l10
type: lane
title: "LGPD export — cobertura total das tabelas com dados pessoais (Art.18)"
sprint: A26
status: shipped
priority: P2
branch_slug: lgpd-export-cobertura
ship_pr: 732
adrs:
  - "[[ADR-275]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a26
  - status/shipped
  - priority/p2
  - area/lgpd
  - area/backend
---

# A26.l10 — `lgpd-export-cobertura` (fora do tema da sprint — decisão do owner, audit r4)

> **Origem:** finding **r2-new-2** do [[AUDITS-active]] (auditoria
> r2, reverificada 2026-06-30; `procede-aberto` por 2 rodadas). Em 2026-07-02 o
> owner decidiu na triagem da r4: **vira lane P2** — não é escolha consciente de
> escopo do Art.18.

## Problema

`backend/app/services/lgpd_export_service.py` exporta transações, documentos e
perfil, mas **não exporta** os aggregates `Debt`, `PropertyIdentity`, `Vehicle`,
`Protection`, `Risk` e `TransactionOverride` — todos contêm dados pessoais do
titular (dívidas, imóveis, veículos, apólices, overrides manuais) e ficam fora
da portabilidade do Art.18 da LGPD.

## Escopo

1. Estender o export para as 6 famílias ausentes (JSON estruturado, mesmo
   formato das seções existentes; dinheiro serializado como nos DTOs — nunca
   float em cálculo, [[ADR-090]]).
2. **Teste de cobertura estrutural**: enumerar models SQLAlchemy com FK direta
   ou transitiva para `workspaces`; cada um deve estar (a) no export ou (b) numa
   allowlist explícita de exclusão com rationale de 1 linha (ex.: tabela
   técnica sem dado pessoal). Novo model fora das duas listas → teste falha.
   É o mecanismo anti-recorrência — sem ele o gap reabre a cada aggregate novo.
3. Alinhar com a retenção/erasure de [[ADR-275]] (cascade FK) — o que o erasure
   apaga, o export deve cobrir.

## Fora de escopo

- Export de artefatos de pipeline (`pipeline_artifacts`) — derivados, não
  fornecidos pelo titular; documentar na allowlist.
- UI de download (endpoint existente já serve o JSON).

## Critério de aceite

- Export de workspace dogfood contém as 6 famílias novas com dados reais.
- Teste de cobertura estrutural verde e falhando sob mutação (remover uma
  família do export → vermelho).
- `make update-openapi-snapshot` se o response model mudar ([[ADR-109]]).
- PR mergeado em `main` com CI verde; disposição r2-new-2 atualizada no
  AUDITS-active para `procede-fechado`.
