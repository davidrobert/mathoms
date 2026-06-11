---
id: A25.l5
type: lane
title: "Data Lineage F6 — produto N1/N2: selo + popover 'Como chegamos a esse número'"
sprint: A25
plan: PLAN-data-lineage
status: shipped
priority: P1
branch_slug: dl-f6-produto-n1n2
adrs:
  - "[[ADR-279]]"
  - "[[ADR-281]]"
depends_on: []
parallel_with: ["[[A25.l1]]", "[[A25.l3]]", "[[A25.l4]]"]
tags:
  - type/lane
  - sprint/a25
  - status/shipped
  - priority/p1
  - area/data-lineage
  - area/frontend
---

# A25.l5 — `dl-f6-produto-n1n2` (F6 · 1ª superfície cliente do lineage)

> **Plano:** [[PLAN-data-lineage]] · §Arquitetura F. **INDEPENDENTE da edge table**
> (N2 é forward single-number; `LineageResolver` sobre `_lineage` inline +
> `_report_lineage` coarse bastam) — abre já. Régua: COPY_GUIDELINES §6.3 (zero
> jargão de pipeline). Substitui o tooltip da [[ADR-045]] (superseded por
> [[ADR-281]]). Precedência de corte da sprint: F7 > **F6**.

## Objetivo

N1 (selo no `<MonetaryValue/>`) + N2 (popover "Como chegamos a esse número") nos
~6 agregados de decisão, atrás de feature flag. N3 drawer NÃO é desta lane.
Teste de valor: dogfooder responde "de onde veio?" em 1 frase sem abrir nada técnico.

## Decisões de co-design (product-designer + senior-cto, 2026-06-10 — travadas)

1. **`collapsed_count` ("Conferi"):** exposto como sinal pré-computado em
   `_lineage.signals` do nó de despesa no E5 (populado quando o adapter E4/builder
   emite o `_lineage` do agregado de fluxo) — NÃO campo novo no payload E4, NÃO ambos
   (1 fonte de verdade; o view-model de `/reports/[id]/data` já serve o payload E5).
   Micro-trabalho de pipeline DESTA lane → **rebaseline não-monetário** do view-model
   snapshot (commit isolado, label `golden-rebaseline`). Log existente
   (`e4_categorizer_adapter.py:232`) permanece para observabilidade.
2. **Copy do popover (fechada):** título "Como chegamos a esse número" + subtítulo =
   `label` do campo. 4 verbos:
   `Li {n} documentos que você enviou` · `Conferi {n} lançamentos — {k} apareciam
   repetidos e contei só uma vez` (k=0 → "…, sem repetições"; nunca "0 repetidos") ·
   `Classifiquei cada lançamento por categoria` · `Calculei somando o que entra e
   subtraindo o que sai` (edge_type `passthrough` → "Confirmei o saldo direto dos
   seus extratos"; meta IF → +rodapé "Projeção — revisar anualmente."). Rodapé fixo:
   **"O número acima é o que vale. Aqui só mostro como conferi."**
3. **needs_review:** faixa âmbar no topo (`--semantic-warning-*`, ícone `clock` —
   nunca `alert-triangle`), copy "Ainda estou conferindo um detalhe deste número.
   Pode mudar levemente." Selo ganha variante âmbar (forma+cor+texto).
4. **Selo N1:** underline pontilhada **sempre visível**, 1px (1.5px em hero),
   `text-underline-offset: 3px`, cor `var(--border)` (fantasma); hover/focus eleva
   p/ `var(--brand-*)` + `cursor: help`. Só nos dígitos (não no sinal +/−).
   `aria-label` sem jargão ("Como chegamos ao patrimônio líquido"). Prop
   `provenance?: { fieldId } | undefined` — ausente ⇒ render idêntico ao atual.
5. **Popover:** **click** (não hover) + Enter/Space; `role="dialog"`
   `aria-modal="false"`; `placement bottom-start` com flip; max-width 320px; tokens
   `--surface-popover`/`popover_foreground` (light+dark, nada hardcoded); Escape
   fecha e retorna foco; `prefers-reduced-motion` desliga animação. Counts `null` →
   verbo sem número (degrada gracioso; nunca "0"); nenhum count → shell não passa
   `provenance`. Reusar primitivo de popover do design system.
6. **Export PDF (Playwright, mesma rota):** selo **suprimido** via
   `@media print { [data-provenance-seal] { text-decoration: none } }`; popover nunca
   renderiza no print (fechado por default). `data-provenance-seal` serve duplo:
   alvo do print E `data-mask-snapshot` do G-h.
7. **Lista negra no N2 (transparency backfire):** hash/member_hashes, run_id,
   document_id/data_source_id, stage/artifact_key/field/edge_type/rule_ref/inputs,
   versions, signals brutos ("ok" nunca aparece), nome de banco cru. Lista branca:
   label, contagens derivadas, needs_review→faixa. `edge_type` só como seletor
   interno da frase.
8. **Mobile `<md`:** N2 popover é desktop-first; até o N3 drawer existir, manter
   `aria-label` + bottom-sheet simples OU click no-op — decidir na implementação com
   o menor custo (acoplado à lane N3 fast-follow).

## Critério de aceite (lista completa no plano §Verificação F6)

- Feature flag registrada em `DEFAULTS` de `feature_flags_service` **no mesmo PR**.
- Flag off ⇒ relatório === atual **E** flag-ON === flag-off exceto máscara do selo (G-h).
- Snapshot isolado do affordance light+dark; selo não altera baseline/line-height;
  popover não estoura o card.
- **G-d:** snapshot textual pt-BR dos valores expostos.
- **G-g:** re-armar visual+`@critical` no filtro `lineage|report` + canary nightly verde.
- Copy gate: 4 verbos + zero `stage|pipeline|artefato|dedup|hash|run` no DOM do
  popover (assert no Vitest).
- A11y completo: teclado, Escape, foco retorna, `prefers-reduced-motion`, badge
  needs_review forma+texto+cor.
- **Teste de confiança 5s dogfood** — único teste de VALOR da F6, não pular.
- Export PDF === relatório atual no número.

## Resultado (shipped 2026-06-11, #602)

Sinais de conferência em `_lineage.signals` (E5) + flag `report_provenance_enabled`
(off) + selo N1 + `ProvenancePopover` N2 com a copy travada + supressão no print +
rebaseline não-monetário isolado. **Pendência humana:** teste de confiança 5s no
dogfood com flag-ON (roteiro no §Critério).

## Owner

Agente da lane; co-design `product-designer` + `senior-cto` (2026-06-10).
