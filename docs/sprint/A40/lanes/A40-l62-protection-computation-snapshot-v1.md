---
id: A40.l62
type: lane
title: "ProtectionComputationSnapshotV1: fontes run-scoped e computabilidade por categoria"
sprint: A40
plan: PLAN-report-trust
status: blocked
priority: P1
branch_slug: a40-l62-protection-computation-snapshot-v1
adrs:
  - "[[ADR-387]]"
depends_on:
  - "[[A40.l61]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p1
  - area/backend
  - area/pipeline
  - area/persistence
  - area/financial-planning
---

# A40.l62 — `protection-computation-snapshot-v1`

> **Aberta bloqueada em 2026-08-13**, no co-design da [[A40.l35]]. Retoma
> depois que a [[A40.l61]] estiver `shipped`. Decisão arquitetural em
> [[ADR-387]] (`Proposto`).

## Problema

O Report aponta para um E5 exato, mas `Protection`, `FamilyMember` e `Workspace`
são estado vivo, e o adapter usa `date.today()`. Recompor o bundle no GET faria a
mesma fotografia mudar após edição de apólice, membro, perfil ou passagem do
calendário. Além disso, o E5 não possui hoje renda ativa líquida mensal nem
status/situs EUA suficientes; E1.x histórico não é recuperável por run sem
fallback `latest`.

## Escopo em dois PRs ordenados

1. **Fontes canônicas.** Contrato E5 para renda ativa anual e líquida mensal;
   patrimônio/dívida sem dupla soma; UF fiscal e exposição EUA explícitas;
   parâmetros ITCMD/US selecionados por vigência. Ausência permanece `null`.
2. **Snapshot do Report.** Migration nullable e contrato versionado com data de
   captura/análise/vigência, ids das fontes, cadastro observado, disponibilidade,
   inputs e output. A criação do Report persiste a fotografia; o GET apenas lê.

As duas partes formam uma propriedade única: “o relatório usa os insumos
vigentes quando foi gerado”. Nenhuma metade libera a S9 isoladamente.

## Critério de aceite

- Schema E5 × produtor estrito e golden de execução verdes; dinheiro em cents no
  snapshot e sem default zero para ausência.
- USD sem situs EUA não satisfaz `has_us_assets`; UF ausente não cai em SP.
- Parâmetro fiscal traz vigência/fonte; ausência ou ambiguidade retém a categoria.
- Snapshot contém versão, `captured_at`, `as_of_date`, proveniência e estados de
  computabilidade.
- Editar apólice, membro, perfil, parâmetro ou relógio depois da criação não muda
  o slice servido pelo mesmo `report_id`.
- Report legado sem snapshot não consulta estado live: proteção fica indisponível.
- Hash de publicação detecta qualquer alteração do snapshot composto.
- Migration, schema do overlay, OpenAPI/view-model snapshot e testes estão
  squash-mergeados em `main` antes de desbloquear a [[A40.l35]].
