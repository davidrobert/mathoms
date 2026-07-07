---
id: A32.l3
type: lane
title: "parser de fatura: período do routing/DB, nunca re-derivado do filename inteiro"
sprint: A32
plan: null
status: shipped
ship_pr: 823
ship_date: "2026-07-07"
priority: P0
branch_slug: a32-l3-fatura-period-regex
adrs: []
depends_on: []
parallel_with: ["[[A32.l1]]", "[[A32.l2]]"]
tags:
  - type/lane
  - sprint/a32
  - status/shipped
  - priority/p0
  - area/pipeline
---

# A32.l3 — `fatura-period-regex` (mata as datas 2100/1899 na fonte)

## Problema

`scripts/e2/banks/santander.py:522-526` e
`scripts/e2/banks/c6bank.py:600-604` re-derivam `data_vencimento` do
filename com `re.search(r"(\d{4})(\d{2})")` **não-ancorada**, que casa a
primeira sequência de 6 dígitos — às vezes dentro do prefixo
content-addressed `sha256[:12]` (ADR-084,
`backend/app/services/canonical_routing.py:158`). Ex.:
`285768f03c9b_..._202602` casa `285768` → ano 2857 → `safe_date` clampa
em [1900, 2100] (`scripts/e2/common.py:228-238`) → `2100-01-06`. O início
sintetizado (= vencimento−30d, `statement_preprocessor.py:419`) produz
`1899-12-07`. Reproduzido 7/7 nos casos da run dogfood.
`documents.period` está **correto** no DB para todos — o parser corrompe
re-derivando o que o sistema já sabia. Os bancos não emitiram data errada.

## Escopo

1. **Preferir o período canônico já resolvido** (`documents.period`,
   propagado pelo routing) passado ao parser via contexto/parâmetro, em
   vez de `re.search` no stem.
2. **Fallback por filename só com regex ancorada** ao token de período no
   fim do stem — ex.: `r"_(\d{4})(\d{2})(?=-0_original|$)"` — nunca
   busca livre de 6 dígitos.
3. **Auditar os demais parsers** em `scripts/e2/banks/` com o mesmo
   padrão de `re.search` de 6 dígitos não-ancorado; corrigir os irmãos
   flagrados no mesmo PR.
4. **Testes assertam a DATA EXATA** (não "dentro da faixa [1900, 2100]")
   — o clamp de `safe_date` não pode mascarar regressão. Fixture com
   prefixo hash contendo 6 dígitos consecutivos (ex.: `285768f03c9b`).

## Critérios de aceite

1. Os 7 documentos que hoje emitem `dedup.sentinel_period` parseiam o
   período correto (fixtures reproduzindo os 4 padrões corrompidos:
   `2100-01-06`, `1899-12-07`, `2100-06-05`, `2100-01-05`).
2. Nenhuma das ~26 faturas que já parseavam certo regride (teste sobre
   corpus sintético de filenames).
3. `rg` confirma zero `re.search` de 6 dígitos não-ancorado remanescente
   em `scripts/e2/banks/`.
4. `pytest tests -q` verde; PR mergeado em `main` com CI verde.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `scripts/e2/banks/santander.py:522-526` | Regex ofensora (faturaunique) |
| `scripts/e2/banks/c6bank.py:600-604` | Regex ofensora (faturacarbon) |
| `scripts/e2/common.py:228-238` | `safe_date` — clamp que transforma bug em data plausível |
| `scripts/e2/common.py:91-92` | `VENC_UNIQUE`/`VENC_CARBON` — por que dia 05/06 |
| `pipeline/domain/services/statement_preprocessor.py:419` | Síntese início = venc−30d |
| `backend/app/services/canonical_routing.py:158` | Origem do prefixo sha256[:12] (ADR-084) |
