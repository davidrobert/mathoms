---
id: A36.l3
type: lane
title: "E7: invariante de conservação (CV1-CV14) pausa o run em vez de ser advisory"
sprint: A36
status: planned
priority: P1
adrs: ["[[ADR-272]]"]
branch_slug: a36-l3-e7-conservation-gate
depends_on: []
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p1
  - area/pipeline
---

# A36.l3 — `e7-conservation-gate` (DAT-01)

## Problema

O E7 (`validate_cross`) roda 14 checks de conservação (ex.:
`patrimonio_liquido == ativos - passivos`) mas **sempre retorna `success: True`**,
mesmo com `errors_count > 0` (`scripts/validate_cross.py:530-539`). O loop do
pipeline só pausa um run como `needs_review` quando o resultado tem
`detail["validation"]["valid"] == False`
(`backend/app/tasks/pipeline_task.py:1109-1115` e `:1203-1211`) — e o
`validate_cross` **não emite esse bloco**. Resultado: um plano com invariante de
conservação violada pode ser entregue ao cliente **sem flag**.

A boa notícia: o mecanismo de pausa **já existe** e é reusável (foi construído
para os checks determinísticos via [[ADR-272]]). Basta o E7 falar a mesma língua.

## Escopo

1. Em `scripts/validate_cross.py`, adicionar ao dict de retorno:
   `"validation": {"valid": len(errors_list) == 0, "errors_count": len(errors_list)}`.
2. Com isso, o `_has_validation_errors` já existente dispara e o run pausa como
   `needs_review` automaticamente — **sem código novo no consumidor**.
3. Decidir a política (registrar em comentário/ADR curta): erro de conservação
   **pausa** (needs_review, recomendado) ou **bloqueia publicação**? Warnings
   permanecem advisory.
4. Golden: um fixture com invariante quebrada deve **pausar** o run; um run
   limpo passa igual.

**Fora de escopo:** mudar a lógica dos 14 checks individuais (CV1-CV14); só a
disposição do resultado.

## Critérios de aceite

- Run com `errors_count > 0` no E7 pausa/flag (`needs_review`) em vez de entregar.
- Run com `errors_count == 0` passa sem regressão.
- Golden de conservação-violada trava; golden limpo verde.
- Fecha o crux da auditoria "o gate de publicação consome `errors_count` do E7?".

**Esforço:** M. **Origem:** auditoria r4 (DAT-01).
