---
id: A28.l8
type: lane
title: "higiene de ingestão: períodos implausíveis (1899/2100) e banco vazio viram needs_review, não artefato silencioso"
sprint: A28
plan: PLAN-report-trust
status: shipped
ship_pr: 786
ship_date: "2026-07-06"
priority: P2
branch_slug: higiene-ingestao-periodos
adrs: []
parallel_with:
  - "[[A28.l5]]"
  - "[[A28.l6]]"
  - "[[A28.l7]]"
tags:
  - type/lane
  - sprint/a28
  - status/shipped
  - priority/p2
  - area/pipeline
---

# A28.l8 — `higiene-ingestao-periodos` (Onda 1 · Should)

## Problema

O run dogfood `72883bde` produziu artefatos E3 com chaves anômalas:

- **Banco vazio** — 8 artefatos `_extrato_BRL_202406_202406` etc.: parsers E2
  emitindo `institution` vazio; `_canonicalize_bank` degrada para string vazia.
- **Período `189912_190001`** (santander faturaunique): `periodo` string bruto
  do parser, abaixo até do clamp de `safe_date`.
- **Períodos `210001`/`210006`** (c6bank faturacarbon): data misparsada clampada
  a 2100 por `safe_date` → propaga via `FATURA_DERIVED_FROM_TX_DATES`.

Culpado direto: `statement_preprocessor._expand_periodo_string` valida mês
(1-12) mas **não valida ano** — contraste com `infer_periodo_from_filename`,
que usa `_valid_ym` (2018-2030). Risco concreto: `2100`/`1899` **não** são o
sentinel oficial (`999999`, tratado em `patrimonio_types.py`) — período
implausível não é reconhecido como sentinela e pode virar **ano-base fantasma**
downstream. As keys contaminam os 3 consumidores do sufixo (`source_document`,
`_source`, campo `arquivo`).

## Escopo

1. **Guardrail de ano em `_expand_periodo_string`** (normalizer E3): ano fora
   do range plausível (reusar `_valid_ym` ou range 2015-2035) → **não expandir
   cego**; emitir `PeriodDerivationReason` de período inválido +
   `review_reason` (o vocabulário `dedup_sentinel_period` já existe em
   `review_reason.py`) → documento vai a `needs_review` com motivo, nunca
   artefato silencioso.
2. **`institution` não-vazio nos parsers E2** (c6bank, santander e onde mais o
   dogfood mostrar): parser que não consegue determinar banco marca
   `needs_review` com motivo — nunca emite extrato com banco vazio.
3. **NÃO tocar `generate_legacy_filename`** (`e3_serialization.py`): o
   serializador está correto — lixo entra, lixo sai; mascarar banco vazio ali
   esconderia o defeito de ingestão. Assinatura e testes existentes intocados.
4. Classificação de entrada dos 2 casos conhecidos que ficaram fora do
   pipeline: Binance CSV e informe Stone PJ caíram em `other` (cripto
   subestimada; perfil tributário incompleto) — **escopo mínimo**: needs_review
   com motivo acionável; parser novo é fora de escopo (candidato A29+).

## Critério de aceite

- Re-run dogfood E3: **zero** key com banco vazio; **zero** período fora de
  `[2015, 2035]` (exceto sentinel oficial `999999`).
- Período implausível → documento `needs_review` com `review_reason` explícito;
  teste unitário de `_expand_periodo_string` cobrindo `189912`, `210001` e
  passthrough de `999999`.
- `generate_legacy_filename` inalterada (testes existentes verdes, incluindo
  `test_legacy_descriptive_parity`).
- Goldens E3 rebaselinados com diff explicado (a saída das keys anômalas É a
  correção).

## Notas

- Subida de Could → **Should** no co-design (data-engineer): o risco de
  ano-base fantasma é integridade de dado, não cosmética. Priority P2 mantida
  (não bloqueia os KRs de fórmula).
- Duas raízes distintas (parser E2 vs normalizer E3) — commits separados.

## Owner

Agente da lane; co-design `data-engineer` feito 2026-07-03.
