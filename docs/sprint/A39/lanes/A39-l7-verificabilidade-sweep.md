---
id: A39.l7
type: lane
title: "Sweep de verificabilidade: itau_xls + santander_xls declaram conservacao_verificavel (wise/rico cortados)"
sprint: A39
status: planned
priority: P1
branch_slug: a39-l7-verificabilidade-sweep
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

# A39.l7 — `verificabilidade-sweep` (achado PC-06)

## Problema (certificação 2026-07-23)

25 extratos passam a conservação float mas o parser **não declara**
`conservacao_verificavel=True` → não podem subir a `completo` (teto
`coberto-sem-verificação`). É o **maior driver do KR-B** (%completo). Parsers que
leem **ambos os saldos de forma independente** deveriam declarar a observação
para o gate HARD ([[ADR-342]] item 2) poder graduá-los.

**MISFRAMES corrigido (data-engineer):** o rascunho incluía 4 parsers, mas
**`parse_wise` e `parse_rico` DERIVAM saldo tautologicamente**
(`saldo_inicial = round(saldo_final − Σtx)`, `wise.py:161` / `rico.py:91`) → gap
sempre 0 por construção. Declarar verificabilidade neles **arma um gate HARD que
nunca dispara** = selo falso, e contradiz o docstring vigente da ADR-342
(`validation.py:26-28`, que estaciona Wise/Rico em WARN por serem tautológicos).
**Cortar wise + rico.**

## Escopo

- Declarar `conservacao_verificavel=True` **apenas** em:
  - `parse_itau_xls` — `saldo_inicial ← saldo_anterior` (`itau.py:257`),
    `saldo_final ← float(célula)` (`itau.py:228`), observados independentemente.
  - `parse_santander_xls` — `saldo_inicial ← saldo_anterior` (`santander.py:209`),
    `saldo_final ← saldo_values[-1]` (`santander.py:211`).
- **NÃO tocar** `parse_wise`/`parse_rico` (saldo derivado; permanecem WARN por
  design — comportamento correto, não regressão).
- Referencia [[ADR-342]] (mecanismo); sem ADR nova.

## Critério de aceite

- itau_xls + santander_xls: golden com arquivo limpo fecha conservação em cents
  e declara `conservacao_verificavel=True`; arquivo com row-drop conhecido escala.
- wise/rico: `conservacao_verificavel` permanece ausente (teste que falha se
  algum flipar — evita selo falso).
- Harness [[A39.l1]]: %completo sobe (KR-B; itau_xls domina o corpo dos 99
  `coberto-sem-verificação`).
- KR-E: nenhum extrato hoje correto muda de veredito por regressão.

## Risco

Baixo — flip de flag em parsers de saldo independente. O único risco (selo falso
em derivado) é eliminado cortando wise/rico. Maior driver do KR-B → P1 (subido
de P2 pelo painel).
