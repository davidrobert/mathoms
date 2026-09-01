---
id: A40.l115
type: lane
title: "O sanitizer de PII mede o contexto de ENTRADA e nunca o output: o relatório publica CPF parcialmente mascarado e conta bancária completa"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l115-sanitizer-mede-a-entrada-e-publica-a-saida
owner: sre-devops
depends_on: []
adrs: ["[[ADR-319]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend, area/frontend]
---

# A40.l115 — `sanitizer-mede-a-entrada-e-publica-a-saida`

> **Origem:** `RR9-16` da rodada unificada **U5** ([[REPORT-REVIEWS-active]] §r9).

## O defeito

O CPF sai **mascarado com os dígitos finais em claro**, em prosa **e** no campo de
`evidencia` — dois canais, o segundo dos quais ninguém revisa. Na **mesma página**, agência
e conta saem **completas**, sem máscara nenhuma: a política protege um identificador e
publica dois.

O gate mede o **contexto de entrada** que vai ao LLM; **nada mede o output**. E a docstring
do sanitizer afirma *"CPF/CNPJ redigidos"* enquanto o conjunto de chaves que ele de fato
cobre tem **um** elemento, que não é CPF nem conta.

## Por que a docstring é a parte grave

Ela é a razão pela qual isto sobreviveu: quem lê o módulo conclui que a cobertura existe.
É o modo de falha *"afirmação global falsa se repete em N sítios"* — a asserção do
docstring vale como justificativa de ausência de gate.

## Critério de aceite

1. O sanitizer roda no **output publicado**, não só no contexto de entrada.
2. Cobertura declarada = cobertura medida: teste que enumera os tipos de identificador e
   falha quando a docstring afirma mais do que o conjunto cobre.
3. Agência/conta entram na política, com decisão explícita de máscara (é dado do próprio
   dono — a decisão é de produto, não técnica).
4. Regressão sobre `evidencia`, não só sobre prosa.
