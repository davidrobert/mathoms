---
id: A39.l6
type: lane
title: "Checksum de CDB observável: traço checksum_ok/skipped_no_total + WARN posições-sem-total; estender Santander xlsx"
sprint: A39
status: planned
priority: P1
branch_slug: a39-l6-cdb-checksum-observavel
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/planned
  - priority/p1
  - area/pipeline
  - area/dados
---

# A39.l6 — `cdb-checksum-observavel` (achado PC-05)

## Problema (certificação 2026-07-23)

`_apply_cdb_checksum` (`santander.py:871`, introduzido pela emenda [[A38.l12]] na
[[ADR-342]]) é um **no-op silencioso** quando `total_declarado is None` (o regex
de total erra) e **não deixa traço no pass** → a certificação não distingue
"checksum passou" de "checksum pulou". É o mesmo anti-padrão de silêncio que a
[[A38.l14]] matou para dormência.

## Escopo

- **Emenda datada à [[ADR-342]]** (protocolo ADR-027, commit separado):
  observabilidade do checksum de posição — emitir `checksum_ok: bool` /
  `checksum_skipped_no_total` como sinais **distintos**; WARN quando há
  `posicoes` mas `total_declarado is None`.
- Estender a cobertura **só onde há total agregado independente**
  (data-engineer): **`parse_santander_cdb_xlsx`** lê `"Valor Total:"` no header
  (`santander.py:277`) → passar como `total_declarado` → checksum legítimo.
- **`parse_itau_cdb_pdf`** emite **posição única** sem total agregado
  (`itau.py:942`) → resultado correto é `skipped_no_total` (honesto), **não** um
  checksum — não força cobertura falsa.
- Contrato cents idêntico (`round(abs(soma−total)*100) != 0`) — extensão
  mecânica, contract-safe.

## Critério de aceite

- `total_declarado is None` emite `checksum_skipped_no_total` (traço no pass) +
  WARN quando há posições — teste.
- Santander xlsx com total → `checksum_ok=True` (cents); com mismatch → escala
  (`extract.investment_sum_mismatch`).
- Itaú CDB PDF → `skipped_no_total` (não checksum) — assert.
- KR-C/KR-D contam `checksum_ok` **separado** de `skipped_no_total` (no-op não
  infla cobertura).

## Risco

Baixo — observabilidade + extensão mecânica de um contrato cents já decidido.
Emenda de calibração, sem ADR nova.
