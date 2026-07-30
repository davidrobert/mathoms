---
id: ADR-354
type: adr
title: "Identidade de transação (K4) exclui atributos de proveniência do documento"
status: Proposto
phase: report-review r3 (RV3-01) · A40.l2
date: "2026-07-30"
relates_to:
  - "[[ADR-278]]"
  - "[[ADR-287]]"
  - "[[ADR-137]]"
  - "[[ADR-350]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
---

# ADR-354 — Identidade de transação (K4) exclui atributos de proveniência do documento

## Contexto

A revisão do relatório entregue ([[REPORT-REVIEWS-active]] §r3, RV3-01) **mediu**
duplicação material no razão E4 do workspace dogfood: o mesmo lançamento entra duas
vezes, vindo de dois documentos do mesmo banco.

As pernas diferem em três campos, e a análise inicial atribuiu a causa ao errado.
`normalize_banco` (`pipeline/domain/services/_tx_identity.py:75`) já faz
`_strip_accents(...).lower()` + colapso de whitespace **antes** do hash, e é
chamada dentro de `_hash_v1` e `_hash_v2` — a caixa de `banco` **não** fura o
`transaction_hash`; fura a chave de grupo. Os carriers reais são:

1. **`tipo_conta` com vocabulário divergente** (`extrato` vs `extratoconta`).
   `normalize_tipo_conta` (`:84`) faz casing e whitespace, **não vocabulário** —
   as duas strings sobrevivem distintas até o hash.
2. **`titular` vazio numa das pernas.** Efeito de segunda ordem:
   `_has_discriminants` (`:169-171`) devolve `False`, então `natural_key` sai
   `None` — mas o `transaction_hash` **continua sendo computado** com titular
   vazio. A perna fica sem chave de re-ancoragem e com hash próprio.

Ambos descrevem **qual documento entregou o dado**, não **o evento bancário**.

A conservação por grupo-fonte fecha em tol-zero (105/105) com a duplicação
presente, porque mede dentro de cada grupo e a duplicação é entre grupos.

## Decisão

**Só campos que descrevem o evento bancário entram na identidade K4.** Campos que
descrevem a proveniência do documento — variante de rótulo de `tipo_conta`, taxa de
preenchimento de `titular`, identificador do documento de origem — são
**canonicalizados a montante** ou **excluídos**, nunca resolvidos dentro da função
de hash.

Consequências:

- **`tipo_conta` ganha alias-map declarado e versionado no DB**, no padrão
  `institution_catalog` ([[ADR-137]]) — não normalização free-form dentro de
  `_hash_v2`. O vocabulário desconhecido é **fail-closed**: emite sinal e a conta
  cai em review, em vez de criar grupo-fonte silencioso.
- **`titular` vazio é defeito de extração** a reparar em E2/E3. Row que bate no
  gate `_has_discriminants` passa a ser **sinal contado e surfaçado**, não passe
  silencioso.
- **Duplicata que sobrevive à canonicalização é quarentenada** (`needs_review`),
  nunca somada em silêncio.
- **A conservação por grupo é declarada insuficiente** como gate de duplicação. O
  gate de duplicação é o check cross-grupo, por chave provenance-free
  `(data, valor_cents, moeda, direction, descricao_normalizada)`.

## Não-decisão explícita

**Nenhum `_hash_v3` nesta ADR.** `_hash_v1` está congelado ([[ADR-278]] D1) e
`_hash_v2` é simultaneamente a chave de dedup e a de re-ancoragem de
`transaction_overrides`. Mudar os inputs de v2 órfãna a categorização manual do
dono — regressão user-facing **pior** que a duplicação que se está corrigindo, e já
vivida neste repositório. Versão nova de chave exige ADR própria **e** plano de
backfill de override.

## Alternativas rejeitadas

- **Canonicalizar `tipo_conta` dentro de `_hash_v2`.** Rejeitada: resolve o caso e
  órfãna overrings existentes em silêncio. É o modo de falha que a sequência de 5
  PRs da [[A40.l2]] existe para evitar.
- **Dedupar por similaridade no E4.** Rejeitada: dedup fuzzy sobre razão já
  fechado esconde o defeito de identidade a montante, e não há como distinguir
  duplicata de compra legítima repetida sem a identidade de conta correta.
- **Aceitar a duplicação e corrigir só o relatório.** Rejeitada: o razão é a fonte
  de verdade de todo agregado; corrigir na saída multiplicaria o erro por consumidor.

## Consequências

Positivas: elimina a classe inteira (qualquer par de documentos do mesmo banco com
rótulo de conta variante), e o alias-map versionado dá rastreabilidade de quando o
vocabulário mudou.

Negativas: exige backfill com re-ancoragem de override, cujo gate operacional é
medir `COUNT(*) WHERE orphaned_at IS NOT NULL` antes e depois — se subir, abortar e
restaurar. O custo é real e é a razão de a lane ter 5 PRs em vez de 1.

Não supersede [[ADR-278]] nem [[ADR-287]]; complementa [[ADR-350]] (mesma família
de falha, lado fatura).
