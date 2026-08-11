---
id: A40.l37
type: lane
title: "A tabela de IR tem três fontes, e uma é hardcoded contra a ADR-135"
sprint: A40
plan: PLAN-report-trust
status: blocked
priority: P2
branch_slug: a40-l37-tabela-de-ir-tres-fontes
adrs:
  - "[[ADR-135]]"
  - "[[ADR-236]]"
  - "[[ADR-375]]"
depends_on:
  - "[[A40.l34]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p2
  - area/pipeline
---

# A40.l37 — `tabela-de-ir-tres-fontes`

> **Aberta em 2026-08-11**, achado do co-design da [[A40.l34]] (`senior-cto`).
> Registrada como §Não-objetivo da [[ADR-375]].
>
> **`blocked` por [[A40.l34]]**: o resolver comum que esta lane consome nasce
> lá (D6). Abrir antes seria construir o consumidor antes do produtor.

## Problema

A mesma regra — "qual a faixa marginal de IR desta renda" — tem **duas
implementações vivas**, sobre **três** fontes de tabela:

| Produtor | Fonte da tabela | Escala | Semântica |
|---|---|---|---|
| `_resolve_aliquota` (S7) | `fiscal_parameters.ir_brackets` (DB, [[ADR-135]]) | anual | **errada** — [[ADR-375]] |
| `_ir_marginal_anual` (S8, `cascata_triggers.py:50`) | `IRRF_TABELA_MENSAL` **hardcoded** (`cascata_calculator.py:41`) | mensal | correta |
| — | `aliquota_fallback = 7,5%` quando as faixas chegam vazias | — | nenhuma |

A tabela hardcoded é **tensão direta com a [[ADR-135]]**, que pôs os parâmetros
fiscais no DB versionados por data justamente para que uma MP nova não exija
deploy de código.

Ambos publicam "economia de IR" no **mesmo documento, sobre a mesma pessoa, por
regras diferentes**. É a mesma classe que nomeia a [[A40.l34]], um andar abaixo.

## Escopo

Migrar `cascata_triggers._ir_marginal_anual` para o resolver comum que a
[[A40.l34]] cria (D6 da [[ADR-375]]), e retirar `IRRF_TABELA_MENSAL` em favor de
`fiscal_parameters`.

**Fora de escopo:** recalibrar limiar ou copy dos triggers T1/T3. A unificação
da regra resolve a divergência; recalibrar é outra conversa.

## Critério de aceite

- Um único produtor de faixa marginal no repo, com fonte única [[ADR-135]].
- `IRRF_TABELA_MENSAL` não existe mais, **ou** existe só como fixture de teste
  com a origem declarada.
- **Delta declarado com sinal próprio:** isto muda T1/T3 publicados, que são
  superfície da [[ADR-236]]. Não pode entrar agregado com o delta da
  [[A40.l34]] — foi por isso que ficou em lane separada.
- Conversor de escala mensal↔anual **explícito**, não implícito no call-site.
