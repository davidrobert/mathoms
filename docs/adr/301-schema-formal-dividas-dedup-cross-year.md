---
id: ADR-301
type: adr
title: "Schema formal de dívidas + dedup cross-IRPF (EntityDedupPolicy)"
status: Decidido
phase: "A22.l5 · F1-O3 launch-trust"
date: "2026-06-26"
relates_to:
  - "[[ADR-276]]"
  - "[[ADR-271]]"
  - "[[ADR-246]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-212]]"
  - "[[ADR-300]]"
supersedes: []
superseded_by: []
aliases: ["ADR 301", "schema dividas", "dedup dívida cross-year"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/data-lineage
  - phase/a22
---

# ADR-301 — Schema formal de dívidas + dedup cross-IRPF

**Status:** Decidido (A22.l5 · F1-O3 launch-trust — implementada em #689) • **Data:** 2026-06-26 •
**Relaciona** [[ADR-276]] (runner `EntityDedupPolicy`), [[ADR-271]] (dedup
investimentos — molde de chave), [[ADR-246]] (label "casal"), [[ADR-090]] (Money),
[[ADR-097]] (warning tipado), [[ADR-212]] (artifact DB-only). Co-design
`data-engineer` + `financial-planner` (co-review) 2026-06-26. Lane [[A22.l5]]
(= F1-O3 de [[PLAN-launch-trust]]).

## Contexto

`config/schemas/baseline_patrimonial.schema.json:144` declara `"dividas":
{"type":"array"}` — array livre, sem schema, `additionalProperties` implícito true.
O consolidador (`e15_consolidate.py`, dois produtores: `:289-304` e `:507-516`) já
emite `{descricao, proprietario, saldo_31_12: {ano: valor}}` (dict-por-ano, análogo
a `valores_31_12` de investimentos). Sem dedup cross-IRPF, a mesma dívida declarada
em N anos vira N entries — double-count latente quando E5 reagrega o array (hoje
`total_dividas` é somado por-ano upstream, então o buraco é latente, não ativo).
Imóveis ([[ADR-246]]) e investimentos ([[ADR-271]]) já têm dedup; dívida é a
entidade patrimonial sem cobertura.

## Decisão

### 1. Schema formal de `dividas` (aperto de contrato)

Cada entry: `required: [descricao, saldo_31_12]`, `additionalProperties: false`.
`saldo_31_12` é objeto `{"^\\d{4}$": number ≥ 0}` (paridade com `valores_31_12` —
`number` no wire, `Decimal`/cents em cálculo, [[ADR-090]]). Campos de enriquecimento
**opcionais** (IRPF não entrega): `tipo` (enum), `credor`, `numero_contrato`,
`taxa_juros_aa`, `parcelas_total`, `fonte`, `ano_referencia`. Campos de dedup:
`divida_id`, `proprietarios[]`, `_dedup_warning`.

**Não-breaking:** sair de array-livre para schema com required é aperto; os dois
produtores já emitem o shape required. Validação entra em **`warn`** (default por
`pipeline.json`), promove a `strict` só após dogfood limpo.

### 2. Dedup como nova `EntityDedupPolicy` ([[ADR-276]])

Arquivo `pipeline/domain/services/dividas_dedup.py` (~40-50 linhas, sem
`remap_groups`/fuzzy — retorna `grouped` intacto, como investimentos). Inserção em
`e15_consolidate.py` como **bloco 3d**, após investimentos (`:805`); um único
call-site cobre os dois produtores (ambos escrevem `dividas` antes do bloco de
dedups).

- **`identity_key`:** `numero_contrato` quando presente (discriminador mais forte);
  senão `("desc", tipo, credor_norm, descricao_norm)` via `normalize_descricao`
  (mesmo helper das outras policies). Chave **estrita, sem fuzzy** — herda calibração
  de [[ADR-271]]: FP (funde dívidas distintas → some passivo → infla PL) é pior que
  FN (2 entries, soma certa, ruído visual).
- **`emit_group`:** cross-year **une `saldo_31_12` ano-a-ano** (não descarta os anos
  antigos — série temporal sobrevive para E5 plotar amortização); saldo corrente =
  `saldo_31_12[max(ano)]`. Dívida quitada some automaticamente (ausente no ano novo
  → saldo corrente zero, sem lógica especial). Cross-declarante (financiamento
  conjunto) funde "casal" **só se saldo idêntico ao centavo** (gate de [[ADR-271]]);
  divergente → 2 entries + warning `possivel_duplicata`, sem somar.

### 3. Warning de monotonicidade condicionado ao tipo (financial-planner)

A regra ingênua "saldo deveria decrescer" produz FP em massa — saldo crescente é
**legítimo** em revolvente (cheque especial/cartão), bullet/balloon, indexado
(SAC/USD), e dentro de carência. Decisão:

- **Emite `saldo_nao_monotonico`** (warning informativo, **não** bloqueia) só quando
  `tipo` é **amortizável de prestação fixa** (financiamento Price/SAC fora de
  carência, empréstimo pessoal parcelado) **E** saldo nominal cresceu **E** sem
  indexador que justifique.
- **Suprime** para revolvente/bullet/indexado/carência e quando `tipo` ausente
  (não classificável → conservador, não inventa). Não inferir tipo pelo valor
  (folclore rejeitado, cf. [[ADR-236]] "receita×32%").
- Renegociação (`numero_contrato`/`data_contratacao` muda) → **dívida nova**, não
  funde (a chave estrita já separa) — resolve o caso consignado-renegociado.

## Consequências

- **Positivas:** fecha o último buraco de double-count patrimonial (KR2/KR3 de
  [[PLAN-launch-trust]]); série temporal de dívida limpa; warning carrega sinal
  (refinanciamento? juros capitalizando?) sem julgar — o julgamento é do parecer.
- **Custo:** +1 policy (~50 linhas) + golden multi-ano; promoção a `strict` faseada.
- **Sem rebaseline indevido:** `total_dividas` (somado por-ano upstream) não deve
  mudar — o dedup só compacta o array. Se mudar, há double-count latente sendo
  corrigido → documentar no manifesto de rebaseline (`dev/golden_diff.py`).

## Invariantes (golden multi-ano, análogos a INV-1..9)

INV-D1 conservação do saldo-corrente · INV-D2 não-double-count cross-year (N anos →
1 entry) · INV-D3 quitação (dívida ausente no ano novo → saldo corrente zero) ·
INV-D4 idempotência (`dedup(dedup(x))==dedup(x)`, `divida_id` estável) · INV-D5
tie-break determinístico (ordem de inserção + hash canônico) · INV-D6 casal sem
double-count (saldo idêntico → 1 entry "casal") · INV-D7 conflito cross-declarante
(saldo divergente → 2 entries + warning, soma intacta) · INV-D8 unidentified passa
intacto (sem `descricao` → `identity_key` None).

## Follow-ups

Extrair `credor`/`tipo` da descrição livre da Ficha de Dívidas (regex em
E2/E1.5) para fortalecer a chave de série multi-ano — hoje só une se a descrição
for textualmente idêntica entre anos. Não bloqueia o MVP.
