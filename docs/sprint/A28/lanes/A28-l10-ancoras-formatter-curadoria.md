---
id: A28.l10
type: lane
title: "âncoras do parecer formatadas por tipo (não tudo é R$) + curadoria defensiva de pontos fortes/alertas"
sprint: A28
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: ancoras-formatter-curadoria
adrs:
  - "[[ADR-296]]"
parallel_with:
  - "[[A28.l9]]"
  - "[[A28.l11]]"
tags:
  - type/lane
  - sprint/a28
  - status/open
  - priority/p1
  - area/frontend
  - area/llm
---

# A28.l10 — `ancoras-formatter-curadoria` (Onda 2 · Should · **∥ desde o dia 1**)

## Problema

1. **Âncoras do parecer renderizam corrompidas:** o formatador de
   `valor_renderizado` ([[ADR-296]] — o finalize escreve o valor da folha)
   aplica formatação BRL a campos não-monetários. No dogfood `72883bde`:
   `prob_if_ate_idade_meta = 0.31` → **"R$ 0,31"**; `idade_meta_usada = 53` →
   **"R$ 53,00"**. Um cliente lendo "idade-meta R$ 53,00" perde a confiança no
   artefato premium exatamente onde ela mais importa.
2. **Listas de destaque sem curadoria:** `PontosFortesCard` /
   `PontosUrgentesCard` são pass-through do DTO. Resultado: alerta único e
   circular ("Score financeiro: 7.2/10 (Bom)" — alerta que não alerta), pontos
   fortes redundantes ("Reserva 32 meses" + "Colchão 27 meses" — a mesma
   cobertura dita 2× com números diferentes) e ponto forte circular ("Score
   Positivo").

## Escopo

**Formatter por tipo (backend — finalize do parecer):**

1. Dispatch de formatação por tipo de folha no `stamp_ancora_values` /
   `format_value`: probabilidade (0-1) → percentual ("31%"); idade/contagem →
   inteiro ("53 anos"); moeda → R$ (mantém `Decimal`, ADR-090). Fonte do tipo:
   catálogo de citação (a folha conhece seu campo) — não heurística sobre o
   valor.
2. Pareceres já persistidos são imutáveis (content_json — [[ADR-204]]): o fix
   vale para gerações novas; não migrar retroativo.

**Curadoria (server-side leve + defensivo na UI):**

3. Supressão de itens circulares: alerta/ponto forte cujo conteúdo referencia
   apenas o próprio score não é emitido ("Nenhum ponto urgente" honesto >
   alerta vazio).
4. Dedup semântico mínimo: reserva ≈ colchão patrimonial (mesma família de
   cobertura) emitem 1 item — resolvido a montante no E5
   (`pontos_fortes_analyzer`), com `dedupeBySemanticKey()` defensivo na UI.

## Critério de aceite

- Round-trip por tipo: fixture com âncoras de probabilidade/idade/moeda →
  `valor_renderizado` correto por tipo; **zero** campo não-monetário com
  prefixo "R$".
- Dogfood re-gerado: âncora de `prob_if_ate_idade_meta` renderiza "31%", idade
  renderiza "53 anos".
- Fixture dogfood: pontos fortes sem par redundante reserva/colchão; alertas
  sem item circular de score; card exibe empty state honesto quando não sobra
  item.
- Testes determinísticos (sem re-eval LLM — mudança é pós-geração/render);
  `pytest backend/tests -q` + `cd frontend && npm test -- --run` verdes.

## Notas

- **100% paralela à Onda 0** — opera sobre tipo de campo e curadoria, independe
  dos valores que l1/l2/l4 corrigem (product-manager, co-design 2026-07-03).
- Não confundir com [[A28.l11]] (guardrails de conteúdo/confiança do parecer);
  esta lane é forma/render/curadoria.

## Owner

Agente da lane; achado verificado por `financial-planner` (ancoras corrompidas)
e spec de curadoria por `product-designer` (revisões de 2026-07-03).
