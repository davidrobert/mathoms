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

## Como o Mathoms sugere contas a partir do IRPF

Pós-[ADR-229](../adr/229-irpf-prefill-suggestions.md), quando o Mathoms processa
seu IRPF (Ficha de Bens e Direitos, código 61), as contas declaradas viram
**sugestões** no `/config` → Membros, evitando que você digite tudo do zero.

**Como aparece:**

- No card de cada membro, no fim da lista de contas, surge um grupo
  "Encontradas no seu IRPF YYYY · você declarou estas contas".
- Cada card de sugestão mostra banco, agência, número e CPF do titular
  mascarado (`***.123.456-**`), com botões "Adicionar" e "Descartar".

**O que acontece em cada cenário:**

| Cenário | UI |
|---|---|
| Sugestão sem conflito | Card normal verde — clique em "Adicionar" cria a conta. |
| Sugestão com **número exato** já cadastrado | Filtrada silenciosamente — não aparece (evita ruído). |
| Sugestão com **mesmo banco** e número diferente | Card âmbar com aviso "Possível duplicata de XYZ" + botão "Comparar e adicionar" abre modal de diff com 2 colunas (IRPF vs cadastrado) e duas opções: **Mesma conta** (mantém o cadastrado) ou **Contas diferentes** (cria as duas). |
| Sugestão descartada | Não volta a aparecer mesmo se você reprocessar o IRPF do mesmo ano. |

**Por que mascaramos o CPF na UI?**

O artifact de origem (extração LLM do IRPF) contém CPF cru e fica
criptografado no DB do workspace. A UI nunca expõe o número completo —
mostra apenas os 6 dígitos centrais (`***.123.456-**`) suficientes para
você reconhecer o membro sem facilitar vazamento.

**Saldo declarado no IRPF aparece em algum lugar?**

V1 V0: o saldo de 31/12 do ano-base fica armazenado no metadado da conta
(`irpf_snapshots`), mas **não é renderizado na UI** — V2 trará a linha do
tempo na tela de detalhamento. Importante: esse saldo não vai ao campo
"saldo atual" — dado de 6-18 meses atrás contaminaria o diagnóstico
presente.

**E se o IRPF não foi processado pelo Mathoms ainda?**

Sem o artifact E1, simplesmente nenhuma sugestão aparece — não é erro,
é estado vazio normal. Faça upload do PDF do IRPF na aba **Inbox** e o
pipeline gera o artifact que destrava as sugestões.

## Referências

- [ADR-226](../adr/226-bank-account-member-disambiguation.md) — Decisão arquitetural completa
- [ADR-229](../adr/229-irpf-prefill-suggestions.md) — Pre-fill IRPF (V1 contas bancárias)
- [Lane A12.bank-account-disambig](../sprint/A12/lanes/A12-bank-account-disambig-multi-member.md)
