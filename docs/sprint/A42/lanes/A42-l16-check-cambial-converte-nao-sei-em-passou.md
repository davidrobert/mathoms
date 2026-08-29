---
id: A42.l16
type: lane
title: "O check de cobertura cambial converte 'não sei o tier' em 'passou'"
sprint: A42
status: planned
priority: P0
branch_slug: a42-l16-check-cambial-converte-nao-sei-em-passou
owner: senior-cto
depends_on: []
adrs:
  - "[[ADR-418]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p0
  - area/pipeline
---

# A42.l16 — `check-cambial-converte-nao-sei-em-passou`

> **Origem:** `PV10-01` da rodada unificada **U2** ([[PIPELINE-REVIEWS-active]] §r10,
> merge `47970706`). Verificado literalmente no código.

## O defeito

`scripts/validate_cross.py:640`:

```python
coberto = len(apurados) == len(componentes) or tier == "indeterminado"
```

A disjunção é uma **escotilha de sinal invertido**: quanto **menos** o sistema sabe, mais
fácil o check passa. No run medido o CV18 saiu `passed: true, severity: info` com
`não apurados=[…]; tier=indeterminado` — um componente não apurado e o tier desconhecido, e o
resultado publicado é verde.

**A política correta está no mesmo módulo, 400 linhas acima** (`:227-229`, CV5):
*"ausência é 'não sei', nunca 'bate'"*. E `_cv18` **já sabe** devolver `None`
(`:628-630`, `if not componentes: return None`).

## Distinga de dois vizinhos

- `PV9-14` é *"definição impressa ≠ implementada"* — produtor é a **calculadora**.
- `PV9-15` foi **REFUTADO** na U2: o tier nunca trocou de sinal;
  `carteira_lastro_estrangeiro` é fixado `Cobertura.indeterminado` **incondicionalmente**
  desde `6c546d7b` (2026-08-21), e `_tier_from_pct` é **código morto em produção** — a
  [[A40.l80]] §C1 já mediu isso em `main`.

Aqui o produtor do defeito é o **validador**.

## Não medido — a lane deve medir

Se `indeterminado` é o tier **default** do dogfood, a escotilha está aberta **sempre**, não
só neste run. Isso muda a severidade.

## Contexto que amplia o alvo — decida o escopo

O mesmo arquivo tem 17 checks e apenas **4** podem pausar o run (`_CONSERVATION_CHECKS`,
`:681`), e os 4 são **recompute de produtor único** (leem componentes **e** total do mesmo
payload E5) — a classe que a [[ADR-418]] §D4 já condenou **no mesmo arquivo**. O CV5 recebeu o
remédio; CV1/CV2/CV3/CV6 não. Ver `PV10-03`. Decida se a lane cobre só o CV18 ou a classe.

## Critério de aceite

- Ausência devolve `None`, nunca `True`.
- **Prove que o check reprova no cenário certo** com `tests/test_e7_conservation_gate.py` — a
  U2 leu o gate no código e **nunca o observou disparando**, e isso está declarado como
  evidência fraca no §r10.
