---
id: A39.l2
type: lane
title: "C6 Bank CSV: declarar conservacao_verificavel (semântica de saldo já correta) → escala perda silenciosa"
sprint: A39
status: shipped
ship_date: "2026-07-23"
ship_pr: 1039
priority: P0
branch_slug: a39-l2-c6-csv-optin-verificabilidade
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/dados
---

# A39.l2 — `c6-csv-optin-verificabilidade` (achado PC-02)

## Problema (certificação 2026-07-23)

`parse_c6bank_csv` grava conservação materialmente quebrada em **WARN
silencioso**: dois extratos do corpus com gap **+R$1.978** (#637b) e **−R$296**
(#5a21). A causa **não** é falta de gate — o gate HARD da [[ADR-342]] já existe;
é opt-in por-parser e o C6 CSV **não opta**. Verificado (data-engineer): a
semântica de saldo do CSV é **ancorada e correta**
(`saldo_inicial = saldo_first − first_valor`, `c6bank.py:232`) — **não**
tautológica (≠ Wise/Rico que derivam `saldo_final − Σtx` → gap sempre 0). Logo,
o gap é **perda de linha real** (44 duplicatas intra-arquivo reportadas → dedup
possivelmente agressivo), e flipar o flag o escala como true-positive **de
graça**, pelo gate existente.

## Escopo

- Verificar que um arquivo C6 CSV **limpo** fecha conservação em cents (gap==0)
  — golden sintético PII-zero.
- **Flipar `conservacao_verificavel=True`** em `parse_c6bank_csv` (só declara a
  observação; o gate detém a política, padrão [[ADR-342]] item 2).
- Investigar o dedup intra-arquivo (44 candidatas) — se está derrubando linha
  real, o gap passa a fechar; senão, escala honesto.
- Referencia [[ADR-342]] (mecanismo existente); **sem ADR nova, sem emenda** —
  é conformidade ao contrato vigente.

## Critério de aceite

- Golden: arquivo C6 CSV limpo → `conservacao_verificavel=True`, gap cents == 0.
- Golden: arquivo com row-drop conhecido → escala
  (`escalation_reason.code == extract.incomplete_conservation`).
- Harness [[A39.l1]]: #637b/#5a21 saem de `coberto-sem-verificação` para
  `completo` (se o dedup for o culpado e fechar) **ou** `escalado-honesto`
  (KR-A). Nunca mais silenciosos.
- KR-E: parsers não tocados idênticos; nenhum C6 CSV hoje bom regride.

## Risco

Baixo — flip de flag num parser de semântica já verificada. `depends_on`
[[A39.l1]] (baseline congelado). Hotspot `c6bank.py` compartilhado com
[[A39.l4]] — sequenciar l2→l4.
