---
id: FAQ-bank-account-member
type: doc
title: "FAQ — Como o Mathoms decide de qual membro é cada conta"
date: "2026-05-19"
tags:
  - area/methodology
  - area/persistence
  - type/doc
  - audience/produto
---

# Como o Mathoms decide de qual membro é cada conta?

Quando uma transação bancária chega ao pipeline (E4 categorize) ou uma posição de investimento é consolidada, o Mathoms precisa decidir a qual membro da família ela pertence. Esta página explica a hierarquia de decisão e o que acontece quando há ambiguidade.

## Hierarquia de resolução

A decisão segue 4 níveis, do mais confiável ao menos:

1. **`strict`** — match exato de `(banco, número da conta)` no cadastro `/config` → Membros. Sempre vence.
2. **`fallback_bank`** — só 1 membro tem conta nesse banco no workspace → atribui a esse membro. OK para single-account ou quando o número não foi extraído.
3. **`ambiguous`** — 2+ membros têm conta nesse banco e a transação não trouxe número de conta para diferenciar. **Não atribui** — marca como `needs_review`.
4. **`unknown`** — banco não cadastrado para nenhum membro. Não atribui.

## Por que isso importa?

Antes da [ADR-226](../adr/226-bank-account-member-disambiguation.md), o Mathoms usava um mapping simples `{banco: membro}`. Quando 2 membros tinham conta no mesmo banco (cenário comum no Brasil: casal com Itaú, Bradesco, Caixa, Nubank), o último cadastrado sobrescrevia o primeiro **silenciosamente** — todas as transações de um dos dois iam para o outro sem qualquer aviso.

Agora, com `account_number` como discriminador real:
- Famílias multi-membro mesmo banco têm transações atribuídas corretamente.
- Ambiguidade real (sem número de conta) gera `needs_review` honesto em vez de chute silencioso.

## O que faço quando vejo `needs_review`?

Significa que o pipeline detectou ambiguidade mas não tem informação para resolver sozinho. Ações:

1. **Verifique o cadastro em `/config` → Membros**: cada membro com conta no banco em questão tem `Número da conta` preenchido?
2. **Se algum membro está sem número**, edite e preencha. Re-rode o pipeline — o resolver passa a usar `strict` match.
3. **Se for posição de investimento sem identificador**, considere declarar o membro diretamente na fonte (ex.: nota de corretora separa por CPF; o sistema tenta inferir via CPF do membro).

## Conta conjunta (David + Mariana mesma conta)

Em V1 o Mathoms **não rateia** transações de conta conjunta — o titular principal recebe tudo. Para diferenciar, recomendamos:
- Cadastrar a conta conjunta no membro com maior representatividade fiscal (folha de pagamento maior).
- Anotar o `co_titulares` no banco (campo está reservado no schema, ativação em V2 ADR follow-up).

A V2 da ADR-226 introduzirá rateio editorial 50/50 (default Cerbasi-style) editável.

## UI: o que acontece quando tento cadastrar conta duplicada?

A interface bloqueia antes do envio: ao salvar `(banco, número)` que já existe para outro membro, mostra erro acionável "Já existe conta em itau para Mariana — informe outro número da conta para diferenciar". O backend reforça o mesmo gate com 409 caso 2 cliques simultâneos passem do check in-app.

## Referências

- [ADR-226](../adr/226-bank-account-member-disambiguation.md) — Decisão arquitetural completa
- [Lane A12.bank-account-disambig](../sprint/A12/lanes/A12-bank-account-disambig-multi-member.md)
