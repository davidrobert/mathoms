---
id: A39.l5
type: lane
title: "Bradesco: diagnosticar saldo R$1/R$1 (raiz não confirmada) + teste de independência antes de flipar"
sprint: A39
status: planned
priority: P1
branch_slug: a39-l5-bradesco-saldo-diagnostico
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

# A39.l5 — `bradesco-saldo-diagnostico` (achado PC-04)

## Problema (certificação 2026-07-23)

`parse_bradesco` grava conservação quebrada em #f658: `saldo_inicial =
saldo_final = R$1,00` (sentinela) com `Σtx = −R$83.528,84` → gap enorme, não
escala. `saldo_final = R$1` **é consumido** → o patrimônio caixa da conta lê
R$1 (errado).

**Refutado (financial-planner + verificação):** o over-count "299 tx > 219
linhas datadas" — 0 duplicatas exatas `(data,valor,desc)`; o layout imprime
**data 1×/dia** com N movimentos abaixo (95 datas, máx 7 tx/data) → **299 é a
contagem correta**, não duplicação. As transações estão provavelmente completas;
o bug é **saldo**.

**Ressalva (data-engineer):** o "default R$1" **não foi confirmado no código** —
`parse_bradesco` lê `saldo_inicial` (`bradesco.py:126`) e `saldo_final`
(`bradesco.py:405`) de forma independente; grep de fallback não revelou o R$1.
Pode ser miss de extração (lê a linha errada) neste layout, não um literal.

## Escopo

- **Diagnosticar a raiz** do `R$1/R$1` para o layout de #f658 (miss de extração
  vs default) — fixture sintética PII-zero reproduzindo o layout; **confirmar a
  evidência antes de enquadrar o fix** (não shippar sobre premissa não-verificada).
- Corrigir a extração de saldo (a raiz confirmada).
- **Teste de independência** (data-engineer): `saldo_inicial` e `saldo_final`
  vêm de células/linhas observadas independentemente (não derivadas de Σtx) →
  só então bradesco vira candidato legítimo a `conservacao_verificavel=True`.
- Após corrigir + passar independência: flipar o flag (referencia [[ADR-342]]).

## Critério de aceite

- Raiz do R$1 documentada (fixture reproduz) antes do fix; regressão red-first.
- Saldo real extraído; #f658 fecha conservação em cents (se tx completas) ou
  escala (KR-A). Patrimônio caixa da conta ≠ R$1.
- Teste de independência de saldo verde antes do flip.
- KR-E: extratos bradesco (extratoconta + os 7 poupança) hoje corretos
  inalterados.

## Risco

Baixo-médio — raiz não confirmada exige diagnóstico antes do fix. Mitigação:
fixture do layout + confirmação de evidência como gate de abertura.
