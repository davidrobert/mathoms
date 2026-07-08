---
id: ADR-310
type: adr
title: "Chave canônica de conta na continuidade de saldo (implementação interina de ADR-278 §B7)"
status: Decidido
phase: A32.l4
date: "2026-07-07"
amended_at: ["2026-07-08"]
relates_to: ["[[ADR-278]]", "[[ADR-090]]", "[[ADR-097]]", "[[ADR-226]]"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/domain
---

# ADR-310 — Chave canônica de conta na continuidade de saldo

**Status:** Decidido (A32.l4) · **Data:** 2026-07-07

> **Emenda 2026-07-08 (A35.l1):** a chave estrita introduzida aqui produz
> um falso negativo quando `account_number_norm` não é extraído de um dos
> extratos da mesma conta — o gap genuíno entre eles some. Ver §Emenda ao
> fim: fallback de coalescência (só `not is_fatura`) + sinal auditável
> `SaldoChainMemberInferred`. Continua interina, absorvida pelo
> `SourceRef.kind` ([[ADR-278]] §B7).

## Contexto

`SaldoContinuityValidator` agrupa statements por
`(institution, member, currency)`
(`pipeline/domain/services/reconciliation_validators.py:84-88`) — sem
`account_type` nem número de conta — e ordena por `period_start` com
empate resolvido pela ordem de inserção (= ordem alfabética da
artifact_key = prefixo sha256 aleatório). Dogfood 2026-07-07 (run
`d1732edd`): 21 `domain.balance_gap`, maioria falsos positivos — fatura
de cartão, conta corrente e poupança do mesmo banco fundidas numa cadeia
única; faturas Santander com início colapsado por
`fatura_inicio_adjusted_to_tx` encadeadas em ordem de hash. Enquanto
isso, `AccountGrouper.key` (`account_grouper.py:177`) **já** separa
fatura e carrega `account_type` — as duas chaves divergiram.

[[ADR-278]] §B7 (Decidido, plano DATA_LINEAGE) prescreve que o validator
filtre por `SourceRef.kind` — infra que só chega em F2+ do plano. Esta
ADR é **implementação interina que conforma** a essa direção, não decisão
concorrente. Co-design 2026-07-07: `senior-cto` + `data-engineer` +
`financial-planner` + `product-manager`.

## Decisão

1. **Chave compartilhada** — `_account_key` deriva da `AccountKey`
   canônica do `AccountGrouper` (value object em `pipeline/domain`),
   incluindo `account_type` e `account_number_norm`. "Mesma conta" tem
   uma única definição no domínio.
2. **Fatura fora da cadeia de saldo** — statements `is_fatura` não
   participam da validação de continuidade: passivo rotativo não tem
   "saldo que continua" entre documentos; `saldo_inicial/final` de
   fatura (= `saldo_anterior/saldo_atual`) é semanticamente distinto de
   saldo de conta (`financial-planner`). Invariante própria de fatura
   (fatura_n paga vs fatura_n+1 aberta) é produto futuro, fora desta ADR.
3. **Desempate determinístico** — ordenação por
   `(period_start, period_end, source_document)`; nunca ordem de
   inserção/hash.
4. **Cláusula de absorção** — quando o filtro por `SourceRef.kind`
   ([[ADR-278]] §B7) entregar, ele absorve esta implementação; esta ADR
   ganha `superseded_by` na ocasião.
5. **Rebaseline disciplinado** — goldens de continuidade re-baselinados
   exclusivamente via `dev/golden_diff.py` + manifesto (padrão A23.l2):
   cada warning removido justificado como falso positivo, item a item.

## Consequências

- Os 21 `balance_gap` da run dogfood caem para apenas gaps genuínos;
  contagem de warnings nos goldens muda (esperado e justificado por
  manifesto).
- Cadeias mais curtas (por conta real) → menos comparações, mensagens
  mais precisas (identificam a conta, não só o banco).
- Risco: conta legítima erroneamente classificada como fatura sairia da
  validação sem sinal — coberto por teste negativo na lane.

## Alternativas rejeitadas

- **Esperar o SourceRef.kind do DATA_LINEAGE:** deixa 21 falsos positivos
  na tela do dogfood por N sprints; o custo da interina é pequeno e ela
  conforma à direção decidida.
- **Só excluir fatura, sem account_type na chave:** manteria
  poupança+corrente fundidas (caso bradesco real do dossiê).
- **ADR nova "concorrente" redefinindo o B7:** rejeitado — fragmentaria a
  decisão; esta ADR se declara subset/interina (resolução do conflito
  data-engineer × senior-cto no co-design).

## Emenda 2026-07-08 — coalescência de cadeia por número de conta ausente (A35.l1)

**Contexto.** A chave estrita (`+ account_number_norm`) resolveu 30 falsos
positivos de `balance_gap` no gate da A32, mas introduziu um falso
negativo: `account_number_norm` vem da **extração** (`document.py:158`) e
falha silenciosamente quando o parser não casa o número. Dois extratos da
MESMA conta — um com número, outro sem — viram cadeias separadas e o gap
genuíno entre eles não é sinalizado. Confirmado pelo owner na triagem KR3
da A32 (issue #860): conta rico, buraco abr–jun/2026 invisível.

**Decisão (escada de resolução — só `not is_fatura`).**

1. **Tier 1 (forte, quando há cadastro):** identidade de cadeia derivada
   do `AccountResolver` ([[ADR-226]]) — `fallback_bank` (banco com 1 conta
   cadastrada → statement sem número herda), `ambiguous` (2+ → isola).
2. **Tier 2 (sem cadastro):** dentro do grupo `(banco, membro, tipo,
   moeda)`, se há **exatamente um** `account_number_norm` distinto
   não-nulo, os sem-número coalescem naquela cadeia (sobrevivente
   canônico = a chave numerada, fixo — determinismo ADR-111). `>= 2`
   distintos → não coalesce (frágil a ruído de normalização; deferido ao
   Tier 1 / `SourceRef.kind`). Todos `None` → agrupam entre si (inalterado).
3. **Sinal `SaldoChainMemberInferred`** (dataclass, sem número cru) em
   toda coalescência — nunca em silêncio. Motivo: número ausente tem duas
   causas indistinguíveis (banco não emite × parser regrediu); o sinal
   impede que o fallback mascare regressão de extração.

**Aposta assimétrica (financial-planner):** no contexto de confiança da
review, falso negativo (gap real invisível) é pior que falso positivo
(warning dispensável) — falso positivo o usuário corrige em 1 clique;
falso negativo ele nunca sabe que existe e decide sobre base incompleta
(custo de vida subestimado → cobertura de reserva inflada, número da IF
otimista). Por isso o viés é **coalescer-e-sinalizar**, restrito ao eixo
`account_number` (os demais discriminadores seguem estritos — poupança
nunca casa com CC).

**Continua interina:** quando o `SourceRef.kind` ([[ADR-278]] §B7,
DATA_LINEAGE) entregar, absorve tanto a chave quanto este fallback; a
lógica de coalescência isolada em `_partition_chains` é fácil de deletar.
Se o ramo `>= 2` (número ausente cercado por 2+ contas reais sem
cadastro) virar recorrente, é gatilho para acelerar o B7, não para
inflar a heurística.
