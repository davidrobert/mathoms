---
id: A39.l3
type: lane
title: "Fatura closure: parsers emitem total_lancamentos_conferivel (gate #1036 pronto) + flip WARN→HARD"
sprint: A39
status: shipped
ship_date: "2026-07-23"
ship_pr: 1045
priority: P0
branch_slug: a39-l3-fatura-optin-parsers
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/dados
---

# A39.l3 — `fatura-optin-parsers` (achado PC-01 · reconciliado com #1036)

> **Reconciliação com `main`:** o **gate** de checksum de fatura foi **entregue
> por #1036** (`a63ec80f`) **durante a autoria deste sprint** — e convergiu com o
> design do painel: opt-in via `total_lancamentos_conferivel`, checksum
> `Σ(tx do escopo) == total_compras` (subtotal declarado no doc, **não**
> `saldo_atual`/"Total desta fatura" — que false-fira com rotativo), int cents
> tol-zero, WARN-first, emenda [[ADR-342]] (§Emenda 2026-07-23 checksums E2).
> **ADR-343 (nova) foi descartada** — a emenda com identidade `total_compras`
> escopada superou a proposta de identidade completa. **Resta o lado do parser.**

## Problema (certificação 2026-07-23, pós-#1036)

O gate existe, mas **nenhum parser de fatura emite `total_lancamentos_conferivel`
ainda** (`git grep` em `scripts/e2/banks/` = 0) → o checksum é **inerte em
produção**: as 36 faturas continuam `coberto-sem-verificação` (parseiam, não há
prova de fechamento). O outcome de PC-01 (lado de despesa incertificável, viés
otimista) permanece até os parsers optarem.

## Escopo

- Popular `total_lancamentos_conferivel = {valor_cents, escopo}` **só onde o
  subtotal de lançamentos-do-período é lido independente do doc**:
  `parse_santander_unique`/`parse_santander_fatura_csv` ("Lançamentos atuais" /
  "Total Despesas no Brasil") e `parse_quintoandar`. Escopo do subtotal casa
  **exatamente** o subconjunto de `transacoes` emitido (mesma moeda, mesma
  inclusão de encargos).
- **NÃO** emitir onde `total_compras` é derivado de Σtx (tautológico — ex.:
  `parse_c6_carbon_csv`, `saldo=round(Σitens)`); documentar a exclusão.
- **Rollout WARN→HARD por parser** (padrão da emenda): flip para escalação
  `needs_review` **só após o corpus dogfood provar zero falso-fire** naquele
  parser (harness [[A39.l1]]).

## Critério de aceite

- Santander/quintoandar emitem `total_lancamentos_conferivel` com escopo casado;
  golden com **saldo rotativo** onde `Σtx ≠ saldo_atual` mas
  `Σ(tx do escopo) == total_compras` **fecha** (prova que o alvo é o subtotal, não
  o "Total desta fatura"); cents tol-zero.
- C6 Carbon CSV **sem** o sinal (assert de ausência — tautológico).
- Harness [[A39.l1]]: faturas com subtotal independente saem de
  `coberto-sem-verificação` para `completo` (checksum passa) ou escalam (KR-C,
  `checksum_ok` contado separado); WARN→HARD documentado por parser.

## Risco

Médio — maior blast radius (parsers de fatura). Mitigação: opt-in por parser +
WARN-first + corpus como gate empírico. O gate/contrato já está em `main` (#1036);
esta lane é o lado do produtor do sinal. `depends_on` [[A39.l1]].
