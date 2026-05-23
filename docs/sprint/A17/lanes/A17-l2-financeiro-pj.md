---
id: A17.l2
type: lane
title: "Informes anuais — L2 financeiro PJ (C6 PJ, Stone, adquirentes)"
sprint: A17
status: in_progress
priority: P1
branch_slug: a17-l2-financeiro-pj
depends_on:
  - "[[A17.l1]]"
parallel_with:
  - "[[TRACK-a16-adr236-tributario-pj-cascata]]"
adrs:
  - "[[ADR-238]]"
  - "[[ADR-236]]"
prompt: "[[TRACK-a17-l2-financeiro-pj]]"
tags:
  - type/lane
  - sprint/a17
  - status/in-progress
  - priority/p1
  - area/pipeline
  - area/methodology
  - methodology/cerbasi
---

# A17.L2 — Financeiro PJ (C6 PJ, Stone, adquirentes)

> **Onda 2 de 4** em [[MOC-sprint-a17]]. **Sinergia direta com [[ADR-236]] em construção** — alimenta `irpf_renda_tributavel.py` via `InformeQuery` service.

## Objetivo

Modelar `tipo_informe="financeiro_pj"` ponta a ponta. Permite que cascata fiscal PJ ([[ADR-236]] D2) funcione sem depender exclusivamente de E1.6 — workspace com informe PJ mas sem declaração entregue.

## PDFs do batch destravados

- Informe C6 PJ 2025
- Informe Stone PJ 2025

## Critério de aceite

- C6 PJ e Stone PJ 2025 classificam como `tipo_informe="financeiro_pj"` com `confidence ≥ 0.7`.
- `InformeQuery` service em `backend/app/application/informes/` consumido por `irpf_renda_tributavel.py` ([[ADR-236]] D2).
- Cascata fiscal PJ ([[ADR-236]] D6) funciona para workspace **sem** E1.6 mas com informe PJ.
- Distinção PF/PJ no `institutions.tax_regime` propaga sem explodir entries (C6 e Stone têm `tax_regime="both"`).
- Workspaces com E1.6 + informe PJ: declaração vence ([[ADR-238]] D4); divergência gera warning em E5.
- 12 PDFs do batch fora desta onda continuam em `.other` sem regressão.

## Coordenação

Síncrona com agente responsável por [[TRACK-a16-adr236-tributario-pj-cascata]] L2 antes do PR. Gate G3 em [[ADR-238]] §Gates.

## Detalhe operacional

[[TRACK-a17-l2-financeiro-pj]].
