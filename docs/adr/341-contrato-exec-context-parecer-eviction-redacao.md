---
id: ADR-341
type: adr
title: "Contrato do exec context do parecer: budget, eviction por seção, blocos densos, hints, recovery e redação de identificadores"
status: Proposto
date: "2026-07-20"
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/pipeline
---

# ADR-341 — Contrato do exec context do parecer (manifest 2.0)

**Status:** Proposto · **Data:** 2026-07-20 · **Lane:** [[A37.l1]] (P0)

## Contexto

O pipeline-review de 2026-07-20 (run `6659d62c`, medição sobre o artefato E5
real) provou que o parecer LLM enxerga menos da metade do relatório, por
**duas camadas cumulativas de truncação**:

1. **Cap global:** corpo destilado de 15.560 bytes cortado em
   `max_exec_context_bytes: 8192` (`config/prompts/parecer_planejador.yaml:454`;
   corte em `backend/app/services/parecer_distiller.py:215-217`). As seções
   7–10 do manifest (`previdencia_irpf`, `riscos_protecao`, `sintese`,
   `plano_acao_atual`) ficam 100% fora; o corte cai no meio da seção 6.
2. **Truncação por bloco:** `_render_scalar` aplica `_short(300)` ao dump de
   cada bloco `format: scalar` (`parecer_distiller.py:107`); o fix R3.3 (#987)
   só wireou `_flatten_leaves` em `key_value`. 10 blocos truncam — ex.:
   `$.protecao_patrimonial` (1.050 chars) perde `apolices_vigentes` (começa no
   char 322).

Consequências observadas: o parecer sugeriu explorar dedução de previdência
com `previdencia_pgbl.limite_pgbl_anual=0` no E5, alegou "ausência de dados de
proteção" com 3 apólices extraídas, e os hints corretivos v1.7–v1.9 (que vivem
nas seções truncadas) ficaram inertes. Hints somam 4.224 bytes no corpo
pré-cap — tirá-los sozinho não basta (corpo sem hints = 11.336 > 8.192). O
tool trace mostra zero `get_e5_section` (o modelo declara ausência em vez de
recuperar). E o sanitizer não rediz identificadores estruturais
(`apolice_numero`) — vetor já existente via `get_e5_section`, que devolve a
seção inteira.

## Decisão (contrato do exec context, manifest 2.0)

1. **Budget:** `max_exec_context_bytes: 16384`. Custo estimado
   ~+US$0,01–0,02/parecer. O número é dimensionado para o corpo atual
   (15,6KB) com folga — mas o budget **não** é a garantia de completude; a
   garantia é o item 2.
2. **Eviction determinística por seção:** o manifest declara a **ordem de
   prioridade** das seções; quando o corpo excede o budget, seções inteiras de
   menor prioridade são removidas — **nunca corte no meio de seção**. Toda
   eviction emite marcador explícito nomeando as seções removidas (o marcador
   atual não diz o que caiu). É isso que fecha a causa-raiz quando o E5
   crescer.
3. **Blocos densos sem dump cru:** blocos hoje `format: scalar` com dump
   grande (`fluxo_caixa` ~15K chars, `consumo_conciente` ~17K) migram para
   `key_value`/campos declarados no manifest — quem decide o que o LLM vê é o
   manifest, não um corte de 300 chars. `_short` permanece apenas como
   safety-net com limite por bloco declarável. Teste de regressão com probes
   **field-level** nos blocos re-formatados (resumo curado é vetor novo de
   truncação silenciosa; contagem de seção não basta).
4. **Hints fora do corpo capped:** `narrative_hints` saem do corpo orçado
   (anexados após o cap, como o citation catalog, ou movidos ao system
   prompt) — guidance não compete com dado por budget.
5. **Recovery obrigatório antes de declarar ausência:** regra no system
   prompt — se o marcador de eviction estiver presente e o conceito pertencer
   a uma seção removida, chamar `get_e5_section` antes de emitir
   `campos_faltantes_pediria_se_iterasse` ou risco de "dado ausente".
   Aceite inclui probes de tool-behavior (tool-calls e `tokens_in` dentro de
   `max_tool_iterations`/`max_total_input_tokens`).
6. **Redação de identificadores estruturais no sanitizer:** campos
   identificadores **declarados por chave** (ex.:
   `apolices_vigentes[].apolice_numero`) são redigidos antes do prompt — no
   corpo destilado **e** nas respostas das tools. Sem regex genérica de
   "dígitos longos" sobre strings livres (over-redigiria CEP/valores em
   prosa). Pré-requisito de PII do restante do contrato: **aterrissa antes**
   da expansão de budget (PR-2a da [[A37.l1]]).

Sentinelas de ausência (`"N/D"`) são coordenadas com [[A37.l4]]: o distiller
não renderiza sentinela como dado presente (normalização no boundary do E5 é
o caminho preferido).

## Alternativas rejeitadas

- **Só subir o cap** (8KB→16KB): move o penhasco; sem eviction por seção, o
  próximo crescimento do E5 re-trunca silenciosamente.
- **Flatten cru dos blocos densos:** `fluxo_caixa`+`consumo_consciente`
  adicionariam ~32KB — estoura budget e custo sem curadoria.
- **Só tirar os hints do corpo:** corpo sem hints = 11.336 bytes > 8.192;
  seções 8–10 continuariam fora.
- **Regex genérica de dígitos no sanitizer:** over-redação silenciosa de
  conteúdo legítimo que o eval não flagra.

## Consequências

- `manifest_version` 2.0 + re-baseline do eval golden do parecer com **N≥3
  execuções e banda explícita** (resíduo determinístico em temperatura baixa
  já medido como material — single-run não é gate). Eval real é owner-gated
  (chave + custo); fallback: golden mockado + medição in-process do distiller.
- Conteúdo do parecer muda por design (mais contexto ⇒ texto diferente).
  Rollback: revert restaura manifest 1.9.
- Fixes v1.7–v1.9 (hint FP-04, scalar de dependentes) voltam a ter efeito.
- Bumps de manifest de outras lanes ([[A37.l7]], [[A37.l9]]) **sequenciam
  depois** desta, com versões próprias — nunca commit cruzado entre lanes.

## Critério de flip para Decidido

PR-2a + PR-2b da [[A37.l1]] mergeados com o aceite da lane batido (10/10
seções no contexto do E5 real; probes field-level verdes; identificadores
redigidos nas duas superfícies; KR-A do [[MOC-sprint-a37]] medido em run
fresco).
