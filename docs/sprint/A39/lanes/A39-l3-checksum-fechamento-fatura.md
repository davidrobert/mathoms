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

## Nota de execução (2026-07-23) — identidade resolvida (co-design financial-planner)

O opt-in do parser (commit 2) foi **deferido** ao descobrir que
`Σ(compras itemizadas) == total_compras` **não fecha em 0/3** faturas reais. O
co-design fechou a identidade correta — **destrava a implementação**:

- **Alvo = subtotal POR SEÇÃO** (`despesas_brasil` + `despesas_exterior`):
  `Σ_cents(tx da seção) == subtotal_declarado_cents(seção)`. **NÃO** comparar com
  `saldo_atual`/"Total desta fatura" (inclui rotativo; [[ADR-342]] proíbe).
- **Escopo ALARGADO:** o subtotal de seção inclui compras **+ anuidade + encargos/
  juros de rotativo + IOF nacional + tarifas + seguros embutidos (SCP)**. A premissa
  "só compras" era o furo.
- **Causa-raiz (no código):** `tx_pattern` (`santander.py:736`) exige `DD/MM` no
  início → linhas de encargo **sem data** somem (R$2,77 = IOF nacional; R$36 =
  anuidade/SCP). **Fix:** capturar linhas sem-data reusando o fallback do IOF
  exterior (`santander.py:762-780`, usa a data da tx anterior / `data_vencimento`).
- **Sinal:** compra vs pagamento por **seção + keyword** (`PAGAMENTO EFETUADO`/
  `ESTORNO`), nunca por `valor<0` — matar o `is_payment` morto (`santander.py:809`).
  Em E2, somar no espaço-de-sinal do doc (débito positivo); normalizar p/ fluxo é E3/E4.
- **Encargos são despesa** → emitir como tx (fecha o checksum **e** alimenta o
  gasto). **Excluir** (double-count): `saldo_anterior`/rotativo; `pagamento efetuado`
  emite com `tipo=pagamento` (E3/E4 = transferência interna).
- **Identidade valor-a-pagar** (`saldo_anterior − pagamentos + encargos + IOF +
  anuidade + Σlançamentos == total_desta_fatura`) = cross-check **secundário**,
  nunca âncora de completude.
- Sem ADR nova — emenda [[ADR-342]] já cobre. Vale também para [[A39.l8]]
  (parser Itaú Visa: "Total dos lançamentos atuais" com a mesma identidade de seção).

## Nota de execução (2026-07-24) — opt-in shipado (fecha a lane)

`parse_santander_unique` opt-in **entregue**. `escopo` declarado em
`$defs/transacao` (enum `despesa_brasil|exterior|pagamento|lancamentos_atuais`);
tag por seção ("Pagamento e Demais Créditos" → pagamento com `tipo=pagamento`;
"Despesas" com coluna US$ → exterior; sem US$ → despesa_brasil; IOF DESPESA NO
EXTERIOR → despesa_brasil, que é onde o emissor o conta). Emite
`total_lancamentos_conferivel={valor_cents, escopo:despesa_brasil}`.

Achado do corpus vs a nota de 2026-07-23: as linhas de encargo **não** somem —
o IOF (única linha sem data) já era capturado; o resíduo era **tag de escopo
errada** (IOF fora do balde Brasil) **+ corrupção de valor** no layout
lado-a-lado (a poluição da coluna Resumo fundida na linha era capturada pelo
`$`-âncora — pagamento −119,21 virava +119,21). Fix = estripe da poluição antes
do match + IOF→despesa_brasil + seção pelo header literal. Os 3 PDFs Santander
fecham a cent (R$ 39,96 / 543,68 / 3.566,08), zero falso-fire. `is_payment`
morto removido. WARN-first mantido (flip HARD após ≥1 sprint verde). Golden
sintético em `test_fatura_parser_checksum.py`.
