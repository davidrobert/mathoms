---
id: A41.l4
type: lane
title: "Gate fecha a rota alternativa ao choke-point: import do SDK fora de pipeline/llm hard-falha"
sprint: A41
plan: PLAN-launch-trust
status: planned
priority: P1
branch_slug: a41-l4-gate-rota-alternativa-ao-choke-point
adrs:
  - "[[ADR-355]]"
depends_on:
  - "[[A41.l2]]"
  - "[[A41.l3]]"
tags:
  - type/lane
  - sprint/a41
  - status/planned
  - priority/p1
  - area/pipeline
  - area/llm
---

# A41.l4 — `gate-rota-alternativa-ao-choke-point`

> Fecha o KR da A41. Entra **junto com a última superfície roteada** — antes
> disso o gate falharia no próprio código que [[A41.l2]] e [[A41.l3]] estão
> consertando.

## Problema

Linha de base medida em `main` (2026-08-03): três arquivos de produção importam
o SDK direto, e **não existe gate em `dev/`** impedindo o quarto.

```
$ rg -l 'import anthropic|anthropic\.Anthropic' --type py
backend/app/services/documents/document_classification.py   # sonda de disponibilidade
scripts/e2/banks/caixa.py                                    # A41.l3
scripts/route_documents.py                                   # A41.l2
tests/fakes/anthropic_sdk.py                                 # fake nomeado — legítimo
```

Sem gate, a próxima superfície nasce igual: as três atuais nasceram assim, cada
uma por um motivo local razoável, nenhuma revisada contra a política de
choke-point. Contar superfícies roteadas mede o trabalho feito, não o resultado
— e para de contar exatamente quando alguém adiciona a quarta.

**Nuance que o gate precisa carregar:** `document_classification.py` importa
`anthropic` só dentro de `_llm_prerequisites_skip_reason`, como **sonda de
capacidade** — nunca instancia client. Uma regra crua marcaria isso como
violação. A sonda migra para o choke-point em [[A41.l2]]; se por algum motivo
ficar, a exceção tem de ser **nomeada no gate com o porquê**, nunca um
`# noqa` mudo.

## Decisão

Gate em `dev/` no pre-commit: `import anthropic` ou `anthropic.Anthropic` fora
de `pipeline/llm/` e `tests/fakes/` **hard-falha**. Alvo: 3 → 0.

O choke-point passa a ser a única porta: quem precisa de LLM pede ao
`LLMService`, e ganha budget, log, cache, métrica e sanitização por construção
em vez de por disciplina.

## Critério de aceite

- **Prova de que o gate morde:** arquivo-fixture com o import ⇒ `EXIT≠0`. Mesmo
  padrão do KR-A da [[A40]] — provar que falha, não que existe.
- `rg 'import anthropic|anthropic\.Anthropic' --type py` retorna 0 fora de
  `pipeline/llm/` e `tests/fakes/`.
- Toda exceção do gate é nomeada com justificativa no próprio script, e a lista
  de exceções cabe em uma tela.
- Entrada no `CLAUDE.md` §Regras críticas: chamada LLM nova entra pelo
  `LLMService`, e o gate é quem cobra.
