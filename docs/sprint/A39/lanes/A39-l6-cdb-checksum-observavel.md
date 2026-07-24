---
id: A39.l6
type: lane
title: "Checksum de CDB observável: traço checksum_ok/skipped_no_total + WARN posições-sem-total; estender Santander xlsx"
sprint: A39
status: shipped
ship_date: "2026-07-23"
ship_pr: 1043
priority: P1
branch_slug: a39-l6-cdb-checksum-observavel
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/dados
---

# A39.l6 — `cdb-checksum-observavel` (achado PC-05 · reconciliado com #1036)

> **Reconciliação com `main`:** a **cobertura** do checksum de CDB foi **entregue
> por #1036** (`a63ec80f`) **durante a autoria** — `apply_cdb_checksum` estende-se
> a CDB XLSX (Santander, total = "Valor Total" bruto) e HTML-XLS (Itaú, total =
> `resumo.saldo_bruto_final`), soma em **int cents** (ADR-090), escopo bruto×bruto;
> posição única Itaú PDF permanece **sem** sum-checksum (degenerada, já coberta
> pelo gate de 0-posição). **Resta só a observabilidade do traço.**

## Problema (certificação 2026-07-23, pós-#1036)

`apply_cdb_checksum` (`validation.py`, emenda [[ADR-342]] l12 + #1036) **não deixa
traço positivo** quando o checksum passa, e faz `return` silencioso quando
`total_declarado is None` — a certificação não distingue "checksum passou" de
"checksum pulou por falta de total". É o mesmo anti-padrão de silêncio que a
[[A38.l14]] matou para dormência, no lado positivo do pass.

## Escopo (residual — observabilidade)

- Emitir `checksum_ok: bool` no result quando o checksum **passa** (traço
  positivo) e `checksum_skipped_no_total` quando `total_declarado is None` mas há
  `posicoes` — sinais **distintos** no artefato (não só o WARN de mismatch, que
  já existe).
- WARN quando há `posicoes` mas total ausente (hoje `return` mudo).
- Sem ADR nova (o contrato/cobertura já está em `main`); no máximo emenda fina de
  observabilidade se o schema exigir declarar os campos.

## Critério de aceite

- `total_declarado is None` com posições → `checksum_skipped_no_total` (traço) +
  WARN — teste.
- Checksum que passa → `checksum_ok=True` no artefato — teste.
- KR-C/KR-D contam `checksum_ok` **separado** de `skipped_no_total` (no-op não
  infla cobertura).

## Risco

Baixo — só observabilidade sobre um contrato cents já entregue (#1036). Escopo
encolhido pela reconciliação com `main`.
