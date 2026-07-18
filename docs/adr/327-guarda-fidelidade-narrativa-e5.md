---
id: ADR-327
type: adr
title: "Guarda de fidelidade narrativa↔E5: binding de token monetário a campo vivo + fail-closed no E5.N"
status: Proposto
date: "2026-07-12"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-148]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/llm
---

# ADR-327 — Guarda de fidelidade narrativa↔E5

> Item **C2.5** do plano PLAN-dogfood-report-fix. Achados LLM-01/LLM-02/LLM-03/UX-03 da revisão dogfood.

## Contexto

O relatório dogfood embarcou narrativas monetariamente erradas sem nenhum gate
falhar: "Patrimônio bruto de R$ 3,6M com **0% investível (R$ 0,00)**", "PJ (R$ 0,00, 0%)",
"US$ 0", frases com placeholder vazio ("é  ()", "Formado em ."), discriminação
registral crua (CNPJ/matrícula/endereço) na prosa, e caption de tendência dizendo
"melhora" enquanto a poupança caiu 67%. Os gates existentes (`validate_narrativas`,
CV9/CV10/CV14) só checam **presença/formato**, não **fidelidade ao E5**.
`check_monetary_format` sequer pega `R$ 0,00`.

A raiz de conteúdo é corrigida por C2.1–C2.4 (item PLAN-dogfood-report-fix);
esta ADR institui o **invariante de guarda** que impede a regressão.

## Decisão

Instituir uma **tabela de binding `slot → dot.path do E5`** e uma guarda
pós-geração no stage `generate_narratives` (E5.N) com 4 predicados:

1. **Zero-vs-campo:** rejeita token monetário `R$ 0,00`/`0%`/`US$ 0` quando o
   campo E5 vinculado é não-zero.
2. **Placeholder:** rejeita sentença com variável de template vazia.
3. **Registral/PII:** rejeita CNPJ/matrícula/IPTU/endereço cru em prosa.
4. **Tendência:** verbo de direção deve casar com `comparisons[].delta_signal`;
   proíbe linguagem comparativa quando não há baseline.

Política de falha **fail-closed** no E5.N (aborta/`needs_review`, não advisory).
O mesmo módulo de predicados é espelhado como um novo check **CV15** em
`validate_cross.py` (decisão gate-vs-advisory registrada aqui). Fonte única de
predicados consumida pela guarda runtime e pelo golden (item C2.6).

## Alternativas consideradas

- **Advisory (warning) em vez de fail-closed.** Rejeitada para os predicados
  1–3 (erro objetivo, deve bloquear); o predicado 4 pode ser advisory se o
  baseline for ruidoso — decisão fica no PR sob esta ADR.
- **Só golden de teste, sem guarda runtime.** Rejeitada: o golden pega em CI,
  mas um run real com E5 anômalo passaria sem a guarda runtime.

## Consequências

- Um run que produza narrativa monetariamente falsa **falha** em vez de embarcar.
- Mensagem de erro no padrão do repo: `slot + token ofensor + campo.dot.path + valor esperado`.
- Acopla ao contrato E5 (a binding-table lista os `dot.path`); mudanças de campo
  exigem atualizar a tabela.

## Critério de aceite (4 lentes)

- **Completude:** guarda cobre os 4 predicados e todos os slots que falharam no run.
- **Corretude:** falha sobre o E5 pré-C2.1, passa pós-fix; zero legítimo não gera falso-positivo.
- **Consistência:** mesmo predicado no E5.N (bloqueio) e no CV15 (E7).
- **Precisão:** erro cita `slot+token+dot.path+valor esperado`.
