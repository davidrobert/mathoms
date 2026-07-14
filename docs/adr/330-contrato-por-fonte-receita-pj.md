---
id: ADR-330
type: adr
title: "Contrato por_fonte: bloco derivado receita_por_natureza (fora de por_fonte)"
status: Proposto
date: "2026-07-14"
relates_to:
  - "[[ADR-236]]"
  - "[[ADR-137]]"
  - "[[ADR-090]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
---

# ADR-330 — Contrato `por_fonte`: bloco `receita_por_natureza`

> Cluster **B** (P1) do [[PLAN-dogfood-report-fix]]: a chave `fluxo_caixa.por_fonte.receita_pj`
> é lida por 5 consumidores mas **nunca emitida** pelo enricher — renda PJ (~46,5% no perfil
> dogfood) some silenciosamente e o perfil de renda colapsa para CLT-única.
> Contrato travado por co-design `data-engineer` (2026-07-14), que corrigiu 2 riscos de
> conservação do draft inicial.

## Contexto

`por_fonte = dict(receitas.totais_por_categoria)` (`fluxo_caixa_enricher.py:279`). As chaves
são **categorias de receita E4** (`receita_clt`, `receita_aluguel`, `lucros_distribuidos`…) —
8 no run dogfood, **sem** agregado `receita_pj`. Invariante travado:
`test_e5_conservation_invariants.py:76-79` assere `_cents(receita_total) == Σ _cents(por_fonte.values())`.

**Consumidores da chave fantasma `receita_pj` (5, não 3 — varredura completa):**

1. `reserva_emergencia_calculator.py:201` — `por_fonte.get("receita_pj")` → `perfil_renda` vira
   CLT-única, `receita_pj_pct=0`. **Bug vivo.**
2. `previdencia_analyzer.py:215` — idem → renda PJ anual `0` → PGBL via proxy zera. **Bug vivo.**
3. `tributario_input_builder.py:151` — E4-scoped; já soma `+ pro_labore + lucros_distribuidos`,
   então o valor **já está correto**; `+ receita_totals.get("receita_pj")` é **termo morto (+0)**.
4. `scripts/analyze_finances.py:analyze_previdencia_pgbl` — **dead code** (0 callers; path vivo é
   `previdencia_analyzer`).
5. `generate_narratives.py:332` — lê só `por_fonte.get("lucros_distribuidos")` → **subconta**
   (ignora `pro_labore`).

Das 5 `PJ_LABELS` (`transaction_classifier_pj.py`), **só `pro_labore` e `lucros_distribuidos`
são receita**; `das_simples`/`iss`/`folha_pj` são **despesa** — não entram num agregado de renda.

## Decisão

1. **Bloco derivado novo `fluxo_caixa.receita_por_natureza`** — **fora** de `por_fonte` (não
   tocar `por_fonte`; a chave nova dentro dele dupla-contaria e quebraria o teste de conservação):
   ```
   receita_pj      = pro_labore + lucros_distribuidos     (só códigos RECEITA-PJ)
   receita_clt     = por_fonte.receita_clt
   receita_aluguel = por_fonte.receita_aluguel
   receita_outras  = receita_total − pj − clt − aluguel   (RESÍDUO)
   ```
   `receita_outras` é **resíduo**, não soma explícita — absorve categorias futuras
   (`receita_investimento`/`_restituicao`/`_resgate`/`_venda_*`/`outras_receitas`) sem quebra
   silenciosa. `Σ receita_por_natureza == receita_total` é tautologia por construção.
2. **Derivação em cents inteiros**: reagrupar os valores **já serializados** de `por_fonte`
   (cada um `round(v,2)`) via `_cents` (Decimal, ROUND_HALF_UP — o mesmo de
   `test_e5_conservation_invariants.py`); resíduo por subtração inteira → **zero off-by-1-cent**.
3. **Migrar os consumidores** (tratamento por consumidor):
   - `reserva_emergencia_calculator` → ler `receita_por_natureza[pj|clt]`; **manter** o
     denominador `pj + clt` (mix de renda-trabalho, **não** `receita_total`); o fix é só o
     numerador (agora inclui `pro_labore`).
   - `previdencia_analyzer` → ler `receita_por_natureza["receita_pj"]`.
   - `tributario_input_builder` → **não** migrar para E5 (é E4-scoped); só **remover o termo morto**.
   - `analyze_previdencia_pgbl` → **deletar** (dead code).
   - `generate_narratives:332` → ler `receita_por_natureza["receita_pj"]` (corrige subcontagem).
4. **Schema**: declarar `receita_por_natureza` em `e5_analysis.schema.json` (**aditivo, sem bump**;
   `additionalProperties` permissivo).

## Rationale

Bloco separado, derivado, com `outras` residual: preserva o invariante de conservação de
`por_fonte` (intocado) e mantém `Σ natureza == receita_total` robusto a categoria nova. Cents
inteiros por reagrupamento (não `round` independente por balde) garante exatidão. `receita_pj`
é renda de trabalho PJ (ativa) — distinta do bucket passivo do cluster A ([[ADR-191]]).

## Alternativas consideradas

- **`receita_pj` como chave dentro de `por_fonte`** (draft inicial): dupla-conta com
  `pro_labore`/`lucros_distribuidos` e quebra `test_e5_conservation_invariants.py:76-79`. Rejeitada.
- **`Σ PJ_LABELS`**: somaria `das_simples`/`iss`/`folha_pj` (despesa) em renda. Rejeitada.
- **`receita_outras` como soma explícita**: perde categoria nova silenciosamente. Rejeitada em
  favor de resíduo.
- **CV como `Σ natureza == por_fonte`**: tautologia (derivado por reagrupamento). Substituída por
  resíduo-não-negativo (sinal real de dupla-contagem).

## Consequências

- **`por_fonte` intocado** → `test_e5_conservation_invariants.py:76-79` segue verde.
- **Duas semânticas de pct, não conflatar**: `perfil_renda.receita_pj_pct` = `pj/(pj+clt)`;
  narrador `pct_receita_pj` = `pj/receita_total`.
- `receita_resgate`/`receita_venda` (realização de patrimônio) ficam em `receita_outras` — não
  excluir (quebraria `Σ == total`); recorrência é eixo ortogonal (`receita_recorrente` vs `one_time`).
- **Follow-up (fora do escopo)**: `receitas_por_fonte` (plural) é dead-read em
  `real_estate_e5_integration.py:206`.
- **Nota de domínio (financial-planner, 2026-07-14)**: `receita_pj` serve 2 consumidores; no
  **proxy PGBL** (`previdencia_analyzer._analyze_via_proxy`), a parcela `lucros_distribuidos`
  (distribuição isenta) **super-estima** levemente a capacidade PGBL — o proxy é fallback; o
  path canônico (`_analyze_via_irpf`, renda tributável) não é afetado. Não bloqueia; documentar.
- Bump: **nenhum** (aditivo). Golden red-before-green e rebaseline coordenado em [[ADR-331]].

## Critério de aceite (4 lentes)

- **Completude** — `rg` zero-hit de `por_fonte…receita_pj` / `receita_totals.get("receita_pj")` em
  código vivo pós-migração; `analyze_previdencia_pgbl` deletada; gate G2 (visitor AST) opcional.
- **Corretude** — teste do reserva com `pro_labore>0` + `lucros_distribuidos>0` → `perfil="pj_dominante"`
  (hoje daria "indefinido"/CLT); golden red-before-green ([[ADR-331]]).
- **Consistência** — **CV16** em `validate_cross.py` (CV15 reservada por [[ADR-327]]):
  `receita_pj + receita_clt + receita_aluguel <= receita_total` (cents), em `_CV_ALWAYS_CHECKS`.
  `test_e5_conservation_invariants.py:76-79` intacto.
- **Precisão** — derivação em cents inteiros (Decimal ROUND_HALF_UP); `Σ receita_por_natureza ==
  receita_total` exato; `receita_outras >= 0` ([[ADR-090]]).
