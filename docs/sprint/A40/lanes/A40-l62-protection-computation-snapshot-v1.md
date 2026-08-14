---
id: A40.l62
type: lane
title: "ProtectionComputationSnapshotV1: fontes run-scoped e computabilidade por categoria"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l62-protection-computation-snapshot-v1
adrs:
  - "[[ADR-387]]"
depends_on:
  - "[[A40.l61]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/pipeline
  - area/persistence
  - area/financial-planning
---

# A40.l62 — `protection-computation-snapshot-v1`

> **Aberta bloqueada em 2026-08-13**, no co-design da [[A40.l35]], e
> **desbloqueada em 2026-08-14** após a [[A40.l61]] shippar no PR #1443.
> Decisão arquitetural em [[ADR-387]] (`Decidido` em 2026-08-14).

## Problema

O Report aponta para um E5 exato, mas `Protection`, `FamilyMember` e `Workspace`
são estado vivo, e o adapter usa `date.today()`. Recompor o bundle no GET faria a
mesma fotografia mudar após edição de apólice, membro, perfil ou passagem do
calendário. Além disso, o E5 não possui hoje renda ativa líquida mensal nem
status/situs EUA suficientes; E1.x histórico não é recuperável por run sem
fallback `latest`.

## Escopo em dois PRs ordenados

1. **Fontes e regras canônicas.** Contrato E5 person-scoped para renda líquida,
   dependência, segurado/benefício/inventário e cenários fiscais; rule-sets
   ITCMD/FBAR/FATCA/Estate NRA por vigência; correção dos calculators atuais.
   Ausência permanece `null`; nenhum PR1 liga a S9.
2. **Snapshot e integridade.** Migrations nullable de Report/publicação,
   envelope V1, captura transacional e hash `report-v2`. O GET apenas injeta o
   bundle persistido; legado não consulta estado live.

As duas partes formam uma propriedade única: “o relatório usa os insumos
vigentes quando foi gerado”. Nenhuma metade libera a S9 isoladamente.

## Critério de aceite

- Schema E5 × produtor estrito e golden de execução verdes; dinheiro em cents,
  pessoa/check explícitos e nenhum default zero para ausência.
- Vida/invalidez não cruzam segurados; capital único não vira benefício mensal;
  inventário parcial não vira cobertura zero.
- Sucessório é cenário por pessoa/direito; FBAR, FATCA e Estate NRA têm bases e
  status separados. USD não prova situs e UF ausente não cai em SP.
- Parâmetro fiscal traz rule-set, vigência e fonte; zero ou ambiguidade retêm só
  a instância afetada.
- Snapshot contém versão, `captured_at`, `as_of_date`, proveniência, versões de
  calculator e estados por instância.
- Editar apólice, membro, perfil, parâmetro ou relógio depois da criação não muda
  o slice servido pelo mesmo `report_id`.
- Report legado sem snapshot não consulta estado live: proteção fica indisponível.
- Publicação nova referencia o Report e hash `report-v2` detecta qualquer
  alteração semântica; `e5-v1` legado continua verificável.
- Migration, schema do overlay, OpenAPI/view-model snapshot e testes estão
  squash-mergeados em `main` antes de desbloquear a [[A40.l35]].
