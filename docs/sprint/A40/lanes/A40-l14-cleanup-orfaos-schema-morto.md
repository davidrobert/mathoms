---
id: A40.l14
type: lane
title: "Limpeza: schema órfão, quarentena inerte no read-path e cauda do A39"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P3
branch_slug: a40-l14-cleanup-orfaos-schema-morto
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p3
  - area/backend
  - area/dx
---

# A40.l14 — `cleanup-orfaos-schema-morto` (RV3-32 + handoff A39)

## Problema

**Schema órfão (RV3-32).** Tabela de custo órfã cuja fonte de verdade é outra
([[ADR-173]]) — higiene, sem efeito user-facing.

**Handoff pré-declarado.** O [[MOC-sprint-a39]] roteia explicitamente para a A40 a
cauda de duas lanes do A38 + os órfãos. Ignorar o handoff cria lane órfã com
backlink pendente — por isso é reconciliado **aqui**, não descartado em silêncio.

**Quarentena inerte.** Override quarentenado tem de ser inerte nos pontos de match
do razão (não em `documents.status`): sem isso ele casa por hash, polui o gate e
ressuscita silencioso.

## Escopo

- Drop da tabela órfã (migration + remoção dos modelos).
- Reconciliar a cauda do A38 declarada no A39: absorver, re-rotear ou **descartar
  com motivo escrito** — nenhuma das três em silêncio.
- Auditar os pontos de match do razão quanto a `orphaned_at IS NULL`.

## Critério de aceite

- Nenhum backlink pendente do [[MOC-sprint-a39]] para a A40.
- Cada item da cauda com disposição explícita.
- Teste: override quarentenado não casa em nenhum dos pontos de match.
