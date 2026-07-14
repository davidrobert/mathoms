---
id: ADR-330
type: adr
title: "Contrato canônico por_fonte: agregado receita_pj + bloco receita_por_natureza"
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

> Fecha o item cluster B (P1) do [[PLAN-dogfood-report-fix]]: a chave `fluxo_caixa.por_fonte.receita_pj` é lida por 3 consumidores mas **nunca emitida** pelo enricher — renda PJ (~46,5% no perfil dogfood) some silenciosamente e o perfil de renda colapsa para CLT-única.
> Achado verificado na revisão dogfood 2026-07-13: `receita_pj → 0` em reserva, previdência e input tributário.

## Contexto

`FluxoCaixaEnricher.enrich` monta `por_fonte` a partir de `receitas.totais_por_categoria` (`pipeline/domain/services/fluxo_caixa_enricher.py:279`). As chaves resultantes são **categorias E4** (`receita_clt`, `receita_aluguel`, `lucros_distribuidos`…) — 8 chaves no run dogfood, **sem** `receita_pj`. Nenhum passo do pipeline agrega os códigos PJ do classifier num único `receita_pj`.

Três consumidores leem essa chave fantasma e recebem `0`:

- `pipeline/domain/services/reserva_emergencia_calculator.py:201` — `por_fonte.get("receita_pj", 0)` → perfil de renda vira CLT-única, `receita_pj_pct=0,0`.
- `pipeline/domain/services/previdencia_analyzer.py:215` — `por_fonte.get("receita_pj", 0)` → renda PJ anual `0` → PGBL via proxy zera.
- `backend/app/services/tributario_input_builder.py:151` — def inline soma `receita_totals.get("receita_pj")` (fantasma) `+ pro_labore + lucros_distribuidos`; sobrevive só porque re-soma os códigos crus.

Os códigos PJ são um set fechado em `pipeline/domain/services/transaction_classifier_pj.py:26` (`PJ_LABELS`): `pro_labore`, `lucros_distribuidos`, `das_simples`, `folha_pj`, `iss`.

## Decisão

1. **Emitir `receita_pj` como agregado canônico** no `por_fonte` do enricher: `receita_pj = Σ round(code, 2)` sobre os códigos de `PJ_LABELS` presentes nos totais de receita. Soma sobre valores **já arredondados por-código** (não `round(Σ Decimal)`) para casar `sum(por_fonte)` em cents exatos, tolerância-zero ([[ADR-090]]).
2. **Adicionar bloco `fluxo_caixa.receita_por_natureza`**: bucketização code→natureza via `NATUREZA_MAP` co-localizado com o enricher. `NATUREZA_MAP` inclui o código fantasma `"receita_pj" → receita_pj` além de `pro_labore`/`lucros_distribuidos`/`das_simples`/`folha_pj`/`iss`, garantindo paridade com a def inline de `tributario_input_builder.py:151-153` **antes de deletá-la**.
3. **Publicar o contrato em `config/schemas/`**: declarar em `e5_analysis.schema.json` o enum de chaves válidas de `por_fonte` + o shape de `receita_por_natureza` — fonte de verdade do gate G2.
4. **Corrigir os 3 consumidores** para ler o agregado canônico (não só a reserva — a previdência também lê `0` para PJ). `tributario_input_builder` passa a consumir `receita_por_natureza`; a def inline é removida.

## Rationale

`receita_pj` é o único agregado que cruza classificação (E4, [[ADR-236]]) e análise (E5) sem contrato. Publicá-lo no schema + gate de completude transforma "chave lida mas nunca escrita" (falha silenciosa que zerou renda ativa PJ) em erro de CI. Somar por-código já arredondado preserva a invariante de conservação em cents (mesma disciplina de `tests/test_e5_conservation_invariants.py`).

## Alternativas consideradas

- **Renomear consumidores para `lucros_distribuidos`** (como `generate_narratives.py:332` faz interinamente): perde `pro_labore` e demais códigos PJ; subestima renda ativa PJ. Rejeitada.
- **Manter def inline em cada consumidor**: 3 cópias divergentes da soma PJ, sem contrato — a origem exata do bug. Rejeitada.
- **Gate por nome de variável** (`grep receita_pj`): não pega acesso encadeado `fluxo.get("por_fonte",{}).get(...)`. Substituída por G2 (visitor AST chaveado no dict de origem).

## Consequências

- Renda PJ passa a fluir para reserva (perfil de renda), previdência (PGBL) e tributário — impacto direto no relatório dogfood.
- **Não dupla-contar**: `receita_pj` (renda de trabalho PJ, ativa) é distinto do bucket passivo — respeitar a decisão A travada (lucro PJ do titular = renda ativa). O agregado é fonte de renda, não patrimônio.
- **Colisão de superfície**: `generate_narratives.py:332` pertence à lane C2.1 (Onda 1) — **não** abrir lane B sobre essa linha.
- Bump de schema E5 **aditivo** (`additionalProperties` segue `true` em `fluxo_caixa` até o flip W6-T01) — landar no **último PR da onda** para evitar churn. Catálogo de códigos PJ ancorado em [[ADR-137]].

## Critério de aceite

- **Completude** — Gate G2: visitor AST varre acessos `.get("KEY")` chaveados nos dicts de origem (`por_fonte`, `por_fonte_detalhado`, `receita_totals`, `despesa_totals`), incluindo acesso encadeado `fluxo.get("por_fonte",{}).get(...)`; falha se qualquer KEY consumida não estiver no enum declarado no schema. Zero consumidor lendo chave não-emitida.
- **Corretude** — Golden: no perfil dogfood, `perfil_renda` migra `"clt_unica_fonte" → "pj_relevante"`, `receita_pj_pct` `0,0 → ~46,5`; `meses_alvo` permanece `12` (ambos os perfis mapeiam 12 na config atual — **não** 18). `por_fonte` mantém as 8 chaves reais + `receita_pj`.
- **Consistência** — CV16 em `validate_cross.py` (perto de :390, registrada em `_CV_ALWAYS_CHECKS` :403; CV15 reservada por [[ADR-327]]): `Σ receita_por_natureza == Σ por_fonte` em cents exatos. `NATUREZA_MAP` em paridade com a def inline removida de `tributario_input_builder.py`.
- **Precisão** — `receita_pj = Σ round(code, 2)` (não `round(Σ Decimal)`); tolerância-zero em cents, alinhado a `tests/test_e5_conservation_invariants.py` e [[ADR-090]].
